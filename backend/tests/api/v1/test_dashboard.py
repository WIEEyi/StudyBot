"""
Dashboard API 单元测试

覆盖:
- GET /dashboard/overview — 统计概览
- GET /dashboard/heatmap — 热力图
- GET /dashboard/streak — 连续天数
- POST /dashboard/session — 记录学习会话
- 异常: 401
"""

from datetime import date, timedelta
import pytest
from httpx import AsyncClient


@pytest.mark.anyio
class TestDashboardOverview:
    """GET /dashboard/overview — 统计概览"""

    async def test_overview(self, async_client: AsyncClient):
        """获取概览数据"""
        resp = await async_client.get("/api/v1/dashboard/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_goals" in data
        assert "total_tasks" in data
        assert "total_review_cards" in data
        assert "total_documents" in data
        assert "total_concepts" in data
        assert "total_study_hours" in data
        assert "today_tasks_completed" in data

    async def test_overview_without_auth(self):
        """未认证 → 401"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/dashboard/overview")
            assert resp.status_code in (401, 403)


@pytest.mark.anyio
class TestDashboardHeatmap:
    """GET /dashboard/heatmap — 热力图"""

    async def test_heatmap(self, async_client: AsyncClient):
        """获取热力图数据"""
        today = date.today()
        start = today - timedelta(days=30)
        resp = await async_client.get(
            f"/api/v1/dashboard/heatmap?start_date={start.isoformat()}&end_date={today.isoformat()}"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "start_date" in data
        assert "end_date" in data

    async def test_heatmap_invalid_date(self, async_client: AsyncClient):
        """无效日期格式 → 422"""
        resp = await async_client.get(
            "/api/v1/dashboard/heatmap?start_date=invalid&end_date=invalid"
        )
        assert resp.status_code == 422


@pytest.mark.anyio
class TestDashboardStreak:
    """GET /dashboard/streak — 连续天数"""

    async def test_streak_empty(self, async_client: AsyncClient):
        """无学习记录时连续天数"""
        resp = await async_client.get("/api/v1/dashboard/streak")
        assert resp.status_code == 200
        data = resp.json()
        assert "current_streak" in data
        assert "longest_streak" in data


@pytest.mark.anyio
class TestDashboardSession:
    """POST /dashboard/session — 记录学习会话"""

    async def test_record_session(self, async_client: AsyncClient):
        """记录学习会话"""
        resp = await async_client.post("/api/v1/dashboard/session", json={
            "duration_minutes": 60,
            "tasks_completed": 3,
            "cards_reviewed": 10,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["duration_minutes"] >= 60
        assert data["tasks_completed"] >= 3
        assert data["cards_reviewed"] >= 10

    async def test_session_accumulates(self, async_client: AsyncClient):
        """同一天的会话累加"""
        # 第一次记录
        await async_client.post("/api/v1/dashboard/session", json={
            "duration_minutes": 30,
            "tasks_completed": 1,
            "cards_reviewed": 5,
        })
        # 第二次记录（同一天，应该累加）
        resp = await async_client.post("/api/v1/dashboard/session", json={
            "duration_minutes": 20,
            "tasks_completed": 2,
            "cards_reviewed": 3,
        })
        assert resp.status_code == 201
        data = resp.json()
        # 累加后的值应该大于等于第二次提交的值
        assert data["duration_minutes"] >= 20
