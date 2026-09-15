"""
eval/retrieval_runner.py

检索评测：黄金集 → hit rate @1/@3/@5。
运行：python -m eval.retrieval_runner
"""

import json
from datetime import datetime
from pathlib import Path

from rag.ingest import COLLECTION_KNOWLEDGE, COLLECTION_PRODUCTS
from rag.retriever import Retriever
from rag.store import get_store

GOLDEN = Path("domain/data/retrieval_golden.json")
REPORT = Path("eval/retrieval_report.md")
KS = (1, 3, 5)


def _collection_for(doc_id: str) -> str:
    return COLLECTION_PRODUCTS if doc_id.startswith("product-") else COLLECTION_KNOWLEDGE


def _doc_id_of(hit) -> str:
    p = hit["payload"]
    return p.get("doc_id") or p.get("_cid") or ""


def run():
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    retriever = Retriever(get_store())
    hits_stat = {k: 0 for k in KS}
    rows = []

    for g in golden:
        expected = (g.get("expected_ids") or [None])[0]
        if not expected:
            continue
        collection = _collection_for(expected)
        hits = retriever.retrieve(collection, g["query"], top_k=max(KS), score_threshold=0.0)

        # 去重：同一文档的多个 chunk 只算一次（按首次出现排序）
        seen, ranked = set(), []
        for h in hits:
            did = _doc_id_of(h)
            if did and did not in seen:
                seen.add(did)
                ranked.append(did)

        row = {"query": g["query"], "expected": expected, "rank": None}
        for k in KS:
            if expected in ranked[:k]:
                hits_stat[k] += 1
        if expected in ranked:
            row["rank"] = ranked.index(expected) + 1
        rows.append(row)

    total = len(rows)
    top10 = min(total, 10)
    lines = [
        "# 检索评测报告",
        "",
        f"> 时间：{datetime.now():%Y-%m-%d %H:%M} · 黄金查询数：{total}",
        "",
        "## 命中率（hit rate）",
        "",
        "| 指标 | 命中 / 总数 | 命中率 |",
        "|---|---|---|",
    ]
    for k in KS:
        lines.append(f"| hit@{k} | {hits_stat[k]} / {total} | {hits_stat[k] / total * 100:.1f}% |")
    lines += [
        "",
        "## 未命中样例（前 10）",
        "",
        "| 查询 | 期望命中 | 名次 |",
        "|---|---|---|",
    ]
    miss = [r for r in rows if r["rank"] is None][:top10]
    if miss:
        for r in miss:
            lines.append(f"| {r['query']} | {r['expected']} | 未命中 |")
    else:
        lines.append("| - | 全部命中 | - |")
    lines += [
        "",
        "## 命中但未进前三（前 10）",
        "",
        "| 查询 | 期望命中 | 名次 |",
        "|---|---|---|",
    ]
    low = [r for r in rows if r["rank"] and r["rank"] > 3][:top10]
    if low:
        for r in low:
            lines.append(f"| {r['query']} | {r['expected']} | {r['rank']} |")
    else:
        lines.append("| - | 无 | - |")

    report = "\n".join(lines)
    REPORT.write_text(report, encoding="utf-8")
    print(report)
    print(f"\n报告已写入：{REPORT}")


if __name__ == "__main__":
    run()
