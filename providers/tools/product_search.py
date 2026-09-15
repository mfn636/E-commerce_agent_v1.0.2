from typing import Optional, List

from domain.models.product import Product
from domain.loader import load_products


# Agent启动时加载一次商品数据
PRODUCTS: List[Product] = load_products()
# ID -> Product 映射（供详情查询）
PRODUCT_MAP = {p.id: p for p in PRODUCTS}


def search_products(
    category: Optional[str] = None,
    budget: Optional[int] = None,
    brand: Optional[str] = None,
    keyword: Optional[str] = None,
    query: Optional[str] = None,
) -> List[Product]:
    """
    商品查询工具

    Args:
        category:
            商品类别，例如：显示器、笔记本电脑

        budget:
            最高预算

        brand:
            品牌，例如：联想、戴尔

        keyword:
            关键词搜索

        query:
            用户原始搜索描述，当keyword未传时作为关键词使用

    Returns:
        List[Product]
    """

    results = []

    for product in PRODUCTS:
        # 类别过滤
        if category:
            if category not in product.category:
                continue
        # 价格过滤
        if budget:
            if product.price > budget:
                continue
        # 品牌过滤
        if brand:
            if brand.lower() not in product.brand.lower():
                continue
        # 关键词过滤
        keyword = keyword or query
        if keyword:
            text = (
                product.name
                + product.category
                + product.description
            )
            if keyword.lower() not in text.lower():
                continue

        results.append(product)


    return results


def get_product_detail(product_id: Optional[str] = None) -> List[Product]:
    """
    商品详情工具：按商品 ID 查询单个商品的完整信息（含 CPU/内存/存储/屏幕/重量/电池/系统 等硬件参数）。

    Args:
        product_id: 商品 ID，例如 NB002

    Returns:
        List[Product]（命中返回 1 条，未命中返回空列表）
    """
    product = PRODUCT_MAP.get(product_id) if product_id else None
    return [product] if product else []