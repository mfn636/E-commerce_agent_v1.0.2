'''
可考虑进行宏观限定client为单一领域
'''

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# 默认模型；可用环境变量 LLM_MODEL 覆盖
DEFAULT_MODEL = "deepseek-v4-flash"


class LLMClient:
    def __init__(self):
        api_key = os.getenv("DEEPSEEK_API_KEY")

        if not api_key:
            raise ValueError("未找到 DEEPSEEK_API_KEY")

        self.model = os.getenv("LLM_MODEL") or DEFAULT_MODEL
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1"
        )

    def chat(
        self,
        messages,           # 对话记录列表，格式：[{role, content}, ...]
        tools=None,         # 工具定义列表
        temperature=0.4,    # 随机程度，0=死板，1=放飞
        max_tokens=1024,    # 回答最长多少字
        stream=False,       # 是否流式输出
        response_format=None,
        system_prompt=None, # 人设 prompt（可以单独传，也可以塞 messages 里）
    ):

        if system_prompt:
            filtered = [m for m in messages if m["role"] != "system"]
            messages = [{"role": "system", "content": system_prompt}] + filtered

        params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"

        if response_format:
            params["response_format"] = response_format

        response = self.client.chat.completions.create(**params)

        if stream:
            return response

        return response.choices[0].message
