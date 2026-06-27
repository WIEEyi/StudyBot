# StudyBot API 接口文档

> **Base URL**: `http://localhost:8000/api/v1`
> **版本**: v1.0
> **最后更新**: 2026-06-24
> **认证方式**: Bearer Token (JWT)

---

## 1. 通用说明

### 1.1 认证

除登录/注册外，所有 API 需要在请求头中携带 JWT Token：

```
Authorization: Bearer <access_token>
```

Token 通过 `/api/v1/auth/login` 或 `/api/v1/auth/register` 获取。
Access Token 有效期 30 分钟，过期后使用 `/api/v1/auth/refresh` 刷新。

### 1.2 通用响应格式

**成功响应**:
```json
{
  "id": 1,
  "field": "value"
}
```

**分页列表响应**:
```json
{
  "items": [...],
  "total": 100,
  "offset": 0,
  "limit": 20
}
```

**错误响应**:
```json
{
  "detail": "错误描述信息"
}
```

### 1.3 HTTP 状态码

| 状态码 | 含义 |
|--------|------|
| 200 | 请求成功 |
| 201 | 创建成功 |
| 204 | 删除成功（无响应体） |
| 401 | 未认证（Token 缺失或无效） |
| 403 | 无权限（操作他人资源） |
| 404 | 资源不存在 |
| 422 | 请求参数校验失败 |

---

## 2. 已实现接口

---

### 2.1 认证模块 (Auth)

#### POST /api/v1/auth/register — 用户注册

**请求体**:
```json
{
  "email": "user@example.com",
  "username": "myusername",
  "password": "mypassword123"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| email | string (email) | 是 | 邮箱地址 |
| username | string (2-50) | 是 | 用户名 |
| password | string (6-128) | 是 | 密码 |

**成功响应** (201):
```json
{
  "access_token": "eyJhbG...",
  "refresh_token": "eyJhbG...",
  "token_type": "bearer"
}
```

**错误响应**:
- `422` — 参数校验失败（如邮箱格式错误、用户名太短）
- `409` — 邮箱或用户名已被注册

---

#### POST /api/v1/auth/login — 用户登录

**请求体**:
```json
{
  "email": "user@example.com",
  "password": "mypassword123"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| email | string (email) | 是 | 注册邮箱 |
| password | string | 是 | 密码 |

**成功响应** (200):
```json
{
  "access_token": "eyJhbG...",
  "refresh_token": "eyJhbG...",
  "token_type": "bearer"
}
```

**错误响应**:
- `401` — 邮箱或密码错误
- `403` — 账户已被禁用

---

#### POST /api/v1/auth/refresh — 刷新令牌

**请求体**:
```json
{
  "refresh_token": "eyJhbG..."
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| refresh_token | string | 是 | 有效的 refresh_token |

**成功响应** (200):
```json
{
  "access_token": "eyJhbG...",
  "refresh_token": "eyJhbG...",
  "token_type": "bearer"
}
```

**错误响应**:
- `401` — refresh_token 无效或已过期

---

### 2.2 用户模块 (Users)

#### GET /api/v1/users/me — 获取当前用户信息

**请求头**: `Authorization: Bearer <access_token>`

**成功响应** (200):
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

**错误响应**:
- `401` — 未认证

---

### 2.3 学习目标模块 (Goals)

#### GET /api/v1/goals — 获取目标列表（分页）

**请求头**: `Authorization: Bearer <access_token>`

**查询参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| goal_status | string | 否 | - | 过滤状态: `active`, `completed`, `paused` |
| offset | integer | 否 | 0 | 分页偏移量 |
| limit | integer | 否 | 20 | 每页数量（最大 100） |

**成功响应** (200):
```json
{
  "items": [
    {
      "id": 1,
      "user_id": 1,
      "title": "学习 Python",
      "description": "掌握 Python 全栈开发",
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

**错误响应**:
- `401` — 未认证
- `422` — goal_status 值无效

---

#### POST /api/v1/goals — 创建学习目标

**请求头**: `Authorization: Bearer <access_token>`

**请求体**:
```json
{
  "title": "学习 Python",
  "description": "掌握 Python 全栈开发",
  "deadline": "2026-12-31T23:59:59Z"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string (1-255) | 是 | 目标标题 |
| description | string | 否 | 详细描述 |
| deadline | datetime (ISO 8601) | 否 | 截止日期 |

**成功响应** (201):
```json
{
  "id": 1,
  "user_id": 1,
  "title": "学习 Python",
  "description": "掌握 Python 全栈开发",
  "deadline": "2026-12-31T23:59:59Z",
  "status": "active",
  "task_count": 0,
  "created_at": "2026-06-01T10:00:00Z",
  "updated_at": "2026-06-01T10:00:00Z"
}
```

**错误响应**:
- `401` — 未认证
- `422` — title 为空或超过 255 字符

---

#### GET /api/v1/goals/{goal_id} — 获取目标详情

**请求头**: `Authorization: Bearer <access_token>`

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| goal_id | integer | 目标 ID |

**成功响应** (200):
```json
{
  "id": 1,
  "user_id": 1,
  "title": "学习 Python",
  "description": "掌握 Python 全栈开发",
  "deadline": null,
  "status": "active",
  "task_count": 3,
  "tasks": [
    {
      "id": 1,
      "user_id": 1,
      "goal_id": 1,
      "title": "学习基础语法",
      "description": "变量、循环、函数",
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

**错误响应**:
- `401` — 未认证
- `403` — 目标不属于当前用户
- `404` — 目标不存在

---

#### PUT /api/v1/goals/{goal_id} — 更新目标

**请求头**: `Authorization: Bearer <access_token>`

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| goal_id | integer | 目标 ID |

**请求体** (所有字段可选):
```json
{
  "title": "学习 Python 进阶",
  "description": "更新后的描述",
  "deadline": "2026-12-31T23:59:59Z",
  "status": "active"
}
```

**成功响应** (200): 同目标详情（不含 tasks）

**错误响应**:
- `401` — 未认证
- `403` — 目标不属于当前用户
- `404` — 目标不存在

---

#### DELETE /api/v1/goals/{goal_id} — 删除目标

**请求头**: `Authorization: Bearer <access_token>`

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| goal_id | integer | 目标 ID |

**成功响应** (204): 无响应体

**错误响应**:
- `401` — 未认证
- `403` — 目标不属于当前用户
- `404` — 目标不存在

---

#### PATCH /api/v1/goals/{goal_id}/status — 切换目标状态

**请求头**: `Authorization: Bearer <access_token>`

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| goal_id | integer | 目标 ID |

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | 是 | `active`, `completed`, `paused` 之一 |

**成功响应** (200): 同目标详情（不含 tasks）

**错误响应**:
- `401` — 未认证
- `403` — 目标不属于当前用户
- `404` — 目标不存在
- `422` — status 值无效

---

### 2.4 任务模块 (Tasks)

#### GET /api/v1/tasks — 获取任务列表（分页）

**请求头**: `Authorization: Bearer <access_token>`

**查询参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| goal_id | integer | 否 | - | 按目标过滤 |
| task_status | string | 否 | - | 过滤状态: `todo`, `in_progress`, `done`, `cancelled` |
| priority | string | 否 | - | 过滤优先级: `low`, `medium`, `high` |
| offset | integer | 否 | 0 | 分页偏移量 |
| limit | integer | 否 | 20 | 每页数量（最大 100） |

**成功响应** (200):
```json
{
  "items": [
    {
      "id": 1,
      "user_id": 1,
      "goal_id": 1,
      "title": "学习基础语法",
      "description": "变量、循环、函数",
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

**错误响应**:
- `401` — 未认证
- `422` — task_status 或 priority 值无效

---

#### POST /api/v1/tasks — 创建任务

**请求头**: `Authorization: Bearer <access_token>`

**请求体**:
```json
{
  "title": "学习基础语法",
  "description": "变量、循环、函数",
  "goal_id": 1,
  "priority": "high",
  "due_date": "2026-06-15T23:59:59Z",
  "estimated_minutes": 120
}
```

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| title | string (1-255) | 是 | - | 任务标题 |
| description | string | 否 | - | 详细描述 |
| goal_id | integer | 否 | - | 所属目标 ID |
| priority | string | 否 | medium | `low`, `medium`, `high` |
| due_date | datetime (ISO 8601) | 否 | - | 截止日期 |
| estimated_minutes | integer (>=1) | 否 | - | 预估耗时（分钟） |

**成功响应** (201):
```json
{
  "id": 1,
  "user_id": 1,
  "goal_id": 1,
  "title": "学习基础语法",
  "description": "变量、循环、函数",
  "priority": "high",
  "due_date": "2026-06-15T23:59:59Z",
  "status": "todo",
  "estimated_minutes": 120,
  "created_at": "2026-06-01T10:00:00Z",
  "updated_at": "2026-06-01T10:00:00Z"
}
```

**错误响应**:
- `401` — 未认证
- `403` — goal_id 对应的目标不属于当前用户
- `422` — title 为空、priority 无效、estimated_minutes < 1

---

#### GET /api/v1/tasks/{task_id} — 获取任务详情

**请求头**: `Authorization: Bearer <access_token>`

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| task_id | integer | 任务 ID |

**成功响应** (200): 同创建任务响应

**错误响应**:
- `401` — 未认证
- `403` — 任务不属于当前用户
- `404` — 任务不存在

---

#### PUT /api/v1/tasks/{task_id} — 更新任务

**请求头**: `Authorization: Bearer <access_token>`

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| task_id | integer | 任务 ID |

**请求体** (所有字段可选):
```json
{
  "title": "更新后的标题",
  "description": "更新后的描述",
  "goal_id": 2,
  "priority": "medium",
  "due_date": "2026-07-01T23:59:59Z",
  "status": "in_progress",
  "estimated_minutes": 90
}
```

**成功响应** (200): 同创建任务响应

**错误响应**:
- `401` — 未认证
- `403` — 任务不属于当前用户，或新 goal_id 对应的目标不属于当前用户
- `404` — 任务不存在

---

#### DELETE /api/v1/tasks/{task_id} — 删除任务

**请求头**: `Authorization: Bearer <access_token>`

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| task_id | integer | 任务 ID |

**成功响应** (204): 无响应体

**错误响应**:
- `401` — 未认证
- `403` — 任务不属于当前用户
- `404` — 任务不存在

---

## 3. 已实现接口（Step 8-21 新增）

---

### 3.1 文档管理模块 (Documents) — Step 21

#### POST /api/v1/documents — 上传文档

**请求头**: `Authorization: Bearer <access_token>`

**请求体**: `multipart/form-data`，字段名 `file`

**支持格式**: PDF / Markdown (.md) / TXT / HTML

**成功响应** (201):
```json
{
  "id": 1,
  "user_id": 1,
  "title": "Python学习笔记",
  "file_type": "pdf",
  "file_path": "/app/uploads/abc123_Python学习笔记.pdf",
  "content": "提取的文本内容...",
  "created_at": "2026-06-24T10:00:00Z",
  "updated_at": "2026-06-24T10:00:00Z"
}
```

**错误响应**: `400` 文件类型不支持 / `413` 文件过大(>50MB)

---

#### GET /api/v1/documents — 文档列表

**查询参数**: `file_type`(过滤), `offset`, `limit`

**成功响应** (200): 标准分页格式

---

#### GET /api/v1/documents/{id} — 文档详情

**成功响应** (200): 同上传响应

---

#### DELETE /api/v1/documents/{id} — 删除文档

**成功响应** (204): 无响应体（同时删除磁盘文件）

---

### 3.2 间隔复习模块 (ReviewCards) — Step 21

#### GET /api/v1/review-cards — 卡片列表

**查询参数**: `due_filter`(overdue/today/all), `offset`, `limit`

---

#### POST /api/v1/review-cards — 创建卡片

**请求体**:
```json
{
  "front": "什么是 Python?",
  "back": "一种高级编程语言",
  "document_id": 1
}
```

---

#### PUT /api/v1/review-cards/{id} — 更新卡片

---

#### DELETE /api/v1/review-cards/{id} — 删除卡片

---

#### POST /api/v1/review-cards/{id}/review — SM-2 评分

**请求体**:
```json
{ "rating": 4 }
```

**成功响应** (200):
```json
{
  "card_id": 1,
  "rating": 4,
  "old_ease_factor": 2.5,
  "new_ease_factor": 2.6,
  "old_interval": 0,
  "new_interval": 1,
  "old_repetitions": 0,
  "new_repetitions": 1,
  "next_review_at": "2026-06-25T10:00:00Z"
}
```

---

### 3.3 学习仪表盘模块 (Dashboard) — Step 21

#### GET /api/v1/dashboard/overview — 统计概览

**成功响应** (200):
```json
{
  "total_goals": 5,
  "active_goals": 3,
  "completed_goals": 2,
  "total_tasks": 25,
  "completed_tasks": 10,
  "todo_tasks": 8,
  "in_progress_tasks": 7,
  "total_review_cards": 50,
  "due_review_cards": 12,
  "total_documents": 3,
  "total_concepts": 15,
  "total_study_hours": 12.5,
  "total_study_days": 8,
  "today_tasks_completed": 3,
  "today_cards_reviewed": 10
}
```

---

#### GET /api/v1/dashboard/heatmap — 热力图

**查询参数**: `start_date`(YYYY-MM-DD), `end_date`(YYYY-MM-DD)

**成功响应** (200):
```json
{
  "items": [
    { "date": "2026-06-20", "duration_minutes": 60, "tasks_completed": 3, "cards_reviewed": 10 }
  ],
  "start_date": "2026-06-01",
  "end_date": "2026-06-24"
}
```

---

#### GET /api/v1/dashboard/streak — 连续学习天数

**成功响应** (200):
```json
{
  "current_streak": 5,
  "current_start_date": "2026-06-20",
  "longest_streak": 12,
  "longest_start_date": "2026-06-01",
  "longest_end_date": "2026-06-12"
}
```

---

#### POST /api/v1/dashboard/session — 记录学习会话

**请求体**:
```json
{
  "duration_minutes": 60,
  "tasks_completed": 3,
  "cards_reviewed": 10
}
```

同一天多次调用会累加。

---

### 3.4 RAG 问答模块 (QA) — Step 21

#### POST /api/v1/qa/ask — 语义问答

**请求体**:
```json
{
  "question": "什么是 Python?",
  "document_id": 1,
  "top_k": 5
}
```

**成功响应** (200):
```json
{
  "question": "什么是 Python?",
  "answer": "根据你上传的 2 份文档，以下是相关内容：...",
  "citations": [
    {
      "document_id": 1,
      "chunk_id": 1,
      "chunk_index": 0,
      "document_title": "Python学习笔记",
      "content": "Python 是一种高级编程语言...",
      "similarity": 0.75
    }
  ],
  "conversation_id": 1
}
```

---

### 3.5 WebSocket — PlannerAgent (Step 8)

#### WS /api/v1/ws/plan — AI 学习计划生成

**连接方式**: `ws://localhost:8000/api/v1/ws/plan?token=<access_token>`

**客户端发送**:
```json
{ "action": "generate_plan", "goal_id": 1 }
```

**服务端推送事件**:
- `thinking` — 分析中
- `milestone` — 里程碑生成
- `task` — 任务生成
- `complete` — 完成
- `error` — 错误

---

### 3.6 计划调整模块 (Scheduler) — Step 22

#### POST /api/v1/goals/{goal_id}/reschedule — 智能重排任务

**请求头**: `Authorization: Bearer <access_token>`

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| goal_id | integer | 目标 ID |

**查询参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| strategy | string | 否 | balanced | 重排策略: balanced/aggressive/relaxed |

**策略说明**:
- `balanced`: 按优先级分配（high=1-3天, medium=4-7天, low=8-14天）
- `aggressive`: 所有任务压缩到 7 天内
- `relaxed`: 所有任务分散到 30 天内

**成功响应** (200):
```json
{
  "goal_id": 1,
  "total_pending": 5,
  "rescheduled": 5,
  "overdue": 3,
  "strategy": "balanced",
  "message": "已重排 5 个任务（3 个过期），策略: balanced"
}
```

**错误响应**:
- `401` — 未认证
- `403` — 目标不属于当前用户
- `404` — 目标不存在
- `422` — 无效的策略值

---

## 4. 新模块接口文档模板

> 以下为开发新模块时填写接口文档的模板。

### 4.X 模块名称

#### METHOD /api/v1/resource — 接口描述

**请求头**: `Authorization: Bearer <access_token>`

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|

**查询参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|

**请求体**:
```json
{
  "field": "value"
}
```

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|

**成功响应** (状态码):
```json
{
  "field": "value"
}
```

**错误响应**:
- `401` — 未认证
- `404` — 资源不存在
- `422` — 参数校验失败

**业务规则**:
1. 规则描述
2. 规则描述

---
