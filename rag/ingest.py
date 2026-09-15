"""
rag/ingest.py

数据管道：JSON → chunk → embed → upsert（幂等，可重复跑）。
CLI：python -m rag.ingest
"""

from domain.loader import load_faq, load_products
from rag.chunker import chunk_faq, chunk_guides, chunk_products
from rag.embedder import EMBED_DIM, Embedder
from rag.store import VectorStore

COLLECTION_PRODUCTS = "products"
COLLECTION_KNOWLEDGE = "knowledge"


def _load_guides():
    try:
        from domain.loader import load_guides
        return load_guides()
    except Exception:  # noqa: BLE001
        return []


def ingest() -> dict:
    store = VectorStore()
    embedder = Embedder()

    # 商品集合
    product_chunks = chunk_products(load_products())
    store.ensure_collection(COLLECTION_PRODUCTS, EMBED_DIM)
    store.upsert(COLLECTION_PRODUCTS, product_chunks,
                 embedder.embed([c["text"] for c in product_chunks]))

    # 知识集合（FAQ + 指南/政策/帮助）
    knowledge_chunks = chunk_faq(load_faq()) + chunk_guides(_load_guides())
    store.ensure_collection(COLLECTION_KNOWLEDGE, EMBED_DIM)
    store.upsert(COLLECTION_KNOWLEDGE, knowledge_chunks,
                 embedder.embed([c["text"] for c in knowledge_chunks]))

    result = {
        "products": store.count(COLLECTION_PRODUCTS),
        "knowledge": store.count(COLLECTION_KNOWLEDGE),
    }
    store.close()
    return result


if __name__ == "__main__":
    print("ingest ->", ingest())
