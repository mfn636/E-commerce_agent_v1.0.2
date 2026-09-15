"""
providers/tools/faq_search.py

FAQ 检索：语义检索（RAG，source=faq），保留关键词兜底。
"""

from typing import List, Optional

from qdrant_client.models import FieldCondition, Filter, MatchValue

from domain.loader import load_faq
from domain.models.faq import FaqItem
from rag.ingest import COLLECTION_KNOWLEDGE
from rag.retriever import Retriever
from rag.store import get_store

FAQ: List[FaqItem] = load_faq()
_retriever = None


def _get_retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = Retriever(get_store())
    return _retriever


def search_faq(
    query: Optional[str] = None,
    category: Optional[str] = None,
) -> List[FaqItem]:
    """FAQ 搜索：优先语义检索，失败/空则回退关键词。"""
    if query:
        try:
            items = _semantic(query, category)
            if items:
                return items
        except Exception:  # noqa: BLE001
            pass
    return _keyword(query, category)


def _semantic(query, category) -> List[FaqItem]:
    must = [FieldCondition(key="source", match=MatchValue(value="faq"))]
    if category:
        must.append(FieldCondition(key="category", match=MatchValue(value=category)))
    hits = _get_retriever().retrieve(
        COLLECTION_KNOWLEDGE, query, top_k=5,
        score_threshold=0.3, query_filter=Filter(must=must),
    )
    return [
        FaqItem(category=h["payload"].get("category", ""),
                question=h["payload"].get("question", ""),
                answer=h["payload"].get("answer", ""))
        for h in hits
    ]


def _keyword(query, category) -> List[FaqItem]:
    results = []
    for entry in FAQ:
        if category and category not in entry.category:
            continue
        if query:
            text = entry.question + entry.answer
            keywords = _extract_keywords(query)
            if not any(kw in text for kw in keywords):
                continue
        results.append(entry)
    return results


def _extract_keywords(text: str) -> List[str]:
    result = [text]
    for i in range(len(text) - 1):
        chunk = text[i:i + 2]
        chunk = chunk.strip(" ?？！!，,。.")
        if chunk and len(chunk) == 2:
            result.append(chunk)
    return result
