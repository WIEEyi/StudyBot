# 改进批次: DeepSeek 适配 + P2/P3 完善 + E2E + 异常处理审计

> **日期**: 2026-06-24
> **状态**: ✅ 完成
> **提交数**: 5 个 commits
> **测试**: 150 backend + 15 E2E

---

## 1. DeepSeek V4 Pro 全局适配

**改动**: 配置层抽象化，默认使用 DeepSeek
- `config.py`: `OPENAI_API_KEY/BASE` → `LLM_API_KEY/BASE`，默认 `deepseek-chat`
- `planner_agent.py`: ChatOpenAI 参数改用 LLM_API_KEY/BASE
- `qa.py`: 提示信息更新
- `.env.example` + `.env`: DeepSeek 默认值
- `PRD_zh/en.md`: 技术栈更新为 DeepSeek V4 Pro

## 2. P0: Quiz AI 出题接 LLM

- `quizzes.py`: mock 数据替换为 DeepSeek 结构化输出 (ChatOpenAI + with_structured_output)
- `test_quizzes.py`: 更新测试 (nonexistent doc + empty content)

## 3. P0: 前端 PlannerAgent 入口

- `goals/[id]/page.tsx`: 添加 AI 生成计划 UI (WebSocket 连接 + 实时进度展示 + 里程碑预览)

## 4. P2: Services 层重构

- `services/sm2_service.py`: SM-2 算法抽取
- `services/quiz_service.py`: LLM 出题逻辑抽取
- `services/task_service.py`: 任务状态变更逻辑抽取 (completed_at 自动管理)
- `services/scheduler_service.py`: 计划重排逻辑抽取
- `services/embedding_service.py`: 文本分块 + 向量嵌入 + 语义搜索

## 5. P2: SchedulerAgent

- `api/v1/scheduler.py`: POST /goals/{id}/reschedule (balanced/aggressive/relaxed)
- `test_scheduler.py`: 5 个测试

## 6. P2: Celery 异步任务

- `celery_app/celery.py`: Celery 应用配置
- `celery_app/tasks.py`: 文档提取 + Embedding 任务
- `celery_app/db_sync.py`: Worker 同步数据库工具
- `docker-compose.yml`: 添加 celery-worker 服务

## 7. P3: RAG 升级

- `models/document_chunk.py`: DocumentChunk 模型 + pgvector 向量列
- `services/embedding_service.py`: chunk_text + generate_embedding + embed_and_store + semantic_search
- `api/v1/qa.py`: 语义搜索优先 + 关键词匹配回退
- `requirements.txt`: 添加 pgvector==0.3.6
- Alembic 迁移: document_chunks 表

## 8. P3: 生产部署

- `docker-compose.prod.yml`: 生产编排 (postgres/redis/rabbitmq/backend/celery/nginx)
- `backend/Dockerfile.prod`: gunicorn + 4 workers
- `nginx/nginx.conf`: 反向代理 + WebSocket + Gzip + 限流
- `.github/workflows/ci.yml`: GitHub Actions (pytest + frontend build)

## 9. P3: 前端 UX 组件

- `components/EmptyState.tsx`: 空状态友好提示
- `components/ErrorBoundary.tsx`: 全局错误边界
- `components/Skeleton.tsx`: 骨架屏加载
- `layout.tsx`: ErrorBoundary 包裹

## 10. E2E: Playwright 测试框架

- `playwright.config.ts`: Chromium, 串行执行, 失败截图/视频
- `e2e/fixtures.ts`: Auth fixture (API 注册 + localStorage 注入)
- 5 个 spec 文件, 15 个测试: auth + goals-tasks + documents-qa + review-quiz + planner

## 11. 全栈异常处理审计 (12 项修复)

**🔴 严重 (3)**:
- `main.py`: 全局异常处理器 (SQLAlchemyError + 兜底 Exception)
- `auth.py`: IntegrityError 兜底 (注册竞态条件)
- `database.py`: get_db() rollback 保护

**🟡 重要 (5)**:
- `rate_limiter.py` + auth 端点限流 (5-10次/分钟, 测试自动禁用)
- `documents.py`: 流式文件上传 (边读边检查大小)
- `qa.py`: 语义搜索异常日志 (exc_info=True)
- `scheduler.py`: Service 调用 try/except
- `api.ts`: 5xx 友好提示

**🟢 改进 (4)**:
- `quizzes.py` + `quiz.py`: 批改透明化 (graded/skipped 计数)
- `dashboard/page.tsx`: 热力图错误状态
- 6 个前端页面: 错误消息统一 (ApiError.detail + fallback)
- `main.py`: CORS 收紧 (具体 methods/headers)
