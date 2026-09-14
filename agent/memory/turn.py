"""
agent/memory/turn.py

对话轮次记录（Turn Record）的组装。
把 agent 一轮 while 循环里发生的工具调用（意图+结果）与用户/AI 对话聚合成一份结构化记录。
"""


def build_turn_record(round_no, user_input, ai_reply, tool_events):
    """
    组装一份轮次记录。

    Args:
        round_no: 第几轮对话
        user_input: 用户本轮输入
        ai_reply: AI 本轮最终回复
        tool_events: 本轮工具调用列表，每项为
            {"intent": {"tool", "args", "reasoning"}, "result": ...}

    Returns:
        dict: 轮次记录，结构如下
        {
            "round": 4,
            "user_input": "...",
            "ai_reply": "...",
            "tool_events": [
                {
                    "intent": {"tool": "search_products", "args": {...},
                               "reasoning": "..."},
                    "result": "..."
                }
            ]
        }
    """
    return {
        "round": round_no,
        "user_input": user_input,
        "ai_reply": ai_reply,
        "tool_events": tool_events,
    }
