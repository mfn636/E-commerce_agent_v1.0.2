# P1 完成笔记：ReAct 显式化 + Reflection 自检体系

> 日期：2026-08-16 · 项目：`E-commerce_agent_v1.0.2`
> 目的：P1 落地记录 + 面试可回看的核心洞察。

---

## 一、P1 做了什么（代码层面）

**改动文件**
- `workflow/agent.py`：ReAct 显式化 + 阶段调试标记 + 自检触发门控（只负责"何时查、怎么用结果"）
- `llm/reflection_prompt.py`：Reflection 专用 prompt（新增）
- `workflow/reflection.py`：`Reflector` 类 + `make_default_verdict()`（自检的"执行者"——负责"怎么查"）

**ReAct 显式化**
- 循环拆成具名状态方法：`_parse_arguments` / `_append_tool_calls` / `_tool_message` / `_build_event`
- 每轮标注 `[ReAct:Thought] → [ReAct:Action] → [ReAct:Observation] → [Answer]`
- 支持一次响应并发多个 tool_calls；多步任务（search→inventory）靠 ReAct 天然多往返完成

**Reflection 自检（关键设计）**
- 触发条件：本轮调过工具 **且** 轮次未满（闲聊/纯问答不触发，省 token）
- 独立一次 LLM 调用（一次生成内不能回头，自检必须另起调用）
- 输出 `response_format=json_object` 强制 JSON：
  ```json
  { "action": "accept" | "revise" | "continue_tool",
    "issues": [...], "revised_reply": "..." | null }
  ```
  - `accept` → 草稿直接返回
  - `revise` → 用 `revised_reply`
  - `continue_tool` → issues 作为反馈消息追加，回环补调工具
- 坏 JSON / 非法 action → 兜底为 `accept`，不打断主流程

**Reflection 代码结构（职责一拆二，2026-08-16 重构）**
- `agent.py` 只留调用点（触发门控 + 消费 verdict）：
  ```python
  if self.REFLECT_ON_TOOL_USE and tool_events and turn < self.MAX_TURNS:
      verdict = self.reflector.reflect(draft, user_input, tool_events)
  else:
      verdict = make_default_verdict()
  ```
- `workflow/reflection.py` 承载全部检查逻辑：`Reflector.reflect()`（组装输入 → 另起 LLM 调用 → 解析判定 → 异常兜底）、`_build_input()`（原话+工具结果+草稿）、`_parse_verdict()`（坏 JSON/非法 action → accept）
- 解耦收益：agent → reflector 单向依赖，reflection 不 import agent；想改判定规则只动 `reflection.py`；`Reflector` 可单独复用/测试
- `continue_tool` 的反馈消息拼装属于循环逻辑，留在 `run()`（agent.py:94-101）
- 验证：假 LLM 冒烟测试三场景全过（工具→自检 accept / 闲聊不触发 / continue_tool 回环补调后再 accept），行为零变化

**不做（按取舍砍掉）**
- Plan-and-Execute：电商 query 模糊（"推荐个性价比高的"），P-E 刚性计划不适配；ReAct 边走边看 + Reflection 收尾足够
- 健壮性兜底、冒烟测试、多会话：均按需求移除

**demo 验证**
- 复合需求"5000 内 Orion 本 + 有货" → search → inventory×2 → REFLECT(accept) → 正确回复缺货
- 闲聊"你好" → 无工具无 REFLECT（门控生效）
- 单需求 → search → REFLECT(accept) → 带价格列表回复

---

## 二、核心洞察：同一个"用真实数据做锚"原则，三层把关

**Groundness / Consistency 校验**——把模型生成的文本，用真实数据（工具 result / 黄金答案）做锚点拿回去自审，防编造与残留矛盾。贯穿三层：

| 层 | 把关位置 | 被检查对象 | 防止什么 |
|---|---|---|---|
| **State 自检**（`memory/state_prompt.py`） | 写持久记忆前 | 更新后的**事实条目库**（用户画像） | AI 的错误理解进长期上下文，污染后续所有对话 |
| **Reflection 自检**（`llm/reflection_prompt.py`） | 发回复前 | 草稿回复 | 回复漏点/编造，误导用户当前轮 |
| **评测断言**（T8，规划中） | 上线/回归前 | 完整回答 | 防回归退化，可度量 |

## 三、State 与 Reflection 的分工边界

> **State 守"记忆入口"（什么该进长期记忆，影响未来）；Reflection 守"回复出口"（这条回复能不能发，影响当下）。**

| | State 自检 | Reflection 自检 |
|---|---|---|
| **判定依据** | 用户原话（增删改依据）+ 真实 result（锚） | 用户原话 + 真实 result + 草稿 |
| **检查对象** | 更新后的条目库（预算/品类/排除项是否记对） | 草稿是否覆盖 query 每条诉求、是否有 result 之外的事实 |
| **产出** | 下一版条目库（注入下轮 system） | `{action, issues, revised_reply}` |
| **防什么** | 理解错 → 记忆被污染（影响后续所有轮） | 漏点 / 编造 → 回复不可信（影响本轮） |

**设计推论**：两者如今都直接锚定「用户原话 + 真实 result」，不依赖模型思考（reasoning）。差异不在约束源，而在**防线位置**——State 决定"什么写进长期记忆"，Reflection 决定"什么发给用户"，一个持久、一个即时，职责不重叠。

## 四、State 更新的当前实现（事实条目库）

`state.text` 是一个 ≤200 字的**用户事实条目库**，每行一条独立事实/约束：

```text
- 想买：笔记本电脑
- 预算：≤5000元
- 排除：联想
```

每轮对话结束单独调一次 LLM，输入 = 旧库 + 本轮对话（用户原话 / AI 回复）+ 工具调用（工具/参数/result），对旧库做**增 / 删 / 改**：
- **改**：用户改口 → 替换对应行，不残留旧值
- **删**：用户放弃某项 → 删行
- **增**：新需求/新约束 → 增行
- 否定表达（"不要/排除"）→ 记排除条目
- result 佐证可写入，与对话矛盾以 result 为准

**不依赖 reasoning**：判定依据是用户原话 + AI 回复 + 工具 result，不读模型思考内容——省成本，模型开不开思考模式都不影响。只落有界数据（条目库 + 最近窗口），溢出处理留待向量记忆层。详见 `docs/9-3-state.md`。

## 五、面试话术（2 分钟版）

> "我的 agent 手写了 function-calling 循环，本质是 ReAct：模型输出 tool_calls（思考+动作），我执行、用 tool_call_id 回填、再送回去，直到出 content；多步任务靠天然多往返完成。出回复前我加了一道 Reflection 自检——另起一次调用，拿工具真实结果当锚，判完整性/真实性/规范性，不合格就带着问题回环补调工具。电商 query 模糊，我没用 Plan-and-Execute（刚性计划不适配），ReAct + Reflection 的组合就够了。
> 更深一层：'用真实数据做锚'的自检我做了三层——写长期记忆前用 result 校验事实条目库（防理解错进记忆）、发回复前用 result 校验草稿（防编造）、评测时用黄金答案断言（防回归）。State 守记忆入口、Reflection 守回复出口，一个持久、一个即时，职责不重叠。"
