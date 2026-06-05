# Step 10: 向量嵌入 — 文本分块 + OpenAI Embedding + pgvector

**日期**: 2026-06-05
**分支**: feature/step-10-vector-embedding
**状态**: ✅ 完成（99/99 测试通过）

---

## 目标

将文档文本分割为小块、通过 OpenAI Embedding 生成向量、存入 pgvector，并提供语义搜索接口。

## 新创建的文件 (7个)

| 文件 | 说明 |
|------|------|
| `app/models/document_chunk.py` | DocumentChunk ORM 模型 (VECTOR(1536)) |
| `app/services/embedding_service.py` | chunk_text + embed_chunks + process_document + embed_query |
| `app/schemas/document_chunk.py` | DocumentChunkResponse, DocumentChunkListResponse |
| `app/schemas/search.py` | SearchRequest, SearchResultItem, SearchResponse |
| `app/api/v1/search.py` | POST /api/v1/search 语义搜索 |
| `alembic/versions/a1b2_create_document_chunks.py` | 迁移: CREATE EXTENSION vector + 建表 + HNSW 索引 |
| `tests/api/v1/test_embedding.py` | 12 个嵌入测试用例 |
| `tests/api/v1/test_search.py` | 9 个搜索测试用例 |

## 修改的文件 (7个)

| 文件 | 变更 |
|------|------|
| `requirements.txt` | + `pgvector==0.3.6` |
| `models/document.py` | 添加 `chunks` relationship |
| `models/user.py` | 添加 `document_chunks` relationship + TYPE_CHECKING |
| `models/__init__.py` | 导出 DocumentChunk |
| `api/v1/documents.py` | + embed 端点 + chunks 端点 + 上传自动嵌入 |
| `api/v1/tasks.py` | + `milestone` 字段创建支持 |
| `main.py` | 注册 search router |
| `tests/conftest.py` | + mock_embedding_service fixture |
| `Dockerfile` | pip 使用清华镜像加速 |

## 测试结果

99/99 全部通过：
- 22 文档测试 (Step 9)
- 12 嵌入测试 (Step 10)
- 19 目标测试 (Step 7)
- 9 搜索测试 (Step 10)
- 24 任务测试 (Step 7)
- 13 WebSocket Planner 测试 (Step 8)

## 关键技术决策

1. **HNSW 索引** 而非 IVFFlat（无需训练步骤，小数据集性能更好）
2. **上传时自动触发嵌入** + 显式 embed 端点（双重入口）
3. **嵌入失败优雅降级**（不阻塞文档上传）
4. **搜索端点放在 Step 10** 验证嵌入流水线，Step 11 在此基础上增加 AI 问答

## 数据库变更

- 启用 pgvector 扩展: `CREATE EXTENSION IF NOT EXISTS vector`
- 新表: `document_chunks` (id, document_id, user_id, chunk_index, content, embedding, token_count, timestamps)
- HNSW 索引: `ix_document_chunks_embedding_hnsw` USING hnsw (embedding vector_cosine_ops)

## 新增 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/documents/{id}/embed | 触发文档分块 + 向量嵌入 |
| GET | /api/v1/documents/{id}/chunks | 获取文档分块列表（分页，不含向量） |
| POST | /api/v1/search | 语义搜索（余弦相似度） |
