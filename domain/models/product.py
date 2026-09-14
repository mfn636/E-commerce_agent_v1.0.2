"""
domain/models/product.py

商品存储模型：忠实镜像 data/products.json 的一条商品记录。
- 6 个核心字段（id/name/category/brand/price/description）供检索与展示
- 规格字段（cpu/memory/...）与 tags 为商品档案的组成部分，随存储一并保留
"""

from typing import Optional
from pydantic import BaseModel, Field


class Product(BaseModel):
    id: str = Field(description="商品唯一编码")
    name: str = Field(description="商品名称")
    category: str = Field(description="商品类别，如 笔记本电脑、手机")
    brand: str = Field(description="品牌")
    price: int = Field(description="价格，单位：元")
    cpu: Optional[str] = Field(default=None, description="CPU 型号")
    memory: Optional[str] = Field(default=None, description="内存")
    storage: Optional[str] = Field(default=None, description="存储")
    display: Optional[str] = Field(default=None, description="屏幕参数")
    weight: Optional[str] = Field(default=None, description="重量")
    battery: Optional[str] = Field(default=None, description="电池容量")
    os: Optional[str] = Field(default=None, description="操作系统")
    description: str = Field(description="商品描述")
    tags: list[str] = Field(default_factory=list, description="标签列表")
