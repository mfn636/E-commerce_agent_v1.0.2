"""
llm/reflection_prompt.py

Reflection 自检的专用 Prompt（与客服 Prompt 分开管理）。
"""

REFLECTION_PROMPT = """
你将收到三部分内容：
1. 用户原话：用户本轮提出的需求。
2. 本轮工具调用与结果：AI 实际调用的工具、参数、以及真实返回的数据。
3. 草稿回复：AI 准备发给用户的回答。

任务：对草稿回复做自检，判定它是否可以发给用户。

判定维度（逐条检查）：
1. 完整性：草稿是否完整覆盖了用户原话中的所有需求？有没有漏掉的约束
   （预算、品类、品牌、库存、有无现货）或问题点？
2. 真实性：草稿中的事实（价格、库存、参数、政策）是否都有工具结果支持？
   有没有编造工具结果中没有的数据？
3. 规范性：语气是否符合电商客服风格（礼貌、简洁、1~5 句话），有没有啰嗦或答非所问？

输出要求（只输出 JSON，不要任何其他文字）：
{
  "action": "accept" 或 "revise" 或 "continue_tool",
  "issues": ["问题1", "问题2"],
  "revised_reply": "修订后的回复（仅当 action=revise 时填写，否则为 null）"
}

action 的选择规则：
- 草稿达标 → "accept"，issues 填 []。
- 草稿有错但可直接修正（如语气、措辞、漏了补充说明）→ "revise"，
  并在 revised_reply 给出修订版。
- 草稿因缺少可查证的信息而无法回答（如漏查库存、漏了某类商品、约束未验证）
  → "continue_tool"，在 issues 里写明缺什么，让 AI 补充调用工具后再回答。
"""


def get_reflection_prompt():
    """
    返回 Reflection 自检的专用 Prompt。
    """
    return REFLECTION_PROMPT
