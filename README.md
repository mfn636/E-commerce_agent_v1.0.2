# 电商智能客服 Agent

> 一个**不依赖 LangChain 等框架**、从零手写核心循环的电商客服 Agent。支持多轮对话、工具调用、回复自检、长期记忆与 RAG 知识检索。

## ✨ 特性

- **ReAct 循环**：基于 Function Calling 自主实现 `tool_calls` 解析 → 工具执行 → `tool_call_id` 回填 → 多轮迭代，支持单轮并发多工具、最大轮数 / 空响应双重终止兜底。
- **Reflection 回复自检**：回复发出前另起一次 LLM 调用，以「用户原话 + 工具真实结果 + 草稿」为锚做完整性 / 真实性 / 规范性三维校验，三态（accept / revise / continue_tool）驱动回环补调工具。
- **双层记忆 + 有界落盘**：短期滑动窗口 + 长期「用户事实条目库」（LLM 每轮增删改、≤200 字、注入 system）；会话快照只落有界数据，进程重启可恢复画像与最近对话。
- **pydantic 驱动工具契约**：用 pydantic 模型定义工具入参，`model_json_schema()` 自动生成 Function Schema，并用同一份模型做参数校验（枚举 / 范围 / 正则 / 长度），单一真相来源。
- **端口-适配器解耦**：抽象 `ToolProvider` 端口 + 本地适配器，核心依赖注入；LLM 层统一 OpenAI 兼容封装，可在不同模型服务间无缝切换。
- **健壮性**：工具幻觉名 / 参数非法 / 执行异常统一降级为可读错误回填，由模型自我纠正；记忆更新 / 落盘失败不影响用户回复。
- **商品详情工具**：搜索返回精简信息，`get_product_detail` 按需拉取单个商品的完整硬件参数（CPU / 内存 / 存储 / 屏幕…），兼顾 token 与信息完整。
- **RAG 知识检索**：文档分块 → bge-m3 嵌入 → Qdrant 向量库 → 语义检索（相似度阈值 + 元数据过滤）；新增 `search_knowledge` 工具，FAQ / 商品工具升级为语义检索（保留关键词兜底）。
- **可观测性**：记录每次 LLM 调用的 token（含缓存命中）与耗时；每轮返回 `TurnResult`，CLI / Web 实时展示本轮成本与延迟。
- **评测体系**：`eval/` 提供黄金用例 + 规则断言 + LLM-judge 双通道（端到端），以及检索 hit rate / recall@k（RAG）——一键输出报告。
- **Web 调试台**：FastAPI + 单页聊天界面，可视化对话、用户画像与本轮用量。

## 🏗 架构

内部 agent 系统只依赖「契约端口」，外部通过适配器接入：

```
              ┌─────────────────────────────────────────┐
              │  agent/（内部系统）                      │
              │  core（循环/自检/压缩）+ memory          │
              └───────────────┬─────────────────────────┘
                              │ 端口：Protocol（行为）+ pydantic（数据）
        ┌─────────────────────┼──────────────────────┬───────────────┐
        ▼                     ▼                      ▼               ▼
   providers/            contract/               domain/          llm/
   工具执行侧            工具契约（数据侧）        领域模型 + 数据    模型客户端
        │
        └──► rag/  向量检索（挂在工具契约后侧：分块 / 嵌入 / 向量库 / 检索）
```

## 📁 目录结构

```
agent/                 内部 agent 系统
  core/                  核心循环
    loop.py                EcommerceAgent 主循环
    reflection.py          Reflection 自检
    compress.py            工具结果压缩
    types.py               TurnResult（回复 + 工具轨迹 + 用量）
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
  tools/                   本地工具实现（商品搜索 / 详情 / 库存 / FAQ / 知识检索）
domain/                领域模型 + 数据源
  models/                  Product / Inventory / Faq / Knowledge
  loader.py                JSON 加载
  data/                    静态数据（*.json，含 guides）
rag/                   RAG 检索（挂在工具契约后侧）
  chunker.py               文档 → 带元数据的 chunk
  embedder.py              Ollama bge-m3 嵌入
  store.py                 Qdrant 本地向量库（幂等 upsert）
  ingest.py                JSON → 向量库（数据管道，可重复跑）
  retriever.py             query → top-k + 阈值 + 元数据过滤
llm/                   模型层
  client.py                OpenAI 兼容客户端（用量/耗时埋点 + 思考开关）
  prompt.py                基座 Prompt
  reflection_prompt.py     自检 Prompt
web/                   Web 调试台
  server.py                FastAPI：/chat、/reset
  index.html               单页聊天界面
eval/                  评测体系
  cases.py / checker.py / judge.py / runner.py    端到端「规则 + LLM-judge」双通道
  retrieval_runner.py      检索 hit rate / recall@k
scripts/               数据生成
  gen_corpus.py            用 LLM 生成 guides / FAQ / 商品描述 / 检索黄金集
main.py                CLI 入口
```

## 🚀 快速开始

### 环境
- Python 3.10+
- 一个 OpenAI 兼容的大模型 API（默认对接 DeepSeek）
- RAG 检索需本地 [Ollama](https://ollama.com/) + `bge-m3` 嵌入模型

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

### 初始化 RAG 向量库（首次 / 数据更新后）
```bash
ollama pull bge-m3        # 拉取嵌入模型（约 1.2GB）
python -m rag.ingest      # JSON → 向量库（幂等，可重复跑）
```

### 运行（CLI）
```bash
python main.py
```

### 运行（Web 调试台）
```bash
python -m uvicorn web.server:app --port 8000
# 浏览器打开 http://127.0.0.1:8000
```

### 运行（评测）
```bash
python -m eval.runner              # 端到端：各能力域通过率 + 成本
python -m eval.retrieval_runner    # 检索：hit rate / recall@k
```

## 🧩 设计要点

- **为什么不用框架**：框架把 tool_call_id 回填、循环终止、记忆裁剪都封成黑盒；手写才能真正理解并掌控每个取舍。
- **记忆的边界**：记忆应是有界的「提炼结果」，无界的对话属于「日志」，两者不混——会话快照只落画像 + 最近窗口。
- **单一真相来源**：工具 schema 与参数校验同源于一份 pydantic 模型，改一处两边同步。
- **可插拔**：RAG / MCP 等都可挂在工具契约两侧，核心无需改动。

## 📊 可观测性与评测

- **成本 / 时延**：每次 LLM 调用的 token（含缓存命中）与耗时被记录；`TurnResult.usage` 给出本轮聚合（主循环 + 自检 + 记忆），CLI / Web 直接展示。
- **端到端准确度**：`eval/` 以「规则断言 + LLM-judge」双通道，按能力域（工具路由 / 售后问答 / 多轮记忆 / 越界拒绝 / 防幻觉）输出通过率与成本。
- **检索质量（RAG）**：`eval/retrieval_runner.py` 用黄金查询集评测 hit rate / recall@k。

```bash
python -m eval.runner              # 端到端
python -m eval.retrieval_runner    # 检索
```

> 示例：端到端 8 用例合计 **7/8**（38 次调用 / 42k tokens / 58s）；检索 110 条黄金查询 **hit@1 83.6% · hit@3 94.5% · hit@5 97.3%**。

## 🗺 路线图

- [x] RAG 语义检索（分块 → bge-m3 嵌入 → Qdrant → 检索）
- [x] 评测体系（端到端双通道 + 检索 hit rate / recall@k）
- [x] 服务化（Web 调试台 + 用量可观测）
- [ ] 混合检索 / reranker
- [ ] SKILL 技能系统（按需加载指令胶囊）
- [ ] 多 Agent 编排（Supervisor 路由）
- [ ] MCP 工具接入

## ⚠️ 说明

本项目为个人学习与实践项目，数据为虚构的示例数据（AI 生成），不涉及任何真实业务，持续更新进度。
