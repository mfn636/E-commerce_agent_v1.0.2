"""
contract/tool.py

工具契约的数据侧：
- TOOL_REGISTRY：工具元数据（name / description / args_model / fn）
- TOOLS：给模型的 function schema，由 args_model.model_json_schema() 自动生成并清洗
- ARGS_MODEL_MAP / TOOL_MAP：按名索引的派生映射
- validate_args()：对 LLM 返回的参数做校验（失败抛 ValidationError）
"""

from providers.tools.product_search import search_products
from providers.tools.inventory import check_inventory
from providers.tools.faq_search import search_faq
from contract.tool_args import SearchProductsArgs, CheckInventoryArgs, SearchFaqArgs


TOOL_REGISTRY = [
    {
        "name": "search_products",
        "description": "搜索商品。按类别、预算、品牌或关键词筛选商品列表。",
        "args_model": SearchProductsArgs,
        "fn": search_products,
    },
    {
        "name": "check_inventory",
        "description": "查询商品库存。可按商品ID或类别查询。",
        "args_model": CheckInventoryArgs,
        "fn": check_inventory,
    },
    {
        "name": "search_faq",
        "description": "搜索常见问题FAQ，用于回答支付、发货、运费、退换货、保修、发票、订单、产品、售后、优惠等售后问题。",
        "args_model": SearchFaqArgs,
        "fn": search_faq,
    },
]


def _clean_schema(node):
    """清洗 model_json_schema 输出：折叠 anyOf[X, null]→X，去掉 title / default。"""
    if isinstance(node, list):
        return [_clean_schema(item) for item in node]
    if not isinstance(node, dict):
        return node

    # anyOf: [X, null] -> X（保留原节点的 description）
    if "anyOf" in node:
        branches = node["anyOf"]
        non_null = [b for b in branches if b.get("type") != "null"]
        if len(non_null) == 1 and len(non_null) < len(branches):
            merged = dict(non_null[0])
            if "description" in node:
                merged["description"] = node["description"]
            node = merged

    node.pop("title", None)
    node.pop("default", None)
    for key, value in list(node.items()):
        if isinstance(value, (dict, list)):
            node[key] = _clean_schema(value)
    return node


def _build_tools():
    tools = []
    for item in TOOL_REGISTRY:
        schema = _clean_schema(item["args_model"].model_json_schema())
        schema.setdefault("required", [])
        tools.append({
            "type": "function",
            "function": {
                "name": item["name"],
                "description": item["description"],
                "parameters": schema,
            },
        })
    return tools


TOOLS = _build_tools()

ARGS_MODEL_MAP = {item["name"]: item["args_model"] for item in TOOL_REGISTRY}

TOOL_MAP = {item["name"]: item["fn"] for item in TOOL_REGISTRY}


def validate_args(name, args):
    """校验并补默认值；未知工具抛 KeyError，参数非法抛 ValidationError。"""
    return ARGS_MODEL_MAP[name].model_validate(args)
