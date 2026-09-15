import json

from providers.local import LocalToolProvider
from llm.client import LLMClient
from llm.prompt import get_system_prompt
from agent.memory.history import ConversationHistory

from agent.memory.state import MemoryState
from agent.memory.turn import build_turn_record
from agent.memory.persist import save_snapshot, load_snapshot

from agent.core.reflection import Reflector, make_default_verdict
from agent.core.compress import compress_tool_result
from agent.core.types import TurnResult


class EcommerceAgent:

    # 发送历史时只带最近多少条（约 3 轮对话）
    WINDOW = 10
    # ReAct 循环最大轮数（终止条件①）
    MAX_TURNS = 5
    # Reflection 仅在本轮调过工具时触发（闲聊/纯问答不触发，省 token）
    REFLECT_ON_TOOL_USE = True

    def __init__(self, session_id: str = "default", tools=None, llm=None):
        self.session_id = session_id
        # 依赖注入：默认用本地适配器 / 真实 LLM，可替换（MCP / 假 LLM 测试）
        self.llm = llm or LLMClient()
        self.tools = tools or LocalToolProvider()
        # Reflection 自检器（独立于主循环，agent 只负责触发与消费结果）
        self.reflector = Reflector(self.llm)
        # 全量对话历史（user/assistant 最终对话，不含工具往返）
        self.history = ConversationHistory()
        # 状态提炼层（叙事 + 轮次日志）
        self.state = MemoryState(self.llm)
        self.round_no = 0
        # 恢复既有会话快照（State 叙事 + 最近窗口）
        self._restore_snapshot()

    def _restore_snapshot(self):
        """加载会话快照：恢复 State 叙事与最近对话；无快照/损坏则静默降级。"""
        state_text, messages = load_snapshot(self.session_id)
        if state_text is None or messages is None:
            return
        if messages:
            self.history.from_dict(messages)
        if state_text:
            self.state.from_dict({"text": state_text, "turn_log": []})

    def run(self, user_input):

        self.history.add_user(user_input)

        system_prompt = get_system_prompt()
        # 初始化启动这个state实例
        state_text = self.state.to_text()
        # 如果非空，拼入上下文
        if state_text:
            system_prompt = system_prompt + "\n\n" + state_text

        messages = [
            {"role": "system", "content": system_prompt},
            *self.history.get_window(self.WINDOW),
        ]

        # 本轮对用户可见的回复（可能多条：中间话术 + 最终回复）
        visible = []
        tool_events = []
        # 本轮用量的起点（聚合主循环 + 自检 + 记忆的所有 LLM 调用）
        usage_mark = len(getattr(self.llm, "usage_log", []))
        # 最大轮次防护
        turn = 0
        # 每轮跑的逻辑流程
        while True:
            if turn >= self.MAX_TURNS:
                break
            turn += 1

            # ---- ReAct: Thought（模型思考：调用什么工具 / 填什么参数）----
            print(f"\n[ReAct:Thought] turn={turn}")
            response = self.llm.chat(messages=messages, tools=self.tools.list_tools())
            print(f"\n[ReAct:Thought] content={getattr(response, 'reasoning_content', '')}")
            # 如果模型调工具
            if response.tool_calls:
                # 把模型的"工具调用意图"原样回填（保留 content，不丢 Thought）
                self._append_tool_calls(messages, response)
                # 伴随工具调用的 content → 对用户可见的中间话术
                if response.content and response.content.strip():
                    visible.append(response.content)

                for tc in response.tool_calls:
                    args = self._parse_arguments(tc.function.arguments)
                    # ---- ReAct: Action（agent 执行工具）----
                    print(f"[ReAct:Action] {tc.function.name} {json.dumps(args, ensure_ascii=False)}")
                    # 执行并序列化（永不抛异常：失败降级为错误 JSON）
                    result_json = self._safe_call_tool(tc.function.name, args)

                    tool_events.append(self._build_event(tc, args, result_json, response))
                    # ---- ReAct: Observation（结果回填，供下一轮参考）----
                    messages.append(self._tool_message(tc, result_json))
                    print(f"[ReAct:Observation] 已回填 {tc.function.name} 结果")

                continue

            # 答案出口，模型最终发出去的话
            elif response.content and response.content.strip():
                draft = response.content
                # ---- Answer 前先过 Reflection 自检 ----
                if self.REFLECT_ON_TOOL_USE and tool_events and turn < self.MAX_TURNS:
                    verdict = self.reflector.reflect(draft, user_input, tool_events)
                else:
                    verdict = make_default_verdict()
                action = verdict.get("action", "accept")
                issues = verdict.get("issues") or []
                # 如果继续调用工具并且有问题
                if action == "continue_tool" and issues:
                    feedback = (
                        "你的上一条回复未通过自检，缺失信息如下，请据此补调工具后再回答：\n"
                        + "\n".join(f"- {i}" for i in issues)
                    )
                    # 先把被打回的草稿写回历史（给模型看），再由 user 反馈补充
                    messages.append({"role": "assistant", "content": draft})
                    messages.append({"role": "user", "content": feedback})
                    print("[Reflection:continue_tool] 带反馈回环")
                    continue
                # accept就直接回复
                reply = verdict.get("revised_reply") or draft
                print(f"[Answer] {reply}")
                # 加入历史对话
                self.history.add_assistant(reply)
                # 更新state
                self._update_state(reply, user_input, tool_events)
                visible.append(reply)
                return self._make_result(visible, tool_events, usage_mark)
            else:
                # 终止条件②：模型未调工具也未输出内容，不再循环
                break

        # 循环退出：超轮数 → 无工具收尾作答；空响应 → 兜底话术
        reply = self._finalize_answer(messages) if turn >= self.MAX_TURNS else None
        if not reply:
            reply = "抱歉，暂时无法处理您的问题，请稍后再试。"
        print(f"[Answer] {reply}")
        self.history.add_assistant(reply)
        self._update_state(reply, user_input, tool_events)
        visible.append(reply)

        return self._make_result(visible, tool_events, usage_mark)

    # ---------- ReAct 具名状态方法 ----------

    def _append_tool_calls(self, messages, response):
        """将模型返回的 tool_calls 转成 assistant 消息加入对话（有 content 则一并保留）。"""
        tool_call_dicts = []
        for tc in response.tool_calls:
            tool_call_dicts.append({
                "id": tc.id,
                "type": tc.type,
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments
                }
            })
        msg = {"role": "assistant", "tool_calls": tool_call_dicts}
        if response.content and response.content.strip():
            msg["content"] = response.content
        messages.append(msg)

    def _parse_arguments(self, args_str):
        """arguments 是 JSON 字符串：解析兜底，坏 JSON / 非 dict 一律返回 {}。"""
        try:
            args = json.loads(args_str) if args_str else {}
        except json.JSONDecodeError:
            args = {}
        return args if isinstance(args, dict) else {}

    def _safe_call_tool(self, name, args):
        """调用工具并序列化结果；任何失败都降级为错误 JSON，绝不抛异常。"""
        try:
            result = self.tools.call(name, args)
            return compress_tool_result(name, result)
        except Exception as e:
            return json.dumps({"error": f"工具调用失败: {e}"}, ensure_ascii=False)

    def _finalize_answer(self, messages):
        """超轮数收尾：禁用工具，强制模型基于已有结果作答；失败返回 None 走兜底。"""
        try:
            resp = self.llm.chat(messages=messages, tools=None)
            return (resp.content or "").strip() or None
        except Exception:
            return None

    def _tool_message(self, tc, result_json):
        """组装 role=tool 消息，tool_call_id 与 assistant 的 tool_calls 一一对应。"""
        return {
            "role": "tool",
            "tool_call_id": tc.id,
            "content": result_json,
        }

    def _build_event(self, tc, args, result_json, response):
        """组装轮次日志事件（intent 含 reasoning + 已序列化 result），供 state 更新。"""
        return {
            "intent": {
                "tool": tc.function.name,
                "args": args,
                "reasoning": getattr(response, "reasoning_content", None) or "",
            },
            "result": result_json,
        }

    # ---------- 指标 ----------

    def _collect_usage(self, mark):
        """聚合本轮（主循环 + 自检 + 记忆）所有 LLM 调用的用量/耗时。"""
        entries = getattr(self.llm, "usage_log", [])[mark:]
        return {
            "llm_calls": len(entries),
            "prompt_tokens": sum(e["prompt_tokens"] for e in entries),
            "completion_tokens": sum(e["completion_tokens"] for e in entries),
            "total_tokens": sum(e["total_tokens"] for e in entries),
            "cached_tokens": sum(e["cached_tokens"] for e in entries),
            "latency_ms": round(sum(e["latency_ms"] for e in entries), 1),
        }

    def _make_result(self, visible, tool_events, usage_mark):
        """组装 TurnResult：可见回复 + 工具轨迹 + 用量。"""
        tool_calls = [
            {"name": e["intent"]["tool"], "args": e["intent"]["args"]}
            for e in tool_events
        ]
        return TurnResult(
            replies=list(visible),
            tool_calls=tool_calls,
            usage=self._collect_usage(usage_mark),
        )

    # ---------- 记忆 / 会话 ----------

    def _update_state(self, reply, user_input, tool_events):
        """组装轮次记录、更新 State、落盘快照。内部失败不影响已确定的回复。"""
        self.round_no += 1
        turn_record = build_turn_record(
            round_no=self.round_no,
            user_input=user_input,
            ai_reply=reply,
            tool_events=tool_events,
        )
        try:
            self.state.update(turn_record)
            # 落盘：State 叙事 + 最近窗口（有界，不存无界审计）
            save_snapshot(self.session_id, self.state.text, self.history.get_window(self.WINDOW))
        except Exception as e:
            print(f"[State] 更新/落盘失败，已跳过：{e}")
