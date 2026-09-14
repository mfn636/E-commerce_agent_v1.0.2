"""
providers/local.py

本地工具适配器：包装 contract 的 TOOLS / TOOL_MAP，供核心调用。
"""

from contract.tool import TOOLS, TOOL_MAP, validate_args


class LocalToolProvider:
    """本地工具适配器：包装 contract/tool.py 的工具注册表。"""

    def list_tools(self) -> list:
        return TOOLS

    def call(self, name: str, args: dict):
        if name not in TOOL_MAP:
            raise KeyError(f"未知工具: {name}")
        validated = validate_args(name, args)
        return TOOL_MAP[name](**validated.model_dump(exclude_none=True))
