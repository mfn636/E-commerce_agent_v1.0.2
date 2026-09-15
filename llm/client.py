'''
可考虑进行宏观限定client为单一领域
'''

import os
import time

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# 默认模型；可用环境变量 LLM_MODEL 覆盖
DEFAULT_MODEL = "deepseek-v4-flash"


def _cached_tokens(usage):
    """
    兼容不同厂商的"缓存命中 token"字段：
    - DeepSeek: usage.prompt_cache_hit_tokens
    - OpenAI / 智谱: usage.prompt_tokens_details.cached_tokens
    """
    if usage is None:
        return 0
    v = getattr(usage, "prompt_cache_hit_tokens", None)
    if v is not None:
        return int(v)
    details = getattr(usage, "prompt_tokens_details", None)
    v = getattr(details, "cached_tokens", None) if details is not None else None
    return int(v) if v is not None else 0


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
        # 每次调用的用量/耗时日志（供指标统计，不影响返回）
        self.usage_log = []

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

        t0 = time.perf_counter()
        response = self.client.chat.completions.create(**params)
        latency_ms = (time.perf_counter() - t0) * 1000

        if stream:
            return response

        usage = getattr(response, "usage", None)
        self.usage_log.append({
            "model": self.model,
            "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
            "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
            "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
            "cached_tokens": _cached_tokens(usage),
            "latency_ms": round(latency_ms, 1),
        })

        return response.choices[0].message
