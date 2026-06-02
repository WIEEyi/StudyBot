# Step 8: PlannerAgent + WebSocket — AI 学习计划生成

**日期**: 2026-06-02 | **状态**: 已完成（57/57 测试通过）

---

## 目标

用户创建学习目标后，通过 WebSocket 触发 PlannerAgent（LangGraph），AI 自动将目标分解为结构化学习计划（里程碑 + 任务），实时推送生成进度。

---

## 会话一 (2026-06-02 上午)：文档 + 方案设计

### 1. 更新 PRD 文档
- `docs/PRD_zh.md` 第 2.3.1 章节扩充：技术实现、Agent 工作流、事件流表、边界处理、错误处理、数据库变更
- `docs/PRD_en.md` 同步更新

### 2. 更新 API 文档
- `docs/API_zh.md` 第 3.1 章节扩充：连接方式、认证、消息协议表、错误码表、完整消息流示例
- `docs/API_en.md` 同步更新

### 3. 方案设计（Plan Mode）
- 架构：LangGraph StateGraph，3 节点（analyze_goal → generate_plan → save_plan）
- milestone 字段决定：Task 表加字符串字段而非独立 Milestone 表
- WebSocket 认证：JWT access_token 通过 query param `token` 传入

---

## 会话二 (2026-06-02 下午)：源码实现 + 测试 + Docker 验证

### 4. Task 模型 + Schema 加 `milestone` 字段

**`backend/app/models/task.py`**:
```python
milestone: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
```

**`backend/app/schemas/task.py`**:
- `TaskCreate`、`TaskUpdate`、`TaskResponse` 各加 `milestone: Optional[str]` 字段

### 5. PlannerAgent (LangGraph)

**`backend/app/agents/planner_agent.py`** — 核心 Agent:

| 组件 | 说明 |
|------|------|
| `MilestoneOutput` | Pydantic 模型：title, order |
| `TaskOutput` | Pydantic 模型：title, description, milestone, priority, estimated_minutes |
| `PlanOutput` | Pydantic 模型：milestones + tasks 列表 |
| `PlannerState` | LangGraph TypedDict：goal 信息 + stream_callback + 结果 |
| `analyze_goal` | 节点1：从 DB 加载目标，验证存在性和归属权 |
| `generate_plan` | 节点2：调用 ChatOpenAI (gpt-4o) with_structured_output，逐条推送进度 |
| `save_plan` | 节点3：`db.add_all()` 批量 INSERT 任务，推送 complete 事件 |
| `build_planner_graph` | 编译带条件边的 StateGraph |
| `run_planner` | 公开入口，接收 goal_id/user_id/db_session/stream_callback |

**Graph 结构**:
```
START → analyze_goal → generate_plan → save_plan → END
            ↓ (error)       ↓ (error)
           END              END
```

### 6. WebSocket 端点

**`backend/app/api/v1/ws.py`** — WebSocket 端点:

- 端点：`ws://host:8000/api/v1/ws/plan?token=<jwt_access_token>`
- 认证：`_authenticate_ws()` — 解析 JWT → 查 DB 验证 → 失败关闭 4001
- 消息循环：30 秒超时，接收 JSON → 分发 `generate_plan` action
- `stream_callback` 封装 `websocket.send_json()` 用于实时事件推送
- 错误处理：JSON 解析错误、无效 action、LLM 失败

**事件协议**:
| 事件 | 触发时机 | 数据结构 |
|------|----------|----------|
| `thinking` | 分析/生成阶段 | `{"event": "thinking", "message": "..."}` |
| `milestone` | 每个里程碑生成后 | `{"event": "milestone", "data": {"title": "...", "order": 1}}` |
| `task` | 每个任务生成后 | `{"event": "task", "data": {...}}` |
| `complete` | 全部保存完成后 | `{"event": "complete", "data": {"total_tasks": 10, "total_minutes": 570}}` |
| `error` | 任何步骤失败 | `{"event": "error", "message": "..."}` |

### 7. 注册路由

**`backend/app/main.py`**:
```python
from app.api.v1.ws import websocket_plan
app.websocket("/api/v1/ws/plan")(websocket_plan)
```

### 8. 单元测试

**`backend/tests/api/v1/test_ws_planner.py`** — 12 个用例，3 个测试类：

**TestPlannerAgent** (6 tests):
- `test_run_planner_success` — 正常流程（mock LLM），验证 3 milestones + 10 tasks 入库
- `test_run_planner_goal_not_found` — goal_id=99999 → error
- `test_run_planner_not_owned` — user_id 不匹配 → "无权" error
- `test_run_planner_llm_error` — LLM 抛异常 → "API 密钥无效" error
- `test_graph_workflow_structure` — 验证 3 节点存在
- `test_task_milestone_field` — 验证每个 task 的 milestone 不为空

**TestWebSocketAuth** (3 tests):
- `test_ws_no_token` — 无 token → 401/403/426
- `test_ws_invalid_token` — 无效 token → 拒绝
- `test_ws_refresh_token_rejected` — refresh_token 不能当 access_token

**TestTaskSchemas** (3 tests):
- `test_task_response_has_milestone` — 创建时 milestone 透传
- `test_task_update_milestone` — 更新 milestone 字段
- `test_task_create_without_milestone` — 不传默认 null

### 9. Docker + 迁移 + 全量测试

```bash
# 构建
docker compose build backend      # 全部层缓存，秒级完成

# 启动
docker compose up -d              # 4 个服务全 Running

# 迁移
alembic revision --autogenerate -m "add milestone to tasks"
alembic upgrade head              # 4e3d32cdf2c8

# 全量测试
pytest -v                         # 57 passed, 0 failed
```

**测试分布**: Goals 21 + Tasks 24 + WS/Planner 12 = 57

---

## Bug 修复记录

| # | 位置 | 问题 | 修复 |
|---|------|------|------|
| 1 | `backend/app/api/v1/tasks.py:161` | `create_task` 中 `Task()` 构造时漏传 `milestone` 字段 | 添加 `milestone=request.milestone` |

---

## 文件变更汇总

| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | `backend/app/models/task.py` | 添加 milestone 字段 |
| 修改 | `backend/app/schemas/task.py` | TaskCreate/Update/Response 加 milestone |
| 新建 | `backend/app/agents/planner_agent.py` | LangGraph PlannerAgent（3 节点） |
| 新建 | `backend/app/api/v1/ws.py` | WebSocket 端点 + JWT 认证 |
| 修改 | `backend/app/main.py` | 注册 WebSocket 路由 |
| 新建 | `backend/tests/api/v1/test_ws_planner.py` | 12 个测试用例 |
| 生成 | `backend/alembic/versions/4e3d32cdf2c8_add_milestone_to_tasks.py` | DB 迁移脚本 |
| 修改 | `docs/PRD_zh.md` + `docs/PRD_en.md` | 补充 Step 8 功能细节 |
| 修改 | `docs/API_zh.md` + `docs/API_en.md` | 补充 WebSocket 接口文档 |
| 修改 | `PROJECT_TRACKER.md` | 更新 Step 8 进度 |

---

## 设计决策

1. **milestone 用字符串字段而非独立表**：避免额外的 JOIN 和迁移复杂度，Task 的 milestone 字段足以支持分组展示
2. **WebSocket 用 query param 传 token**：浏览器 WebSocket API 不支持自定义请求头，query param 是行业通用方案
3. **测试只 mock LLM 不测试真实 WebSocket 连接**：httpx 对 WebSocket 测试支持有限，通过直接调用 Agent 函数 + mock LLM 覆盖核心逻辑，WebSocket 认证测试验证连接拒绝场景
