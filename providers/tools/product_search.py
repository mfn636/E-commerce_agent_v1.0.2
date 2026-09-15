"""
providers/tools/product_search.py

商品检索：语义检索（RAG）+ 结构化过滤（预算/品牌/类别），保留关键词兜底。
"""

from typing import List, Optional

from qdrant_client.models import FieldCondition, Filter, MatchValue, Range

from domain.loader import load_products
from domain.models.product import Product
from rag.ingest import COLLECTION_PRODUCTS
from rag.retriever import Retriever
from rag.store import get_store

# Agent启动时加载一次商品数据
PRODUCTS: List[Product] = load_products()
# ID -> Product 映射（供详情查询 / 语义结果还原）
PRODUCT_MAP = {p.id: p for p in PRODUCTS}

_retriever = None


def _get_retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = Retriever(get_store())
    return _retriever


def _build_filter(category, budget, brand) -> Filter:
    must = [FieldCondition(key="source", match=MatchValue(value="product"))]
    if category:
        must.append(FieldCondition(key="category", match=MatchValue(value=category)))
    if brand:
        must.append(FieldCondition(key="brand", match=MatchValue(value=brand)))
    if budget:
        must.append(FieldCondition(key="price", range=Range(lte=budget)))
    return Filter(must=must)


def search_products(
    category: Optional[str] = None,
    budget: Optional[int] = None,
    brand: Optional[str] = None,
    keyword: Optional[str] = None,
    query: Optional[str] = None,
) -> List[Product]:
    """
    商品搜索：有自由文本时走语义检索（叠加结构化过滤），否则结构化过滤；
    失败/空则回退关键词。
    """
    text_query = keyword or query
    if text_query:
        try:
            hits = _get_retriever().retrieve(
                COLLECTION_PRODUCTS, text_query, top_k=8,
                score_threshold=0.3, query_filter=_build_filter(category, budget, brand),
            )
            products = [PRODUCT_MAP[h["payload"]["product_id"]]
                        for h in hits if h["payload"].get("product_id") in PRODUCT_MAP]
            if products:
                return products
        except Exception:  # noqa: BLE001
            pass
    return _keyword(category, budget, brand, keyword or query)


def _keyword(category, budget, brand, keyword) -> List[Product]:
    results = []
    for product in PRODUCTS:
        if category and category not in product.category:
            continue
        if budget and product.price > budget:
            continue
        if brand and brand.lower() not in product.brand.lower():
            continue
        if keyword:
            text = product.name + product.category + product.description
            if keyword.lower() not in text.lower():
                continue
        results.append(product)
    return results


def get_product_detail(product_id: Optional[str] = None) -> List[Product]:
    """按商品 ID 查询单个商品的完整信息（含硬件参数）。"""
    product = PRODUCT_MAP.get(product_id) if product_id else None
    return [product] if product else []
