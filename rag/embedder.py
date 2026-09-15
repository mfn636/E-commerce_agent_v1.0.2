"""
rag/embedder.py

文本 → 向量：调用 Ollama /api/embed（bge-m3，1024 维），带批处理、重试与超时。
"""

import time

import requests

OLLAMA_URL = "http://127.0.0.1:11434"
EMBED_MODEL = "bge-m3"
EMBED_DIM = 1024


class Embedder:
    def __init__(self, base_url: str = OLLAMA_URL, model: str = EMBED_MODEL,
                 timeout: int = 60, retries: int = 3, batch_size: int = 32):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.retries = retries
        self.batch_size = batch_size

    def embed(self, texts):
        """texts: str 或 list[str] -> list[float] 或 list[list[float]]。"""
        single = isinstance(texts, str)
        if single:
            texts = [texts]
        out = []
        for i in range(0, len(texts), self.batch_size):
            out.extend(self._embed_batch(texts[i:i + self.batch_size]))
        return out[0] if single else out

    def _embed_batch(self, batch):
        payload = {"model": self.model, "input": list(batch)}
        last_err = None
        for attempt in range(self.retries):
            try:
                r = requests.post(f"{self.base_url}/api/embed", json=payload, timeout=self.timeout)
                r.raise_for_status()
                return r.json()["embeddings"]
            except Exception as e:  # noqa: BLE001
                last_err = e
                time.sleep(1.0 * (attempt + 1))
        raise RuntimeError(f"embed 失败（已重试 {self.retries} 次）：{last_err}")
