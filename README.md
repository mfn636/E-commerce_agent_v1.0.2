# 电商智能客服 Agent

> 一个**不依赖 LangChain 等框架**、从零手写核心循环的电商客服 Agent。支持多轮对话、工具调用、回复自检与长期记忆。

## ✨ 特性

- **手写 ReAct 循环**：基于 Function Calling 自主实现 `tool_calls` 解析 → 工具执行 → `tool_call_id` 回填 → 多轮迭代，支持单轮并发多工具、最大轮数 / 空响应双重终止兜底。
- **Reflection 回复自检**：回复发出前另起一次 LLM 调用，以「用户原话 + 工具真实结果 + 草稿」为锚做完整性 / 真实性 / 规范性三维校验，三态（accept / revise / continue_tool）驱动回环补调工具。
- **双层记忆 + 有界落盘**：短期滑动窗口 + 长期「用户事实条目库」（LLM 每轮增删改、≤200 字、注入 system）；会话快照只落有界数据，进程重启可恢复画像与最近对话。
- **pydantic 驱动工具契约**：用 pydantic 模型定义工具入参，`model_json_schema()` 自动生成 Function Schema，并用同一份模型做参数校验（枚举 / 范围 / 正则 / 长度），单一真相来源。
- **端口-适配器解耦**：抽象 `ToolProvider` 端口 + 本地适配器，核心依赖注入；LLM 层统一 OpenAI 兼容封装，可在不同模型服务间无缝切换。
- **健壮性**：工具幻觉名 / 参数非法 / 执行异常统一降级为可读错误回填，由模型自我纠正；记忆更新 / 落盘失败不影响用户回复。

## 🏗 架构

内部 agent 系统只依赖「契约端口」，外部通过适配器接入：

```
              ┌─────────────────────────────────────────┐
              │  agent/（内部系统，纯净）                 │
              │  core（循环 / 自检 / 压缩） + memory（记忆）│
              └───────────────┬─────────────────────────┘
                              │ 端口：Protocol（行为）+ pydantic（数据）
        ┌─────────────────────┼──────────────────────┬───────────────┐
        ▼                     ▼                      ▼               ▼
   providers/            contract/               domain/          llm/
   工具执行侧            工具契约（数据侧）        领域模型 + 数据    模型客户端
```

## 📁 目录结构

```
agent/                 内部 agent 系统
  core/                  核心循环
    loop.py                EcommerceAgent 主循环
    reflection.py          Reflection 自检
    compress.py            工具结果压缩
  memory/                记忆
    history.py             短期对话窗口
    state.py               长期事实条目库
    state_prompt.py        State 更新 Prompt
    turn.py                轮次记录
    persist.py             会话快照落盘
contract/              工具契约（数据侧）
  tool.py                  注册表 + schema 生成 + validate_args
  tool_args.py             pydantic 入参模型 + 约束
providers/             工具契约（执行侧）
  base.py                  ToolProvider 端口（Protocol）
  local.py                 LocalToolProvider 适配器
  tools/                   本地工具实现（商品搜索 / 库存 / FAQ）
domain/                领域模型 + 数据源
  models/                  Product / Inventory / Faq
  loader.py                JSON 加载
  data/                    静态数据（*.json）
llm/                   模型层
  client.py                OpenAI 兼容客户端
  prompt.py                基座 Prompt
  reflection_prompt.py     自检 Prompt
main.py                CLI 入口
```

## 🚀 快速开始

### 环境
- Python 3.10+
- 一个 OpenAI 兼容的大模型 API（默认对接 DeepSeek）

### 安装
```bash
pip install -r requirements.txt
```

### 配置
在项目根目录创建 `.env`：
```
DEEPSEEK_API_KEY=你的密钥
# 可选：覆盖默认模型
# LLM_MODEL=deepseek-v4-flash
```

### 运行
```bash
python main.py
```

## 🧩 设计要点

- **为什么手写**：框架把 tool_call_id 回填、循环终止、记忆裁剪都封成黑盒；手写才能真正理解并掌控每个取舍。
- **记忆的边界**：记忆应是有界的「提炼结果」，无界的对话属于「日志」，两者不混——会话快照只落画像 + 最近窗口。
- **单一真相来源**：工具 schema 与参数校验同源于一份 pydantic 模型，改一处两边同步。
- **可插拔**：RAG / MCP 等都可挂在工具契约两侧，核心无需改动。

## 🗺 路线图

- [ ] SKILL 技能系统（按需加载指令胶囊）
- [ ] 多 Agent 编排（Supervisor 路由）
- [ ] MCP 工具接入
- [ ] RAG 语义检索
- [ ] 评测体系 / 服务化

## ⚠️ 说明

本项目为个人学习与实践项目，数据为虚构的静态示例数据，不涉及任何真实业务。
