"""
eval/checker.py

规则通道：确定性断言（工具名、必备/禁止子串、记忆）。
返回问题列表，空列表 = 通过。
"""


def rule_check(case, replies, tool_calls, state_text):
    """
    Args:
        case: 用例
        replies: 本轮所有可见回复
        tool_calls: [{"name":..., "args":...}]
        state_text: 会话结束后的 State 条目库文本
    Returns:
        list[str]: 未通过的问题（空 = 通过）
    """
    issues = []
    called = [t["name"] for t in tool_calls]

    for tool in case.get("expect_tools", []):
        if tool not in called:
            issues.append(f"未调用预期工具：{tool}")

    for tool in case.get("forbid_tools", []):
        if tool in called:
            issues.append(f"不应调用工具：{tool}")

    text = "\n".join(replies)
    for s in case.get("must_contain", []):
        if s not in text:
            issues.append(f"缺少必需内容：{s}")
    for s in case.get("must_not_contain", []):
        if s in text:
            issues.append(f"出现禁止内容：{s}")

    for s in case.get("state_contains", []):
        if s not in (state_text or ""):
            issues.append(f"记忆缺少：{s}")

    return issues
