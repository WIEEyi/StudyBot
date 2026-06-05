# Step 11: RAG 问答 — 语义搜索 + AI 答案生成 (DigestAgent)

> **日期**: 2026-06-05
> **状态**: ✅ 完成
> **分支**: feature/step-10-vector-embedding（未切新分支，继续在 Step 10 分支开发）

---

## 目标

在 Step 10 语义搜索基础上，增加 LLM 答案生成能力，实现完整的 RAG（检索增强生成）问答流程。

---

## 技术概念

| 概念 | 说明 |
|------|------|
| RAG (Retrieval-Augmented Generation) | 先检索相关文档，再将文档作为上下文喂给 LLM 生成答案 |
| DigestAgent | 基于 LangGraph 的 RAG Agent（search_chunks → generate_answer） |
| Prompt 工程 | 将搜索到的分块 + 用户问题组装为结构化 prompt，要求 LLM 引用来源 |
| 引用溯源 | 答案中标注每个事实来自哪个文档的分块 |

---

## 创建的文件

### 源码文件

1. **`backend/app/schemas/qa.py`** — QA Pydantic 模型
   - `QARequest` — question (1-1000), document_id (optional), top_k (1-20, default 5)
   - `CitationItem` — chunk_id, document_id, document_title, chunk_index, content, similarity
   - `QAResponse` — question, answer, citations

2. **`backend/app/agents/digest_agent.py`** — DigestAgent LangGraph 工作流
   - `AnswerOutput` / `CitationOutput` — LLM 结构化输出模型
   - `DigestState` — LangGraph 状态定义
   - `search_chunks()` — 向量化问题 → pgvector 语义搜索
   - `generate_answer()` — 构建 RAG Prompt → 调用 LLM → 解析引用
   - `build_digest_graph()` — 构建两节点工作流
   - `run_digest()` — 公开入口函数

3. **`backend/app/api/v1/qa.py`** — RAG 问答 API 端点
   - `POST /api/v1/qa/ask` — RAG 知识库问答

### 测试文件

4. **`backend/tests/api/v1/test_qa.py`** — RAG 问答单元测试
   - `TestQAAsk` — 正常流程（3 tests）
   - `TestQAValidation` — 参数校验（5 tests）
   - `TestQAAuthErrors` — 权限测试（2 tests）
   - `TestQAEdgeCases` — 边界条件（2 tests）

### 文档更新

5. **PRD 中英文** — 补充 §2.3.2 RAG 问答详细描述（输入输出、RAG 流程、边界条件、技术实现）
6. **API 中英文** — 新增 §3.5 RAG 问答模块（`POST /api/v1/qa/ask` 完整 API 文档）

---

## 修改的文件

7. **`backend/app/main.py`** — 注册 `qa_router`
8. **`PROJECT_TRACKER.md`** — 更新当前状态（Step 11 完成），下一步指向 Step 12

---

## 设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| Agent 模式 | LangGraph 两节点工作流 | 与 PlannerAgent 保持一致 |
| LLM 模型 | gpt-4o-mini | RAG 场景知识主要来自检索上下文，轻量模型即可 |
| 搜索复用 | 复用 embedding_service.embed_query() + pgvector SQL | 与 Step 10 搜索共用基础设施，避免重复 |
| 引用格式 | LLM 返回 chunk_id，后端映射回完整 Citation | 分离关注点：LLM 只需关心 ID，后端负责组装完整信息 |
| 结构化输出 | ChatOpenAI.with_structured_output(AnswerOutput) | 确保 LLM 返回的答案 + 引用格式正确 |

---

## 测试验证

```
docker compose exec backend pytest -v
111/111 passed (3m 12s)
```

新增 12 个测试全部通过: 正常流程 3 + 参数校验 5 + 权限 2 + 边界 2

---

## API 端点

```
POST /api/v1/qa/ask
```

请求:
```json
{"question": "Python 中如何实现异步编程", "document_id": null, "top_k": 5}
```

响应:
```json
{
  "question": "Python 中如何实现异步编程",
  "answer": "Python 的异步编程主要通过 asyncio 库实现...",
  "citations": [{"chunk_id": 5, "document_id": 1, "document_title": "...", ...}]
}
```

---

## 关键发现

- RAG 问答的 DigestAgent 比 PlannerAgent 更简单（同步请求-响应，不需要 WebSocket 流式推送）
- LLM 结构化输出（with_structured_output）能可靠地获取格式化的答案和引用列表
- 测试中 mock ChatOpenAI 类本身（而非实例方法）是 mock langchain LLM 调用的最简洁方式
- 当搜索不到相关分块时（无文档或相似度 < threshold），Agent 优雅降级返回友好提示
