"""
Document 文档 Pydantic 模型

用于文件上传、列表、详情等接口的请求/响应校验。
"""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    """文档响应（列表/详情通用）"""
    id: int
    user_id: int
    title: str
    file_type: str
    file_path: Optional[str] = None
    content: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    """文档分页列表"""
    items: list[DocumentResponse]
    total: int
    offset: int
    limit: int


class DocumentUpdate(BaseModel):
    """文档更新（仅标题可改）"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
