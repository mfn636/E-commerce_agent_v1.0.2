"""
agent/memory/history.py

短期记忆容器：只存/取 user/assistant 最终对话，不含 state/session/裁剪。
"""



class ConversationHistory:

    def __init__(self):
        self.messages = []

    def add_user(self, content):
        """追加一条 user 消息。"""
        self.messages.append({"role": "user", "content": content})

    def add_assistant(self, content):
        """追加一条 assistant 消息。"""
        self.messages.append({"role": "assistant", "content": content})

    def get_window(self, n):
        """返回最近 n 条历史（发送时用）；不足 n 条则全返回。"""
        return self.messages[-n:]

    def to_dict(self):
        """序列化：全量消息列表（供会话持久化）。"""
        return self.messages

    def from_dict(self, messages):
        """恢复历史（供会话持久化加载）。"""
        self.messages = list(messages or [])