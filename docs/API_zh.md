# StudyBot API 接口文档

> **Base URL**: `http://localhost:8000/api/v1`
> **版本**: v1.0
> **最后更新**: 2026-06-02
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

## 3. 待开发接口

---

### 3.1 PlannerAgent — AI 学习计划生成 (Step 8)

#### WS /api/v1/ws/plan — WebSocket 学习计划生成

**描述**: 建立 WebSocket 连接，触发 AI 生成学习计划，实时接收生成进度。

**连接方式**:
```
ws://localhost:8000/api/v1/ws/plan?token=<access_token>
```

**客户端发送** (触发生成):
```json
{
  "action": "generate_plan",
  "goal_id": 1
}
```

**服务端推送事件**:
```json
// 分析阶段
{"event": "thinking", "message": "正在分析学习目标..."}

// 里程碑生成
{"event": "milestone", "data": {"title": "阶段一：Python 基础", "order": 1}}

// 任务生成
{"event": "task", "data": {"title": "安装 Python 环境", "priority": "high", "estimated_minutes": 30}}

// 完成
{"event": "complete", "data": {"total_tasks": 15, "total_minutes": 720}}

// 错误
{"event": "error", "message": "生成失败：API 密钥无效"}
```

---

### 3.2 文档模块 (Documents) — Step 9 🔄

**支持的文档格式**: PDF (.pdf)、Markdown (.md)、纯文本 (.txt)、HTML (.html/.htm)

---

#### POST /api/v1/documents — 上传文档

**描述**: 上传一个学习文档。系统自动提取文本内容、保存原始文件、记录到数据库。

**请求头**: `Authorization: Bearer <access_token>`
**Content-Type**: `multipart/form-data`

**请求体**:

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| file | file (binary) | 是 | - | 要上传的文件，最大 50MB |
| title | string (1-255) | 否 | 文件名 | 文档标题，不传则取文件名 |

**支持的文件类型**: `pdf`, `md`, `txt`, `html`, `htm`

**成功响应** (201):
```json
{
  "id": 1,
  "user_id": 1,
  "title": "Python学习笔记",
  "file_path": "/app/uploads/1/a1b2c3d4.pdf",
  "file_type": "pdf",
  "content": "第一章 Python基础...（提取后的纯文本）",
  "created_at": "2026-06-04T10:00:00Z",
  "updated_at": "2026-06-04T10:00:00Z"
}
```

**字段说明**:

| 字段 | 说明 |
|------|------|
| content | 提取后的文本内容，用于后续向量化和全文搜索 |

**错误响应**:
- `401` — 未认证
- `422` — 文件类型不支持、文件为空（0 字节）、title 参数校验失败
- `413` — 文件大小超过 50MB
- `500` — 文件保存失败或文本提取失败

**业务规则**:
1. 文件按 `{user_id}/{uuid}.{ext}` 命名存储，同名文件不冲突
2. 上传后立即触发文本提取，提取结果同步写入 content 字段
3. 文本提取失败不影响文件保存（原始文件仍保留在磁盘上）
4. 一次请求只能上传一个文件

---

#### GET /api/v1/documents — 获取文档列表（分页）

**请求头**: `Authorization: Bearer <access_token>`

**查询参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| file_type | string | 否 | - | 过滤文件类型: `pdf`, `md`, `txt`, `html` |
| offset | integer | 否 | 0 | 分页偏移量 |
| limit | integer | 否 | 20 | 每页数量（最大 100） |

**成功响应** (200):
```json
{
  "items": [
    {
      "id": 1,
      "user_id": 1,
      "title": "Python学习笔记",
      "file_path": "/app/uploads/1/a1b2c3d4.pdf",
      "file_type": "pdf",
      "content": "第一章 Python基础...",
      "created_at": "2026-06-04T10:00:00Z",
      "updated_at": "2026-06-04T10:00:00Z"
    }
  ],
  "total": 10,
  "offset": 0,
  "limit": 20
}
```

**注意**: 列表中的 `content` 字段会截断，仅返回前 200 个字符作为预览。完整内容需通过详情接口获取。

**错误响应**:
- `401` — 未认证
- `422` — file_type 值无效

---

#### GET /api/v1/documents/{document_id} — 获取文档详情

**请求头**: `Authorization: Bearer <access_token>`

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| document_id | integer | 文档 ID |

**成功响应** (200):
```json
{
  "id": 1,
  "user_id": 1,
  "title": "Python学习笔记",
  "file_path": "/app/uploads/1/a1b2c3d4.pdf",
  "file_type": "pdf",
  "content": "第一章 Python基础\n1.1 变量和数据类型\n...（完整提取文本内容）",
  "created_at": "2026-06-04T10:00:00Z",
  "updated_at": "2026-06-04T10:00:00Z"
}
```

**错误响应**:
- `401` — 未认证
- `403` — 文档不属于当前用户
- `404` — 文档不存在

---

#### DELETE /api/v1/documents/{document_id} — 删除文档

**描述**: 同时删除磁盘上的原始文件和数据库记录。此操作不可逆。

**请求头**: `Authorization: Bearer <access_token>`

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| document_id | integer | 文档 ID |

**成功响应** (204): 无响应体

**错误响应**:
- `401` — 未认证
- `403` — 文档不属于当前用户
- `404` — 文档不存在

**业务规则**:
1. 数据库记录和磁盘文件同时删除（尽力而为：文件删除失败不影响数据库删除）
2. 删除后 content 不可恢复

---

#### GET /api/v1/review-cards — 复习卡片列表（留作 Step 12）
#### POST /api/v1/review-cards — 创建复习卡片（留作 Step 12）
#### PATCH /api/v1/review-cards/{id}/review — 提交复习评分（留作 Step 12）
#### POST /api/v1/qa/ask — RAG 问答（留作 Step 11）
#### POST /api/v1/quizzes/generate — AI 自动出题（留作 Step 13）
#### GET /api/v1/quizzes — 测验列表（留作 Step 13）

---

### 3.3 知识图谱模块 (Step 12+)

#### GET /api/v1/concepts — 概念列表
#### POST /api/v1/concepts — 创建概念
#### POST /api/v1/concepts/{id}/relations — 创建概念关系
#### GET /api/v1/graph — 获取知识图谱数据

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
