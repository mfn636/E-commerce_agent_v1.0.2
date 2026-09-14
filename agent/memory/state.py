"""
agent/memory/state.py

MemoryState：长期记忆层——用户事实条目库。
- text：压缩文本库（每行一条用户事实/约束，LLM 维护，唯一注入 system 的长期状态）
- turn_log：轮次记录内存日志（每次 update 追加一份，定位问题用）

每次 update 输入一份轮次记录（turn record）：
- 本轮事件（用户原话 / AI 回复）：增删改的依据
- intent（工具 + 参数）：本轮 AI 做了什么动作（可参考，非事实）
- result（真实执行结果）：作真实依据；无 result 时仅凭对话增量
"""

from llm.client import LLMClient
from agent.memory.state_prompt import get_state_update_prompt

# 条目库长度硬上限（字），超出截断兜底（state_prompt 要求 200 字内）
MAX_STATE_CHARS = 200


class MemoryState:

    def __init__(self, llm: LLMClient):
        self.llm = llm
        # 用户事实条目库："- 预算：≤5000元\n- 排除：游戏本\n..."
        self.text = ""
        # 轮次记录内存日志：每次 update 追加一份，定位问题用
        self.turn_log = []

    def update(self, turn_record: dict) -> None:
        """
        用 LLM 增量更新条目库：旧 text + 本轮事件 + intent + result → 新 text。

        Args:
            turn_record: 由 memory.turn.build_turn_record 组装的轮次记录
        """
        # 追加内存日志
        self.turn_log.append(turn_record)

        input_text = self._build_input(turn_record)
        response = self.llm.chat(messages=[
            {"role": "system", "content": get_state_update_prompt()},
            {"role": "user", "content": input_text},
        ])
        new_text = self._clip(response.content)
        # 兜底：本轮提炼为空时保留旧库，避免清空记忆
        if new_text:
            self.text = new_text
    # 需要完善一下，不能截断尾部，应该保留开头和结尾
    def _clip(self, text: str) -> str:
        """长度兜底：超过 MAX_STATE_CHARS 则截断。"""
        if text is None:
            return ""
        return text.strip()[:MAX_STATE_CHARS]

    def to_dict(self) -> dict:
        """序列化：text + turn_log（供会话持久化）。"""
        return {
            "text": self.text,
            "turn_log": self.turn_log,
        }

    def from_dict(self, data: dict) -> None:
        """恢复状态（供会话持久化加载）。"""
        self.text = self._clip(data.get("text", ""))
        self.turn_log = list(data.get("turn_log", []) or [])

    # 构建 State 更新输入（旧库 + 本轮事件 + 工具调用）
    def _build_input(self, turn_record: dict) -> str:
        """组装 State 更新输入：旧条目库 + 本轮对话 + 工具调用（intent 动作 / result 真实依据）。"""
        parts = []
        if self.text:
            parts.append(f"当前用户条目库：\n{self.text}")

        parts.append(
            f"本轮事件：\n用户：{turn_record['user_input']}\nAI：{turn_record['ai_reply']}"
        )

        tool_events = turn_record.get("tool_events") or []
        if tool_events:
            lines = []
            for event in tool_events:
                intent = event.get("intent") or {}
                lines.append(
                    "本轮工具调用：\n"
                    f"工具：{intent.get('tool')}\n"
                    f"参数：{intent.get('args')}"
                )
                lines.append(f"执行结果（result）：\n{event.get('result')}")
            parts.append("\n".join(lines))

        return "\n\n".join(parts)

    def to_text(self) -> str:
        """
        返回注入 system 的条目库文本；空 State 返回 ""。
        """
        if not self.text:
            return ""
        return f"当前已知用户信息：\n{self.text}\n"
