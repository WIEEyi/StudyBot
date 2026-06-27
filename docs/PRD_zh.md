# StudyBot 产品需求文档 (PRD)

> **版本**: v1.0
> **最后更新**: 2026-06-02
> **状态**: Phase 1 MVP 开发中

---

## 1. 项目概述

### 1.1 产品定位

StudyBot 是一个**个人学习与任务调度 AI Agent 应用**，帮助用户将模糊的学习目标自动分解为可执行的每日任务，并提供知识库问答、间隔复习、自动出题等 AI 驱动的学习辅助功能。

### 1.2 目标用户

- **自学者**：没有老师制定学习计划，需要 AI 辅助拆解目标
- **备考者**：需要在有限时间内高效复习，需要间隔复习和自动出题
- **知识工作者**：需要管理大量学习材料，快速检索和问答

### 1.3 核心价值

| 痛点 | StudyBot 解决方案 |
|------|-------------------|
| 不知道该学什么、怎么学 | AI 自动将目标分解为里程碑和每日任务 |
| 学了就忘 | SM-2 间隔复习算法，自动安排复习时间 |
| 不知道掌握程度 | AI 自动出题，检验学习效果 |
| 学习材料分散 | 统一知识库，RAG 语义搜索问答 |
| 缺乏学习动力 | 学习仪表盘（热力图、连续天数、AI 周报） |

---

## 2. 功能模块

### 2.1 功能总览

| 序号 | 功能模块 | 状态 | 优先级 | 所属阶段 |
|------|----------|------|--------|----------|
| 1 | 用户认证系统 (JWT) | ✅ 已完成 | P0 | Phase 1 |
| 2 | 学习目标管理 (CRUD) | ✅ 已完成 | P0 | Phase 1 |
| 3 | 任务管理 (CRUD) | ✅ 已完成 | P0 | Phase 1 |
| 4 | AI 学习计划生成 (PlannerAgent) | ✅ 已完成 | P0 | Phase 1 |
| 5 | 知识库 RAG 问答 (DigestAgent) | ✅ 已完成 | P1 | Phase 2 |
| 6 | 间隔复习 (SM-2 算法) | ✅ 已完成 | P1 | Phase 2 |
| 7 | 自动出题 (QuizAgent) | ✅ 已完成 | P2 | Phase 2 |
| 8 | 知识图谱可视化 | ✅ 已完成 | P2 | Phase 3 |
| 9 | 动态计划调整 (SchedulerAgent) | 📋 规划中 | P2 | Phase 3 |
| 10 | 学习仪表盘 | ✅ 已完成 | P2 | Phase 3 |

### 2.2 已完成功能详情

#### 2.2.1 用户认证系统 (Step 5)

- **注册**: 邮箱 + 用户名 + 密码，bcrypt 密码哈希
- **登录**: 返回 JWT access_token（30分钟） + refresh_token（7天）
- **令牌刷新**: 用 refresh_token 换新的 access_token
- **当前用户**: 获取已登录用户信息

#### 2.2.2 学习目标管理 (Step 7)

- **CRUD 完整操作**: 创建、查看列表（分页+过滤）、查看详情、更新、删除
- **状态管理**: 支持 active / completed / paused 三种状态切换
- **权限隔离**: 用户只能操作自己的目标
- **关联查询**: 查看目标时展示关联的任务列表

#### 2.2.3 任务管理 (Step 7)

- **CRUD 完整操作**: 创建、查看列表（分页+多维度过滤）、查看详情、更新、删除
- **过滤维度**: 按目标(goal_id)、状态(status)、优先级(priority) 过滤
- **优先级**: low / medium / high
- **预估耗时**: estimated_minutes 字段，用于日计划时间分配
- **权限隔离**: 用户只能操作自己的任务，创建任务时校验目标归属

### 2.3 待开发功能详情

#### 2.3.1 AI 学习计划生成 (Step 8 - 进行中)

**功能描述**: 用户创建一个学习目标后，通过 WebSocket 连接触发 PlannerAgent（LangGraph），AI 自动将目标分解为结构化的学习计划（里程碑 + 任务），并通过 WebSocket 实时推送生成进度。

**技术实现**:
- **Agent 框架**: LangGraph StateGraph（3 节点工作流）
- **LLM**: ChatOpenAI（model=gpt-4o），使用 structured output 确保返回格式
- **实时通信**: FastAPI WebSocket，JWT Token 认证

**Agent 工作流**:
```
START → analyze_goal（分析目标）→ generate_plan（LLM 生成计划）→ save_plan（批量入库）→ END
```
每个节点执行时通过 WebSocket 推送进度事件。

**输入**:
- `goal_id`: 已有学习目标的 ID
- JWT access_token（WebSocket 连接时通过 query param 传入）

**处理流程**:
1. **分析阶段** (`analyze_goal`): 从数据库加载目标信息，构造 LLM 上下文
2. **生成阶段** (`generate_plan`): LLM 分析目标，拆解为 3-5 个里程碑，每个里程碑下生成 3-8 个具体任务，为每个任务分配优先级和预估耗时
3. **保存阶段** (`save_plan`): 批量 INSERT 任务到数据库，关联到目标

**WebSocket 事件流**:
| 事件 | 触发时机 | 数据格式 |
|------|----------|----------|
| `thinking` | 开始分析 | `{"event": "thinking", "message": "正在分析..."}` |
| `milestone` | 每生成一个里程碑 | `{"event": "milestone", "data": {"title": "阶段一", "order": 1}}` |
| `task` | 每生成一个任务 | `{"event": "task", "data": {...task字段}}` |
| `complete` | 全部完成 | `{"event": "complete", "data": {"total_tasks": N, "total_minutes": M}}` |
| `error` | 发生错误 | `{"event": "error", "message": "错误描述"}` |

**输出**:
- 一系列 Task（任务）写入数据库，关联到该 Goal
- 每个 Task 包含：标题、描述、优先级、预估耗时(分钟)、milestone(里程碑名称)

**边界条件与错误处理**:
- Goal 不存在 → 返回 `error` 事件
- Goal 不属于当前用户 → 返回 `error` 事件
- LLM API 调用失败 → 返回 `error` 事件，不保存部分结果
- 无有效 OpenAI API Key → 返回 `error` 事件
- WebSocket 连接超时(30s) → 自动关闭连接

**数据库变更**:
- Task 模型新增 `milestone` 字段（VARCHAR(100)，可空），用于按里程碑分组任务

#### 2.3.2 知识库 RAG 问答 (Step 9+)

**功能描述**: 用户上传学习文档（PDF/Markdown/TXT），系统进行文本分块和向量化存储（pgvector），支持语义搜索和 AI 问答。

**输入**: 文档文件 + 用户问题
**输出**: AI 生成的答案 + 引用来源

#### 2.3.3 间隔复习 (Step 10+)

**功能描述**: 基于 SM-2 算法，根据用户的复习反馈（遗忘程度）自动计算下次复习时间。

**核心逻辑**:
- 用户对复习卡片评分（0-5）
- SM-2 算法调整 ease_factor、interval、repetitions
- 系统自动提醒到期复习的卡片

#### 2.3.4 自动出题 (Step 11+)

**功能描述**: 基于用户的学习材料，AI 自动生成测验题目（选择题、判断题、简答题）。

#### 2.3.5 知识图谱 (Step 12+)

**功能描述**: 将学习过程中的概念和它们之间的关系（前置/相关/包含）可视化为知识图谱。

#### 2.3.6 动态计划调整 (Step 13+)

**功能描述**: 检测学习进度落后时，AI 自动重新排程，调整后续任务的截止日期和优先级。

#### 2.3.7 学习仪表盘 (Step 14+)

**功能描述**: 可视化展示学习统计——热力图（每日学习时长）、连续学习天数、完成任务数、AI 每周学习洞察。

---

## 3. 技术架构

### 3.1 架构图

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend (Next.js)                    │
│                   React + TypeScript                      │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTP REST + WebSocket
┌─────────────────────▼───────────────────────────────────┐
│                  Backend (FastAPI)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │
│  │ API v1   │  │ Services │  │ Agents (LangGraph)    │  │
│  │ - auth   │  │          │  │ - PlannerAgent        │  │
│  │ - goals  │  │          │  │ - DigestAgent         │  │
│  │ - tasks  │  │          │  │ - QuizAgent           │  │
│  │ - ws     │  │          │  │ - SchedulerAgent      │  │
│  └──────────┘  └──────────┘  └──────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐   │
│  │              Core Infrastructure                  │   │
│  │  - database (SQLAlchemy async)                   │   │
│  │  - security (JWT + bcrypt)                       │   │
│  │  - redis_client (cache + pub/sub)                │   │
│  │  - logging                                       │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                   Infrastructure                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │
│  │PostgreSQL│  │  Redis   │  │     RabbitMQ         │  │
│  │ pgvector │  │ cache    │  │   (Celery broker)    │  │
│  │ pg16     │  │ pub/sub  │  │                      │  │
│  └──────────┘  └──────────┘  └──────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐   │
│  │              Celery Workers (async tasks)         │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │        DeepSeek API (LLM) + OpenAI (Embedding)    │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 3.2 技术栈

| 层级 | 技术 | 版本 | 用途 |
|------|------|------|------|
| **前端** | React + Next.js | 待定 | 用户界面 |
| **后端框架** | FastAPI | 0.115.0 | REST API + WebSocket |
| **ASGI 服务器** | Uvicorn | 0.30.6 | 服务运行 |
| **AI Agent** | LangGraph | 0.2.45 | Agent 工作流编排 |
| **AI 框架** | LangChain | 0.3.7 | LLM 集成 |
| **LLM** | DeepSeek V4 Pro (兼容 API) | - | deepseek-chat |
| **向量嵌入** | OpenAI Embeddings | - | text-embedding-3-small |
| **数据库** | PostgreSQL 16 + pgvector | - | 主存储 + 向量搜索 |
| **ORM** | SQLAlchemy 2.0 | 2.0.35 | 异步数据库操作 |
| **迁移工具** | Alembic | 1.13.2 | 数据库版本管理 |
| **缓存** | Redis 7 | - | 缓存 + Pub/Sub |
| **消息队列** | RabbitMQ 3.12 | - | Celery 任务队列 |
| **异步任务** | Celery | 5.4.0 | 后台任务处理 |
| **认证** | JWT + bcrypt | - | 用户认证 |
| **容器化** | Docker + Docker Compose | - | 环境编排 |
| **测试** | pytest + httpx | 8.3.3 | 单元测试 |

### 3.3 关键设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 数据库驱动 | asyncpg (异步) | FastAPI 异步架构，避免阻塞 |
| 迁移策略 | Alembic auto-generate | 模型变更自动生成迁移脚本 |
| Agent 框架 | LangGraph | 支持有状态的多步骤 Agent 工作流 |
| 向量存储 | pgvector | 与主数据库统一，减少运维复杂度 |
| 消息队列 | RabbitMQ + Celery | 成熟的异步任务方案 |
| 实时通信 | WebSocket | 支持 Agent 进度流式推送 |

---

## 4. 数据库设计

### 4.1 ER 图 (文字描述)

```
User (1) ────< (N) LearningGoal
User (1) ────< (N) Task
User (1) ────< (N) Document
User (1) ────< (N) ReviewCard
User (1) ────< (N) Quiz
User (1) ────< (N) Concept

LearningGoal (1) ────< (N) Task

Document (1) ────< (N) ReviewCard
Document (1) ────< (N) Quiz

Concept (1) ────< (N) ConceptRelation (as source)
Concept (1) ────< (N) ConceptRelation (as target)
```

### 4.2 表结构

#### users（用户表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, 自增 | 用户 ID |
| email | VARCHAR(255) | UNIQUE, NOT NULL, INDEX | 登录邮箱 |
| username | VARCHAR(100) | UNIQUE, NOT NULL, INDEX | 用户名 |
| hashed_password | VARCHAR(128) | NOT NULL | bcrypt 密码哈希 |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE | 账户启用状态 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 更新时间 |

#### learning_goals（学习目标表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, 自增 | 目标 ID |
| user_id | INTEGER | FK → users.id, CASCADE, INDEX, NOT NULL | 所属用户 |
| title | VARCHAR(255) | NOT NULL | 目标标题 |
| description | TEXT | NULLABLE | 详细描述 |
| deadline | TIMESTAMP | NULLABLE | 截止日期 |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'active' | active/completed/paused |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 更新时间 |

#### tasks（任务表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, 自增 | 任务 ID |
| user_id | INTEGER | FK → users.id, CASCADE, INDEX, NOT NULL | 所属用户 |
| goal_id | INTEGER | FK → learning_goals.id, SET NULL, INDEX, NULLABLE | 关联目标 |
| title | VARCHAR(255) | NOT NULL | 任务标题 |
| description | TEXT | NULLABLE | 详细描述 |
| priority | VARCHAR(20) | NOT NULL, DEFAULT 'medium' | low/medium/high |
| due_date | TIMESTAMP | NULLABLE | 截止日期 |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'todo' | todo/in_progress/done/cancelled |
| estimated_minutes | INTEGER | NULLABLE | 预估耗时（分钟） |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 更新时间 |

#### documents（文档表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, 自增 | 文档 ID |
| user_id | INTEGER | FK → users.id, CASCADE, INDEX, NOT NULL | 所属用户 |
| title | VARCHAR(255) | NOT NULL | 文档标题 |
| file_path | VARCHAR(500) | NULLABLE | 文件路径 |
| content | TEXT | NULLABLE | 提取的文本内容 |
| file_type | VARCHAR(20) | NOT NULL, DEFAULT 'txt' | pdf/md/txt/html |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 更新时间 |

#### review_cards（复习卡片表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, 自增 | 卡片 ID |
| user_id | INTEGER | FK → users.id, CASCADE, INDEX, NOT NULL | 所属用户 |
| document_id | INTEGER | FK → documents.id, SET NULL, INDEX, NULLABLE | 来源文档 |
| front | TEXT | NOT NULL | 正面（问题） |
| back | TEXT | NOT NULL | 背面（答案） |
| source | VARCHAR(20) | NOT NULL, DEFAULT 'manual' | manual/ai_generated |
| ease_factor | FLOAT | NOT NULL, DEFAULT 2.5 | SM-2 难度系数 |
| interval | INTEGER | NOT NULL, DEFAULT 0 | SM-2 复习间隔（天） |
| repetitions | INTEGER | NOT NULL, DEFAULT 0 | SM-2 连续正确次数 |
| next_review_at | TIMESTAMP | NULLABLE | 下次复习时间 |
| last_reviewed_at | TIMESTAMP | NULLABLE | 上次复习时间 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 更新时间 |

#### quizzes（测验表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, 自增 | 题目 ID |
| user_id | INTEGER | FK → users.id, CASCADE, INDEX, NOT NULL | 所属用户 |
| document_id | INTEGER | FK → documents.id, SET NULL, INDEX, NULLABLE | 来源文档 |
| question | TEXT | NOT NULL | 题目内容 |
| options | JSON | NULLABLE | 选项列表 |
| correct_answer | VARCHAR(255) | NOT NULL | 正确答案 |
| explanation | TEXT | NULLABLE | 解析 |
| source | VARCHAR(20) | NOT NULL, DEFAULT 'manual' | manual/ai_generated |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 更新时间 |

#### concepts（概念表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, 自增 | 概念 ID |
| user_id | INTEGER | FK → users.id, CASCADE, INDEX, NOT NULL | 所属用户 |
| name | VARCHAR(255) | NOT NULL | 概念名称 |
| description | TEXT | NULLABLE | 概念描述 |
| category | VARCHAR(20) | NOT NULL, DEFAULT 'topic' | subject/topic/subtopic/term/other |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 更新时间 |

#### concept_relations（概念关系表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, 自增 | 关系 ID |
| source_id | INTEGER | FK → concepts.id, CASCADE, INDEX, NOT NULL | 源概念 |
| target_id | INTEGER | FK → concepts.id, CASCADE, INDEX, NOT NULL | 目标概念 |
| relation_type | VARCHAR(20) | NOT NULL | prerequisite/related/part_of |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 更新时间 |

---

## 5. 开发阶段

### Phase 1: MVP（最小可行产品）

**目标**: 核心学习计划生成流程可用

| Step | 模块 | 描述 | 状态 |
|------|------|------|------|
| 1 | 项目骨架 | 目录结构和基础配置 | ✅ |
| 2 | Docker 环境 | PostgreSQL + Redis + RabbitMQ | ✅ |
| 3 | FastAPI 初始化 | 应用入口 + 配置 + 数据库连接 | ✅ |
| 4 | 日志系统 | 统一日志格式和输出 | ✅ |
| 5 | 用户认证 | 注册/登录/JWT | ✅ |
| 6 | 数据模型 | 全部 8 个 ORM 模型 + Alembic | ✅ |
| 7 | Goals + Tasks CRUD | 目标和任务的完整 REST API | ✅ |
| 8 | PlannerAgent | AI 学习计划生成 + WebSocket | ✅ |

### Phase 2: 智能学习辅助

**目标**: 知识库 + 复习 + 测验功能

| Step | 模块 | 描述 | 状态 |
|------|------|------|------|
| 9 | 文档上传 | 文件上传 + 文本提取 | ✅ |
| 10 | 向量嵌入 | 文本分块 + OpenAI Embedding + pgvector 存储 | ✅ |
| 11 | RAG 问答 | 语义搜索 + AI 问答（DigestAgent） | ✅ |
| 12 | 间隔复习 | SM-2 算法实现 + 复习提醒 | ✅ |
| 13 | 自动出题 | 基于材料 AI 生成测验（QuizAgent） | ✅ |

| Step | 模块 | 描述 |
|------|------|------|
| 9 | 文档上传 | 文件上传 + 文本提取 |
| 10 | 向量嵌入 | 文本分块 + OpenAI Embedding + pgvector 存储 |
| 11 | RAG 问答 | 语义搜索 + AI 问答（DigestAgent） |
| 12 | 间隔复习 | SM-2 算法实现 + 复习提醒 |
| 13 | 自动出题 | 基于材料 AI 生成测验（QuizAgent） |

### Phase 3: 高级功能 + 前端

**目标**: 完整的用户体验

| Step | 模块 | 描述 |
|------|------|------|
| 14 | 知识图谱 | 概念关系可视化 |
| 15 | 计划调整 | 进度检测 + 动态重排 |
| 16 | 学习仪表盘 | 数据可视化 + AI 周报 |
| 17 | Next.js 前端 | React 前端界面 |

---

## 6. 非功能性需求

### 6.1 性能

| 指标 | 目标 |
|------|------|
| API 响应时间 (P95) | < 200ms (CRUD), < 5s (AI 生成) |
| WebSocket 推送延迟 | < 100ms |
| 数据库连接池 | 10 基础 + 20 溢出 |
| Redis 连接池 | 10 最大连接 |

### 6.2 安全

| 需求 | 实现 |
|------|------|
| 密码存储 | bcrypt 哈希 |
| 认证 | JWT (HS256)，access 30min / refresh 7day |
| API 授权 | 所有数据操作校验 user_id 归属 |
| SQL 注入防护 | SQLAlchemy ORM 参数化查询 |
| CORS | 仅允许配置的域名 |
| 敏感信息 | .env 不入库，.env.example 为模板 |

### 6.3 可扩展性

| 需求 | 实现 |
|------|------|
| API 版本化 | /api/v1/ 前缀，后续可加 v2 |
| 水平扩展 | 无状态 FastAPI，可多实例部署 |
| 异步任务 | Celery + RabbitMQ，独立 Worker 扩展 |
| 配置管理 | pydantic-settings，支持 .env 和环境变量 |
| AI 模型切换 | 通过配置切换任何 OpenAI 兼容模型（默认 DeepSeek V4 Pro） |

### 6.4 代码质量

| 需求 | 实现 |
|------|------|
| 类型检查 | Python 类型注解 + Pydantic 校验 |
| 测试覆盖 | 每个 API 端点有正常+异常测试，pytest |
| 代码风格 | 模块化，每个模块有 __init__.py |
| 文档 | PRD + API 文档 + 中文代码注释 + 开发日志 |

---

## 7. 附录

### 7.1 项目文档索引

| 文档 | 位置 | 用途 |
|------|------|------|
| 项目追踪 | `PROJECT_TRACKER.md` | 开发进度、步骤指令 |
| 任务日志 | `TASK_LOG.md` | 任务执行日志索引 |
| 详细日志 | `task_logs/step_NN_xxx.md` | 每步详细执行记录 |
| 问答记录 | `QA_LOG.md` | 问题和回答记录 |
| PRD 中文 | `docs/PRD_zh.md` | 本文件 |
| PRD 英文 | `docs/PRD_en.md` | English version |
| API 中文 | `docs/API_zh.md` | API 接口文档 |
| API 英文 | `docs/API_en.md` | English API documentation |

### 7.2 环境变量参考

见 `backend/.env.example`

### 7.3 开发约定

- **分支**: feature/step-XX-xxx 从 develop 分出
- **提交**: `[Step X] 描述` 格式
- **测试**: 每个模块完成后运行 `docker compose exec backend pytest -v`
- **文档**: 开发前先写 PRD 子章节和 API 文档
