"""
domain/models/inventory.py

库存相关的 Pydantic 模型，区分两种「形状」：
- InventoryItem：存储形状，镜像 data/inventory.json（只有 商品ID + 库存数）
- InventoryDetail：查询输出视图，由 InventoryItem + Product 组装，给模型看的形状
"""

from pydantic import BaseModel, Field


class InventoryItem(BaseModel):
    product_id: str = Field(description="商品 ID")
    stock: int = Field(description="库存数量")


class InventoryDetail(BaseModel):
    product_id: str = Field(description="商品 ID")
    product_name: str = Field(description="商品名称")
    stock: int = Field(description="库存数量")
    in_stock: bool = Field(description="是否有货")
