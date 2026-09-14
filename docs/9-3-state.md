# 9-3 State：长期记忆（事实条目库）与持久化设计

> 日期：2026-09-03 · 项目：`E-commerce_agent_v1.0.2`
> 本文记录 State 模块当前的设计逻辑：长期记忆的形态、更新机制、以及会话持久化方案。

---

## 一、定位

State（`memory/state.py`）是 agent 的**长期记忆层**，解决"模型如何跨轮记住关于用户的事实"：

- 对话会无限增长、token 会爆 → 不能把全量对话喂给模型
- 用户画像（预算、偏好、排除项）必须**跨轮、跨会话地保留** → 需要一份提炼后的持久上下文

State 的产出是一段 **≤200 字的压缩文本**，在每一轮开始时注入 system prompt，让模型"带着用户的记忆"回答。

## 二、数据模型

```
MemoryState
├── text      用户事实条目库（压缩文本，LLM 维护，唯一注入 system 的长期状态）
└── turn_log  轮次记录内存日志（每轮 update 追加一份，定位问题用，不落盘）
```

**text 的物理格式：条目式库**，每行一条独立事实/约束：

```text
- 想买：笔记本电脑
- 预算：≤5000元
- 排除：联想
- 关注：有现货
```

每行是一个最小独立单位，互不粘连——这样增删改查可以精确定位到行，改口不会残留旧值。

## 三、生命周期（谁在什么时候调用）

**写入（每轮对话收尾）**，`agent.py`：

```
run() 确定最终 reply
  → _update_state(reply, user_input, tool_events)
      → build_turn_record(...)            组装轮次记录
      → state.update(turn_record)          ① 写日志 ② LLM 增删改 ③ 更新 text
      → save_snapshot(state.text, 最近窗口) 落盘
```

**读取（每轮对话开始）**，`agent.py run()`：

```
state.to_text()
  → "当前已知用户信息：\n{text}\n"
  → 拼进 system prompt（有内容才拼）
```

**恢复（agent 实例化时）**：

```
EcommerceAgent(session_id)  →  _restore_snapshot()
  → load_snapshot 读回 text + 最近消息
  → state.from_dict 恢复 text，history 恢复最近窗口
```

## 四、update() 内部流程

`state.update(turn_record)` 做三件事：

1. **写内存日志**：`turn_log.append(turn_record)`
2. **组装输入**：`_build_input(turn_record)`
3. **一次 LLM 调用**：调专用 prompt（`memory/state_prompt.py`），用返回更新 text，`_clip` 长度兜底

### _build_input 组装什么

```
当前用户条目库：{旧 text}                 ← 已有的库（首次为空则无此段）
本轮事件：
  用户：{user_input}
  AI：{ai_reply}                         ← 增删改的主要依据
本轮工具调用：
  工具：{tool}                            ← 本轮 AI 做了什么动作
  参数：{args}
  执行结果（result）：{真实数据}            ← 真实依据（groundedness 锚点）
```

### prompt 的任务规则（state_prompt.py）

把旧库当成"待维护的文本库"，对照本轮内容**逐条增删改**：

| 动作 | 触发 | 处理 |
|---|---|---|
| 保留 | 信息未变化 | 对应行原样抄回 |
| 改 | 用户改口（预算/品类/偏好变更） | 用新值替换那一行，**不残留旧行** |
| 删 | 用户明确放弃某项约束 | 删除对应行 |
| 增 | 本轮出现新需求/新约束 | 新增一行 |
| 排除 | 用户说"不要/排除/除了/别推荐" | 记为排除条目（与正向偏好同等重要） |

关键原则：
- **改口是最高优先级**：必须覆盖旧值，不得保留互相矛盾的旧条目
- **result 是真实锚点**：能佐证的约束放心写入；与对话内容矛盾时**以真实结果为准**
- 只记用户侧的**需求/偏好/预算/约束/决策进度**；不记 AI 回复里的商品介绍与参数（对话记录里已有）

### 输出约束

- 每行一条，换行分隔，格式统一 `- 内容`，无编号无解释
- ≤200 字；**装不下时按重要性淘汰或合并低优条目**，不拦腰截断某一行
- 本轮无新信息也要完整保留原有条目，不清空

## 五、为什么每轮都跑

- 改口、排除项常出现在**纯对话**里（无工具轮），漏提炼画像就会失准
- 所以 update 不做触发门控——每轮对话结束都跑一次，保证画像实时

## 六、不依赖 reasoning（成本考量）

State 更新**不读模型思考内容（reasoning）**：
- reasoning 文本可能很长，喂进每次 state 更新会白白烧输入 token
- 增删改的判定依据是"用户原话 + AI 回复 + 工具 result"，reasoning 只是锦上添花的诊断线索，非依赖
- 因此模型开不开思考模式，State 都能正常工作

## 七、持久化设计（memory/persist.py）

**原则：只落"有界数据"，无界数据（日志/全量对话）一律不落盘。**

每个会话一个文件 `sessions/<session_id>.json`，内容只有两类：

```
{
  "state_text": "- 想买：笔记本电脑\n- 预算：≤5000元...",   ← 长期记忆（≤200字）
  "messages": [ 最近 ≤10 条 user/assistant 消息 ]          ← 短期窗口
}
```

- `save_snapshot(session_id, state_text, recent_messages)`：覆盖写
- `load_snapshot(session_id)`：读回 `(text, messages)`，无文件/损坏则返回 `(None, None)` 静默降级为新会话
- 调用点：`_update_state` 末尾，用 `state.text` + `history.get_window(WINDOW=10)` 落盘

**为什么这样设计**：
- 续聊真正需要的信息只有两样：长期画像（text）+ 最近对话（窗口），就这么点
- `turn_log` / `tool_events` 是审计性质、无界增长，恢复续聊没人消费它们 → 不落盘，进程退出即丢
- 会话隔离 = session_id 隔离：同一 id 重启续聊，不同 id 互不串记忆

## 八、长度兜底与未来

- `_clip`：`text.strip()[:MAX_STATE_CHARS]`（MAX=200），纯字符截断，仅作最后防线
- 200 字装不下（溢出）的处理属于**向量记忆 / 语义记忆**层的事：提炼出的条目超出压缩库容量后，按相关性向量化召回。当前阶段先不实现，`_clip` 的智能截断（保头尾、整行淘汰）也一并留到那个环节统一设计

## 九、示例：一轮对话的完整链路

```
用户：预算5000以内，想要笔记本，不要联想
  ↓ run() 主循环（可能多轮工具调用）
  ↓ AI 最终回复：为您推荐...
  ↓ _update_state
      ↓ build_turn_record
      ↓ state.update：
          输入 = 旧库(若有) + 本轮对话 + search_products 工具调用 + result
          LLM 按规则 → 输出新库：
            - 想买：笔记本电脑
            - 预算：≤5000元
            - 排除：联想
          text ← 新库（_clip 兜底）
      ↓ save_snapshot：text + 最近10条 写入 sessions/default.json

下一轮"那换个3000的"
  ↓ state.to_text() 把旧库拼进 system
  ↓ LLM 带着"预算≤5000、排除联想"回答
  ↓ update 时识别改口 → 预算行改为 ≤3000，删除 5000 旧行
```
