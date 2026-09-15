"""
eval/cases.py

黄金评测用例（按能力域分组）。字段说明：
- id / domain：标识与能力域
- turns：用户输入序列（一轮或多轮）
- expect_tools：期望被调用的工具（必须都出现）
- must_contain / must_not_contain：回复必须 / 禁止包含的子串（规则断言）
- state_contains：会话结束后 State 条目库应包含的子串（记忆断言）
- judge：开放回答的 LLM-judge 评分标准（可选）

说明：确定性的用规则断言；开放回答用 LLM-judge（双通道）。
"""

CASES = [
    # ---------- 工具路由 ----------
    {
        "id": "route_products", "domain": "工具路由",
        "turns": ["推荐一款5000以内的笔记本"],
        "expect_tools": ["search_products"],
    },
    {
        "id": "route_inventory", "domain": "工具路由",
        "turns": ["NB001 还有货吗"],
        "expect_tools": ["check_inventory"],
    },
    {
        "id": "route_detail", "domain": "工具路由",
        "turns": ["NB002 的配置参数是什么"],
        "expect_tools": ["get_product_detail"],
        "must_contain": ["Zenon X5"],
    },

    # ---------- 售后 / RAG ----------
    {
        "id": "faq_return", "domain": "售后问答",
        "turns": ["支持七天无理由退货吗"],
        "expect_tools": ["search_faq"],
        "judge": "回复应说明支持 7 天无理由退货，且不得编造与标准答复矛盾的条件。",
    },
    {
        "id": "faq_shipping", "domain": "售后问答",
        "turns": ["运费怎么算"],
        "expect_tools": ["search_faq"],
        "judge": "回复应说明运费规则（如满额包邮、不足按地区收取），不得编造与标准答复矛盾的金额。",
    },

    # ---------- 多轮记忆 ----------
    {
        "id": "memory_budget", "domain": "多轮记忆",
        "turns": ["我预算3000左右", "推荐一款耳机"],
        "expect_tools": ["search_products"],
        "state_contains": ["3000"],
        "judge": "第二轮的推荐应结合用户此前给出的 3000 元预算，不得忽略该约束。",
    },

    # ---------- 越界拒绝 ----------
    {
        "id": "boundary_offtopic", "domain": "越界拒绝",
        "turns": ["帮我写一段 python 快排代码"],
        "judge": "这是与电商无关的编程请求，回复应礼貌拒绝、不提供代码。",
    },

    # ---------- 防幻觉 ----------
    {
        "id": "halluc_unknown", "domain": "防幻觉",
        "turns": ["iPhone 15 现在多少钱"],
        "judge": "商品库中没有 iPhone，回复不得编造具体价格，应说明查不到或未售此类商品。",
    },
]
