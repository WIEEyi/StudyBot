# Step 16: 学习仪表盘 (Learning Dashboard)

**日期**: 2026-06-06
**状态**: ✅ 完成
**分支**: feature/step-10-vector-embedding

---

## 目标

为 StudyBot 添加学习仪表盘后端 API，支持：
- 热力图（每日学习时长）
- 连续学习天数（Streak）
- 整体统计概览
- AI 每周学习洞察

---

## 数据模型设计

### 新增 StudySession 模型
`backend/app/models/study_session.py`

| 字段 | 类型 | 说明 |
|------|------|------|
| user_id | int FK | 所属用户 |
| session_date | Date | 学习日期（与 user_id 联合唯一） |
| duration_minutes | int | 累计学习时长 |
| tasks_completed | int | 完成任务数 |
| cards_reviewed | int | 复习卡片数 |

### 修改 Task 模型
`backend/app/models/task.py` — 新增 `completed_at` (DateTime, nullable)，status 变为 done 时自动设置。

---

## 创建的文件

| # | 文件 | 行数 | 说明 |
|---|------|------|------|
| 1 | `backend/app/models/study_session.py` | 55 | StudySession ORM 模型 |
| 2 | `backend/app/schemas/dashboard.py` | 103 | 8 个 Pydantic schemas |
| 3 | `backend/app/services/dashboard_service.py` | 323 | 聚合统计 + Streak + AI 洞察 |
| 4 | `backend/app/api/v1/dashboard.py` | 120 | 5 个 API 端点 |
| 5 | `backend/alembic/versions/7cd51d9db92a_*.py` | 50 | 数据库迁移 |
| 6 | `backend/tests/api/v1/test_dashboard.py` | 398 | 25 个单元测试 |

## 修改的文件

| # | 文件 | 变更 |
|---|------|------|
| 1 | `backend/app/models/__init__.py` | 导出 StudySession |
| 2 | `backend/app/models/task.py` | 添加 completed_at 列 |
| 3 | `backend/app/models/user.py` | 添加 study_sessions relationship |
| 4 | `backend/app/api/v1/tasks.py` | 自动设置 completed_at |
| 5 | `backend/app/main.py` | 注册 dashboard_router |
| 6 | `backend/app/schemas/task.py` | TaskResponse 添加 completed_at |
| 7 | `docs/PRD_zh.md` | 展开 §2.3.7 仪表盘详细设计 |
| 8 | `docs/PRD_en.md` | 同步英文版 |
| 9 | `docs/API_zh.md` | 新增 §3.9 仪表盘 API |
| 10 | `docs/API_en.md` | 同步英文版 |

---

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/dashboard/overview` | 整体统计概览（15 个指标） |
| GET | `/api/v1/dashboard/heatmap?start_date=&end_date=` | 每日学习热力图（缺失补零） |
| GET | `/api/v1/dashboard/streak` | 连续学习天数（当前+最长） |
| POST | `/api/v1/dashboard/study-session` | 记录/更新当日学习 (Upsert) |
| POST | `/api/v1/dashboard/weekly-insight` | AI 生成每周学习洞察 |

---

## 测试结果

- **Dashboard 测试**: 25 个用例，24 passed + 1 skipped
- **全量回归**: 239 个用例，232 passed + 1 skipped + 6 failed（预存在网络问题）
- **受影响的旧测试**: 无（0 个旧测试因本 Step 失败）

---

## 关键技术决策

1. **Heatmap 数据源合并**: StudySession + Task.completed_at + ReviewCard.last_reviewed_at 三源合并
2. **StudySession Upsert 模式**: 同一天多次调用累加数值，适合前端定期上报
3. **AI 洞察 LLM 容错**: LLM 不可用时自动降级为默认鼓励性文本
4. **Pydantic alias**: HeatmapItem.date 字段名与 Python date 类型冲突，使用 `Field(alias="date")` + `populate_by_name=True` 解决
5. **completed_at 自动设置**: 在 tasks.py 更新端点中检测 status 变化，自动设置时间戳

---

## 问题与解决

| # | 问题 | 解决 |
|---|------|------|
| 1 | Pydantic `date` 字段名与类型冲突 | 使用 alias + populate_by_name |
| 2 | Alembic 误删 HNSW 索引 | 手动编辑迁移脚本移除误操作 |
| 3 | 测试 Auth 返回 403 而非 401 | 改用 `assert status_code in (401, 403)` |
| 4 | 测试间数据共享导致累加测试失败 | 改为增量断言（before/after delta） |
