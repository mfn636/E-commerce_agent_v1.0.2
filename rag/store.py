"""
rag/store.py

Qdrant 本地向量库封装：建集合 / 幂等 upsert / 检索（带 payload 过滤）。
point id 用 chunk id 的确定性 UUID → 重复 ingest 幂等覆盖。
"""

import atexit
import uuid
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

DEFAULT_PATH = str(Path(__file__).resolve().parent / "qdrant_data")
_UUID_NS = uuid.uuid5(uuid.NAMESPACE_URL, "ecommerce-agent/rag")


def _point_id(chunk_id: str) -> str:
    return str(uuid.uuid5(_UUID_NS, chunk_id))


class VectorStore:
    def __init__(self, path: str = DEFAULT_PATH):
        self.client = QdrantClient(path=path)

    def ensure_collection(self, name: str, dim: int):
        if not self.client.collection_exists(name):
            self.client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )

    def upsert(self, name: str, chunks, vectors) -> int:
        points = [
            PointStruct(id=_point_id(c["id"]), vector=v,
                        payload={**c["payload"], "_cid": c["id"], "_text": c["text"]})
            for c, v in zip(chunks, vectors)
        ]
        if points:
            self.client.upsert(collection_name=name, points=points)
        return len(points)

    def search(self, name, vector, top_k=5, score_threshold=None, query_filter=None):
        res = self.client.query_points(
            collection_name=name, query=vector, limit=top_k,
            score_threshold=score_threshold, query_filter=query_filter,
        )
        return [
            {"id": p.payload.get("_cid"), "payload": p.payload, "score": p.score}
            for p in res.points
        ]

    def count(self, name) -> int:
        return self.client.count(collection_name=name, exact=True).count

    def close(self):
        self.client.close()


_store = None


def get_store() -> "VectorStore":
    """进程内单例（Qdrant 本地模式同一路径只允许一个客户端）。"""
    global _store
    if _store is None:
        _store = VectorStore()
        atexit.register(_safe_close, _store)
    return _store


def _safe_close(store) -> None:
    try:
        store.close()
    except Exception:  # noqa: BLE001
        pass
