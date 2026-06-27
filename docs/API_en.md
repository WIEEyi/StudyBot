# StudyBot API Documentation

> **Base URL**: `http://localhost:8000/api/v1`
> **Version**: v1.0
> **Last Updated**: 2026-06-24
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

## 3. Implemented Endpoints (Steps 8-21)

---

### 3.1 Documents — Step 21

#### POST /api/v1/documents — Upload Document

**Headers**: `Authorization: Bearer <access_token>`

**Request**: `multipart/form-data`, field name `file`

**Supported formats**: PDF / Markdown (.md) / TXT / HTML

**Success Response** (201):
```json
{
  "id": 1, "user_id": 1, "title": "Python Notes",
  "file_type": "pdf", "content": "Extracted text...",
  "created_at": "2026-06-24T10:00:00Z", "updated_at": "2026-06-24T10:00:00Z"
}
```

**Errors**: `400` unsupported type / `413` file too large (>50MB)

---

#### GET /api/v1/documents — List Documents

**Query**: `file_type` (filter), `offset`, `limit`

---

#### GET /api/v1/documents/{id} — Document Detail

---

#### DELETE /api/v1/documents/{id} — Delete Document (also removes disk file)

---

### 3.2 Review Cards (SM-2 Spaced Repetition) — Step 21

#### GET /api/v1/review-cards — List Cards

**Query**: `due_filter` (overdue/today/all), `offset`, `limit`

---

#### POST /api/v1/review-cards — Create Card

**Request Body**:
```json
{ "front": "What is Python?", "back": "A high-level language", "document_id": 1 }
```

---

#### PUT /api/v1/review-cards/{id} — Update Card

---

#### DELETE /api/v1/review-cards/{id} — Delete Card

---

#### POST /api/v1/review-cards/{id}/review — SM-2 Rating

**Request Body**:
```json
{ "rating": 4 }
```

**Success Response** (200):
```json
{
  "card_id": 1, "rating": 4,
  "old_ease_factor": 2.5, "new_ease_factor": 2.6,
  "old_interval": 0, "new_interval": 1,
  "old_repetitions": 0, "new_repetitions": 1,
  "next_review_at": "2026-06-25T10:00:00Z"
}
```

---

### 3.3 Dashboard — Step 21

#### GET /api/v1/dashboard/overview — Statistics Overview

**Success Response** (200):
```json
{
  "total_goals": 5, "active_goals": 3, "completed_goals": 2,
  "total_tasks": 25, "completed_tasks": 10, "todo_tasks": 8, "in_progress_tasks": 7,
  "total_review_cards": 50, "due_review_cards": 12,
  "total_documents": 3, "total_concepts": 15,
  "total_study_hours": 12.5, "total_study_days": 8,
  "today_tasks_completed": 3, "today_cards_reviewed": 10
}
```

---

#### GET /api/v1/dashboard/heatmap — Heatmap Data

**Query**: `start_date` (YYYY-MM-DD), `end_date` (YYYY-MM-DD)

**Success Response** (200):
```json
{
  "items": [{ "date": "2026-06-20", "duration_minutes": 60, "tasks_completed": 3, "cards_reviewed": 10 }],
  "start_date": "2026-06-01", "end_date": "2026-06-24"
}
```

---

#### GET /api/v1/dashboard/streak — Consecutive Study Days

**Success Response** (200):
```json
{
  "current_streak": 5, "current_start_date": "2026-06-20",
  "longest_streak": 12, "longest_start_date": "2026-06-01", "longest_end_date": "2026-06-12"
}
```

---

#### POST /api/v1/dashboard/session — Record Study Session

**Request Body**:
```json
{ "duration_minutes": 60, "tasks_completed": 3, "cards_reviewed": 10 }
```

Multiple calls on the same day accumulate values.

---

### 3.4 RAG Q&A — Step 21

#### POST /api/v1/qa/ask — Semantic Q&A

**Request Body**:
```json
{ "question": "What is Python?", "document_id": 1, "top_k": 5 }
```

**Success Response** (200):
```json
{
  "question": "What is Python?",
  "answer": "Based on your 2 documents, here is relevant content:...",
  "citations": [
    { "document_id": 1, "document_title": "Python Notes", "content": "...", "relevance": 0.75 }
  ]
}
```

---

### 3.5 WebSocket — PlannerAgent (Step 8)

#### WS /api/v1/ws/plan — AI Learning Plan Generation

**Connection**: `ws://localhost:8000/api/v1/ws/plan?token=<access_token>`

**Client Sends**:
```json
{ "action": "generate_plan", "goal_id": 1 }
```

**Server Pushes**: `thinking` | `milestone` | `task` | `complete` | `error`

---

### 3.6 Schedule Adjustment (Scheduler) — Step 22

#### POST /api/v1/goals/{goal_id}/reschedule — Smart Reschedule Tasks

**Headers**: `Authorization: Bearer <access_token>`

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| goal_id | integer | Goal ID |

**Query Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| strategy | string | No | balanced | Reschedule strategy: balanced/aggressive/relaxed |

**Strategy Description**:
- `balanced`: By priority (high=1-3d, medium=4-7d, low=8-14d)
- `aggressive`: All tasks compressed to 7 days
- `relaxed`: All tasks spread to 30 days

**Success Response** (200):
```json
{
  "goal_id": 1,
  "total_pending": 5,
  "rescheduled": 5,
  "overdue": 3,
  "strategy": "balanced",
  "message": "Rescheduled 5 tasks (3 overdue), strategy: balanced"
}
```

**Error Responses**: `401` Unauthorized / `403` Forbidden / `404` Not Found / `422` Invalid strategy

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
