"""
SchedulerAgent 单元测试

覆盖:
- POST /goals/{id}/reschedule — 重排任务
- 策略: balanced / aggressive / relaxed
- 异常: 无任务/无权限/404/无效策略
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta, timezone


@pytest.mark.anyio
class TestReschedule:
    """POST /goals/{id}/reschedule"""

    async def test_reschedule_with_tasks(self, async_client: AsyncClient):
        """有任务时重排"""
        # 创建目标
        goal_resp = await async_client.post("/api/v1/goals", json={
            "title": "Reschedule test goal",
        })
        assert goal_resp.status_code == 201
        goal_id = goal_resp.json()["id"]

        # 创建 3 个任务
        for i in range(3):
            await async_client.post("/api/v1/tasks", json={
                "title": f"Task {i+1}",
                "goal_id": goal_id,
                "priority": ["high", "medium", "low"][i],
                "due_date": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
            })

        # 重排
        resp = await async_client.post(f"/api/v1/goals/{goal_id}/reschedule?strategy=balanced")
        assert resp.status_code == 200
        data = resp.json()
        assert data["rescheduled"] == 3
        assert data["overdue"] == 3
        assert data["strategy"] == "balanced"

        # 清理
        await async_client.delete(f"/api/v1/goals/{goal_id}")

    async def test_reschedule_no_tasks(self, async_client: AsyncClient):
        """无任务时返回 0"""
        goal_resp = await async_client.post("/api/v1/goals", json={
            "title": "Empty goal",
        })
        goal_id = goal_resp.json()["id"]

        resp = await async_client.post(f"/api/v1/goals/{goal_id}/reschedule")
        assert resp.status_code == 200
        assert resp.json()["rescheduled"] == 0

        await async_client.delete(f"/api/v1/goals/{goal_id}")

    async def test_reschedule_nonexistent_goal(self, async_client: AsyncClient):
        """不存在的目标 → 404"""
        resp = await async_client.post("/api/v1/goals/99999/reschedule")
        assert resp.status_code == 404

    async def test_reschedule_invalid_strategy(self, async_client: AsyncClient):
        """无效策略 → 422"""
        goal_resp = await async_client.post("/api/v1/goals", json={
            "title": "Strategy test",
        })
        goal_id = goal_resp.json()["id"]

        resp = await async_client.post(f"/api/v1/goals/{goal_id}/reschedule?strategy=invalid")
        assert resp.status_code == 422

        await async_client.delete(f"/api/v1/goals/{goal_id}")

    async def test_reschedule_aggressive(self, async_client: AsyncClient):
        """aggressive 策略"""
        goal_resp = await async_client.post("/api/v1/goals", json={
            "title": "Aggressive test",
        })
        goal_id = goal_resp.json()["id"]

        await async_client.post("/api/v1/tasks", json={
            "title": "Urgent task",
            "goal_id": goal_id,
            "priority": "high",
        })

        resp = await async_client.post(f"/api/v1/goals/{goal_id}/reschedule?strategy=aggressive")
        assert resp.status_code == 200
        assert resp.json()["strategy"] == "aggressive"

        await async_client.delete(f"/api/v1/goals/{goal_id}")
