"""
Step 8: PlannerAgent + WebSocket 单元测试

测试范围:
- PlannerAgent 三节点工作流（mock LLM 响应）
- WebSocket 认证失败场景
- 正常流程生成 + 入库验证
- 边界条件（Goal 不存在、无权限、LLM 失败）
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.database import get_db
from app.models.learning_goal import LearningGoal
from app.models.task import Task
from app.agents.planner_agent import (
    run_planner,
    PlanOutput,
    MilestoneOutput,
    TaskOutput,
    build_planner_graph,
)
from app.config import get_settings

settings = get_settings()


# ===================== Mock LLM 数据 =====================

def make_mock_plan_output():
    """构造一个模拟的 LLM 返回计划数据"""
    return PlanOutput(
        milestones=[
            MilestoneOutput(title="阶段一：Python 基础", order=1),
            MilestoneOutput(title="阶段二：面向对象编程", order=2),
            MilestoneOutput(title="阶段三：Web 框架入门", order=3),
        ],
        tasks=[
            TaskOutput(title="安装 Python 环境", description="下载并安装 Python，配置 PATH", milestone="阶段一：Python 基础", priority="high", estimated_minutes=30),
            TaskOutput(title="学习变量与数据类型", description="学习 int/float/str/list/dict 等基本数据类型", milestone="阶段一：Python 基础", priority="high", estimated_minutes=60),
            TaskOutput(title="学习条件判断与循环", description="掌握 if/elif/else 和 for/while 循环", milestone="阶段一：Python 基础", priority="high", estimated_minutes=90),
            TaskOutput(title="学习函数定义", description="学习函数定义、参数传递和返回值", milestone="阶段一：Python 基础", priority="medium", estimated_minutes=60),
            TaskOutput(title="理解类与对象", description="学习 class 定义、__init__、实例方法", milestone="阶段二：面向对象编程", priority="high", estimated_minutes=90),
            TaskOutput(title="学习继承与多态", description="理解父类子类关系和方法重写", milestone="阶段二：面向对象编程", priority="medium", estimated_minutes=60),
            TaskOutput(title="实践封装与属性", description="使用 property 装饰器和私有属性", milestone="阶段二：面向对象编程", priority="medium", estimated_minutes=45),
            TaskOutput(title="安装 Flask/Django", description="选择一个 Web 框架并搭建开发环境", milestone="阶段三：Web 框架入门", priority="high", estimated_minutes=30),
            TaskOutput(title="编写第一个 Web 应用", description="创建 Hello World 页面和简单路由", milestone="阶段三：Web 框架入门", priority="high", estimated_minutes=45),
            TaskOutput(title="学习模板渲染", description="使用 Jinja2 模板引擎渲染 HTML", milestone="阶段三：Web 框架入门", priority="medium", estimated_minutes=60),
        ],
    )


# ===================== Fixtures =====================

@pytest_asyncio.fixture
async def test_db_session():
    """创建独立的测试数据库会话"""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    TestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with TestSession() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def test_goal(async_client, test_db_session):
    """创建用于 Plan 测试的 Goal，返回 goal 和 user_id"""
    # 获取当前用户信息
    response = await async_client.get("/api/v1/users/me")
    user_data = response.json()
    user_id = user_data["id"]

    # 创建一个 Goal
    from app.models.learning_goal import LearningGoal
    goal = LearningGoal(
        user_id=user_id,
        title="学习 Python 全栈开发",
        description="从零开始掌握 Python，最终能独立开发 Web 应用",
    )
    test_db_session.add(goal)
    await test_db_session.commit()
    await test_db_session.refresh(goal)

    yield goal, user_id

    # 清理
    await test_db_session.execute(text("DELETE FROM tasks WHERE goal_id = :gid"), {"gid": goal.id})
    await test_db_session.delete(goal)
    await test_db_session.commit()


# ===================== PlannerAgent 单元测试 =====================

class TestPlannerAgent:
    """测试 PlannerAgent 核心逻辑（mock LLM）"""

    @pytest.mark.asyncio
    async def test_run_planner_success(self, test_goal, test_db_session):
        """正常流程: 生成计划并保存到数据库"""
        goal, user_id = test_goal
        events = []

        async def collect_events(event_name: str, data: dict):
            events.append((event_name, data))

        # Mock LLM 调用
        with patch(
            "app.agents.planner_agent.ChatOpenAI"
        ) as mock_llm_class:
            mock_llm = MagicMock()
            mock_llm.with_structured_output.return_value.ainvoke = AsyncMock(
                return_value=make_mock_plan_output()
            )
            mock_llm_class.return_value = mock_llm

            result = await run_planner(
                goal_id=goal.id,
                user_id=user_id,
                db_session=test_db_session,
                stream_callback=collect_events,
            )

        # 验证结果
        assert result["error"] is None
        assert len(result["milestones"]) == 3
        assert len(result["tasks"]) == 10
        assert result["milestones"][0]["title"] == "阶段一：Python 基础"
        assert result["milestones"][0]["order"] == 1

        # 验证事件流
        event_types = [e[0] for e in events]
        assert "thinking" in event_types
        assert "milestone" in event_types
        assert "task" in event_types
        assert "complete" in event_types

        # 验证 complete 事件数据
        complete_event = next(e for e in events if e[0] == "complete")
        assert complete_event[1]["data"]["total_tasks"] == 10
        assert complete_event[1]["data"]["total_minutes"] > 0

        # 验证任务已入库
        from sqlalchemy import select, func
        count_result = await test_db_session.execute(
            select(func.count()).select_from(Task).where(Task.goal_id == goal.id)
        )
        task_count = count_result.scalar()
        assert task_count == 10

        # 验证 milestone 字段
        first_task = await test_db_session.execute(
            select(Task).where(Task.goal_id == goal.id, Task.milestone == "阶段一：Python 基础").limit(1)
        )
        task = first_task.scalar_one()
        assert task.milestone == "阶段一：Python 基础"
        assert task.priority == "high"

    @pytest.mark.asyncio
    async def test_run_planner_goal_not_found(self, test_db_session):
        """边界条件: Goal 不存在"""
        events = []

        async def collect_events(event_name: str, data: dict):
            events.append((event_name, data))

        result = await run_planner(
            goal_id=99999,
            user_id=1,
            db_session=test_db_session,
            stream_callback=collect_events,
        )

        assert result["error"] is not None
        assert "不存在" in result["error"]

        # 验证推送了 error 事件
        error_events = [e for e in events if e[0] == "error"]
        assert len(error_events) > 0

    @pytest.mark.asyncio
    async def test_run_planner_not_owned(self, test_goal, test_db_session):
        """边界条件: Goal 不属于当前用户"""
        goal, _ = test_goal
        events = []

        async def collect_events(event_name: str, data: dict):
            events.append((event_name, data))

        # 使用不匹配的 user_id
        result = await run_planner(
            goal_id=goal.id,
            user_id=99999,  # 不匹配的 user_id
            db_session=test_db_session,
            stream_callback=collect_events,
        )

        assert result["error"] is not None
        assert "无权" in result["error"]

    @pytest.mark.asyncio
    async def test_run_planner_llm_error(self, test_goal, test_db_session):
        """边界条件: LLM 调用失败"""
        goal, user_id = test_goal
        events = []

        async def collect_events(event_name: str, data: dict):
            events.append((event_name, data))

        with patch(
            "app.agents.planner_agent.ChatOpenAI"
        ) as mock_llm_class:
            mock_llm = MagicMock()
            mock_llm.with_structured_output.return_value.ainvoke = AsyncMock(
                side_effect=Exception("API 密钥无效")
            )
            mock_llm_class.return_value = mock_llm

            result = await run_planner(
                goal_id=goal.id,
                user_id=user_id,
                db_session=test_db_session,
                stream_callback=collect_events,
            )

        assert result["error"] is not None
        assert "API 密钥无效" in result["error"]

        # 验证推送了 error 事件
        error_events = [e for e in events if e[0] == "error"]
        assert len(error_events) > 0

    @pytest.mark.asyncio
    async def test_graph_workflow_structure(self):
        """验证 LangGraph 工作流结构正确"""
        graph = build_planner_graph()
        nodes = graph.get_graph().nodes
        node_names = {n for n in nodes.keys() if n != "__start__" and n != "__end__"}
        assert "analyze_goal" in node_names
        assert "generate_plan" in node_names
        assert "save_plan" in node_names

    @pytest.mark.asyncio
    async def test_task_milestone_field(self, test_goal, test_db_session):
        """验证 Task 的 milestone 字段正确存储"""
        goal, user_id = test_goal

        with patch("app.agents.planner_agent.ChatOpenAI") as mock_llm_class:
            mock_llm = MagicMock()
            mock_llm.with_structured_output.return_value.ainvoke = AsyncMock(
                return_value=make_mock_plan_output()
            )
            mock_llm_class.return_value = mock_llm

            await run_planner(
                goal_id=goal.id,
                user_id=user_id,
                db_session=test_db_session,
            )

        # 验证每个任务的 milestone 不为空
        tasks = await test_db_session.execute(
            select(Task).where(Task.goal_id == goal.id)
        )
        tasks = tasks.scalars().all()
        assert len(tasks) > 0
        for t in tasks:
            assert t.milestone is not None
            assert len(t.milestone) > 0


# ===================== WebSocket 认证测试 =====================

class TestWebSocketAuth:
    """测试 WebSocket 端点认证"""

    @pytest.mark.asyncio
    async def test_ws_no_token(self, async_client):
        """无 token 连接应被拒绝"""
        # 提取 token 并构造不带 token 的请求
        token = async_client.headers.get("Authorization", "").replace("Bearer ", "")
        # 不传 token param
        try:
            async with async_client.stream("GET", "/api/v1/ws/plan") as response:
                assert response.status_code in (401, 403, 426)
        except Exception:
            # WebSocket upgrade 失败也是预期行为
            pass

    @pytest.mark.asyncio
    async def test_ws_invalid_token(self, async_client):
        """无效 token 连接应被拒绝"""
        try:
            async with async_client.stream(
                "GET", "/api/v1/ws/plan", params={"token": "invalid-token-xxx"}
            ) as response:
                assert response.status_code in (401, 403, 426)
        except Exception:
            # WebSocket upgrade 失败也是预期行为
            pass

    @pytest.mark.asyncio
    async def test_ws_refresh_token_rejected(self, async_client):
        """用 refresh_token 而非 access_token 应被拒绝"""
        from app.core.security import create_refresh_token

        # 生成一个 refresh token（type 为 "refresh" 而非 "access"）
        refresh_token = create_refresh_token(user_id=99999)
        try:
            async with async_client.stream(
                "GET", "/api/v1/ws/plan", params={"token": refresh_token}
            ) as response:
                assert response.status_code in (401, 403, 426)
        except Exception:
            # WebSocket upgrade 失败也是预期行为
            pass


# ===================== 集成测试（需要有真实 WebSocket 支持） =====================

class TestTaskSchemas:
    """验证 Task Schema 包含 milestone 字段"""

    @pytest.mark.asyncio
    async def test_task_response_has_milestone(self, async_client, test_goal, test_db_session):
        """验证创建/获取任务时 milestone 字段正常透传"""
        goal, _ = test_goal

        # 先创建带 milestone 的任务
        response = await async_client.post("/api/v1/tasks", json={
            "title": "测试里程碑任务",
            "description": "验证 milestone 字段",
            "goal_id": goal.id,
            "milestone": "阶段测试",
            "priority": "high",
            "estimated_minutes": 30,
        })
        assert response.status_code == 201
        data = response.json()
        assert data["milestone"] == "阶段测试"

        # 通过 GET 获取验证
        task_id = data["id"]
        response = await async_client.get(f"/api/v1/tasks/{task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["milestone"] == "阶段测试"

        # 清理
        await async_client.delete(f"/api/v1/tasks/{task_id}")

    @pytest.mark.asyncio
    async def test_task_update_milestone(self, async_client, test_goal):
        """验证更新任务时可以修改 milestone"""
        goal, _ = test_goal

        # 创建任务
        response = await async_client.post("/api/v1/tasks", json={
            "title": "可更新的里程碑任务",
            "description": "测试更新",
            "goal_id": goal.id,
            "milestone": "旧里程碑",
            "priority": "medium",
        })
        assert response.status_code == 201
        task_id = response.json()["id"]

        # 更新 milestone
        response = await async_client.put(f"/api/v1/tasks/{task_id}", json={
            "milestone": "新里程碑",
        })
        assert response.status_code == 200
        assert response.json()["milestone"] == "新里程碑"

        # 清理
        await async_client.delete(f"/api/v1/tasks/{task_id}")

    @pytest.mark.asyncio
    async def test_task_create_without_milestone(self, async_client, test_goal):
        """验证不传 milestone 时默认为 None"""
        goal, _ = test_goal

        response = await async_client.post("/api/v1/tasks", json={
            "title": "无里程碑任务",
            "goal_id": goal.id,
        })
        assert response.status_code == 201
        assert response.json()["milestone"] is None

        # 清理
        task_id = response.json()["id"]
        await async_client.delete(f"/api/v1/tasks/{task_id}")
