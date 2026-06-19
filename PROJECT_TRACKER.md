# StudyBot 项目开发追踪文档

> **给 Claude 的新终端指令**：阅读此文件，在 `## 当前状态` 找到进度，从 `### 🔄 进行中` 或 `### 📋 下一步` 继续开发。按照 `## 开发原则` 引导用户。

---

## 开发原则

1. **文件/类/方法级引导**：每一步都要解释到每个文件、每个类、每个方法的级别
2. **先解释再动手**：每步开始前说明目标、涉及的技术概念、会创建/修改哪些文件
3. **完成后更新本文档**：标记步骤完成，更新当前状态，预写下一步的详细指令
4. **关键代码写中文注释**：帮助理解逻辑
5. **执行中同步更新 task_logs/**：每完成一个子步骤立即追加到对应 step 文件，不要等全部做完再补（容易漏）
6. **每次回答问题后更新 QA_LOG.md**：记录用户问题和 Claude 的回答，方便回顾
7. **功能模块必须伴随单元测试**：每个功能模块（API 路由、Service、工具函数）开发完成后，立即编写对应的单元测试。测试文件跟随源码目录镜像结构——
   - 测试目录: `backend/tests/` 内镜像 `app/` 的目录结构
   - 命名规则: `test_{模块名}.py`（如 `test_goals.py`、`test_tasks.py`）
   - 测试框架: pytest + httpx.AsyncClient（FastAPI 官方推荐）
   - 覆盖要求: 每个端点的正常路径 + 异常路径（401 未认证、404 不存在、422 参数校验）
   - 测试完成后必须运行 `docker compose exec backend pytest -v` 确认全部通过
8. **新模块开发前置要求**：每个新模块开发前，必须先完成——
   - 在 `docs/PRD_zh.md` 中补充该模块的 PRD 子章节（功能描述、输入输出、边界条件）
   - 在 `docs/API_zh.md` 中补充该模块的 API 文档（接口路径、请求/响应格式、错误码）
   - PRD 和 API 文档需要审查通过后才能开始写代码
   - 英文版 PRD 和 API 文档同步更新
9. **Git 分支工作流**：
   - **开始开发**: `git checkout develop` → `git pull origin develop` → `git checkout -b feature/step-XX-xxx`
   - **开发中**: 小步提交，commit message 格式 `[Step X] 简短描述`
   - **合并前**: 代码审查（自查：测试是否通过、权限校验是否完整、是否有安全隐患）
   - **合并**: 审查通过后 `git checkout develop` → `git merge feature/step-XX-xxx`
10. **会话终止流程**：每次开发结束时执行以下步骤，确保下次新会话能无缝恢复——
   - 更新 `PROJECT_TRACKER.md` 当前状态、进度日志、下一步
   - 更新 `task_logs/step_NN_xxx.md` 追加本次会话完成的所有工作
   - 更新 `TASK_LOG.md` 索引和「当前会话」部分
   - 更新 `QA_LOG.md` 追加本次会话的所有问答
   - 更新 `docs/API_zh.md` 和 `docs/API_en.md`（如有新增/修改接口）
   - `git push origin feature/step-XX-xxx`（推送当前分支）
   - 在 `TASK_LOG.md` 末尾写入「会话结束」标记，含恢复指令

---

## 项目文档结构

| 文件 | 用途 | 更新时机 |
|------|------|----------|
| `PROJECT_TRACKER.md` | 项目追踪文档（本文件） | 每个步骤完成后 |
| `TASK_LOG.md` | 任务执行日志索引 | 步骤开始/结束时 |
| `task_logs/step_NN_xxx.md` | 各 Step 详细执行记录 | 步骤执行中同步更新 |
| `QA_LOG.md` | 问题与回答记录 | 每次回答问题后 |
| `docs/PRD_zh.md` | 中文产品需求文档 | 新模块开发前 + 完成后 |
| `docs/PRD_en.md` | English PRD | Sync with Chinese PRD |
| `docs/API_zh.md` | 中文 API 接口文档 | 新模块开发前 + 接口变更后 |
| `docs/API_en.md` | English API Documentation | Sync with Chinese API docs |

---

## 项目概况

| 属性 | 值 |
|------|-----|
| 项目名 | StudyBot |
| 描述 | 个人学习与任务调度 AI Agent 应用 |
| 技术栈 | FastAPI + LangGraph + React(Next.js) + PostgreSQL(pgvector) + Redis + RabbitMQ |
| 仓库 | E:\StudyCode\pyProject |

## 核心功能

1. **AI学习计划生成** (PlannerAgent) - 输入目标 -> 自动分解为里程碑和每日任务
2. **知识库RAG问答** (DigestAgent) - 上传文档 -> 语义搜索 -> AI问答带引用
3. **间隔复习** (SM-2算法) - 根据遗忘曲线自动安排复习时间
4. **自动出题** (QuizAgent) - 基于学习材料生成测验
5. **知识图谱** - 可视化概念关系网络
6. **动态计划调整** (SchedulerAgent) - 检测进度落后 -> 自动重排
7. **学习仪表盘** - 热力图、连续天数、AI每周洞察

---

## 项目目录结构

```
pyProject/
├── PROJECT_TRACKER.md          <- 项目追踪文档
├── TASK_LOG.md                 <- 任务执行日志
├── QA_LOG.md                   <- 问题与回答记录
├── .gitignore                  <- Git 忽略规则
├── docs/                       <- 项目文档
│   ├── PRD_zh.md               <- 中文产品需求文档
│   ├── PRD_en.md               <- English PRD
│   ├── API_zh.md               <- 中文 API 文档
│   └── API_en.md               <- English API Docs
├── backend/
│   ├── __init__.py
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI 应用入口
│   │   ├── config.py            # 环境变量配置 (Pydantic Settings)
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── database.py      # SQLAlchemy 异步引擎 + 会话工厂
│   │   │   ├── security.py      # JWT 编解码 + 密码哈希
│   │   │   ├── logging_config.py # 日志系统配置
│   │   │   └── redis_client.py  # Redis 连接池
│   │   ├── models/              # SQLAlchemy ORM 模型
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── user.py
│   │   │   ├── learning_goal.py
│   │   │   ├── task.py
│   │   │   └── ... (document, review_card, quiz, concept 等)
│   │   ├── schemas/             # Pydantic 请求/响应模型
│   │   ├── api/                 # 路由处理
│   │   │   ├── deps.py
│   │   │   └── v1/
│   │   ├── agents/              # LangGraph Agent 系统
│   │   ├── services/            # 业务逻辑层
│   │   ├── mq/                  # RabbitMQ 集成
│   │   └── celery_app/          # Celery 异步任务
│   ├── tests/                   # 单元测试 (镜像 app/ 目录结构)
│   │   ├── __init__.py
│   │   ├── conftest.py          # 共享 fixtures
│   │   └── api/v1/              # API v1 测试
│   ├── alembic/                 # 数据库迁移
│   └── requirements.txt
├── frontend/                    # Next.js 前端 (后续创建)
└── docker-compose.yml           # 容器编排
```

---

## 当前状态

- **阶段**: Phase 3 完成 ✅
- **步骤**: Step 19 完成 ✅
- **开始时间**: 2026-05-31
- **最后更新**: 2026-06-19 (Step 19 前端间隔复习页面 + AI 问答页面)

---

## 进度日志

### ✅ 已完成

| 日期 | 步骤 | 描述 |
|------|------|------|
| 2026-05-31 | Step 1 | 删除旧目录(long-chain, React)，创建项目骨架目录，初始化 __init__.py 和三个跟踪文档 |
| 2026-05-31 | Step 2 | Docker Compose 环境搭建完成，PostgreSQL+Redis+RabbitMQ 均 healthy |
| 2026-06-01 | Step 3 | FastAPI 项目初始化 + Docker 化。health check 通过 ✅ |
| 2026-06-01 | Step 4 | 日志系统改进完成 ✅ |
| 2026-06-01 | Step 5 | JWT 用户认证系统完成 ✅ |
| 2026-06-01 | Step 6 | 数据库模型 + Alembic 迁移完成 ✅ |
| 2026-06-02 | Step 7 | Goals + Tasks CRUD API + 单元测试（45/45 全部通过）✅ |
| 2026-06-02 | 基础设施 | PRD 中英文文档 + API 中英文文档 + Git 初始化 + 开发流程完善 ✅ |
| 2026-06-02 | Step 8 | PlannerAgent + WebSocket — AI 学习计划生成 ✅ |
| 2026-06-04 | Step 9 | 文档上传 + 文本提取 ✅ |
| 2026-06-05 | Step 10 | 向量嵌入 — 文本分块 + OpenAI Embedding + pgvector 存储 + 语义搜索 ✅ |
| 2026-06-05 | Step 11 | RAG 问答 — 语义搜索 + AI 答案生成 (DigestAgent) ✅ |
| 2026-06-05 | Step 12 | 间隔复习 — SM-2 算法 + ReviewCard CRUD + 评分 API ✅ |
| 2026-06-05 | Step 13 | 自动出题 — AI 基于文档生成测验题 (QuizAgent) ✅ |
| 2026-06-05 | 审计 | 全量代码审计: 修复 3 个问题 (Quiz注释 + threshold + milestone_order) ✅ |
| 2026-06-05 | Step 14 | 知识图谱: Concept CRUD + Relations + Graph API + 45 个测试 ✅ |
| 2026-06-05 | Step 15 | 动态计划调整 — SchedulerAgent + POST /goals/{id}/schedule + 12 个测试 ✅ |
| 2026-06-06 | Step 16 | 学习仪表盘 — StudySession + 热力图 + 连续天数 + AI 周报 + 25 个测试 ✅ |
| 2026-06-06 | Step 17 | Next.js 前端 — 登录页 + 仪表盘页面 (StatCard/Heatmap/Streak/AI周报) ✅ |
| 2026-06-06 | Step 18 | 前端扩展 — Goals/Tasks CRUD + 文档上传管理 ✅ |
| 2026-06-19 | Step 19 | 前端扩展 — 间隔复习页面 + AI 问答页面 ✅ |

### 🔄 进行中

_无_

### 📋 下一步

| 步骤 | 描述 |
|------|------|
| Step 20 | 前端扩展 — 自动出题页面 + 知识图谱可视化 |

### 💡 待办改进

- [ ] 前端热力图改用 Recharts 日历热力图组件
- [ ] 复习页可添加批量导入功能（从文档自动生成卡片）
- [ ] QA 页可添加对话历史持久化

---

## 详细步骤指令

---

### Step 1: 项目骨架搭建 ✅ (已完成)

**目标**: 建立项目目录结构，Python 包初始化

**创建的文件**:
- `backend/__init__.py` - 后端包标识
- `backend/app/__init__.py` - FastAPI 应用主包
- `backend/app/core/__init__.py` - 核心基础设施
- `backend/app/models/__init__.py` - 数据模型
- `backend/app/schemas/__init__.py` - Pydantic 模型
- `backend/app/api/__init__.py` - API 路由
- `backend/app/agents/__init__.py` - Agent 系统
- `backend/app/services/__init__.py` - 业务服务
- `backend/app/mq/__init__.py` - 消息队列
- `backend/app/celery_app/__init__.py` - 异步任务

---

### Step 2: Docker Compose 环境搭建 ✅ (已完成)

**目标**: 用 Docker Compose 拉起 PostgreSQL 16、Redis 7、RabbitMQ 3.12 三个服务

**创建的文件**:
- `docker-compose.yml` - 定义三个服务 + 网络 + 数据卷
- `backend/.env.example` - 环境变量模板

**技术要点**:
- 镜像: pgvector/pgvector:pg16, redis:7-alpine, rabbitmq:3.12-management-alpine
- 数据持久化: 命名卷 (volumes)
- 健康检查: postgres(pg_isready), redis(redis-cli ping), rabbitmq(rabbitmq-diagnostics)

---

### Step 3: FastAPI 项目初始化 + 配置管理 + 数据库连接 ✅ (已完成)

**创建的文件**:
- `backend/requirements.txt` - Python 依赖清单
- `backend/app/config.py` - Pydantic Settings 配置管理
- `backend/app/core/database.py` - SQLAlchemy 异步引擎 + 依赖注入
- `backend/app/core/redis_client.py` - Redis 异步连接池
- `backend/app/main.py` - FastAPI 入口（lifespan、CORS、/health、/）
- `backend/Dockerfile` - Python 3.11-slim 镜像

**关键发现**: Docker Desktop Windows 端口代理有 Bug，后端必须进 Docker 用内网通信

---

### Step 4: 日志系统改进 ✅ (已完成)

**创建的文件**:
- `backend/app/core/logging_config.py` - 日志配置模块
  - `setup_logging()` - 清空 root/uvicorn/SQLAlchemy handler
  - `_clear_logger_handlers()` - 递归清除子 logger handler
  - 格式: `2026-06-01 17:30:00 | INFO     | app.main | 数据库连接成功`

**修改的文件**:
- `backend/app/main.py` - print -> logging
- `backend/.dockerignore` - 加 logs/

**验证结果**: ✅ 控制台无重复，文件日志正常

---

### Step 5: 用户认证系统 (JWT) ✅ (已完成)

**目标**: 实现完整的用户注册/登录/JWT 认证系统

**创建的文件**:
- `backend/app/core/security.py` — JWT 编解码（access/refresh/decode）+ bcrypt 密码哈希
- `backend/app/models/base.py` — SQLAlchemy 声明式基类 + TimestampMixin
- `backend/app/models/user.py` — User 模型（email/username/hashed_password/is_active）
- `backend/app/schemas/auth.py` — Pydantic 请求/响应模型
- `backend/app/api/deps.py` — get_current_user 依赖注入
- `backend/app/api/v1/__init__.py` — v1 路由包
- `backend/app/api/v1/auth.py` — POST /register, /login, /refresh
- `backend/app/api/v1/users.py` — GET /users/me

**修改的文件**:
- `backend/app/main.py` — 注册 v1 路由，启动时自动建表
- `backend/requirements.txt` — 添加 bcrypt==4.2.1

**关键发现**: passlib 1.7.4 与新版 bcrypt 不兼容，改用 bcrypt 直接调用

**最终 API**:
```
POST /api/v1/auth/register  -> 201  {access_token, refresh_token, token_type}
POST /api/v1/auth/login     -> 200  {access_token, refresh_token, token_type}
POST /api/v1/auth/refresh   -> 200  {access_token, refresh_token, token_type}
GET  /api/v1/users/me       -> 200  {id, email, username, is_active, created_at, updated_at}
```

---

### Step 6: 数据库模型 + Alembic 迁移 ✅ (已完成)

**创建的文件**:
- 7 个 ORM 模型: learning_goal, task, document, review_card, quiz, concept, concept_relation
- `backend/alembic/` — Alembic 迁移工具（env.py 接入 Base.metadata + 项目配置）

**关键发现**: Alembic 需要同步驱动，`env.py` 中将 `asyncpg` 替换为 `psycopg2`

**修改的文件**:
- `backend/app/models/user.py` — 添加 6 个反向 relationship
- `backend/app/models/__init__.py` — 导出所有模型
- `backend/app/main.py` — 移除 `create_all`，改用 Alembic

**数据库操作**:
```bash
# 修改模型后生成迁移
docker compose exec backend alembic revision --autogenerate -m "描述"
# 执行迁移
docker compose exec backend alembic upgrade head
```

---

### Step 7: Goals + Tasks CRUD API ✅ (已完成)

**目标**: 实现学习目标和任务的完整增删改查接口

**技术概念**:
- **RESTful CRUD**: Create(POST) / Read(GET) / Update(PUT) / Delete(DELETE)
- **分页**: offset + limit 分页，避免一次返回全量数据
- **权限隔离**: 用户只能操作自己的数据（通过 get_current_user 限定的 user_id 过滤）

**要创建的文件**:

**源码文件**:

1. `backend/app/schemas/goal.py` — Goal Pydantic 模型
   - `GoalCreate` — title, description, deadline
   - `GoalUpdate` — 所有字段可选（部分更新用）
   - `GoalResponse` — 包含 id / created_at / task 数量
   - `GoalListResponse` — 分页列表 {items, total, offset, limit}

2. `backend/app/schemas/task.py` — Task Pydantic 模型
   - `TaskCreate` — title, description, goal_id(optional), priority, due_date
   - `TaskUpdate` — 所有字段可选
   - `TaskResponse` — 完整 task 数据
   - `TaskListResponse` — 分页列表

3. `backend/app/api/v1/goals.py` — 目标路由
   - `GET    /goals` — 分页列表（支持 status 过滤）
   - `GET    /goals/{id}` — 单个目标详情（含 task 列表）
   - `POST   /goals` — 创建目标
   - `PUT    /goals/{id}` — 更新目标
   - `DELETE /goals/{id}` — 删除目标
   - `PATCH  /goals/{id}/status` — 切换状态

4. `backend/app/api/v1/tasks.py` — 任务路由
   - `GET    /tasks` — 分页列表（支持 goal_id/status/priority 过滤）
   - `GET    /tasks/{id}` — 单个任务详情
   - `POST   /tasks` — 创建任务
   - `PUT    /tasks/{id}` — 更新任务
   - `DELETE /tasks/{id}` — 删除任务

**测试文件** (跟随 app/ 目录镜像结构):

5. `backend/tests/__init__.py` — 测试包标识
6. `backend/tests/conftest.py` — 共享 fixtures（test client、测试数据库、认证 header）
7. `backend/tests/api/__init__.py`
8. `backend/tests/api/v1/__init__.py`
9. `backend/tests/api/v1/test_goals.py` — 目标 CRUD 测试
   - 正常: 创建/读取/更新/删除/切换状态
   - 异常: 401 无认证、404 目标不存在、422 参数校验
10. `backend/tests/api/v1/test_tasks.py` — 任务 CRUD 测试
   - 正常: 创建/读取/更新/删除
   - 异常: 401 无认证、404 任务不存在、422 参数校验

**要修改的文件**:
- `backend/app/main.py` — 注册 goals 和 tasks 路由
- `backend/requirements.txt` — 添加 pytest, pytest-asyncio, httpx

**验证方法**:

手动验证:
```bash
# 先登录获取 token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}' | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

# 创建学习目标
curl -X POST http://localhost:8000/api/v1/goals -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"学习 Python","description":"掌握 Python 全栈开发"}'

# 获取目标列表
curl http://localhost:8000/api/v1/goals -H "Authorization: Bearer $TOKEN"
```

自动化测试:
```bash
# 运行所有单元测试
docker compose exec backend pytest -v

# 只跑 goals 相关测试
docker compose exec backend pytest tests/api/v1/test_goals.py -v

# 只跑 tasks 相关测试
docker compose exec backend pytest tests/api/v1/test_tasks.py -v
```

### 本次会话完成 (2026-06-02)

**已创建的文件 (14个)**:
- ✅ `schemas/goal.py` — GoalCreate/Update/Response/DetailResponse/ListResponse
- ✅ `schemas/task.py` — TaskCreate/Update/Response/ListResponse
- ✅ `api/v1/goals.py` — 6 个端点（含分页/过滤/权限隔离）
- ✅ `api/v1/tasks.py` — 5 个端点（含分页/过滤/goal_id 校验）
- ✅ `tests/__init__.py`, `tests/api/__init__.py`, `tests/api/v1/__init__.py`
- ✅ `tests/conftest.py` — 测试 fixtures + dependency_overrides
- ✅ `tests/api/v1/test_goals.py` — 21 个测试用例（正常+异常）
- ✅ `tests/api/v1/test_tasks.py` — 24 个测试用例（正常+异常）
- ✅ `pytest.ini` — pytest 配置（pythonpath + asyncio_mode）

**已修改的文件 (5个)**:
- ✅ `main.py` — 注册 goals_router + tasks_router
- ✅ `requirements.txt` — 添加 pytest==8.3.3 + pytest-asyncio==0.24.0
- ✅ `schemas/task.py` — priority 字段改为 Literal 类型（添加枚举校验）
- ✅ `api/v1/goals.py` — 修复 `status` 参数名和模块名冲突（改 `http_status`）
- ✅ `backend/__init__.py` — 删除（与 app 包冲突导致 pytest 导入失败）

**测试验证结果**:
- ✅ `docker compose build backend` — 镜像重建成功
- ✅ `docker compose exec backend pytest -v` — 45/45 全部通过
- ✅ 手动 CRUD 验证（注册→创建目标→创建任务→分页→过滤→更新→删除）全部通过

**测试期间发现并修复的问题**:
1. `backend/__init__.py` 造成命名空间冲突 → 删除该文件
2. `tests/conftest.py` 的 `sys.path` 未使用 `abspath` 规范化路径
3. ASGITransport + FastAPI lifespan 导致跨 event loop 错误 → 禁用 lifespan + dependency_overrides
4. `goals.py` 函数参数 `status` 遮蔽 `starlette.status` 模块 → 改别名为 `http_status`
5. `test_tasks.py` 中 `data` 变量未定义 → 添加 `data = response.json()`
6. `TaskCreate.priority` 缺少字符串枚举校验 → 改为 `Literal["low","medium","high"]`

---

### Step 19: 前端扩展 — 间隔复习页面 + AI 问答页面 ✅ (已完成)

**目标**: 在前端添加间隔复习（SM-2）和 RAG AI 问答两个页面

**创建的文件**:
- `frontend/src/app/review/page.tsx` — 间隔复习页面（列表 + 复习模式 + CRUD）
- `frontend/src/app/qa/page.tsx` — AI 问答页面（对话界面 + 简易 Markdown + 引用列表）
- `task_logs/step_19_review_qa_pages.md` — 详细执行记录

**修改的文件**:
- `frontend/src/lib/types.ts` — 添加 ReviewCard/QA 相关 TS 类型
- `frontend/src/components/Navbar.tsx` — 添加"复习"和"AI 问答"导航链接

**技术要点**:
- 翻转卡片动画（CSS perspective + transition）
- SM-2 评分 UI（0-5 分，每个分值有对应颜色和标签）
- 简易 Markdown 渲染器（支持标题/粗体/代码/列表）
- 对话历史管理（useState 会话内保留）

---

### Step 20: 前端扩展 — 自动出题页面 + 知识图谱可视化

_(详细指令将在 Step 19 完成后写入)_

---

> **使用说明**: 每次新开终端，将本文件提供给 Claude，告诉它 "继续 StudyBot 项目"。Claude 会从 `### 📋 下一步` 找到当前要做的步骤。
