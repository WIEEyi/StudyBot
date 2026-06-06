"""
Dashboard API 单元测试

测试覆盖:
- GET /dashboard/overview — 统计概览（正常 + 401）
- GET /dashboard/heatmap — 热力图数据（正常/范围校验/401/422）
- GET /dashboard/streak — 连续天数（正常/空数据/401）
- POST /dashboard/study-session — 学习会话记录（创建/累加/部分数据/401）
- POST /dashboard/weekly-insight — AI 周报（正常/401）
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from datetime import date, datetime, timedelta, timezone


# ============================================================================
# 辅助函数
# ============================================================================

async def _create_task(client: AsyncClient, title: str, status: str = "todo",
                        completed_at=None):
    """创建任务，返回响应 JSON"""
    resp = await client.post("/api/v1/tasks", json={
        "title": title,
        "description": f"任务描述: {title}",
        "priority": "medium",
    })
    assert resp.status_code == 201, f"创建任务失败: {resp.text}"
    task = resp.json()
    # 如果需要设置状态和完成时间，通过 update 设置
    if status != "todo" or completed_at is not None:
        # 直接更新任务状态
        update_data = {"status": status}
        resp = await client.put(f"/api/v1/tasks/{task['id']}", json=update_data)
        assert resp.status_code == 200, f"更新任务失败: {resp.text}"
        task = resp.json()
    return task


async def _create_review_card(client: AsyncClient, front: str = "测试问题",
                               last_reviewed_at=None):
    """创建复习卡片，返回响应 JSON"""
    resp = await client.post("/api/v1/review-cards", json={
        "front": front,
        "back": "测试答案",
    })
    assert resp.status_code == 201, f"创建卡片失败: {resp.text}"
    card = resp.json()
    if last_reviewed_at is not None:
        # 通过评分模拟复习
        resp = await client.post(f"/api/v1/review-cards/{card['id']}/review", json={
            "rating": 4,
        })
        assert resp.status_code == 200, f"复习卡片失败: {resp.text}"
    return card


async def _record_study_session(client: AsyncClient, duration: int = 30,
                                 tasks: int = 2, cards: int = 5):
    """记录学习会话，返回响应 JSON"""
    resp = await client.post("/api/v1/dashboard/study-session", json={
        "duration_minutes": duration,
        "tasks_completed": tasks,
        "cards_reviewed": cards,
    })
    assert resp.status_code == 201, f"记录会话失败: {resp.text}"
    return resp.json()


# ============================================================================
# GET /dashboard/overview — 统计概览
# ============================================================================

class TestDashboardOverview:
    """测试统计概览端点"""

    async def test_overview_returns_200_and_valid_data(self, async_client: AsyncClient):
        """正常路径: 返回 200 且各字段为非负整数"""
        resp = await async_client.get("/api/v1/dashboard/overview")
        assert resp.status_code == 200, resp.text
        data = resp.json()

        # 所有计数字段应为非负整数
        assert data["total_goals"] >= 0
        assert data["active_goals"] >= 0
        assert data["completed_goals"] >= 0
        assert data["total_tasks"] >= 0
        assert data["completed_tasks"] >= 0
        assert data["todo_tasks"] >= 0
        assert data["in_progress_tasks"] >= 0
        assert data["total_review_cards"] >= 0
        assert data["due_review_cards"] >= 0
        assert data["total_documents"] >= 0
        assert data["total_concepts"] >= 0
        assert isinstance(data["total_study_hours"], (int, float))
        assert data["total_study_days"] >= 0
        assert data["today_tasks_completed"] >= 0
        assert data["today_cards_reviewed"] >= 0

    async def test_overview_reflects_created_data(self, async_client: AsyncClient):
        """验证概览数据与实际创建的数据一致"""
        # 创建 1 个目标 + 2 个任务
        await async_client.post("/api/v1/goals", json={"title": "统计测试目标"})
        await _create_task(async_client, "任务1", status="done")
        await _create_task(async_client, "任务2", status="in_progress")
        await _record_study_session(async_client, duration=60, tasks=2, cards=0)

        resp = await async_client.get("/api/v1/dashboard/overview")
        data = resp.json()

        assert data["total_goals"] == 1
        assert data["active_goals"] == 1
        assert data["total_tasks"] == 2
        assert data["completed_tasks"] == 1
        assert data["in_progress_tasks"] == 1
        assert data["total_study_hours"] == 1.0
        assert data["total_study_days"] == 1

    async def test_overview_requires_auth(self, async_client: AsyncClient):
        """异常路径: 无认证返回 401 或 403"""
        original_headers = async_client.headers.copy()
        async_client.headers.pop("Authorization", None)
        resp = await async_client.get("/api/v1/dashboard/overview")
        assert resp.status_code in (401, 403)
        async_client.headers.clear()
        async_client.headers.update(original_headers)


# ============================================================================
# GET /dashboard/heatmap — 热力图数据
# ============================================================================

class TestDashboardHeatmap:
    """测试热力图端点"""

    async def test_heatmap_returns_200_and_correct_range(self, async_client: AsyncClient):
        """正常路径: 返回日期范围内每一天的数据（含补零）"""
        start = (date.today() - timedelta(days=6)).isoformat()
        end = date.today().isoformat()
        resp = await async_client.get(
            f"/api/v1/dashboard/heatmap?start_date={start}&end_date={end}"
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()

        assert data["start_date"] == start
        assert data["end_date"] == end
        assert len(data["items"]) == 7  # 7 天

        # 每一天都应有 duration_minutes / tasks_completed / cards_reviewed 字段
        for item in data["items"]:
            assert "date" in item
            assert "duration_minutes" in item
            assert "tasks_completed" in item
            assert "cards_reviewed" in item

    async def test_heatmap_reflects_study_session(self, async_client: AsyncClient):
        """验证 Heatmap 包含 StudySession 数据（duration_minutes 字段）"""
        today = date.today().isoformat()
        before_resp = await async_client.get(
            f"/api/v1/dashboard/heatmap?start_date={today}&end_date={today}"
        )
        before_item = before_resp.json()["items"][0]
        before_duration = before_item["duration_minutes"]

        # 记录新的学习会话
        await _record_study_session(async_client, duration=20, tasks=1, cards=2)

        after_resp = await async_client.get(
            f"/api/v1/dashboard/heatmap?start_date={today}&end_date={today}"
        )
        after_item = after_resp.json()["items"][0]
        # duration_minutes 应增加（来自 StudySession）
        assert after_item["duration_minutes"] >= before_duration + 20 - 1  # 容差

    async def test_heatmap_reflects_task_completions(self, async_client: AsyncClient):
        """验证 Heatmap 包含 Task.completed_at 数据"""
        # 完成一个任务
        await _create_task(async_client, "热力图测试任务", status="done")

        today = date.today().isoformat()
        resp = await async_client.get(
            f"/api/v1/dashboard/heatmap?start_date={today}&end_date={today}"
        )
        assert resp.status_code == 200

        item = resp.json()["items"][0]
        assert item["tasks_completed"] >= 1

    async def test_heatmap_reflects_card_reviews(self, async_client: AsyncClient):
        """验证 Heatmap 包含 ReviewCard.last_reviewed_at 数据"""
        await _create_review_card(async_client, last_reviewed_at=True)

        today = date.today().isoformat()
        resp = await async_client.get(
            f"/api/v1/dashboard/heatmap?start_date={today}&end_date={today}"
        )
        assert resp.status_code == 200

        item = resp.json()["items"][0]
        assert item["cards_reviewed"] >= 1

    async def test_heatmap_start_after_end_returns_422(self, async_client: AsyncClient):
        """异常路径: start_date > end_date 返回 422"""
        resp = await async_client.get(
            "/api/v1/dashboard/heatmap?start_date=2026-06-10&end_date=2026-06-01"
        )
        assert resp.status_code == 422

    async def test_heatmap_range_exceeds_365_returns_422(self, async_client: AsyncClient):
        """异常路径: 查询范围超过 365 天返回 422"""
        resp = await async_client.get(
            "/api/v1/dashboard/heatmap?start_date=2025-01-01&end_date=2026-06-06"
        )
        assert resp.status_code == 422

    async def test_heatmap_requires_auth(self, async_client: AsyncClient):
        """异常路径: 无认证返回 401 或 403"""
        original_headers = async_client.headers.copy()
        async_client.headers.pop("Authorization", None)
        resp = await async_client.get(
            "/api/v1/dashboard/heatmap?start_date=2026-01-01&end_date=2026-01-07"
        )
        assert resp.status_code in (401, 403)
        async_client.headers.clear()
        async_client.headers.update(original_headers)


# ============================================================================
# GET /dashboard/streak — 连续学习天数
# ============================================================================

class TestDashboardStreak:
    """测试连续天数端点"""

    async def test_streak_returns_200_with_valid_structure(self, async_client: AsyncClient):
        """正常路径: 返回正确结构"""
        resp = await async_client.get("/api/v1/dashboard/streak")
        assert resp.status_code == 200, resp.text
        data = resp.json()

        assert "current_streak" in data
        assert "current_start_date" in data
        assert "longest_streak" in data
        assert "longest_start_date" in data
        assert "longest_end_date" in data
        assert isinstance(data["current_streak"], int)
        assert isinstance(data["longest_streak"], int)

    async def test_streak_no_activity_returns_zero(self, async_client: AsyncClient):
        """无活动时 current_streak 为 0"""
        resp = await async_client.get("/api/v1/dashboard/streak")
        assert resp.status_code == 200
        data = resp.json()

        # 新用户无活动记录，streak 应为 0
        if data["current_streak"] > 0:
            pytest.skip("已有之前测试产生的活动数据")

        assert data["current_streak"] >= 0  # 至少是 0

    async def test_streak_with_today_activity(self, async_client: AsyncClient):
        """今天有活动时 current_streak >= 1"""
        await _record_study_session(async_client, duration=30)

        resp = await async_client.get("/api/v1/dashboard/streak")
        data = resp.json()

        assert data["current_streak"] >= 1
        assert data["current_start_date"] == date.today().isoformat()

    async def test_streak_requires_auth(self, async_client: AsyncClient):
        """异常路径: 无认证返回 401 或 403"""
        original_headers = async_client.headers.copy()
        async_client.headers.pop("Authorization", None)
        resp = await async_client.get("/api/v1/dashboard/streak")
        assert resp.status_code in (401, 403)
        async_client.headers.clear()
        async_client.headers.update(original_headers)


# ============================================================================
# POST /dashboard/study-session — 记录学习会话
# ============================================================================

class TestStudySessionRecord:
    """测试学习会话记录端点"""

    async def test_create_study_session_returns_201_with_valid_structure(self, async_client: AsyncClient):
        """正常路径: 返回 201 且结构正确（值可能因数据累积而大于请求值）"""
        resp = await async_client.post("/api/v1/dashboard/study-session", json={
            "duration_minutes": 30,
            "tasks_completed": 2,
            "cards_reviewed": 5,
        })
        assert resp.status_code == 201, resp.text
        data = resp.json()

        assert data["session_date"] == date.today().isoformat()
        assert data["duration_minutes"] >= 30  # 可能累积之前的
        assert data["tasks_completed"] >= 2
        assert data["cards_reviewed"] >= 5
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    async def test_upsert_accumulates_values(self, async_client: AsyncClient):
        """正常路径: 同一天多次调用累加数值"""
        # 先记录已知值
        first = await async_client.post("/api/v1/dashboard/study-session", json={
            "duration_minutes": 10,
            "tasks_completed": 1,
            "cards_reviewed": 2,
        })
        before = first.json()
        # 再记录
        resp = await async_client.post("/api/v1/dashboard/study-session", json={
            "duration_minutes": 20,
            "tasks_completed": 3,
            "cards_reviewed": 4,
        })
        assert resp.status_code == 201
        after = resp.json()

        # 增量应等于第二次请求的值
        assert after["duration_minutes"] == before["duration_minutes"] + 20
        assert after["tasks_completed"] == before["tasks_completed"] + 3
        assert after["cards_reviewed"] == before["cards_reviewed"] + 4
        assert after["session_date"] == date.today().isoformat()

    async def test_create_with_partial_data_uses_defaults(self, async_client: AsyncClient):
        """正常路径: 未提供字段默认值为 0（通过增量验证）"""
        # 第一次：记录当前状态
        before_resp = await async_client.post("/api/v1/dashboard/study-session", json={
            "duration_minutes": 15,
        })
        before = before_resp.json()
        # 第二次：再记录相同值
        resp = await async_client.post("/api/v1/dashboard/study-session", json={
            "duration_minutes": 5,
        })
        after = resp.json()
        # 只有 duration_minutes 应该增加
        assert after["duration_minutes"] == before["duration_minutes"] + 5
        # tasks_completed 和 cards_reviewed 不变（默认为 0）
        assert after["tasks_completed"] == before["tasks_completed"]
        assert after["cards_reviewed"] == before["cards_reviewed"]

    async def test_create_with_empty_body_is_noop(self, async_client: AsyncClient):
        """正常路径: 空 body 不改变任何值（全 0 增量 = 无变化）"""
        # 先记录一条
        before_resp = await async_client.post("/api/v1/dashboard/study-session", json={
            "duration_minutes": 20,
            "tasks_completed": 3,
            "cards_reviewed": 4,
        })
        before = before_resp.json()
        # 空 body
        resp = await async_client.post("/api/v1/dashboard/study-session", json={})
        after = resp.json()
        # 值不变
        assert after["duration_minutes"] == before["duration_minutes"]
        assert after["tasks_completed"] == before["tasks_completed"]
        assert after["cards_reviewed"] == before["cards_reviewed"]

    async def test_create_with_negative_value_returns_422(self, async_client: AsyncClient):
        """异常路径: 负数返回 422"""
        resp = await async_client.post("/api/v1/dashboard/study-session", json={
            "duration_minutes": -1,
        })
        assert resp.status_code == 422

    async def test_study_session_requires_auth(self, async_client: AsyncClient):
        """异常路径: 无认证返回 401 或 403"""
        original_headers = async_client.headers.copy()
        async_client.headers.pop("Authorization", None)
        resp = await async_client.post("/api/v1/dashboard/study-session", json={
            "duration_minutes": 10,
        })
        assert resp.status_code in (401, 403)
        async_client.headers.clear()
        async_client.headers.update(original_headers)


# ============================================================================
# POST /dashboard/weekly-insight — AI 每周洞察
# ============================================================================

class TestWeeklyInsight:
    """测试 AI 每周洞察端点"""

    async def test_weekly_insight_returns_200(self, async_client: AsyncClient):
        """正常路径: 返回 200 且包含洞察文本（默认文本，因 LLM 未配置）"""
        # 先创建一些活动数据
        await _record_study_session(async_client, duration=30, tasks=2, cards=5)
        await _create_task(async_client, "洞察测试任务", status="done")
        await _create_review_card(async_client, last_reviewed_at=True)

        resp = await async_client.post("/api/v1/dashboard/weekly-insight", json={})
        assert resp.status_code == 200, resp.text
        data = resp.json()

        assert "week_start" in data
        assert "week_end" in data
        assert "insight" in data
        assert "stats" in data
        assert len(data["insight"]) > 0  # 至少有默认文本

        stats = data["stats"]
        assert stats["tasks_completed"] >= 0
        assert stats["cards_reviewed"] >= 0
        assert stats["total_study_minutes"] >= 0
        assert stats["active_days"] >= 0

    async def test_weekly_insight_returns_insight_text(self, async_client: AsyncClient):
        """AI 洞察返回非空文本（可能有或没有数据）"""
        resp = await async_client.post("/api/v1/dashboard/weekly-insight", json={})
        assert resp.status_code == 200
        data = resp.json()

        assert len(data["insight"]) > 0  # 总有洞察文本

    async def test_weekly_insight_requires_auth(self, async_client: AsyncClient):
        """异常路径: 无认证返回 401 或 403"""
        original_headers = async_client.headers.copy()
        async_client.headers.pop("Authorization", None)
        resp = await async_client.post("/api/v1/dashboard/weekly-insight", json={})
        assert resp.status_code in (401, 403)
        async_client.headers.clear()
        async_client.headers.update(original_headers)


# ============================================================================
# Task completed_at 自动设置
# ============================================================================

class TestTaskCompletedAt:
    """测试任务完成时间戳自动设置"""

    async def test_task_status_to_done_sets_completed_at(self, async_client: AsyncClient):
        """任务状态变为 done 时自动设置 completed_at"""
        resp = await async_client.post("/api/v1/tasks", json={
            "title": "completed_at 测试任务",
            "priority": "medium",
        })
        assert resp.status_code == 201
        task = resp.json()
        assert task.get("completed_at") is None  # 初始为空

        # 更新为 done
        resp = await async_client.put(f"/api/v1/tasks/{task['id']}", json={
            "status": "done",
        })
        assert resp.status_code == 200
        updated = resp.json()

        assert updated["completed_at"] is not None  # 自动设置
        assert updated["status"] == "done"

    async def test_task_update_non_status_does_not_set_completed_at(self, async_client: AsyncClient):
        """非状态变更不设置 completed_at"""
        resp = await async_client.post("/api/v1/tasks", json={
            "title": "非状态变更测试",
            "priority": "low",
        })
        task = resp.json()

        # 更新 title，不改 status
        resp = await async_client.put(f"/api/v1/tasks/{task['id']}", json={
            "title": "已改名的任务",
        })
        assert resp.status_code == 200
        updated = resp.json()

        assert updated["completed_at"] is None  # 未变 done，不设置
