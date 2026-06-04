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

### 3.2 Documents Module — Step 9 🔄

**Supported Document Formats**: PDF (.pdf), Markdown (.md), Plain Text (.txt), HTML (.html/.htm)

---

#### POST /api/v1/documents — Upload Document

**Description**: Upload a learning document. The system automatically extracts text content, saves the original file, and records it in the database.

**Headers**: `Authorization: Bearer <access_token>`
**Content-Type**: `multipart/form-data`

**Request Body**:

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| file | file (binary) | Yes | - | File to upload, max 50MB |
| title | string (1-255) | No | Filename | Document title, defaults to filename if omitted |

**Supported File Types**: `pdf`, `md`, `txt`, `html`, `htm`

**Success Response** (201):
```json
{
  "id": 1,
  "user_id": 1,
  "title": "Python Study Notes",
  "file_path": "/app/uploads/1/a1b2c3d4.pdf",
  "file_type": "pdf",
  "content": "Chapter 1: Python Basics...(extracted plain text)",
  "created_at": "2026-06-04T10:00:00Z",
  "updated_at": "2026-06-04T10:00:00Z"
}
```

**Field Descriptions**:

| Field | Description |
|-------|-------------|
| content | Extracted text content for subsequent vectorization and full-text search |

**Error Responses**:
- `401` — Unauthorized
- `422` — Unsupported file type, empty file (0 bytes), or title validation failure
- `413` — File size exceeds 50MB
- `500` — File save failure or text extraction failure

**Business Rules**:
1. Files are stored as `{user_id}/{uuid}.{ext}`, avoiding name collisions
2. Text extraction is triggered immediately after upload, result written to content field synchronously
3. Text extraction failure does not prevent file saving (original file preserved on disk)
4. Only one file per request

---

#### GET /api/v1/documents — List Documents (Paginated)

**Headers**: `Authorization: Bearer <access_token>`

**Query Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| file_type | string | No | - | Filter by type: `pdf`, `md`, `txt`, `html` |
| offset | integer | No | 0 | Pagination offset |
| limit | integer | No | 20 | Items per page (max 100) |

**Success Response** (200):
```json
{
  "items": [
    {
      "id": 1,
      "user_id": 1,
      "title": "Python Study Notes",
      "file_path": "/app/uploads/1/a1b2c3d4.pdf",
      "file_type": "pdf",
      "content": "Chapter 1: Python Basics...",
      "created_at": "2026-06-04T10:00:00Z",
      "updated_at": "2026-06-04T10:00:00Z"
    }
  ],
  "total": 10,
  "offset": 0,
  "limit": 20
}
```

**Note**: `content` field in the list is truncated to the first 200 characters as a preview. Use the detail endpoint for the full content.

**Error Responses**:
- `401` — Unauthorized
- `422` — Invalid file_type value

---

#### GET /api/v1/documents/{document_id} — Get Document Detail

**Headers**: `Authorization: Bearer <access_token>`

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| document_id | integer | Document ID |

**Success Response** (200):
```json
{
  "id": 1,
  "user_id": 1,
  "title": "Python Study Notes",
  "file_path": "/app/uploads/1/a1b2c3d4.pdf",
  "file_type": "pdf",
  "content": "Chapter 1: Python Basics\n1.1 Variables and Data Types\n...(full extracted text content)",
  "created_at": "2026-06-04T10:00:00Z",
  "updated_at": "2026-06-04T10:00:00Z"
}
```

**Error Responses**:
- `401` — Unauthorized
- `403` — Document does not belong to current user
- `404` — Document not found

---

#### DELETE /api/v1/documents/{document_id} — Delete Document

**Description**: Deletes both the original file on disk and the database record. This operation is irreversible.

**Headers**: `Authorization: Bearer <access_token>`

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| document_id | integer | Document ID |

**Success Response** (204): No body

**Error Responses**:
- `401` — Unauthorized
- `403` — Document does not belong to current user
- `404` — Document not found

**Business Rules**:
1. Database record and disk file are both deleted (best effort: file deletion failure won't block database cleanup)
2. Deleted content is unrecoverable

---

#### GET /api/v1/review-cards — List Review Cards (reserved for Step 12)
#### POST /api/v1/review-cards — Create Review Card (reserved for Step 12)
#### PATCH /api/v1/review-cards/{id}/review — Submit Review Rating (reserved for Step 12)
#### POST /api/v1/qa/ask — RAG Q&A (reserved for Step 11)
#### POST /api/v1/quizzes/generate — AI Generate Quiz (reserved for Step 13)
#### GET /api/v1/quizzes — List Quizzes (reserved for Step 13)

---

### 3.3 Knowledge Graph (Step 12+)

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
