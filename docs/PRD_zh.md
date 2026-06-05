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
| 4 | AI 学习计划生成 (PlannerAgent) | 🔄 待开发 | P0 | Phase 1 |
| 5 | 知识库 RAG 问答 (DigestAgent) | 🔄 开发中 | P1 | Phase 2 |
| 6 | 间隔复习 (SM-2 算法) | 🔄 开发中 | P1 | Phase 2 |
| 7 | 自动出题 (QuizAgent) | 🔄 开发中 | P2 | Phase 2 |
| 8 | 知识图谱可视化 | ✅ 已完成 | P2 | Phase 3 |
| 9 | 动态计划调整 (SchedulerAgent) | ✅ 已完成 | P2 | Phase 3 |
| 10 | 学习仪表盘 | 📋 规划中 | P2 | Phase 3 |

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

#### 2.3.1 AI 学习计划生成 (Step 8 - 下一步)

**功能描述**: 用户创建一个学习目标后，调用 PlannerAgent（LangGraph），AI 自动将目标分解为结构化的学习计划。

**输入**:
- 目标 ID（已有 Goal）
- 用户的偏好设置（可选：每日学习时长、截止日期）

**处理流程**:
1. 分析目标范围和学习路径
2. 生成里程碑（阶段性目标）
3. 为每个里程碑生成具体任务
4. 为任务分配优先级和预估时间
5. 通过 WebSocket 实时推送生成进度

**输出**:
- 一系列 Task（任务），关联到该 Goal
- 每个 Task 包含：标题、描述、优先级、预估耗时、截止日期、里程碑标记

#### 2.3.2 知识库 RAG 问答 (Step 11 - 当前步骤)

**功能描述**: 基于 Step 9（文档上传 + 文本提取）和 Step 10（文本分块 + 向量嵌入）的基础设施，实现完整的 RAG（检索增强生成）问答流程。用户用自然语言提问，系统自动在已上传的文档中语义搜索相关内容，将检索到的分块作为上下文提供给 LLM，生成带引用来源的答案。

**RAG 流程**:
1. 接收用户自然语言问题
2. 将问题向量化（OpenAI text-embedding-3-small）
3. 在用户所有文档分块中执行语义搜索（pgvector 余弦相似度）
4. 选取 top_k 个最相关分块作为上下文
5. 构建 RAG Prompt（系统提示词 + 上下文分块 + 用户问题 + 引用要求）
6. 调用 LLM（gpt-4o-mini）生成答案
7. 返回答案 + 引用的分块列表

**输入**:
- question: 用户的自然语言问题（1-1000 字符）
- document_id: 可选，限定搜索特定文档
- top_k: 可选，检索的分块数量（默认 5，最大 20）

**处理流程**:
1. **语义搜索**: 将问题向量化后执行 pgvector 余弦相似度搜索，返回 top_k 个最相关分块
2. **上下文组装**: 将搜索到的分块内容 + 文档标题 + 相似度分数组装为 LLM 上下文
3. **答案生成**: 使用 DigestAgent（LangGraph 工作流），调用 LLM 基于上下文生成答案
4. **引用附加**: 答案中标注引用来源（文档名 + 分块序号 + 相关原文）

**输出**:
- answer: LLM 生成的自然语言答案
- citations: 引用列表 [{chunk_id, document_id, document_title, chunk_index, content, similarity}]

**边界条件**:
- 用户没有上传任何文档 → 返回提示"您还没有上传文档，请先上传学习资料"
- 搜索不到相关分块（所有分块相似度 < threshold）→ 返回"未找到相关信息，请尝试换个问法"
- 文档内容为空 → 该文档不参与搜索
- document_id 指定的文档不存在/不属于当前用户 → 返回 403/404 错误

**技术实现**:
- Agent: LangGraph DigestAgent（search_chunks → generate_answer 两节点工作流）
- 搜索: 复用 embedding_service.embed_query() + pgvector SQL
- LLM: ChatOpenAI + with_structured_output（确保答案 + 引用格式正确）
- 模型: gpt-4o-mini（轻量模型，RAG 场景下质量已足够）

#### 2.3.3 间隔复习 (Step 12 - 当前步骤)

**功能描述**: 基于 SM-2（SuperMemo 2）间隔重复算法，根据用户的复习反馈（遗忘程度评分 0-5）自动计算下次复习时间。实现完整的复习卡片 CRUD + 评分 API。

**SM-2 算法流程**:
1. 用户对卡片评分 (0-5)：0=完全忘记, 5=完美回忆
2. 计算新的 ease_factor：`EF' = EF + (0.1 - (5-q) × (0.08 + (5-q) × 0.02))`，下限 1.3
3. 评分 >= 3（正确）: repetitions+1, 按公式计算新 interval
4. 评分 < 3（遗忘）: 重置 repetitions=0, interval=1天
5. 更新 next_review_at = now + interval 天

**输入**:
- 复习卡片 (front/back): 正面问题 + 背面答案
- 评分 (0-5): 用户对自己回忆程度的评价

**核心逻辑**:
- `q >= 3`: repetitions++, interval 递增 (1→6→×EF→×EF...)
- `q < 3`: repetitions=0, interval=1（从零开始）
- ease_factor 动态调整: 连续正确→升高（间隔拉长），连续错误→降低到 1.3（最小间隔）
- next_review_at = 当前时间 + interval 天

**输出**:
- 更新后的卡片（含新的 ease_factor、interval、repetitions、next_review_at）

**API 端点**:
- `GET /review-cards` — 列表（支持 overdue/today 过滤）
- `POST /review-cards` — 创建卡片
- `GET /review-cards/{id}` — 卡片详情
- `PUT /review-cards/{id}` — 更新内容
- `DELETE /review-cards/{id}` — 删除卡片
- `POST /review-cards/{id}/review` — 提交复习评分（核心 SM-2 端点）

#### 2.3.4 自动出题 (Step 13 - 当前步骤)

**功能描述**: 基于用户上传的学习材料（文档），AI 自动生成测验题目。支持选择题（4 选项）、判断题和简答题。使用 QuizAgent (LangGraph) 编排出题流程。

**输入**: document_id + 题目数量（默认 5 道）
**输出**: 生成的测验题目列表（question + options + correct_answer + explanation）

**QuizAgent 工作流**:
1. load_document: 加载文档内容/chunks
2. generate_quizzes: 调用 LLM (gpt-4o-mini) 基于文档内容生成题目
3. save_quizzes: 批量存入数据库

**边界条件**:
- 文档内容为空 → 返回 422 "文档没有可提取的内容"
- 文档不存在/无权限 → 404/403
- LLM 调用失败 → 500 优雅降级

**API**: POST /quizzes/generate | GET /quizzes | GET /quizzes/{id} | DELETE /quizzes/{id}

**功能描述**: 基于用户的学习材料，AI 自动生成测验题目（选择题、判断题、简答题）。

#### 2.3.5 知识图谱 (Step 14) ✅

**功能描述**: 将学习过程中的概念和它们之间的关系（前置/相关/包含）可视化为知识图谱。

**概念 CRUD**:
- 创建/查看/更新/删除概念节点
- 支持 5 种分类: subject（学科）、topic（主题）、subtopic（子主题）、term（术语）、other（其他）
- 支持按分类过滤和按名称模糊搜索

**概念关系**:
- 创建/删除概念之间的有向关系
- 支持 3 种关系类型: prerequisite（前置知识）、related（相关）、part_of（包含）
- 防重复：同一对概念之间相同类型的关系不能重复创建
- 防自引用：不能创建指向自身的关系
- 级联删除：删除概念时自动删除其所有关联关系

**图谱可视化 API**:
- `GET /graph` — 返回完整图谱数据（节点列表 + 边列表），前端可直接用 D3.js/Cytoscape.js 渲染
- `GET /graph/stats` — 返回统计信息（按分类/按关系类型）

#### 2.3.6 动态计划调整 (Step 15) ✅

**功能描述**: 检测学习进度落后时，AI 自动重新排程，调整后续任务的截止日期和优先级。

**SchedulerAgent 工作流** (LangGraph):
1. **analyze_progress**: 加载目标 + 所有任务，计算完成率、过期任务数、预估剩余时间
2. **generate_schedule**: 调用 LLM 分析进度状况，生成 TaskAdjustment 列表（新截止日期/新优先级/调整理由）
3. **apply_schedule**: 将调整方案写入数据库

**核心特性**:
- 预览模式: `apply_changes=false` 仅生成分析报告，不修改数据
- 自动应用: `apply_changes=true` 直接更新任务 due_date 和 priority
- AI 只调整 todo/in_progress 状态的任务，不碰 done/cancelled
- 调整后的截止日期不会超过目标 deadline

**API**: POST /goals/{goal_id}/schedule

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
│  │           OpenAI API (LLM + Embedding)            │   │
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
| **LLM** | OpenAI (兼容 API) | - | GPT-4o-mini / GPT-4o |
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
| 8 | PlannerAgent | AI 学习计划生成 + WebSocket | 🔄 下一步 |

### Phase 2: 智能学习辅助

**目标**: 知识库 + 复习 + 测验功能

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
| AI 模型切换 | 通过配置切换 OpenAI 兼容的任何模型 |

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
