"""
agent/core/compress.py

工具结果的"硬压缩"：回填给 LLM / 喂给自检前，先按工具类型裁剪字段、限制条数。
省 token，同时保证 LLM 与 state/Reflection 自检看到同一份精简数据。
"""

import json

# 每个工具的保留字段表（未列出的字段一律丢弃）
_TOOL_CONFIG = {
    "search_products": {
        "fields": ["id", "name", "brand", "price", "category", "description"],
    },
    "check_inventory": {
        "fields": ["product_id", "product_name", "stock", "in_stock"],
    },
    "search_faq": {
        "fields": ["category", "question", "answer"],
    },
}

DEFAULT_MAX_ITEMS = 8


def compress_tool_result(tool_name, result, max_items=DEFAULT_MAX_ITEMS):
    """
    按工具类型把 result 压缩为结构化 JSON 字符串。

    Args:
        tool_name: 工具名（决定用哪张保留字段表）
        result: 工具返回的 pydantic 对象列表
        max_items: 最多展示多少条；超出时 items 截断、total 标注真实命中数

    Returns:
        str: {"items": [...], "total": N}，未知工具走全量兜底，不丢数据
    """
    items = [item.model_dump() for item in result]

    config = _TOOL_CONFIG.get(tool_name)
    if config:
        fields = config["fields"]
        items = [
            {k: item.get(k) for k in fields if k in item}
            for item in items
        ]

    visible = items[:max_items]
    return json.dumps({
        "items": visible,
        "total": len(items),
    }, ensure_ascii=False)
