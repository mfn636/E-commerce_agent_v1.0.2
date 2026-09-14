"""
agent/core/reflection.py

Reflection 自检逻辑：接收「草稿 + 用户原话 + 工具事件」，另起一次 LLM 调用判定。
agent 只负责触发与消费结果，不关心具体怎么检查。
"""

import json

from llm.reflection_prompt import get_reflection_prompt


def make_default_verdict():
    """解析失败 / 未触发时的兜底判定：直接采用草稿，不打断主流程。"""
    return {"action": "accept", "issues": [], "revised_reply": None}


class Reflector:

    def __init__(self, llm):
        self.llm = llm

    def reflect(self, draft, user_input, tool_events):
        """
        对草稿做一次自检（另起一次 LLM 调用）。

        返回解析后的 JSON 判定：
            {"action": "accept"|"revise"|"continue_tool", "issues": [], "revised_reply": ...}
        调用失败 / 坏 JSON -> 兜底为 accept，不打断。
        """
        # 组装出 Reflection 自检所需的输入
        print("[Reflection] 触发自检...")
        input_text = self._build_input(user_input, tool_events, draft)
        try:
            # 组装 Reflection 要发送的 msg
            response = self.llm.chat(
                messages=[
                    {"role": "system", "content": get_reflection_prompt()},
                    {"role": "user", "content": input_text},
                ],
                response_format={"type": "json_object"},
            )
            # 得到自检结果
            verdict = self._parse_verdict(response.content)
        except Exception:
            verdict = make_default_verdict()
        print(f"[Reflection] action={verdict['action']} issues={verdict['issues']}")
        return verdict

    def _build_input(self, user_input, tool_events, draft):
        """组装自检输入：用户原话 + 工具调用及真实结果 + 草稿回复。"""
        lines = [f"用户原话：{user_input}", "", "本轮工具调用与结果："]
        for event in tool_events:
            intent = event.get("intent") or {}
            lines.append(f"- 工具：{intent.get('tool')}，参数：{intent.get('args')}")
            lines.append(f"  结果：{event.get('result')}")
        lines.append("")
        lines.append(f"草稿回复：{draft}")
        return "\n".join(lines)

    def _parse_verdict(self, content):
        """Reflection 返回值的解析兜底：坏 JSON / 非法 action -> accept。"""
        if not content or not content.strip():
            return make_default_verdict()
        try:
            obj = json.loads(content)
        except json.JSONDecodeError:
            return make_default_verdict()
        if not isinstance(obj, dict):
            return make_default_verdict()
        action = obj.get("action")
        if action not in ("accept", "revise", "continue_tool"):
            action = "accept"
        return {
            "action": action,
            "issues": obj.get("issues") or [],
            "revised_reply": obj.get("revised_reply"),
        }