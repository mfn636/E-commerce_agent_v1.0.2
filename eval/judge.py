"""
eval/judge.py

LLM-judge 通道：对开放回答按评分标准打分（0~1）。
"""

import json

JUDGE_SYSTEM = "你是一个严格的评测裁判，只输出 JSON。"

JUDGE_TEMPLATE = """请根据评分标准，判断 AI 回复是否达标。

评分标准：{criteria}

用户输入：{user}

AI 回复：{reply}

只输出 JSON：{{"score": 0~1 的小数, "reason": "简短理由"}}
- 完全达标 = 1.0；部分达标 = 0~1 之间；不达标 = 0.0。
"""


def llm_judge(llm, criteria, user, reply):
    """调用 LLM 打分；失败则返回 0 分并说明。"""
    try:
        resp = llm.chat(
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM},
                {"role": "user", "content": JUDGE_TEMPLATE.format(
                    criteria=criteria, user=user, reply=reply)},
            ],
            response_format={"type": "json_object"},
        )
        obj = json.loads(resp.content)
        return {"score": float(obj.get("score", 0)), "reason": obj.get("reason", "")}
    except Exception as e:
        return {"score": 0.0, "reason": f"judge 调用失败：{e}"}
