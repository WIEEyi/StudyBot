"""
Document 相关的 Pydantic 请求/响应模型
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

# 支持的文档格式
SUPPORTED_DOCUMENT_TYPES = {"pdf", "md", "txt", "html", "htm"}
# 文件扩展名 → file_type 映射
EXT_TO_TYPE = {
    "pdf": "pdf",
    "md": "md",
    "txt": "txt",
    "html": "html",
    "htm": "html",
}


# ===================== 请求模型 =====================

class DocumentCreate(BaseModel):
    """上传文档请求（title 可选，默认取文件名）"""
    title: Optional[str] = Field(
        None, min_length=1, max_length=255, description="文档标题，不传则取文件名"
    )


class DocumentUpdate(BaseModel):
    """更新文档信息请求
    仅允许更新标题，文件和内容不可通过此接口修改
    """
    title: Optional[str] = Field(None, min_length=1, max_length=255)


# ===================== 响应模型 =====================

class DocumentResponse(BaseModel):
    """文档响应（含基本信息 + 提取的文本内容）"""
    id: int
    user_id: int
    title: str
    file_path: Optional[str] = None
    file_type: str
    content: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    """文档分页列表响应"""
    items: list[DocumentResponse]
    total: int = Field(description="总记录数")
    offset: int = Field(description="当前偏移量")
    limit: int = Field(description="每页条数")
