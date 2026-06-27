# 审计修复 — 全量代码审计 + 10 项修复

**日期**: 2026-06-28  
**分支**: `feature/step-20-quiz-concepts`

---

## 审计范围

33 文件，1798 行新增，273 行删除（Steps 24-26 全部变更）

## 发现与修复

### 🔴 严重
1. **HNSW 向量索引被删除** — autogenerate 迁移错误删除 pgvector 索引
   - 修复：手动 `CREATE INDEX ... USING hnsw`

### 🟠 高优先
2. **WebSocket 空 URL 异常** — `new WebSocket("")` 抛出 SyntaxError
   - 修复：`useWebSocket.ts` connect() 添加 `if (!url) return;`
3. **对话 ID 前后端断连** — QAResponse 不返回 conversation_id，前端不存储
   - 修复：`QAResponse` 添加 `conversation_id`，前端 `handleAsk` 捕获并 setConvId

### 🟡 中优先
4. **迁移 autogenerate 漂移** — 错误删除不存在的 columns/constraints
   - 修复：清理迁移文件，仅保留 conversations/chat_messages 创建
5. **N+1 COUNT 查询** — list_conversations 每条对话单独 COUNT
   - 修复：`LEFT JOIN + GROUP BY` 单次查询
6. **冗余 planning state** — 可从 planPhase 派生
   - 修复：删除 `useState(false)`，改为派生值

### 🟢 低优先
7. Celery ↔ Service 逻辑重复 — 保留（同步/异步上下文差异）
8. 手写 Markdown 解析器 — 保留（后续可用 react-markdown）
9. 侧边栏遮罩重复 — 保留（两处用途略有差异）
10. API 文档 `relevance`→`similarity` — 中英文文档已同步

---

## 验证

- `npx next build` — 12/12 ✅
- `docker compose exec backend pytest -v` — 162/162 ✅
