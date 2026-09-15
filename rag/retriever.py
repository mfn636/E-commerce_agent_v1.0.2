"""
rag/retriever.py

query → 向量 → top-k + 相似度阈值 + 元数据过滤 → chunks（带 score/来源）。
"""

from rag.embedder import Embedder


class Retriever:
    def __init__(self, store, embedder=None):
        self.store = store
        self.embedder = embedder or Embedder()

    def retrieve(self, collection: str, query: str, top_k: int = 5,
                 score_threshold: float = 0.3, query_filter=None):
        vector = self.embedder.embed(query)
        return self.store.search(
            collection, vector, top_k=top_k,
            score_threshold=score_threshold, query_filter=query_filter,
        )
