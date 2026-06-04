# StudyBot Product Requirements Document (PRD)

> **Version**: v1.0
> **Last Updated**: 2026-06-02
> **Status**: Phase 1 MVP In Development

---

## 1. Project Overview

### 1.1 Product Positioning

StudyBot is a **personal learning and task scheduling AI Agent application** that helps users automatically break down vague learning goals into executable daily tasks, and provides AI-driven learning assistance features such as knowledge base Q&A, spaced repetition, and auto-generated quizzes.

### 1.2 Target Users

- **Self-learners**: No teacher to create study plans; need AI assistance to break down goals
- **Exam candidates**: Need efficient review within limited time; need spaced repetition and auto-generated quizzes
- **Knowledge workers**: Manage large amounts of learning materials; need quick retrieval and Q&A

### 1.3 Core Value

| Pain Point | StudyBot Solution |
|-------------|-------------------|
| Don't know what or how to learn | AI automatically breaks down goals into milestones and daily tasks |
| Learn and forget | SM-2 spaced repetition algorithm automatically schedules reviews |
| Unsure of mastery level | AI auto-generates quizzes to test understanding |
| Scattered learning materials | Unified knowledge base with RAG semantic search and Q&A |
| Lack of motivation | Learning dashboard (heatmap, streak, AI weekly insights) |

---

## 2. Feature Modules

### 2.1 Feature Overview

| # | Feature Module | Status | Priority | Phase |
|---|----------------|--------|----------|-------|
| 1 | User Authentication (JWT) | ✅ Complete | P0 | Phase 1 |
| 2 | Learning Goal Management (CRUD) | ✅ Complete | P0 | Phase 1 |
| 3 | Task Management (CRUD) | ✅ Complete | P0 | Phase 1 |
| 4 | AI Learning Plan Generation (PlannerAgent) | ✅ Complete | P0 | Phase 1 |
| 5 | Knowledge Base RAG Q&A (DigestAgent) | 📋 Planned | P1 | Phase 2 |
| 6 | Spaced Repetition (SM-2 Algorithm) | 📋 Planned | P1 | Phase 2 |
| 7 | Auto Quiz Generation (QuizAgent) | 📋 Planned | P2 | Phase 2 |
| 8 | Knowledge Graph Visualization | 📋 Planned | P2 | Phase 3 |
| 9 | Dynamic Schedule Adjustment (SchedulerAgent) | 📋 Planned | P2 | Phase 3 |
| 10 | Learning Dashboard | 📋 Planned | P2 | Phase 3 |

### 2.2 Completed Features Detail

#### 2.2.1 User Authentication System (Step 5)

- **Register**: Email + Username + Password, bcrypt hashing
- **Login**: Returns JWT access_token (30min) + refresh_token (7 days)
- **Token Refresh**: Exchange refresh_token for new access_token
- **Current User**: Get authenticated user info

#### 2.2.2 Learning Goal Management (Step 7)

- **Full CRUD**: Create, list (paginated + filtered), view detail, update, delete
- **Status Management**: Toggle between active / completed / paused
- **Permission Isolation**: Users can only operate their own goals
- **Related Queries**: View goal details with associated task list

#### 2.2.3 Task Management (Step 7)

- **Full CRUD**: Create, list (paginated + multi-dimension filtered), view detail, update, delete
- **Filter Dimensions**: By goal (goal_id), status, priority
- **Priority Levels**: low / medium / high
- **Estimated Time**: estimated_minutes field for daily time allocation
- **Permission Isolation**: Users can only operate their own tasks; goal ownership verified on creation

### 2.3 Planned Features Detail

#### 2.3.1 AI Learning Plan Generation (Step 8 - Complete)

**Description**: After creating a learning goal, users connect via WebSocket to trigger PlannerAgent (LangGraph), which automatically decomposes the goal into a structured learning plan (milestones + tasks) and streams progress in real-time via WebSocket.

**Technical Implementation**:
- **Agent Framework**: LangGraph StateGraph (3-node workflow)
- **LLM**: ChatOpenAI (model=gpt-4o), structured output for guaranteed format
- **Real-time Communication**: FastAPI WebSocket with JWT token authentication

**Agent Workflow**:
```
START → analyze_goal → generate_plan (LLM) → save_plan (batch insert) → END
```
Each node pushes progress events via WebSocket during execution.

**Input**:
- `goal_id`: ID of an existing learning goal
- JWT access_token (passed as query param during WebSocket connection)

**Processing Flow**:
1. **Analysis Phase** (`analyze_goal`): Load goal info from DB, prepare LLM context
2. **Generation Phase** (`generate_plan`): LLM analyzes goal, breaks into 3-5 milestones, generates 3-8 tasks per milestone, assigns priority and time estimates
3. **Save Phase** (`save_plan`): Batch INSERT tasks into DB linked to the goal

**WebSocket Event Stream**:
| Event | Trigger | Data Format |
|-------|---------|-------------|
| `thinking` | Analysis starts | `{"event": "thinking", "message": "Analyzing..."}` |
| `milestone` | Each milestone generated | `{"event": "milestone", "data": {"title": "Phase 1", "order": 1}}` |
| `task` | Each task generated | `{"event": "task", "data": {...task fields}}` |
| `complete` | All done | `{"event": "complete", "data": {"total_tasks": N, "total_minutes": M}}` |
| `error` | Error occurred | `{"event": "error", "message": "Error description"}` |

**Output**:
- Series of Tasks written to DB, linked to the Goal
- Each Task includes: title, description, priority, estimated_minutes, milestone, due_date

**Edge Cases & Error Handling**:
- Goal not found → `error` event
- Goal not owned by current user → `error` event
- LLM API call failure → `error` event, no partial results saved
- No valid OpenAI API key → `error` event
- WebSocket connection timeout (30s) → auto close connection

**Database Change**:
- Task model adds `milestone` field (VARCHAR(100), nullable) for grouping tasks by milestone

#### 2.3.2 Document Upload + Text Extraction (Step 9 - In Progress)

**Description**: Users upload learning documents (PDF/Markdown/TXT/HTML). The system automatically extracts text content and stores it in the database. This is the foundational prerequisite for text chunking, vector embedding, and RAG Q&A.

**Technical Implementation**:
- **File Upload**: FastAPI `UploadFile` + `File`, received via multipart/form-data
- **Text Extraction**: PDF→PyPDF2, Markdown→markdown-it-py, HTML→BeautifulSoup4, TXT→direct read
- **File Storage**: Local disk `/app/uploads/{user_id}/` (Docker named volume for persistence)
- **Database**: Document model already exists (created in Step 6), includes title, file_path, content, file_type fields

**Input**:
- `file`: Uploaded file (max 50MB)
- `title`: Document title (optional, defaults to filename)
- JWT access_token (request header)

**Processing Flow**:
1. **Receive File**: Validate file type (only pdf/md/txt/html allowed), validate file size
2. **Save File**: Save to disk at path `{user_id}/{uuid}.{ext}`
3. **Text Extraction**: Call the appropriate extractor based on file type to get plain text
4. **Store Record**: Write file path and extracted text to documents table

**Output**:
- Document record written to database, referencing original file and extracted text

**Edge Cases & Error Handling**:
- Unsupported file type → 422 error
- File size exceeds 50MB → 413 error
- Empty file (0 bytes) → 422 error
- Text extraction failure (corrupted file) → 500 error, but file is saved (no data loss)
- Duplicate filenames → Allowed (internal UUID naming, no conflicts)
- Disk full → 500 error

**Supported File Formats**:

| Format | Extensions | Extraction Method | Library |
|--------|-----------|-------------------|---------|
| PDF | `.pdf` | PyPDF2 page-by-page extraction | pypdf2 (installed) |
| Markdown | `.md` | Raw text preservation | markdown-it-py (installed) |
| Plain Text | `.txt` | Direct read | None |
| HTML | `.html`, `.htm` | BeautifulSoup4 plain text extraction | beautifulsoup4 (new) |

**Database Change**: None (Document model already created in Step 6)

#### 2.3.3 Vector Embedding + RAG Q&A (Step 10-11)

**Description**: Perform text chunking and vector embedding storage (pgvector) on extracted document text, supporting semantic search and AI Q&A.

**Input**: Document text + User question
**Output**: AI-generated answer + Source references

#### 2.3.4 Spaced Repetition (Step 12+)

**Description**: Based on SM-2 algorithm, automatically calculate next review time from user feedback (forgetting degree).

**Core Logic**:
- User rates review cards (0-5)
- SM-2 algorithm adjusts ease_factor, interval, repetitions
- System automatically reminds due review cards

#### 2.3.5 Auto Quiz Generation (Step 13+)

**Description**: Based on user's learning materials, AI auto-generates quiz questions (multiple choice, true/false, short answer).

#### 2.3.6 Knowledge Graph (Step 14+)

**Description**: Visualize concepts and their relationships (prerequisite/related/part_of) as a knowledge graph.

#### 2.3.7 Dynamic Schedule Adjustment (Step 15+)

**Description**: Detect when learning progress falls behind, AI automatically reschedules tasks.

#### 2.3.8 Learning Dashboard (Step 16+)

**Description**: Visualize learning statistics — heatmap (daily study time), streak, completed task count, AI weekly insights.

---

## 3. Technical Architecture

### 3.1 Architecture Diagram

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

### 3.2 Tech Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Frontend** | React + Next.js | TBD | User interface |
| **Backend Framework** | FastAPI | 0.115.0 | REST API + WebSocket |
| **ASGI Server** | Uvicorn | 0.30.6 | Server runtime |
| **AI Agent** | LangGraph | 0.2.45 | Agent workflow orchestration |
| **AI Framework** | LangChain | 0.3.7 | LLM integration |
| **LLM** | OpenAI (compatible API) | - | GPT-4o-mini / GPT-4o |
| **Vector Embedding** | OpenAI Embeddings | - | text-embedding-3-small |
| **Database** | PostgreSQL 16 + pgvector | - | Primary storage + vector search |
| **ORM** | SQLAlchemy 2.0 | 2.0.35 | Async database operations |
| **Migration Tool** | Alembic | 1.13.2 | Database version management |
| **Cache** | Redis 7 | - | Cache + Pub/Sub |
| **Message Queue** | RabbitMQ 3.12 | - | Celery task queue |
| **Async Tasks** | Celery | 5.4.0 | Background task processing |
| **Authentication** | JWT + bcrypt | - | User authentication |
| **Containerization** | Docker + Docker Compose | - | Environment orchestration |
| **Testing** | pytest + httpx | 8.3.3 | Unit testing |

### 3.3 Key Design Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Database Driver | asyncpg (async) | FastAPI async architecture, avoid blocking |
| Migration Strategy | Alembic auto-generate | Auto-generate migration scripts from model changes |
| Agent Framework | LangGraph | Supports stateful multi-step agent workflows |
| Vector Storage | pgvector | Unified with primary database, less ops overhead |
| Message Queue | RabbitMQ + Celery | Mature async task solution |
| Real-time Communication | WebSocket | Supports streaming agent progress |

---

## 4. Database Design

### 4.1 ER Diagram (Text Description)

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

### 4.2 Table Structures

#### users

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, autoincrement | User ID |
| email | VARCHAR(255) | UNIQUE, NOT NULL, INDEX | Login email |
| username | VARCHAR(100) | UNIQUE, NOT NULL, INDEX | Username |
| hashed_password | VARCHAR(128) | NOT NULL | bcrypt password hash |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE | Account status |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation time |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Update time |

#### learning_goals

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, autoincrement | Goal ID |
| user_id | INTEGER | FK → users.id, CASCADE, INDEX, NOT NULL | Owner |
| title | VARCHAR(255) | NOT NULL | Goal title |
| description | TEXT | NULLABLE | Detailed description |
| deadline | TIMESTAMP | NULLABLE | Due date |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'active' | active/completed/paused |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation time |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Update time |

#### tasks

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, autoincrement | Task ID |
| user_id | INTEGER | FK → users.id, CASCADE, INDEX, NOT NULL | Owner |
| goal_id | INTEGER | FK → learning_goals.id, SET NULL, INDEX, NULLABLE | Parent goal |
| title | VARCHAR(255) | NOT NULL | Task title |
| description | TEXT | NULLABLE | Detailed description |
| priority | VARCHAR(20) | NOT NULL, DEFAULT 'medium' | low/medium/high |
| due_date | TIMESTAMP | NULLABLE | Due date |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'todo' | todo/in_progress/done/cancelled |
| estimated_minutes | INTEGER | NULLABLE | Estimated time (minutes) |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation time |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Update time |

#### documents

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, autoincrement | Document ID |
| user_id | INTEGER | FK → users.id, CASCADE, INDEX, NOT NULL | Owner |
| title | VARCHAR(255) | NOT NULL | Document title |
| file_path | VARCHAR(500) | NULLABLE | File path |
| content | TEXT | NULLABLE | Extracted text |
| file_type | VARCHAR(20) | NOT NULL, DEFAULT 'txt' | pdf/md/txt/html |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation time |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Update time |

#### review_cards

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, autoincrement | Card ID |
| user_id | INTEGER | FK → users.id, CASCADE, INDEX, NOT NULL | Owner |
| document_id | INTEGER | FK → documents.id, SET NULL, INDEX, NULLABLE | Source document |
| front | TEXT | NOT NULL | Front side (question) |
| back | TEXT | NOT NULL | Back side (answer) |
| source | VARCHAR(20) | NOT NULL, DEFAULT 'manual' | manual/ai_generated |
| ease_factor | FLOAT | NOT NULL, DEFAULT 2.5 | SM-2 ease factor |
| interval | INTEGER | NOT NULL, DEFAULT 0 | SM-2 interval (days) |
| repetitions | INTEGER | NOT NULL, DEFAULT 0 | SM-2 consecutive correct |
| next_review_at | TIMESTAMP | NULLABLE | Next review time |
| last_reviewed_at | TIMESTAMP | NULLABLE | Last review time |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation time |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Update time |

#### quizzes

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, autoincrement | Quiz ID |
| user_id | INTEGER | FK → users.id, CASCADE, INDEX, NOT NULL | Owner |
| document_id | INTEGER | FK → documents.id, SET NULL, INDEX, NULLABLE | Source document |
| question | TEXT | NOT NULL | Question content |
| options | JSON | NULLABLE | Options list |
| correct_answer | VARCHAR(255) | NOT NULL | Correct answer |
| explanation | TEXT | NULLABLE | Explanation |
| source | VARCHAR(20) | NOT NULL, DEFAULT 'manual' | manual/ai_generated |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation time |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Update time |

#### concepts

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, autoincrement | Concept ID |
| user_id | INTEGER | FK → users.id, CASCADE, INDEX, NOT NULL | Owner |
| name | VARCHAR(255) | NOT NULL | Concept name |
| description | TEXT | NULLABLE | Description |
| category | VARCHAR(20) | NOT NULL, DEFAULT 'topic' | subject/topic/subtopic/term/other |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation time |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Update time |

#### concept_relations

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, autoincrement | Relation ID |
| source_id | INTEGER | FK → concepts.id, CASCADE, INDEX, NOT NULL | Source concept |
| target_id | INTEGER | FK → concepts.id, CASCADE, INDEX, NOT NULL | Target concept |
| relation_type | VARCHAR(20) | NOT NULL | prerequisite/related/part_of |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation time |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Update time |

---

## 5. Development Phases

### Phase 1: MVP (Minimum Viable Product)

**Goal**: Core learning plan generation flow works

| Step | Module | Description | Status |
|------|--------|-------------|--------|
| 1 | Project Skeleton | Directory structure and basic config | ✅ |
| 2 | Docker Environment | PostgreSQL + Redis + RabbitMQ | ✅ |
| 3 | FastAPI Init | App entry + config + DB connection | ✅ |
| 4 | Logging System | Unified log format and output | ✅ |
| 5 | User Authentication | Register/Login/JWT | ✅ |
| 6 | Data Models | All 8 ORM models + Alembic | ✅ |
| 7 | Goals + Tasks CRUD | Full REST API for goals and tasks | ✅ |
| 8 | PlannerAgent | AI learning plan generation + WebSocket | ✅ |

### Phase 2: Intelligent Learning Assistance

**Goal**: Knowledge base + review + quiz features

| Step | Module | Description |
|------|--------|-------------|
| 9 | Document Upload | File upload + text extraction |
| 10 | Vector Embedding | Text chunking + OpenAI Embedding + pgvector storage |
| 11 | RAG Q&A | Semantic search + AI Q&A (DigestAgent) |
| 12 | Spaced Repetition | SM-2 algorithm + review reminders |
| 13 | Auto Quiz | AI-generated quizzes from materials (QuizAgent) |

### Phase 3: Advanced Features + Frontend

**Goal**: Complete user experience

| Step | Module | Description |
|------|--------|-------------|
| 14 | Knowledge Graph | Concept relationship visualization |
| 15 | Schedule Adjustment | Progress detection + dynamic rescheduling |
| 16 | Learning Dashboard | Data visualization + AI weekly report |
| 17 | Next.js Frontend | React frontend interface |

---

## 6. Non-Functional Requirements

### 6.1 Performance

| Metric | Target |
|--------|--------|
| API Response Time (P95) | < 200ms (CRUD), < 5s (AI generation) |
| WebSocket Push Latency | < 100ms |
| DB Connection Pool | 10 base + 20 overflow |
| Redis Connection Pool | 10 max connections |

### 6.2 Security

| Requirement | Implementation |
|-------------|----------------|
| Password Storage | bcrypt hashing |
| Authentication | JWT (HS256), access 30min / refresh 7day |
| API Authorization | All data ops verify user_id ownership |
| SQL Injection Prevention | SQLAlchemy ORM parameterized queries |
| CORS | Only configured origins allowed |
| Sensitive Data | .env excluded from repo, .env.example as template |

### 6.3 Scalability

| Requirement | Implementation |
|-------------|----------------|
| API Versioning | /api/v1/ prefix, v2 can be added later |
| Horizontal Scaling | Stateless FastAPI, multi-instance deployable |
| Async Tasks | Celery + RabbitMQ, independent Worker scaling |
| Config Management | pydantic-settings, supports .env and env vars |
| AI Model Switching | Switch any OpenAI-compatible model via config |

### 6.4 Code Quality

| Requirement | Implementation |
|-------------|----------------|
| Type Checking | Python type annotations + Pydantic validation |
| Test Coverage | Normal + error tests per API endpoint, pytest |
| Code Style | Modular, __init__.py per module |
| Documentation | PRD + API docs + Chinese code comments + dev logs |

---

## 7. Appendix

### 7.1 Project Document Index

| Document | Location | Purpose |
|----------|----------|---------|
| Project Tracker | `PROJECT_TRACKER.md` | Dev progress, step instructions |
| Task Log | `TASK_LOG.md` | Task execution log index |
| Detailed Logs | `task_logs/step_NN_xxx.md` | Per-step execution records |
| Q&A Log | `QA_LOG.md` | Questions and answers record |
| PRD (中文) | `docs/PRD_zh.md` | Chinese PRD |
| PRD (English) | `docs/PRD_en.md` | This file |
| API (中文) | `docs/API_zh.md` | Chinese API documentation |
| API (English) | `docs/API_en.md` | English API documentation |

### 7.2 Environment Variables Reference

See `backend/.env.example`

### 7.3 Development Conventions

- **Branching**: feature/step-XX-xxx branched from develop
- **Commits**: `[Step X] description` format
- **Testing**: Run `docker compose exec backend pytest -v` after each module
- **Documentation**: Write PRD subsection and API docs before coding
