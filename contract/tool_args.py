"""
contract/tool_args.py

工具入参的 Pydantic 模型（工具契约的数据侧）：字段名、类型、约束与 description 即真相来源。
- 给模型的工具 schema 由 model_json_schema() 自动生成（不再手写）
- LLM 返回的参数用这些模型校验（validate_args）
约束取值来自 data/*.json 的真实取值。
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

# 真实数据取值（与 data/*.json 对齐）
ProductCategory = Literal[
    "笔记本电脑", "手机", "平板电脑", "显示器", "键盘", "鼠标", "耳机", "路由器"
]
Brand = Literal["Apex", "Orion", "Vortex", "Nova", "Zenith"]
FaqCategory = Literal[
    "支付", "发货", "运费", "退换货", "保修", "发票", "产品", "售后", "订单", "优惠"
]


class SearchProductsArgs(BaseModel):
    category: Optional[ProductCategory] = Field(
        None, description="商品类别（只能取枚举值之一）"
    )
    budget: Optional[int] = Field(None, gt=0, description="用户最高预算，单位：元，必须为正整数")
    brand: Optional[Brand] = Field(
        None, description="品牌（只能取枚举值之一）"
    )
    keyword: Optional[str] = Field(
        None, min_length=1, description="关键词搜索，在商品名称、类别、描述中模糊匹配"
    )
    query: Optional[str] = Field(
        None, min_length=1, description="用户原始搜索需求描述，当 keyword 未传时生效"
    )


class CheckInventoryArgs(BaseModel):
    product_id: Optional[str] = Field(
        None, pattern=r"^[A-Z]{2,4}\d{3}$", description="商品ID，例如：NB001"
    )
    category: Optional[ProductCategory] = Field(
        None, description="商品类别（只能取枚举值之一）"
    )


class SearchFaqArgs(BaseModel):
    query: str = Field(..., min_length=1, description="用户问题的关键词或短语，不可为空")
    category: Optional[FaqCategory] = Field(
        None, description="FAQ 类别（只能取枚举值之一）"
    )
