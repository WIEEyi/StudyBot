# Step 26: LLM 集成 — QA 接入 DeepSeek + 对话历史持久化

**日期**: 2026-06-27～2026-06-28  
**分支**: `feature/step-20-quiz-concepts`

---

## 目标

1. QA 模块接入 DeepSeek LLM 生成 RAG 综合回答
2. 对话历史数据模型 + API + 前端管理

---

## 新增文件 (3 个)

- `backend/app/models/conversation.py` — Conversation + ChatMessage ORM 模型
- `backend/app/api/v1/chat_history.py` — 对话历史 CRUD API（列表/创建/详情/删除）
- `backend/alembic/versions/396413980466_add_conversations_and_chat_messages.py` — DB 迁移

## 修改文件 (7 个)

### 后端 LLM 答案生成
- `backend/app/api/v1/qa.py`
  - 新增 `_generate_llm_answer()` — ChatOpenAI + RAG context → 综合回答
  - 新增 `_build_fallback_answer()` — LLM 不可用时的手动拼接回退
  - 新增 `_save_chat_message()` — 自动保存问答到对话历史
  - `QARequest` 添加 `conversation_id`
  - `QAResponse` 添加 `conversation_id`
  - `CitationItem.relevance` → `similarity`

### 路由注册
- `backend/app/main.py` — 注册 `chat_history_router`
- `backend/app/models/__init__.py` — 导出 Conversation, ChatMessage
- `backend/app/models/user.py` — 添加 conversations 反向关系

### 前端
- `frontend/src/lib/types.ts` — 新增 Conversation/QAMessage 类型，QAResponse 添加 conversation_id
- `frontend/src/lib/api.ts` — 新增 getConversations/createConversation/getConversation/deleteConversation
- `frontend/src/app/qa/page.tsx` — 对话管理侧边栏（历史列表/切换/新建/删除）+ convId 状态管理

---

## 验证

- `npx next build` — 12/12 页面编译通过 ✅
- `docker compose exec backend pytest -v` — 162/162 全部通过 ✅
