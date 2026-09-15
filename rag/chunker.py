"""
rag/chunker.py

把领域数据切成带元数据的 chunk。
Chunk = {"id": str, "text": str, "payload": dict}
"""


def chunk_faq(faq_items):
    """FAQ：一条一个 chunk；payload 存 question/answer 以便还原。"""
    chunks = []
    for i, f in enumerate(faq_items):
        chunks.append({
            "id": f"faq-{i}",
            "text": f"{f.question}\n{f.answer}",
            "payload": {
                "source": "faq",
                "category": f.category,
                "question": f.question,
                "answer": f.answer,
            },
        })
    return chunks


def chunk_products(products):
    """商品：一款一个 chunk；payload 存可过滤字段（类别/品牌/价格/ID）。"""
    chunks = []
    for p in products:
        text = f"{p.name}（{p.brand} {p.category}）售价 {p.price} 元。{p.description}"
        chunks.append({
            "id": f"product-{p.id}",
            "text": text,
            "payload": {
                "source": "product",
                "product_id": p.id,
                "category": p.category,
                "brand": p.brand,
                "price": p.price,
            },
        })
    return chunks


def chunk_guides(guides):
    """长文档（指南/政策/帮助）：按段落切成带 overlap 的块。"""
    chunks = []
    for g in guides:
        for j, sec in enumerate(chunk_text(g.get("content", ""))):
            chunks.append({
                "id": f"guide-{g['id']}-{j}",
                "text": f"{g.get('title', '')}｜{sec}",
                "payload": {
                    "source": g.get("source", "guide"),
                    "doc_id": g["id"],
                    "title": g.get("title", ""),
                    "category": g.get("category", ""),
                },
            })
    return chunks


def chunk_text(text, max_len=400, overlap=60):
    """按行(段落)聚合成长度 <= max_len 的块，块间保留 overlap 字符。"""
    paras = [p.strip() for p in text.splitlines() if p.strip()]
    chunks, cur = [], ""
    for p in paras:
        if cur and len(cur) + len(p) + 1 > max_len:
            chunks.append(cur)
            cur = (cur[-overlap:] if overlap else "")
        cur = f"{cur}\n{p}" if cur else p
    if cur:
        chunks.append(cur)
    return chunks
