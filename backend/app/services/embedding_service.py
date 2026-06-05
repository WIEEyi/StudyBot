"""
Embedding 向量化服务模块

提供文档文本分块、OpenAI 嵌入向量生成、以及完整的文档处理流水线。

技术栈:
- 分块: LangChain RecursiveCharacterTextSplitter + tiktoken (cl100k_base)
- 嵌入: langchain_openai OpenAIEmbeddings (text-embedding-3-small, 1536 维)
- 存储: pgvector (通过 DocumentChunk 模型 + Vector(1536) 列)

分块参数:
- chunk_size=500 tokens, chunk_overlap=50 tokens
- 重叠保证上下文连续性，相邻块之间有 50 token 的共同内容
"""

import logging
from fastapi import HTTPException, status as http_status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.document import Document
from app.models.document_chunk import DocumentChunk

logger = logging.getLogger(__name__)

# 分块参数（可根据实际效果调整）
CHUNK_SIZE = 500   # 每个块的最大 token 数
CHUNK_OVERLAP = 50  # 相邻块重叠的 token 数


# ===================== 文本分块 =====================

def chunk_text(content: str) -> list[dict]:
    """将文档纯文本分割为重叠块

    使用 LangChain RecursiveCharacterTextSplitter + tiktoken cl100k_base 编码器。
    cl100k_base 与 text-embedding-3-small 使用的编码一致，确保 token 计数准确。

    Args:
        content: 文档提取后的纯文本内容

    Returns:
        [{"text": str, "token_count": int}, ...] 分块列表，空内容返回空列表
    """
    import tiktoken
    from langchain.text_splitter import RecursiveCharacterTextSplitter

    if not content or not content.strip():
        logger.info("文档内容为空，跳过文本分块")
        return []

    # 使用 from_tiktoken_encoder 确保按 token 数分割（而非字符数）
    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        encoding_name="cl100k_base",
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )

    chunks = splitter.split_text(content)

    # 用 tiktoken 精确计算每个块的 token 数（用于成本追踪）
    encoding = tiktoken.get_encoding("cl100k_base")
    result = []
    for text in chunks:
        token_count = len(encoding.encode(text))
        result.append({"text": text, "token_count": token_count})

    logger.info(
        "文本分块完成: 输入 %d 字符 → %d 个分块 (chunk_size=%d, overlap=%d)",
        len(content), len(result), CHUNK_SIZE, CHUNK_OVERLAP,
    )
    return result


# ===================== 向量嵌入生成 =====================

async def embed_chunks(texts: list[str]) -> list[list[float]]:
    """对一批文本块批量生成嵌入向量

    使用 OpenAI text-embedding-3-small 模型，每个向量 1536 维。
    LangChain 的 aembed_documents 内部会自动分批（最多 2048 条/请求）。

    Args:
        texts: 文本块列表

    Returns:
        [[float, ...], ...] 嵌入向量列表，与输入一一对应

    Raises:
        HTTPException 500: OpenAI API 调用失败
    """
    from langchain_openai import OpenAIEmbeddings

    if not texts:
        return []

    settings = get_settings()
    embeddings_model = OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,        # text-embedding-3-small
        openai_api_key=settings.OPENAI_API_KEY,
        openai_api_base=settings.OPENAI_API_BASE,
    )

    try:
        logger.info("开始生成嵌入向量: %d 个文本块", len(texts))
        vectors = await embeddings_model.aembed_documents(texts)
        logger.info("嵌入向量生成完成: %d 个向量, 维度=%d", len(vectors), len(vectors[0]) if vectors else 0)
        return vectors
    except Exception as e:
        logger.error("OpenAI Embedding API 调用失败: %s", str(e))
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"嵌入向量生成失败: {str(e)}",
        )


async def embed_query(query: str) -> list[float]:
    """将单个搜索查询文本向量化

    Args:
        query: 用户输入的自然语言搜索词

    Returns:
        [float, ...] 1536 维查询向量

    Raises:
        HTTPException 500: OpenAI API 调用失败
    """
    from langchain_openai import OpenAIEmbeddings

    settings = get_settings()
    embeddings_model = OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        openai_api_key=settings.OPENAI_API_KEY,
        openai_api_base=settings.OPENAI_API_BASE,
    )

    try:
        vector = await embeddings_model.aembed_query(query)
        return vector
    except Exception as e:
        logger.error("查询向量化失败: %s", str(e))
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询向量化失败: {str(e)}",
        )


# ===================== 完整处理流水线 =====================

async def process_document(document: Document, db: AsyncSession) -> int:
    """编排文档分块→嵌入→存储的完整流水线

    流程:
    1. 删除该文档的旧分块（幂等：支持重新嵌入）
    2. 调用 chunk_text 分割文本
    3. 调用 embed_chunks 生成向量
    4. 批量 INSERT DocumentChunk 到数据库

    Args:
        document: Document ORM 对象（必须已包含 content 和 user_id）
        db: 数据库异步会话

    Returns:
        创建的分块数量，content 为空时返回 0
    """
    if not document.content or not document.content.strip():
        logger.info("文档 content 为空 (doc_id=%d)，跳过嵌入", document.id)
        return 0

    # 1. 删除旧分块（支持重新嵌入）
    await db.execute(
        delete(DocumentChunk).where(DocumentChunk.document_id == document.id)
    )

    # 2. 文本分块
    chunk_data = chunk_text(document.content)
    if not chunk_data:
        await db.commit()
        return 0

    # 3. 提取文本列表用于向量化
    texts = [c["text"] for c in chunk_data]

    # 4. 生成嵌入向量
    vectors = await embed_chunks(texts)

    # 5. 批量创建 DocumentChunk ORM 对象
    chunk_objs = []
    for i, (chunk, vector) in enumerate(zip(chunk_data, vectors)):
        chunk_obj = DocumentChunk(
            document_id=document.id,
            user_id=document.user_id,
            chunk_index=i,
            content=chunk["text"],
            embedding=vector,
            token_count=chunk["token_count"],
        )
        chunk_objs.append(chunk_obj)

    db.add_all(chunk_objs)
    await db.commit()

    logger.info(
        "文档嵌入完成: doc_id=%d, 分块数=%d, 总 token 数=%d",
        document.id,
        len(chunk_objs),
        sum(c["token_count"] for c in chunk_data),
    )
    return len(chunk_objs)
