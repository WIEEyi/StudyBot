# Step 21: 补齐缺失的后端 API

> **日期**: 2026-06-24
> **状态**: ✅ 完成
> **测试**: 132/132 通过

---

## 背景

Steps 9-16 的 ORM 模型存在，但后端 API 路由/Schema/测试均未实现。Step 20 补全了 Quiz 和 Concept。Step 21 补齐剩余 5 个模块。

## 缺失分析

通过扫描前端 `api.ts` 和页面中的 API 调用，确认以下模块缺失：

| 模块 | 前端页面 | 需要的端点 |
|------|----------|-----------|
| Documents | documents/page.tsx, qa/page.tsx, quiz/page.tsx | POST(GET/DELETE) |
| ReviewCards | review/page.tsx | CRUD + POST review |
| Dashboard | dashboard/page.tsx | overview + heatmap + streak |
| QA | qa/page.tsx | POST /qa/ask |
| WebSocket | (前端未直接使用) | WS /ws/plan |

## 实现过程

### Phase 1: 配置 + 模型

1. `config.py` — 添加 `UPLOAD_DIR` 和 `MAX_UPLOAD_SIZE`
2. `models/study_session.py` — 新建 StudySession ORM 模型
3. `models/user.py` — 添加 `study_sessions` 关系
4. `models/task.py` — 添加 `milestone`, `milestone_order`, `completed_at` 字段
5. `models/__init__.py` — 导出 StudySession

### Phase 2: Schemas

6. `schemas/document.py` — DocumentResponse / ListResponse / Update
7. `schemas/review_card.py` — ReviewCardCreate/Update/Response + SM-2 ReviewSubmission/Response
8. `schemas/dashboard.py` — DashboardOverview / HeatmapResponse / StreakResponse
9. `schemas/task.py` — TaskResponse 添加新字段

### Phase 3: API Routes

10. `api/v1/documents.py` — 文件上传(UploadFile) + 文本提取(PDF/MD/TXT/HTML) + CRUD
11. `api/v1/review_cards.py` — CRUD + SM-2 算法 + due_filter(overdue/today/all)
12. `api/v1/dashboard.py` — overview(聚合统计) + heatmap(按日期聚合) + streak(连续天数) + session(累加记录)
13. `api/v1/qa.py` — RAG 问答(关键词匹配，后续可升级向量搜索)
14. `api/v1/ws.py` — WebSocket PlannerAgent (从 main 分支恢复)
15. `agents/planner_agent.py` — LangGraph 三节点工作流 (从 main 分支恢复)
16. `main.py` — 注册全部 5 个新路由 + WebSocket

### Phase 4: Tests

17. `tests/api/v1/test_documents.py` — 12 个用例 (上传4种格式 + 列表/过滤 + 详情 + 删除 + 401)
18. `tests/api/v1/test_review_cards.py` — 13 个用例 (创建 + 列表/过滤 + 更新 + 删除 + SM-2评分高低/重置/无效 + 404)
19. `tests/api/v1/test_dashboard.py` — 7 个用例 (overview + heatmap + streak + session累加 + 401)
20. `tests/api/v1/test_qa.py` — 5 个用例 (无文档 + 有文档 + 指定文档 + 401 + 空问题)

### Phase 5: Bug 修复

21. `api/v1/concepts.py` — `/graph` 路由被 `/{concept_id}` 覆盖导致 422 → 调整注册顺序

### Phase 6: 数据库迁移

22. `alembic revision --autogenerate` → `eb0ace215fb2_add_study_sessions_and_task_fields.py`
23. `alembic upgrade head` → study_sessions 表 + tasks 新列

## SM-2 算法实现

```python
# rating >= 3: 回忆正确
if repetitions == 0: interval = 1
elif repetitions == 1: interval = 6
else: interval = round(interval * ease_factor)

# rating < 3: 回忆失败 → 重置
repetitions = 0, interval = 1

# ease_factor 调整 (最低 1.3)
EF' = EF + (0.1 - (5-q) * (0.08 + (5-q) * 0.02))
```

## 测试结果

```
132 passed, 0 failed — 39.64s
```

| 测试文件 | 用例数 |
|----------|--------|
| test_goals.py | 21 |
| test_tasks.py | 24 |
| test_concepts.py | 27 |
| test_quizzes.py | 21 |
| test_documents.py | 12 |
| test_review_cards.py | 13 |
| test_dashboard.py | 7 |
| test_qa.py | 5 |
| **总计** | **132** |
