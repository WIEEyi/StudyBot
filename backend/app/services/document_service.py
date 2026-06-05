"""
文档服务模块

提供文档文本提取和文件管理功能。支持 4 种格式:
- PDF: PyPDF2 逐页提取
- Markdown: 直接读取（保留格式）
- TXT: 直接读取
- HTML: BeautifulSoup4 提取纯文本
"""

import os
import uuid
import logging
from pathlib import Path
from typing import Optional
from fastapi import UploadFile, HTTPException, status

from app.schemas.document import EXT_TO_TYPE, SUPPORTED_DOCUMENT_TYPES

logger = logging.getLogger(__name__)

# 文件存储根目录（Docker 容器内路径）
UPLOAD_ROOT = Path("/app/uploads")
# 最大文件大小 50MB
MAX_FILE_SIZE = 50 * 1024 * 1024


# ===================== 文件类型校验 =====================

def _get_extension(filename: str) -> str:
    """从文件名提取小写扩展名（不含点）"""
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def validate_file_type(filename: str) -> str:
    """校验文件类型是否支持，返回 file_type 值

    Raises:
        HTTPException 422: 文件类型不支持
    """
    ext = _get_extension(filename)
    if ext not in SUPPORTED_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"不支持的文件类型 '.{ext}'，仅支持: {', '.join(sorted(SUPPORTED_DOCUMENT_TYPES))}",
        )
    return EXT_TO_TYPE[ext]


# ===================== 文本提取函数 =====================

def extract_text_from_pdf(file_path: Path) -> str:
    """PyPDF2 提取 PDF 文本

    遍历 PDF 每一页，提取文本后拼接。空页自动跳过。
    """
    from PyPDF2 import PdfReader

    reader = PdfReader(str(file_path))
    pages: list[str] = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text and text.strip():
            pages.append(text.strip())
    return "\n\n".join(pages)


def extract_text_from_markdown(file_path: Path) -> str:
    """直接读取 Markdown 文件，保留原始文本格式"""
    return file_path.read_text(encoding="utf-8")


def extract_text_from_txt(file_path: Path) -> str:
    """直接读取纯文本文件"""
    return file_path.read_text(encoding="utf-8")


def extract_text_from_html(file_path: Path) -> str:
    """BeautifulSoup4 提取 HTML 纯文本（去掉所有标签）"""
    from bs4 import BeautifulSoup

    html_content = file_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html_content, "html.parser")
    # 移除 script 和 style 标签（它们的内容不是正文）
    for tag in soup(["script", "style"]):
        tag.decompose()
    # get_text() 会自动合并空白，去掉多余换行
    text = soup.get_text(separator="\n", strip=True)
    return text


def extract_text(file_path: Path, file_type: str) -> str:
    """统一文本提取入口，根据 file_type 分发到对应提取器

    Args:
        file_path: 磁盘上的文件路径
        file_type: 文件类型 (pdf/md/txt/html)

    Returns:
        提取后的纯文本内容

    Raises:
        HTTPException 500: 文本提取失败
    """
    extractors = {
        "pdf": extract_text_from_pdf,
        "md": extract_text_from_markdown,
        "txt": extract_text_from_txt,
        "html": extract_text_from_html,
    }
    extractor = extractors.get(file_type)
    if extractor is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"不支持的文件类型: {file_type}",
        )

    try:
        logger.info("开始提取文本: %s (类型: %s)", file_path.name, file_type)
        text = extractor(file_path)
        logger.info(
            "文本提取完成: %s, 共 %d 字符", file_path.name, len(text)
        )
        return text
    except Exception as e:
        logger.error("文本提取失败: %s, 错误: %s", file_path.name, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文本提取失败: {str(e)}",
        )


# ===================== 文件管理函数 =====================

async def save_upload_file(upload_file: UploadFile, user_id: int) -> tuple[Path, str]:
    """保存上传文件到磁盘

    文件按 {user_id}/{uuid}.{ext} 路径保存，避免同名冲突。

    Args:
        upload_file: FastAPI UploadFile 对象
        user_id: 当前用户 ID

    Returns:
        (file_path, file_type) — 保存路径和文件类型

    Raises:
        HTTPException 422: 文件为空
        HTTPException 413: 文件超过大小限制
        HTTPException 500: 写入失败
    """
    # 1. 校验文件类型
    original_name = upload_file.filename or "untitled"
    file_type = validate_file_type(original_name)

    # 2. 读取文件内容
    content_bytes = await upload_file.read()

    # 3. 校验文件大小
    if len(content_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="文件为空，请上传非空文件",
        )
    if len(content_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"文件大小超过限制 ({MAX_FILE_SIZE // 1024 // 1024}MB)",
        )

    # 4. 保存到磁盘
    ext = upload_file.filename.rsplit(".", 1)[-1].lower() if "." in (upload_file.filename or "") else file_type
    unique_name = f"{uuid.uuid4().hex}{'.' + ext}"
    user_dir = UPLOAD_ROOT / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    file_path = user_dir / unique_name

    try:
        file_path.write_bytes(content_bytes)
        logger.info("文件保存成功: %s (用户: %d, 大小: %d 字节)", file_path, user_id, len(content_bytes))
    except Exception as e:
        logger.error("文件保存失败: %s, 错误: %s", file_path, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文件保存失败",
        )

    return file_path, file_type


def delete_upload_file(file_path_str: Optional[str]) -> None:
    """删除磁盘上的上传文件（如果存在）

    删除失败只记录日志，不抛出异常（尽力而为策略）。
    """
    if not file_path_str:
        return
    file_path = Path(file_path_str)
    if file_path.exists():
        try:
            file_path.unlink()
            logger.info("文件删除成功: %s", file_path)
        except Exception as e:
            logger.warning("文件删除失败（磁盘操作）: %s, 错误: %s", file_path, str(e))
