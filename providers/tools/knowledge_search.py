"""
providers/tools/knowledge_search.py

知识库语义检索（RAG）：FAQ / 指南 / 政策 / 帮助 统一检索。
"""

from typing import List, Optional

from qdrant_client.models import FieldCondition, Filter, MatchValue

from domain.models.knowledge import KnowledgeItem
from rag.ingest import COLLECTION_KNOWLEDGE
from rag.retriever import Retriever
from rag.store import get_store

_retriever = None


def _get_retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = Retriever(get_store())
    return _retriever


def search_knowledge(
    query: str,
    category: Optional[str] = None,
    top_k: int = 5,
) -> List[KnowledgeItem]:
    """
    知识库语义检索工具。

    Args:
        query: 用户问题（自然语言）
        category: 可选，按知识类别过滤（如 退换货、支付）
        top_k: 返回条数上限

    Returns:
        List[KnowledgeItem]
    """
    query_filter = None
    if category:
        query_filter = Filter(must=[
            FieldCondition(key="category", match=MatchValue(value=category))
        ])

    hits = _get_retriever().retrieve(
        COLLECTION_KNOWLEDGE, query, top_k=top_k,
        score_threshold=0.3, query_filter=query_filter,
    )

    items = []
    for h in hits:
        p = h["payload"]
        items.append(KnowledgeItem(
            source=p.get("source", "knowledge"),
            title=p.get("question") or p.get("title") or "",
            content=p.get("_text", ""),
            score=round(float(h.get("score", 0.0)), 4),
        ))
    return items
