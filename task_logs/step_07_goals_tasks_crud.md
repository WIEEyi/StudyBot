# Step 7: Goals + Tasks CRUD API

**日期**: 2026-06-02 | **状态**: ✅ 已完成（45/45 测试通过 + 手动验证通过）

---

## 会话一 (2026-06-02 上午)：源码编写

#### 1. 创建 Pydantic Schemas

**`schemas/goal.py`** — 5 个模型:
- `GoalCreate` — title(必填), description(可选), deadline(可选)
- `GoalUpdate` — 所有字段可选，部分更新语义
- `GoalResponse` — id, user_id, title, description, deadline, status, task_count, created_at, updated_at
- `GoalDetailResponse` — 继承 GoalResponse，额外包含 tasks 列表
- `GoalListResponse` — items, total, offset, limit

**`schemas/task.py`** — 4 个模型:
- `TaskCreate` — title(必填), description, goal_id, priority, due_date, estimated_minutes
- `TaskUpdate` — 所有字段可选
- `TaskResponse` — 完整任务数据，`model_config = {"from_attributes": True}`
- `TaskListResponse` — 标准分页结构

#### 2. 创建 API 路由

**`api/v1/goals.py`** — 6 个端点:

| 方法 | 路径 | 功能 | 状态码 |
|------|------|------|--------|
| GET | /goals | 分页列表（status 过滤） | 200 |
| GET | /goals/{id} | 目标详情（含 tasks） | 200 |
| POST | /goals | 创建目标 | 201 |
| PUT | /goals/{id} | 更新目标（部分更新） | 200 |
| DELETE | /goals/{id} | 删除目标 | 204 |
| PATCH | /goals/{id}/status | 切换状态 | 200 |

关键逻辑:
- `_get_user_goal()` 辅助函数统一校验归属权（404 + 403）
- 列表接口用 `selectinload(LearningGoal.tasks)` 预加载 task 数量
- 详情接口构造 `TaskResponse` 避免循环引用

**`api/v1/tasks.py`** — 5 个端点:

| 方法 | 路径 | 功能 | 状态码 |
|------|------|------|--------|
| GET | /tasks | 分页列表（goal_id/status/priority 过滤） | 200 |
| GET | /tasks/{id} | 任务详情 | 200 |
| POST | /tasks | 创建任务（校验 goal 归属） | 201 |
| PUT | /tasks/{id} | 更新任务（校验新 goal 归属） | 200 |
| DELETE | /tasks/{id} | 删除任务 | 204 |

关键逻辑:
- 创建/更新时如果指定 goal_id，校验目标是否存在且属于当前用户
- 使用 `alias="status"` 处理 Query 参数命名冲突

#### 3. 注册路由

`main.py` 新增:
```python
from app.api.v1.goals import router as goals_router
from app.api.v1.tasks import router as tasks_router
app.include_router(goals_router, prefix="/api/v1")
app.include_router(tasks_router, prefix="/api/v1")
```

---

### 阶段二：测试基础设施

#### 4. 目录结构

```
backend/tests/
├── __init__.py
├── conftest.py           # 共享 fixtures
└── api/
    ├── __init__.py
    └── v1/
        ├── __init__.py
        ├── test_goals.py  # 15 个测试用例
        └── test_tasks.py  # 18 个测试用例
```

#### 5. `conftest.py` 设计

- **传输层**: `httpx.AsyncClient + ASGITransport`，直接调用 ASGI app（不走网络）
- **测试用户**: session 级别，uuid 随机生成 email/username 避免冲突
- **认证**: 注册后从响应提取 `access_token`，预设到 client headers

```python
transport = ASGITransport(app=app)
async with AsyncClient(transport=transport, base_url="http://test") as client:
    # 注册 → 获取 token → 设置 Authorization header
    yield client
```

#### 6. 测试用例覆盖

**test_goals.py** (15 个):
- Class TestCreateGoal: 完整字段创建 / 最小字段创建
- Class TestListGoals: 空列表 / 分页 / status 过滤
- Class TestGetGoal: 获取存在的 / 404 不存在
- Class TestUpdateGoal: 更新字段 / 404 / 空 body 400
- Class TestDeleteGoal: 删除成功 204 / 404 / 二次确认
- Class TestToggleGoalStatus: completed / paused / 无效 status 422
- Class TestUnauthorized: 无 token 401 / 权限隔离
- Class TestValidation: 空 title / 缺 title / 超长 title 422

**test_tasks.py** (18 个):
- Class TestCreateTask: 全字段 / 最小字段 / 无 goal / 无效 goal_id 404
- Class TestListTasks: 空列表 / 分页 / status/priority/goal_id 过滤
- Class TestGetTask: 存在的 / 404
- Class TestUpdateTask: 全字段更新 / 404 / 空 body 400 / 换 goal
- Class TestDeleteTask: 成功 204 / 404 / 二次确认
- Class TestUnauthorized: 无 token 401
- Class TestValidation: 空 title / 缺 title / 超长 title / 负数时间 / 零时间

---

### 阶段三：依赖更新

`requirements.txt` 新增:
```
pytest==8.3.3
pytest-asyncio==0.24.0
```

---

---

## 会话二 (2026-06-02 下午)：测试验证

### 1. 重建镜像

```bash
docker compose build backend
```
镜像重建成功，pytest 8.3.3 + pytest-asyncio 0.24.0 已安装。

### 2. 测试基础设施调整

**问题 1**: `backend/__init__.py` 造成命名空间冲突
- 文件位于 `/app/__init__.py`，使 `/app` 目录本身成为一个 Python 包
- `from app.main import app` 实际导入 `/app/__init__.py` 而非 `/app/app/main.py`
- 修复: 删除 `backend/__init__.py`（无实际用途）

**问题 2**: conftest 的 sys.path 未规范化
- `os.path.join(..., "..")` 生成 `/app/tests/..`，Python 不自动解析
- 修复: 改用 `os.path.abspath()`

**问题 3**: ASGITransport + FastAPI lifespan 跨 event loop 冲突
- ASGITransport 运行 lifespan → 创建 engine → dispose engine
- 第二测试再运行 lifespan → 已销毁的 engine 在旧 event loop
- 多次尝试 session scope / loop_scope 均无效（anyio 内部管理 loop）
- 修复: `app.router.lifespan_context = None` + function scope fixture + dependency_overrides

**新增文件**: `pytest.ini` — pythonpath + asyncio_mode 配置

### 3. 测试运行结果

```bash
docker compose exec backend pytest -v
# 结果: 45 passed, 0 failed
```

全部 45 个测试用例通过:
- Goals: 21 个（正常 + 异常路径全覆盖）
- Tasks: 24 个（正常 + 异常路径全覆盖）

### 4. 修复的 3 个代码 Bug

1. **`goals.py:238`** — `status.HTTP_422_UNPROCESSABLE_ENTITY` 错误
   - 原因: 函数参数 `status` 遮蔽了 `starlette.status` 模块
   - 修复: `from fastapi import ... status as http_status`

2. **`test_tasks.py:70`** — `data['id']` NameError
   - 原因: 变量 `data` 未定义（应为 `response.json()`）
   - 修复: 添加 `created = response.json()`

3. **`schemas/task.py`** — priority 缺少枚举校验
   - 原因: `priority: str` 接受任意字符串，无效值直达 DB 导致 500
   - 修复: 改为 `Literal["low", "medium", "high"]`

### 5. 手动 CRUD 验证

用 httpx 脚本在容器内验证完整流程:
- 注册 → 创建目标 → 创建任务 → 列表/分页/过滤 → 切换状态 → 更新 → 删除
- 全部接口返回正确状态码和数据

---

## 待执行任务

_全部完成 ✅_

---

## 技术要点记录

| 概念 | 说明 |
|------|------|
| ASGITransport | httpx 提供的 ASGI 传输适配器，直接调用 FastAPI app 实例，不需要真实 HTTP 服务器 |
| selectinload | SQLAlchemy 预加载方案，用单独的 SELECT IN 查询加载关联数据，避免 N+1 |
| model_dump(exclude_unset=True) | Pydantic 序列化时只包含显式赋值的字段，实现部分更新 |
| model_validate() vs from_orm | Pydantic v2 的 ORM 转换方法，替代 v1 的 from_orm |
| alias Query 参数 | FastAPI 允许用 `Query(alias=...)` 解决 Python 保留字冲突（如 status） |

---

[返回索引](../TASK_LOG.md)
