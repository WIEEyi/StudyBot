"""
文档管理 CRUD 路由

提供的接口:
- POST   /documents             — 上传文档（multipart form: file + title）
- GET    /documents             — 分页列表（支持 file_type 过滤）
- GET    /documents/{id}        — 文档详情（含完整提取文本）
- DELETE /documents/{id}        — 删除文档（文件 + 数据库记录）
- POST   /documents/{id}/embed  — 触发文档分块 + 向量嵌入
- GET    /documents/{id}/chunks — 获取文档分块列表（不含向量）
"""

import logging
from fastapi import (
    APIRouter, Depends, HTTPException, File, Form, UploadFile, Query,
    status as http_status,
)
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.schemas.document import (
    DocumentResponse,
    DocumentListResponse,
    SUPPORTED_DOCUMENT_TYPES,
)
from app.schemas.document_chunk import (
    DocumentChunkResponse,
    DocumentChunkListResponse,
)
from app.services.document_service import (
    save_upload_file,
    delete_upload_file,
    extract_text,
)
from app.services.embedding_service import process_document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["文档管理"])


# ===================== 辅助函数 =====================

async def _get_user_document(
    document_id: int, user: User, db: AsyncSession
) -> Document:
    """查找文档并校验归属权
    1. 查文档是否存在 → 404
    2. 文档是否属于当前用户 → 403
    """
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"文档不存在: id={document_id}",
        )
    if document.user_id != user.id:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="无权访问此文档",
        )
    return document


# ===================== API 端点 =====================

@router.post("", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(..., description="要上传的文档文件"),
    title: str = Form(None, description="文档标题，不传则取文件名"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """上传一个新文档

    1. 接收文件并校验类型
    2. 保存文件到磁盘
    3. 提取文本内容
    4. 创建数据库记录
    """
    # 1. 保存文件
    file_path, file_type = await save_upload_file(file, current_user.id)

    # 2. 提取文本
    content = extract_text(file_path, file_type)

    # 3. 创建数据库记录
    doc_title = (title or file.filename or "untitled").strip()
    document = Document(
        user_id=current_user.id,
        title=doc_title,
        file_path=str(file_path),
        content=content,
        file_type=file_type,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    logger.info(
        "文档上传成功: id=%d, title=%s, type=%s, 内容长度=%d",
        document.id, document.title, document.file_type, len(content),
    )

    # 4. 自动生成嵌入向量（如果内容非空）
    if document.content and document.content.strip():
        try:
            chunk_count = await process_document(document, db)
            logger.info(
                "文档上传 + Embedding 完成: id=%d, title=%s, 分块数=%d",
                document.id, document.title, chunk_count,
            )
        except Exception as e:
            # Embedding 失败不要阻塞上传 — 文档已保存，用户可稍后重试
            logger.error(
                "Embedding 失败（文档已保存，可通过 /embed 端点重试）: doc_id=%d, error=%s",
                document.id, str(e),
            )
    else:
        logger.info("文档上传成功（无内容，跳过 Embedding）: id=%d", document.id)

    return document


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    file_type: str = Query(None, description="按文件类型过滤: pdf, md, txt, html"),
    offset: int = Query(0, ge=0, description="分页偏移量"),
    limit: int = Query(20, ge=1, le=100, description="每页条数（最大 100）"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的文档列表（分页）

    - 支持按 file_type 过滤
    - 列表中的 content 截断为前 200 字符作为预览
    """
    # 构建查询条件
    conditions = [Document.user_id == current_user.id]
    if file_type is not None:
        if file_type not in SUPPORTED_DOCUMENT_TYPES:
            # htm 是 html 的别名，统一为 html
            valid_types = {t for t in SUPPORTED_DOCUMENT_TYPES if t != "htm"}
            if file_type not in valid_types:
                raise HTTPException(
                    status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"无效的文件类型: {file_type}，支持: {', '.join(sorted(valid_types))}",
                )
        conditions.append(Document.file_type == file_type)

    # 查总数和分页数据
    total_result = await db.execute(
        select(func.count(Document.id)).where(*conditions)
    )
    total = total_result.scalar()

    result = await db.execute(
        select(Document)
        .where(*conditions)
        .order_by(Document.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    documents = result.scalars().all()

    # 列表响应中 content 截断为预览
    items = []
    for doc in documents:
        doc_dict = {
            "id": doc.id,
            "user_id": doc.user_id,
            "title": doc.title,
            "file_path": doc.file_path,
            "file_type": doc.file_type,
            "content": doc.content[:200] if doc.content else None,
            "created_at": doc.created_at,
            "updated_at": doc.updated_at,
        }
        items.append(DocumentResponse(**doc_dict))

    return DocumentListResponse(
        items=items,
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取文档详情（含完整提取的文本内容）"""
    document = await _get_user_document(document_id, current_user, db)
    return document


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除文档

    1. 删除磁盘上的原始文件（尽力而为）
    2. 删除数据库记录
    """
    document = await _get_user_document(document_id, current_user, db)

    # 先记下文件路径，再删数据库记录
    file_path_str = document.file_path
    await db.delete(document)
    await db.commit()

    # 删除磁盘文件
    delete_upload_file(file_path_str)

    logger.info("文档删除成功: id=%d", document_id)


# ===================== 嵌入向量端点 =====================

@router.post("/{document_id}/embed")
async def embed_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """触发文档分块 + 向量嵌入

    - 如果文档已有分块，先删除旧分块再重新生成（幂等）
    - 如果文档 content 为空，返回 422 错误
    - 返回创建的分块数量
    """
    document = await _get_user_document(document_id, current_user, db)

    if not document.content or not document.content.strip():
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="文档内容为空，无法生成嵌入向量",
        )

    try:
        chunk_count = await process_document(document, db)
        logger.info(
            "Embedding 完成: doc_id=%d, 分块数=%d", document_id, chunk_count
        )
        return {
            "document_id": document_id,
            "chunks_created": chunk_count,
        }
    except Exception as e:
        logger.error("Embedding 失败: doc_id=%d, error=%s", document_id, str(e))
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"嵌入向量生成失败: {str(e)}",
        )


@router.get(
    "/{document_id}/chunks",
    response_model=DocumentChunkListResponse,
)
async def list_document_chunks(
    document_id: int,
    offset: int = Query(0, ge=0, description="分页偏移量"),
    limit: int = Query(50, ge=1, le=200, description="每页条数（最大 200）"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取文档的分块列表（分页，不含 embedding 向量）

    分块按 chunk_index 升序排列，保持原文顺序。
    embedding 向量仅用于服务端相似度计算，不通过 API 返回。
    """
    document = await _get_user_document(document_id, current_user, db)

    # 查总数
    count_query = select(func.count(DocumentChunk.id)).where(
        DocumentChunk.document_id == document_id
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 查分页数据（按 chunk_index 升序，保持原文顺序）
    query = (
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    chunks = result.scalars().all()

    return DocumentChunkListResponse(
        items=[DocumentChunkResponse.model_validate(c) for c in chunks],
        total=total,
        offset=offset,
        limit=limit,
    )
