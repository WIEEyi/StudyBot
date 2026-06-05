"""
QA RAG 问答相关的 Pydantic 请求/响应模型

Step 11: RAG 问答 = 语义搜索 + AI 答案生成
"""

from pydantic import BaseModel, Field


class QARequest(BaseModel):
    """RAG 问答请求

    用户输入自然语言问题，系统自动搜索相关文档分块并生成带引用的答案。
    """
    question: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="用户的自然语言问题",
    )
    document_id: int | None = Field(
        None,
        ge=1,
        description="可选，限定搜索特定文档；不传则搜索用户所有文档",
    )
    top_k: int = Field(
        5,
        ge=1,
        le=20,
        description="检索的最相关分块数量",
    )
    threshold: float = Field(
        0.3,
        ge=0.0,
        le=1.0,
        description="最低余弦相似度阈值 (0-1)，低于此值的结果将被过滤",
    )


class CitationItem(BaseModel):
    """单条引用来源

    包含分块内容、来源文档信息和相似度分数，方便用户追溯原文。
    """
    chunk_id: int
    document_id: int
    document_title: str
    chunk_index: int
    content: str = Field(description="分块的原始文本内容")
    similarity: float = Field(description="余弦相似度 (0-1)，1 表示完全匹配")


class QAResponse(BaseModel):
    """RAG 问答响应

    answer 是 LLM 基于检索到的文档上下文生成的答案；
    citations 是答案中引用的文档分块列表，按相似度降序排列。
    """
    question: str
    answer: str = Field(description="LLM 基于文档上下文生成的答案")
    citations: list[CitationItem] = Field(
        default_factory=list,
        description="答案中引用的文档分块列表"
    )
