# Step 25: RAG 完善 — Celery 自动向量化 + 语义搜索验证

**日期**: 2026-06-27  
**分支**: `feature/step-20-quiz-concepts`

---

## 目标

1. 文档上传后自动触发 Embedding 生成（Celery 后台任务）
2. QA Schema 修复（字段不一致）
3. 数据库迁移链修复

---

## 修改文件 (5 个)

### QA Schema 修复
- `backend/app/api/v1/qa.py`
  - `CitationItem.relevance` → `similarity`（对齐前端 TS 类型）
  - `QARequest` 添加 `threshold` 字段
  - 修复 `request.threshold or 0.3` → `request.threshold`

### Celery Embedding 任务
- `backend/app/celery_app/tasks.py`
  - `generate_document_embeddings` 占位符 → 真实实现
  - 分块 → HTTP 调用 Embedding API → 存入 document_chunks 表
  - 同步 `httpx.Client` + 每块错误跳过 + 最多重试 2 次

### Celery Worker DB 工具
- `backend/app/celery_app/db_sync.py`
  - 新增 `delete_document_chunks(document_id)` — 删除旧块
  - 新增 `insert_document_chunk(...)` — 插入新块含 embedding

### 文档上传触发
- `backend/app/api/v1/documents.py`
  - 上传成功后 `generate_document_embeddings.delay(document_id, content)`
  - try/except 包裹，Celery 不可用不影响上传响应

### 数据库迁移修复
- `backend/alembic/versions/4e3d32cdf2c8_add_milestone_to_tasks.py`
  - `down_revision` 从 `4c33aef808eb`（已删除）→ `eb0ace215fb2`
- 手动修复 `alembic_version` 表
- 丢弃旧 `study_sessions` 表（`session_date` → `study_date`）
- 手动创建新 `study_sessions` 表
- Stamp DB 到 `a1b2c3d4e5f6`

---

## 验证

- `docker compose exec backend pytest -v` — 162/162 全部通过 ✅
