"""
Search 语义搜索相关的 Pydantic 请求/响应模型

Step 10: 基础语义搜索（返回分块 + 相似度）
Step 11: 将在此之上增加 LLM 问答生成（RAG）
"""

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """语义搜索请求"""
    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="自然语言搜索词，会被向量化后执行相似度搜索",
    )
    top_k: int = Field(
        5,
        ge=1,
        le=50,
        description="返回的最相关分块数量",
    )
    threshold: float = Field(
        0.3,
        ge=0.0,
        le=1.0,
        description="最低余弦相似度阈值 (0-1)，低于此值的结果将被过滤",
    )


class SearchResultItem(BaseModel):
    """单条搜索结果

    包含分块内容、来源文档信息和相似度分数。
    """
    chunk_id: int
    document_id: int
    document_title: str
    chunk_index: int
    content: str
    similarity: float = Field(description="余弦相似度 (0-1)，1 表示完全匹配")
    token_count: int | None = None


class SearchResponse(BaseModel):
    """语义搜索响应"""
    query: str
    results: list[SearchResultItem]
    total: int
