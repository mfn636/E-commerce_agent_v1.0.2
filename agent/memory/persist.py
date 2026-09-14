"""
agent/memory/persist.py

会话快照持久化：只落两类有界数据——
- state_text：State 长期叙事（本身有 200 字截断）
- recent_messages：最近 WINDOW 条对话（发送窗口用）

无界数据（turn_log / tool_events / 全量对话）一律不落盘：
它们是审计性质，进程退出即丢，恢复续聊不需要。
每个会话一个 JSON 文件：sessions/<session_id>.json
"""

import json
from pathlib import Path

SESSION_ROOT = Path("sessions")


def _snapshot_path(session_id: str) -> Path:
    return SESSION_ROOT / f"{session_id}.json"


def save_snapshot(session_id: str, state_text: str, recent_messages: list) -> None:
    """写快照（覆盖）：state_text + recent_messages。"""
    SESSION_ROOT.mkdir(parents=True, exist_ok=True)
    data = {
        "state_text": state_text,
        "messages": recent_messages,
    }
    with open(_snapshot_path(session_id), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_snapshot(session_id: str):
    """
    加载快照。

    Returns:
        (state_text, messages) 或 (None, None)（无快照 / 文件损坏，静默降级为全新会话）。
    """
    path = _snapshot_path(session_id)
    if not path.is_file():
        return None, None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None, None
    return data.get("state_text", ""), data.get("messages", [])
