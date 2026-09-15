"""
domain/models/knowledge.py

知识检索的输出视图：从知识库（FAQ / 指南 / 政策 / 帮助）检索到的片段。
"""

from pydantic import BaseModel, Field


class KnowledgeItem(BaseModel):
    source: str = Field(description="来源类型：faq / guide / policy / help")
    title: str = Field(description="标题（FAQ 问题，或文档标题）")
    content: str = Field(description="知识片段正文")
    score: float = Field(description="与查询的相似度得分")
