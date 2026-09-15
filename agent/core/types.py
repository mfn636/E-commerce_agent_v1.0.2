"""
agent/core/types.py

一轮对话的返回结构：可见回复 + 工具调用轨迹 + 用量/耗时。
"""

from dataclasses import dataclass, field


@dataclass
class TurnResult:
    replies: list = field(default_factory=list)      # 对用户可见的回复（可能多条）
    tool_calls: list = field(default_factory=list)   # [{"name":..., "args":...}]
    usage: dict = field(default_factory=dict)        # llm_calls / tokens / latency_ms
