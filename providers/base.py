"""
providers/base.py

工具契约·执行侧的端口（Protocol）。
核心（agent）只依赖此端口；任何实现 list_tools / call 的对象都可作为工具来源接入。
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class ToolProvider(Protocol):
    def list_tools(self) -> list: ...
    def call(self, name: str, args: dict): ...
