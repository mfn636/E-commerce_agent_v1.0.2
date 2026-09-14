"""
domain/models/faq.py

售后问答存储模型：忠实镜像 data/faq.json 的一条 FAQ 记录。
"""

from pydantic import BaseModel, Field


class FaqItem(BaseModel):
    category: str = Field(description="FAQ 类别，如 退换货、支付、发货")
    question: str = Field(description="常见问题")
    answer: str = Field(description="标准回答")
