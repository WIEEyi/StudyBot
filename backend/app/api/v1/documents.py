"""
文档上传管理路由

提供的接口:
- POST   /documents          — 上传文档（multipart/form-data，支持 PDF/MD/TXT/HTML）
- GET    /documents          — 文档分页列表（支持 file_type 过滤）
- GET    /documents/{id}     — 文档详情（含提取的文本内容）
- DELETE /documents/{id}     — 删除文档（同时删除磁盘文件）
"""

import os
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status as http_status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.document import Document
from app.schemas.document import DocumentResponse, DocumentListResponse

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/documents", tags=["文档管理"])

# 支持的文件类型
ALLOWED_TYPES = {"pdf", "md", "txt", "html"}


# ===================== 文本提取 =====================

def _extract_text_from_pdf(file_bytes: bytes) -> str:
    """从 PDF 二进制数据中提取文本"""
    from PyPDF2 import PdfReader
    import io

    reader = PdfReader(io.BytesIO(file_bytes))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n\n".join(pages)


def _extract_text_from_markdown(file_bytes: bytes) -> str:
    """从 Markdown 文件中提取纯文本"""
    from markdown_it import MarkdownIt

    raw_text = file_bytes.decode("utf-8", errors="replace")
    md = MarkdownIt()
    # 渲染为 HTML 后再提取纯文本（去除 Markdown 语法标记）
    html = md.render(raw_text)
    # 简单的 HTML 标签去除
    import re
    text = re.sub(r"<[^>]+>", "", html)
    return text.strip()


def _extract_text_from_txt(file_bytes: bytes) -> str:
    """直接解码纯文本"""
    return file_bytes.decode("utf-8", errors="replace")


def _extract_text_from_html(file_bytes: bytes) -> str:
    """从 HTML 中提取纯文本"""
    import re
    raw = file_bytes.decode("utf-8", errors="replace")
    text = re.sub(r"<[^>]+>", "", raw)
    return text.strip()


# 提取器映射
_EXTRACTORS = {
    "pdf": _extract_text_from_pdf,
    "md": _extract_text_from_markdown,
    "txt": _extract_text_from_txt,
    "html": _extract_text_from_html,
}


# ===================== 辅助函数 =====================

def _detect_file_type(filename: str) -> str:
    """根据文件扩展名推断类型"""
    ext = Path(filename).suffix.lower().lstrip(".")
    if ext in ALLOWED_TYPES:
        return ext
    # markdown 可能的扩展名
    if ext == "markdown":
        return "md"
    if ext in ("htm",):
        return "html"
    # 默认当纯文本处理
    return "txt"


async def _get_user_document(doc_id: int, user: User, db: AsyncSession) -> Document:
    """查找文档并校验归属权"""
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()

    if doc is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"文档不存在: id={doc_id}",
        )
    if doc.user_id != user.id:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="无权操作此文档",
        )
    return doc


# ===================== 接口实现 =====================

@router.post("", response_model=DocumentResponse, status_code=http_status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """上传文档并自动提取文本内容

    支持 PDF / Markdown / TXT / HTML 四种格式。
    文件名作为默认标题，提取的文本存入 content 字段。
    """
    if not file.filename:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="文件名不能为空",
        )

    # 检测文件类型
    file_type = _detect_file_type(file.filename)
    if file_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型: {file_type}，仅支持 {ALLOWED_TYPES}",
        )

    # 流式读取文件内容（边读边检查大小，防止内存耗尽）
    file_bytes = bytearray()
    chunk_size = 1024 * 1024  # 每次读 1MB
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        file_bytes.extend(chunk)
        if len(file_bytes) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=http_status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"文件过大，最大允许 {settings.MAX_UPLOAD_SIZE // (1024*1024)}MB",
            )
    file_bytes = bytes(file_bytes)

    # 确保上传目录存在
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # 生成唯一文件名，避免冲突
    unique_name = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = str(upload_dir / unique_name)

    # 保存文件到磁盘
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    # 提取文本内容
    content = ""
    try:
        extractor = _EXTRACTORS.get(file_type, _extract_text_from_txt)
        content = extractor(file_bytes)
    except Exception as e:
        logger.warning("文本提取失败 (file=%s): %s", file.filename, e)
        content = ""

    # 创建数据库记录
    title = Path(file.filename).stem  # 去掉扩展名作为标题
    doc = Document(
        user_id=current_user.id,
        title=title,
        file_path=file_path,
        content=content,
        file_type=file_type,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    logger.info(
        "上传文档: id=%s, title=%s, type=%s, size=%d bytes, user_id=%s",
        doc.id, doc.title, doc.file_type, len(file_bytes), current_user.id,
    )

    # 异步触发向量化（Celery 后台任务，不阻塞 API 响应）
    try:
        from app.celery_app.tasks import generate_document_embeddings
        generate_document_embeddings.delay(document_id=doc.id, content=content)
        logger.info("已触发 Celery embedding 任务: document_id=%s", doc.id)
    except Exception as e:
        logger.warning("触发 Celery embedding 任务失败（RabbitMQ 可能未就绪）: %s", e)
    # 即使 Celery 不可用也不阻塞响应

    return DocumentResponse.model_validate(doc)


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    file_type: str = Query(None, description="按类型过滤: pdf/md/txt/html"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """获取当前用户的文档分页列表"""
    conditions = [Document.user_id == current_user.id]
    if file_type:
        conditions.append(Document.file_type == file_type)

    # 总数
    count_q = select(func.count()).where(*conditions)
    total = (await db.execute(count_q)).scalar()

    # 分页数据
    query = (
        select(Document)
        .where(*conditions)
        .order_by(Document.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    docs = result.scalars().all()

    return DocumentListResponse(
        items=[DocumentResponse.model_validate(d) for d in docs],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取文档详情（含提取的文本内容）"""
    doc = await _get_user_document(doc_id, current_user, db)
    return DocumentResponse.model_validate(doc)


@router.delete("/{doc_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除文档（同时清理磁盘文件）"""
    doc = await _get_user_document(doc_id, current_user, db)

    # 删除磁盘上的文件
    if doc.file_path and os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except OSError as e:
            logger.warning("删除文件失败: %s — %s", doc.file_path, e)

    await db.delete(doc)
    await db.commit()

    logger.info("删除文档: id=%s, title=%s", doc_id, doc.title)
