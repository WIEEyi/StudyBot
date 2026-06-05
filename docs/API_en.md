# StudyBot API Documentation

> **Base URL**: `http://localhost:8000/api/v1`
> **Version**: v1.0
> **Last Updated**: 2026-06-02
> **Authentication**: Bearer Token (JWT)

---

## 1. General Information

### 1.1 Authentication

All APIs except login/register require a JWT Token in the request header:

```
Authorization: Bearer <access_token>
```

Obtain token via `/api/v1/auth/login` or `/api/v1/auth/register`.
Access Token expires in 30 minutes. Use `/api/v1/auth/refresh` to renew.

### 1.2 Common Response Format

**Success Response**:
```json
{
  "id": 1,
  "field": "value"
}
```

**Paginated List Response**:
```json
{
  "items": [...],
  "total": 100,
  "offset": 0,
  "limit": 20
}
```

**Error Response**:
```json
{
  "detail": "Error description"
}
```

### 1.3 HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 204 | Deleted (no body) |
| 401 | Unauthorized (missing or invalid token) |
| 403 | Forbidden (accessing another user's resource) |
| 404 | Not found |
| 422 | Validation error |

---

## 2. Implemented Endpoints

---

### 2.1 Authentication (Auth)

#### POST /api/v1/auth/register — Register User

**Request Body**:
```json
{
  "email": "user@example.com",
  "username": "myusername",
  "password": "mypassword123"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| email | string (email) | Yes | Email address |
| username | string (2-50) | Yes | Username |
| password | string (6-128) | Yes | Password |

**Success Response** (201):
```json
{
  "access_token": "eyJhbG...",
  "refresh_token": "eyJhbG...",
  "token_type": "bearer"
}
```

**Error Responses**:
- `422` — Validation failed (invalid email format, short username)
- `409` — Email or username already registered

---

#### POST /api/v1/auth/login — User Login

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "mypassword123"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| email | string (email) | Yes | Registered email |
| password | string | Yes | Password |

**Success Response** (200):
```json
{
  "access_token": "eyJhbG...",
  "refresh_token": "eyJhbG...",
  "token_type": "bearer"
}
```

**Error Responses**:
- `401` — Invalid email or password
- `403` — Account disabled

---

#### POST /api/v1/auth/refresh — Refresh Token

**Request Body**:
```json
{
  "refresh_token": "eyJhbG..."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| refresh_token | string | Yes | Valid refresh_token |

**Success Response** (200):
```json
{
  "access_token": "eyJhbG...",
  "refresh_token": "eyJhbG...",
  "token_type": "bearer"
}
```

**Error Responses**:
- `401` — Invalid or expired refresh_token

---

### 2.2 Users

#### GET /api/v1/users/me — Get Current User

**Headers**: `Authorization: Bearer <access_token>`

**Success Response** (200):
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "myusername",
  "is_active": true,
  "created_at": "2026-06-01T10:00:00Z",
  "updated_at": "2026-06-01T10:00:00Z"
}
```

**Error Responses**:
- `401` — Unauthorized

---

### 2.3 Learning Goals

#### GET /api/v1/goals — List Goals (Paginated)

**Headers**: `Authorization: Bearer <access_token>`

**Query Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| goal_status | string | No | - | Filter by: `active`, `completed`, `paused` |
| offset | integer | No | 0 | Pagination offset |
| limit | integer | No | 20 | Items per page (max 100) |

**Success Response** (200):
```json
{
  "items": [
    {
      "id": 1,
      "user_id": 1,
      "title": "Learn Python",
      "description": "Master Python full-stack development",
      "deadline": null,
      "status": "active",
      "task_count": 5,
      "created_at": "2026-06-01T10:00:00Z",
      "updated_at": "2026-06-01T10:00:00Z"
    }
  ],
  "total": 10,
  "offset": 0,
  "limit": 20
}
```

**Error Responses**:
- `401` — Unauthorized
- `422` — Invalid goal_status value

---

#### POST /api/v1/goals — Create Goal

**Headers**: `Authorization: Bearer <access_token>`

**Request Body**:
```json
{
  "title": "Learn Python",
  "description": "Master Python full-stack development",
  "deadline": "2026-12-31T23:59:59Z"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| title | string (1-255) | Yes | Goal title |
| description | string | No | Detailed description |
| deadline | datetime (ISO 8601) | No | Due date |

**Success Response** (201):
```json
{
  "id": 1,
  "user_id": 1,
  "title": "Learn Python",
  "description": "Master Python full-stack development",
  "deadline": "2026-12-31T23:59:59Z",
  "status": "active",
  "task_count": 0,
  "created_at": "2026-06-01T10:00:00Z",
  "updated_at": "2026-06-01T10:00:00Z"
}
```

**Error Responses**:
- `401` — Unauthorized
- `422` — Title empty or exceeds 255 characters

---

#### GET /api/v1/goals/{goal_id} — Get Goal Detail

**Headers**: `Authorization: Bearer <access_token>`

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| goal_id | integer | Goal ID |

**Success Response** (200):
```json
{
  "id": 1,
  "user_id": 1,
  "title": "Learn Python",
  "description": "Master Python full-stack development",
  "deadline": null,
  "status": "active",
  "task_count": 3,
  "tasks": [
    {
      "id": 1,
      "user_id": 1,
      "goal_id": 1,
      "title": "Learn basic syntax",
      "description": "Variables, loops, functions",
      "priority": "high",
      "due_date": null,
      "status": "todo",
      "estimated_minutes": 120,
      "created_at": "2026-06-01T10:00:00Z",
      "updated_at": "2026-06-01T10:00:00Z"
    }
  ],
  "created_at": "2026-06-01T10:00:00Z",
  "updated_at": "2026-06-01T10:00:00Z"
}
```

**Error Responses**:
- `401` — Unauthorized
- `403` — Goal does not belong to current user
- `404` — Goal not found

---

#### PUT /api/v1/goals/{goal_id} — Update Goal

**Headers**: `Authorization: Bearer <access_token>`

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| goal_id | integer | Goal ID |

**Request Body** (all fields optional):
```json
{
  "title": "Learn Python Advanced",
  "description": "Updated description",
  "deadline": "2026-12-31T23:59:59Z",
  "status": "active"
}
```

**Success Response** (200): Same as goal detail (without tasks)

**Error Responses**:
- `401` — Unauthorized
- `403` — Goal does not belong to current user
- `404` — Goal not found

---

#### DELETE /api/v1/goals/{goal_id} — Delete Goal

**Headers**: `Authorization: Bearer <access_token>`

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| goal_id | integer | Goal ID |

**Success Response** (204): No body

**Error Responses**:
- `401` — Unauthorized
- `403` — Goal does not belong to current user
- `404` — Goal not found

---

#### PATCH /api/v1/goals/{goal_id}/status — Toggle Goal Status

**Headers**: `Authorization: Bearer <access_token>`

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| goal_id | integer | Goal ID |

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| status | string | Yes | One of: `active`, `completed`, `paused` |

**Success Response** (200): Same as goal detail (without tasks)

**Error Responses**:
- `401` — Unauthorized
- `403` — Goal does not belong to current user
- `404` — Goal not found
- `422` — Invalid status value

---

### 2.4 Tasks

#### GET /api/v1/tasks — List Tasks (Paginated)

**Headers**: `Authorization: Bearer <access_token>`

**Query Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| goal_id | integer | No | - | Filter by goal |
| task_status | string | No | - | Filter by: `todo`, `in_progress`, `done`, `cancelled` |
| priority | string | No | - | Filter by: `low`, `medium`, `high` |
| offset | integer | No | 0 | Pagination offset |
| limit | integer | No | 20 | Items per page (max 100) |

**Success Response** (200):
```json
{
  "items": [
    {
      "id": 1,
      "user_id": 1,
      "goal_id": 1,
      "title": "Learn basic syntax",
      "description": "Variables, loops, functions",
      "priority": "high",
      "due_date": "2026-06-15T23:59:59Z",
      "status": "todo",
      "estimated_minutes": 120,
      "created_at": "2026-06-01T10:00:00Z",
      "updated_at": "2026-06-01T10:00:00Z"
    }
  ],
  "total": 25,
  "offset": 0,
  "limit": 20
}
```

**Error Responses**:
- `401` — Unauthorized
- `422` — Invalid task_status or priority value

---

#### POST /api/v1/tasks — Create Task

**Headers**: `Authorization: Bearer <access_token>`

**Request Body**:
```json
{
  "title": "Learn basic syntax",
  "description": "Variables, loops, functions",
  "goal_id": 1,
  "priority": "high",
  "due_date": "2026-06-15T23:59:59Z",
  "estimated_minutes": 120
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| title | string (1-255) | Yes | - | Task title |
| description | string | No | - | Detailed description |
| goal_id | integer | No | - | Parent goal ID |
| priority | string | No | medium | `low`, `medium`, `high` |
| due_date | datetime (ISO 8601) | No | - | Due date |
| estimated_minutes | integer (>=1) | No | - | Estimated time (minutes) |

**Success Response** (201):
```json
{
  "id": 1,
  "user_id": 1,
  "goal_id": 1,
  "title": "Learn basic syntax",
  "description": "Variables, loops, functions",
  "priority": "high",
  "due_date": "2026-06-15T23:59:59Z",
  "status": "todo",
  "estimated_minutes": 120,
  "created_at": "2026-06-01T10:00:00Z",
  "updated_at": "2026-06-01T10:00:00Z"
}
```

**Error Responses**:
- `401` — Unauthorized
- `403` — goal_id target does not belong to current user
- `422` — Title empty, invalid priority, estimated_minutes < 1

---

#### GET /api/v1/tasks/{task_id} — Get Task Detail

**Headers**: `Authorization: Bearer <access_token>`

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| task_id | integer | Task ID |

**Success Response** (200): Same as create task response

**Error Responses**:
- `401` — Unauthorized
- `403` — Task does not belong to current user
- `404` — Task not found

---

#### PUT /api/v1/tasks/{task_id} — Update Task

**Headers**: `Authorization: Bearer <access_token>`

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| task_id | integer | Task ID |

**Request Body** (all fields optional):
```json
{
  "title": "Updated title",
  "description": "Updated description",
  "goal_id": 2,
  "priority": "medium",
  "due_date": "2026-07-01T23:59:59Z",
  "status": "in_progress",
  "estimated_minutes": 90
}
```

**Success Response** (200): Same as create task response

**Error Responses**:
- `401` — Unauthorized
- `403` — Task does not belong to current user, or new goal_id target does not belong to current user
- `404` — Task not found

---

#### DELETE /api/v1/tasks/{task_id} — Delete Task

**Headers**: `Authorization: Bearer <access_token>`

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| task_id | integer | Task ID |

**Success Response** (204): No body

**Error Responses**:
- `401` — Unauthorized
- `403` — Task does not belong to current user
- `404` — Task not found

---

## 3. Planned Endpoints

---

### 3.1 PlannerAgent — AI Learning Plan Generation (Step 8)

#### WS /api/v1/ws/plan — WebSocket Plan Generation

**Description**: Establish WebSocket connection, trigger AI plan generation, receive real-time progress.

**Connection**:
```
ws://localhost:8000/api/v1/ws/plan?token=<access_token>
```

**Client Sends** (trigger generation):
```json
{
  "action": "generate_plan",
  "goal_id": 1
}
```

**Server Pushes Events**:
```json
// Analysis phase
{"event": "thinking", "message": "Analyzing learning goal..."}

// Milestone generated
{"event": "milestone", "data": {"title": "Phase 1: Python Basics", "order": 1}}

// Task generated
{"event": "task", "data": {"title": "Install Python environment", "priority": "high", "estimated_minutes": 30}}

// Complete
{"event": "complete", "data": {"total_tasks": 15, "total_minutes": 720}}

// Error
{"event": "error", "message": "Generation failed: Invalid API key"}
```

---

### 3.2 Knowledge Base (Step 9-11)

#### POST /api/v1/documents — Upload Document
#### GET /api/v1/documents — List Documents
#### GET /api/v1/documents/{id} — Document Detail
#### DELETE /api/v1/documents/{id} — Delete Document
#### POST /api/v1/qa/ask — RAG Q&A
#### GET /api/v1/review-cards — List Review Cards
#### POST /api/v1/review-cards — Create Review Card
#### PATCH /api/v1/review-cards/{id}/review — Submit Review Rating
#### POST /api/v1/quizzes/generate — AI Generate Quiz
#### GET /api/v1/quizzes — List Quizzes

---

### 3.5 RAG Q&A Module (QA) — Step 11 🔄 In Progress

#### POST /api/v1/qa/ask — RAG Knowledge Base Q&A

**Description**: Users ask questions in natural language. The system automatically searches for relevant content in uploaded documents, provides retrieved chunks as context to the LLM, and generates answers with source citations.

**Headers**: `Authorization: Bearer <access_token>`

**Request Body**:
```json
{
  "question": "How to implement async programming in Python",
  "document_id": null,
  "top_k": 5
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| question | string (1-1000) | Yes | - | User's natural language question |
| document_id | integer | No | null | Limit search to a specific document; null = search all |
| top_k | integer (1-20) | No | 5 | Number of most relevant chunks to retrieve |

**Success Response** (200):
```json
{
  "question": "How to implement async programming in Python",
  "answer": "Python's async programming is primarily implemented through the asyncio library. Core concepts include:\n\n1. **Coroutines**: Functions defined with async def...\n2. **Event Loop**: Started via asyncio.run()...",
  "citations": [
    {
      "chunk_id": 5,
      "document_id": 1,
      "document_title": "Python Study Notes",
      "chunk_index": 4,
      "content": "Python async programming is based on the asyncio library...",
      "similarity": 0.8542
    },
    {
      "chunk_id": 12,
      "document_id": 2,
      "document_title": "Advanced Python Programming",
      "chunk_index": 11,
      "content": "The core of async programming is the event loop mechanism...",
      "similarity": 0.7621
    }
  ]
}
```

**Error Responses**:
- `401` — Unauthorized
- `403` — Specified document_id does not belong to current user
- `404` — Specified document_id not found
- `422` — question empty or exceeds 1000 characters, top_k out of range
- `500` — OpenAI API call failed (LLM or Embedding)

**Business Rules**:
1. Search scope limited to current user's own document chunks (user_id filter)
2. When no relevant chunks found (all similarity < 0.3), return a generic message instead of fabricating an answer
3. LLM is required to answer based on provided context only, must not fabricate information
4. Cited chunks in answer are annotated with source document name and chunk index
5. Supports limiting search to a single document via document_id
6. Uses gpt-4o-mini model (lightweight model; RAG quality comes from retrieved context)
7. Uses pgvector HNSW index for accelerated vector search

---

### 3.6 Spaced Repetition Module (Review Cards) — Step 12 🔄 In Progress

#### POST /api/v1/review-cards — Create Review Card
#### GET /api/v1/review-cards — List Review Cards (filter: overdue/today)
#### GET /api/v1/review-cards/{card_id} — Card Detail
#### PUT /api/v1/review-cards/{card_id} — Update Card Content
#### DELETE /api/v1/review-cards/{card_id} — Delete Card

#### POST /api/v1/review-cards/{card_id}/review — Submit Review Rating 🔑

**Description**: After user rates a card (0-5), SM-2 algorithm automatically updates ease_factor, interval, repetitions, and next_review_at. This is the core endpoint of spaced repetition.

**Request Body**:
```json
{ "rating": 4 }
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| rating | integer (0-5) | Yes | Recall quality: 0=blackout, 5=perfect |

**Success Response** (200):
```json
{
  "id": 1,
  "rating": 4,
  "previous_interval": 6,
  "new_interval": 15,
  "ease_factor": 2.5,
  "repetitions": 2,
  "next_review_at": "2026-06-20T10:00:00Z"
}
```

**SM-2 Algorithm Rules**:
1. Rating >= 3: repetitions+1. 1st interval=1d, 2nd=6d, 3rd+=interval×ease_factor
2. Rating < 3: repetitions=0, interval=1d (restart)
3. ease_factor adjusted: EF' = EF + (0.1 - (5-q) × (0.08 + (5-q) × 0.02)), minimum 1.3

---

### 3.7 Knowledge Graph Module (Step 14+)

#### GET /api/v1/concepts — List Concepts
#### POST /api/v1/concepts — Create Concept
#### POST /api/v1/concepts/{id}/relations — Create Concept Relation
#### GET /api/v1/graph — Get Knowledge Graph Data

---

## 4. New Module API Documentation Template

> Use this template when writing API documentation for new modules.

### 4.X Module Name

#### METHOD /api/v1/resource — Description

**Headers**: `Authorization: Bearer <access_token>`

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|

**Query Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|

**Request Body**:
```json
{
  "field": "value"
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|

**Success Response** (status code):
```json
{
  "field": "value"
}
```

**Error Responses**:
- `401` — Unauthorized
- `404` — Resource not found
- `422` — Validation failed

**Business Rules**:
1. Rule description
2. Rule description

---
