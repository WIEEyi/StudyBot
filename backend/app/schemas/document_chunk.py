"""
DocumentChunk 相关的 Pydantic 请求/响应模型

注意: 响应中不包含 embedding 向量字段（1536 维浮点数数组太大，
不适合通过 API 传输）。向量仅用于服务端相似度计算。
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DocumentChunkResponse(BaseModel):
    """分块响应（不含 embedding 向量）"""
    id: int
    document_id: int
    chunk_index: int
    content: str
    token_count: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentChunkListResponse(BaseModel):
    """分块分页列表响应"""
    items: list[DocumentChunkResponse]
    total: int
    offset: int
    limit: int
