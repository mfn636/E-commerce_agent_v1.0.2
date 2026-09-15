"""
eval/runner.py

一键评测：跑黄金用例 → 规则断言（checker）+ LLM-judge（judge）→ 输出 Markdown 报告。

运行（项目根目录）：
    python -m eval.runner
"""

from collections import defaultdict
from datetime import datetime
from pathlib import Path

from agent.core.loop import EcommerceAgent
from llm.client import LLMClient
from eval.cases import CASES
from eval.checker import rule_check
from eval.judge import llm_judge

JUDGE_PASS = 0.6
REPORT_PATH = Path("eval/report.md")


def _cleanup_eval_sessions():
    d = Path("sessions")
    if d.is_dir():
        for f in d.glob("eval_*.json"):
            f.unlink()


def run():
    _cleanup_eval_sessions()
    llm = LLMClient()
    rows = []
    domain_stat = defaultdict(lambda: {"total": 0, "passed": 0})
    totals = {"llm_calls": 0, "total_tokens": 0, "latency_ms": 0.0}

    for case in CASES:
        case_mark = len(llm.usage_log)
        agent = EcommerceAgent(session_id=f"eval_{case['id']}", llm=llm)

        replies, tool_calls = [], []
        for turn in case["turns"]:
            r = agent.run(turn)
            replies.extend(r.replies)
            tool_calls.extend(r.tool_calls)

        issues = rule_check(case, replies, tool_calls, agent.state.text)

        judge = None
        if case.get("judge"):
            judge = llm_judge(llm, case["judge"], " / ".join(case["turns"]), "\n".join(replies))
            if judge["score"] < JUDGE_PASS:
                issues.append(f"judge 不达标（{judge['score']:.2f}）：{judge['reason']}")

        # 本用例用量（含多轮 + judge）
        entries = llm.usage_log[case_mark:]
        case_usage = {
            "llm_calls": len(entries),
            "total_tokens": sum(e["total_tokens"] for e in entries),
            "latency_ms": round(sum(e["latency_ms"] for e in entries), 1),
        }
        totals["llm_calls"] += case_usage["llm_calls"]
        totals["total_tokens"] += case_usage["total_tokens"]
        totals["latency_ms"] += case_usage["latency_ms"]

        passed = not issues
        domain_stat[case["domain"]]["total"] += 1
        domain_stat[case["domain"]]["passed"] += 1 if passed else 0
        rows.append({"case": case, "passed": passed, "issues": issues,
                     "judge": judge, "usage": case_usage})

    report = _render(domain_stat, rows, totals)
    REPORT_PATH.write_text(report, encoding="utf-8")
    _cleanup_eval_sessions()
    print(report)
    print(f"\n报告已写入：{REPORT_PATH}")


def _render(domain_stat, rows, totals):
    total_pass = sum(1 for r in rows if r["passed"])
    lines = [
        "# Agent 评测报告",
        "",
        f"> 时间：{datetime.now():%Y-%m-%d %H:%M} · 用例数：{len(rows)}",
        "",
        "## 各能力域通过率",
        "",
        "| 能力域 | 通过 / 总数 | 通过率 |",
        "|---|---|---|",
    ]
    for domain, s in domain_stat.items():
        rate = s["passed"] / s["total"] * 100 if s["total"] else 0
        lines.append(f"| {domain} | {s['passed']} / {s['total']} | {rate:.0f}% |")
    lines.append(f"| **合计** | **{total_pass} / {len(rows)}** | **{total_pass / len(rows) * 100:.0f}%** |")
    lines += [
        "",
        "## 用例明细",
        "",
        "| 用例 | 域 | 结果 | 说明 |",
        "|---|---|---|---|",
    ]
    for r in rows:
        case = r["case"]
        mark = "PASS" if r["passed"] else "FAIL"
        detail = "通过" if r["passed"] else "；".join(r["issues"])
        if r["judge"]:
            detail += f"（judge {r['judge']['score']:.2f}）"
        lines.append(f"| {case['id']} | {case['domain']} | {mark} | {detail} |")
    lines += [
        "",
        "## 成本 / 耗时",
        "",
        f"- LLM 调用：{totals['llm_calls']} 次",
        f"- 总 token：{totals['total_tokens']}",
        f"- 总耗时：{totals['latency_ms'] / 1000:.1f}s",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    run()
