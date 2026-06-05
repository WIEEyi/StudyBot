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

### 3.2 文档管理模块 (Documents) — Step 9 ✅ 已完成

接口详情见 [2.5 文档模块](#待补充)

---

### 3.3 文档向量化模块 (Embedding) — Step 10 ✅ 已完成

#### POST /api/v1/documents/{document_id}/embed — 触发文档分块 + 向量嵌入

**描述**: 对已上传文档的文本内容进行分块和向量化，存入 pgvector。幂等操作，重复调用会删除旧分块后重新生成。

**请求头**: `Authorization: Bearer <access_token>`

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| document_id | integer | 文档 ID |

**成功响应** (200):
```json
{
  "document_id": 1,
  "chunks_created": 12
}
```

**错误响应**:
- `401` — 未认证
- `403` — 文档不属于当前用户
- `404` — 文档不存在
- `422` — 文档内容为空，无法生成嵌入向量
- `500` — OpenAI API 调用失败

**业务规则**:
1. 分块策略: RecursiveCharacterTextSplitter, chunk_size=500 tokens, chunk_overlap=50 tokens
2. 向量维度: text-embedding-3-small = 1536 维
3. 文档上传后自动触发嵌入（失败时优雅降级，不阻塞上传）

---

#### GET /api/v1/documents/{document_id}/chunks — 获取文档分块列表

**描述**: 分页获取文档的所有分块（**不含** embedding 向量字段，向量仅用于服务端相似度计算）。

**请求头**: `Authorization: Bearer <access_token>`

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| document_id | integer | 文档 ID |

**查询参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| offset | integer | 否 | 0 | 分页偏移量 |
| limit | integer | 否 | 50 | 每页条数（最大 200） |

**成功响应** (200):
```json
{
  "items": [
    {
      "id": 1,
      "document_id": 1,
      "chunk_index": 0,
      "content": "第一章 Python基础...",
      "token_count": 350,
      "created_at": "2026-06-05T10:00:00Z",
      "updated_at": "2026-06-05T10:00:00Z"
    }
  ],
  "total": 12,
  "offset": 0,
  "limit": 50
}
```

**错误响应**:
- `401` — 未认证
- `403` — 文档不属于当前用户
- `404` — 文档不存在

---

### 3.4 语义搜索模块 (Search) — Step 10 ✅ 已完成

#### POST /api/v1/search — 语义搜索

**描述**: 将查询文本向量化后，在用户所有文档分块中执行余弦相似度搜索，返回最相关的分块及相似度分数。Step 11 将在此基础上增加 AI 答案生成（RAG）。

**请求头**: `Authorization: Bearer <access_token>`

**请求体**:
```json
{
  "query": "Python 中如何实现异步编程",
  "top_k": 5,
  "threshold": 0.3
}
```

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| query | string (1-1000) | 是 | - | 自然语言搜索词 |
| top_k | integer (1-50) | 否 | 5 | 返回的最相关分块数量 |
| threshold | float (0.0-1.0) | 否 | 0.3 | 最低余弦相似度阈值 |

**成功响应** (200):
```json
{
  "query": "Python 中如何实现异步编程",
  "results": [
    {
      "chunk_id": 5,
      "document_id": 1,
      "document_title": "Python 学习笔记",
      "chunk_index": 4,
      "content": "Python 的异步编程主要基于 asyncio 库...",
      "similarity": 0.8542,
      "token_count": 480
    }
  ],
  "total": 1
}
```

| 字段 | 说明 |
|------|------|
| similarity | 余弦相似度 (0-1)，1 表示完全匹配 |

**错误响应**:
- `401` — 未认证
- `422` — query 为空或超过 1000 字符、top_k 超出范围
- `500` — OpenAI API 调用失败

**业务规则**:
1. 搜索范围仅限当前用户自己的文档分块
2. 使用 pgvector HNSW 索引加速向量搜索
3. 结果按相似度降序排列

---

### 3.5 知识图谱模块 (Step 12+)

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
