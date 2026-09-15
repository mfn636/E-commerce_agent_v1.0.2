"""
scripts/gen_corpus.py

用 LLM 批量生成 RAG 语料（可断点续跑）：
- guides   选购指南 / 售后政策 / 帮助文档 → domain/data/guides.json
- faq      扩充 FAQ → domain/data/faq.json
- products 扩写商品描述 → domain/data/products.json
- golden   检索黄金集 → domain/data/retrieval_golden.json

用法：python -m scripts.gen_corpus [guides|faq|products|golden|all]
"""

import json
import re
import sys
from pathlib import Path

from llm.client import LLMClient

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "domain" / "data"

BRANDS = "Apex、Orion、Vortex、Nova、Zenith（均为虚构品牌）"
SYSTEM = "你是电商知识库的资深编辑，负责撰写规范、准确、可被检索的知识内容。"

GUIDE_TOPICS = [
    ("笔记本电脑", "guide", "笔记本电脑选购指南：预算、配置、场景怎么选"),
    ("笔记本电脑", "guide", "笔记本电脑使用与保养指南"),
    ("手机", "guide", "手机选购指南：参数怎么看、如何避坑"),
    ("手机", "guide", "手机使用与保养指南"),
    ("平板电脑", "guide", "平板电脑选购指南：尺寸、用途、配件"),
    ("平板电脑", "guide", "平板电脑使用与保养指南"),
    ("显示器", "guide", "显示器选购指南：分辨率、刷新率、尺寸怎么选"),
    ("显示器", "guide", "显示器使用与保养指南"),
    ("键盘", "guide", "键盘选购指南：机械与薄膜、轴体怎么选"),
    ("键盘", "guide", "键盘使用与保养指南"),
    ("鼠标", "guide", "鼠标选购指南：有线无线、DPI 与握持手感"),
    ("鼠标", "guide", "鼠标使用与保养指南"),
    ("耳机", "guide", "耳机选购指南：降噪、入耳与头戴、音质"),
    ("耳机", "guide", "耳机使用与保养指南"),
    ("路由器", "guide", "路由器选购指南：WiFi 6、覆盖范围与组网"),
    ("路由器", "guide", "路由器使用与保养指南"),
    ("售后", "policy", "退换货政策：七天无理由、质量问题与运费承担"),
    ("售后", "policy", "保修政策：保修期限、所需凭证、人为损坏"),
    ("物流", "policy", "发货与物流政策：发货时效、合作快递、偏远地区"),
    ("财务", "policy", "发票政策：电子发票、抬头修改与开票时效"),
    ("支付", "policy", "支付与分期政策：支持的支付方式与免息分期"),
    ("营销", "policy", "优惠与会员政策：优惠券、满减、学生优惠"),
    ("帮助", "help", "如何下单购买"),
    ("帮助", "help", "如何查询订单状态"),
    ("帮助", "help", "如何申请退货"),
    ("帮助", "help", "如何申请换货"),
    ("帮助", "help", "如何开具发票"),
    ("帮助", "help", "如何联系客服"),
    ("帮助", "help", "如何取消订单"),
    ("帮助", "help", "如何修改收货地址"),
]

FAQ_CATEGORIES = ["支付", "发货", "运费", "退换货", "保修", "发票", "产品", "售后", "订单", "优惠"]


def _load(path, default):
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def _extract_json(text):
    """从 LLM 输出里抠出 JSON 对象（容忍 ```json 包裹）。"""
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0)) if m else {}


# ---------------- guides ----------------
def gen_guides():
    out_path = DATA / "guides.json"
    docs = _load(out_path, [])
    existing = {d["id"] for d in docs}
    llm = LLMClient()
    counters = {}
    for cat, source, topic in GUIDE_TOPICS:
        key = f"{source}-{cat}"
        counters[key] = counters.get(key, 0) + 1
        doc_id = f"{source}-{cat}-{counters[key]}"
        if doc_id in existing:
            continue
        prompt = (f"请撰写一篇电商知识库文档。\n主题：{topic}\n品牌背景：本店销售电子产品，品牌有 {BRANDS}。\n\n"
                  "要求：1) 面向客服与用户，专业、准确、可落地，不编造具体价格或绝对承诺；"
                  "2) 用「## 小标题」分 3-5 节，开头一句话概述；3) 篇幅 700-1200 字；"
                  "4) 只输出文档正文（Markdown），不要解释。")
        resp = llm.chat(messages=[{"role": "system", "content": SYSTEM},
                                  {"role": "user", "content": prompt}],
                        temperature=0.7, max_tokens=2500, thinking=False)
        docs.append({"id": doc_id, "title": topic, "category": cat,
                     "source": source, "content": (resp.content or "").strip()})
        out_path.write_text(json.dumps(docs, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[guides] {doc_id} | {topic} | {len(docs[-1]['content'])} 字")
    print(f"[guides] done, total={len(docs)}")


# ---------------- faq ----------------
def gen_faq(target_per_cat=9):
    out_path = DATA / "faq.json"
    faq = _load(out_path, [])
    seen = {(e["category"], e["question"]) for e in faq}
    llm = LLMClient()
    for cat in FAQ_CATEGORIES:
        have = sum(1 for e in faq if e["category"] == cat)
        need = target_per_cat - have
        if need <= 0:
            continue
        prompt = (f'请为电商客服知识库生成 {need} 条「{cat}」类常见问题（FAQ）。\n'
                  f'严格输出 JSON：{{"items":[{{"question":"...","answer":"..."}}]}}\n'
                  f'要求：问题真实常见；回答简洁准确（30-80字）；不编造具体价格/绝对承诺；品牌有 {BRANDS}。')
        resp = llm.chat(messages=[{"role": "system", "content": SYSTEM},
                                  {"role": "user", "content": prompt}],
                        temperature=0.8, max_tokens=4000, thinking=False,
                        response_format={"type": "json_object"})
        items = _extract_json(resp.content or "{}").get("items", [])
        added = 0
        for it in items:
            q = (it.get("question") or "").strip()
            a = (it.get("answer") or "").strip()
            if q and a and (cat, q) not in seen:
                faq.append({"category": cat, "question": q, "answer": a})
                seen.add((cat, q))
                added += 1
        out_path.write_text(json.dumps(faq, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[faq] {cat} +{added} (该类共 {have + added})")
    print(f"[faq] done, total={len(faq)}")


# ---------------- products ----------------
def gen_products(batch=10):
    out_path = DATA / "products.json"
    data = _load(out_path, {"products": []})
    products = data["products"]
    llm = LLMClient()
    for i in range(0, len(products), batch):
        group = products[i:i + batch]
        lines = [f'{p["id"]}: {p["name"]}（{p["brand"]} {p["category"]}，{p["price"]}元，'
                 f'CPU {p.get("cpu") or "-"}，内存 {p.get("memory") or "-"}，存储 {p.get("storage") or "-"}）'
                 for p in group]
        prompt = ('下面是一批商品，请为每款重写一段 150-250 字的商品描述（卖点+适用人群+注意事项），专业不夸大。\n'
                  '严格输出 JSON：{"items":[{"id":"...","description":"..."}]}\n\n' + "\n".join(lines))
        resp = llm.chat(messages=[{"role": "system", "content": SYSTEM},
                                  {"role": "user", "content": prompt}],
                        temperature=0.7, max_tokens=4000, thinking=False,
                        response_format={"type": "json_object"})
        items = _extract_json(resp.content or "{}").get("items", [])
        desc = {it["id"]: it.get("description", "") for it in items if it.get("id")}
        n = 0
        for p in products:
            if p["id"] in desc and desc[p["id"]]:
                p["description"] = desc[p["id"]].strip()
                n += 1
        out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[products] batch {i // batch + 1} 更新 {n} 款")
    print(f"[products] done, total={len(products)}")


# ---------------- golden ----------------
def gen_golden():
    out_path = DATA / "retrieval_golden.json"
    golden = _load(out_path, [])
    done = {g["expected_ids"][0] for g in golden if g.get("expected_ids")}
    llm = LLMClient()

    # 候选：FAQ / guides / products（采样控制规模）
    cands = []
    for i, e in enumerate(_load(DATA / "faq.json", [])[:25]):
        cands.append((f"faq-{i}", f"{e['question']} {e['answer'][:80]}"))
    for g in _load(DATA / "guides.json", [])[:15]:
        cands.append((g["id"], f"{g['title']} {g['content'][:120]}"))
    for p in _load(DATA / "products.json", {"products": []})["products"][:15]:
        cands.append((f"product-{p['id']}", f"{p['name']} {p['brand']} {p['category']} {p['description'][:80]}"))

    pending = [(cid, text) for cid, text in cands if cid not in done]
    for i in range(0, len(pending), 10):
        group = pending[i:i + 10]
        lines = [f"{cid}|||{text}" for cid, text in group]
        prompt = ('下面是知识/商品片段，请为每条写 1-2 个"用户可能提出的、应当检索到该条"的自然语言查询。\n'
                  '严格输出 JSON：{"items":[{"id":"...","queries":["...","..."]}]}\n\n' + "\n".join(lines))
        resp = llm.chat(messages=[{"role": "system", "content": SYSTEM},
                                  {"role": "user", "content": prompt}],
                        temperature=0.7, max_tokens=3000, thinking=False,
                        response_format={"type": "json_object"})
        items = _extract_json(resp.content or "{}").get("items", [])
        for it in items:
            cid = it.get("id")
            for q in (it.get("queries") or []):
                if q.strip():
                    golden.append({"query": q.strip(), "expected_ids": [cid]})
        out_path.write_text(json.dumps(golden, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[golden] batch {i // 10 + 1} -> {len(golden)} 条")
    print(f"[golden] done, total={len(golden)}")


STEPS = {"guides": gen_guides, "faq": gen_faq, "products": gen_products, "golden": gen_golden}

if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "all"
    for name in (STEPS if step == "all" else [step]):
        STEPS[name]()
