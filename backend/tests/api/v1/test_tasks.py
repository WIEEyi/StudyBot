"""
任务 CRUD 单元测试

覆盖:
- 正常路径: 创建/列表/详情/更新/删除
- 异常路径: 401 未认证 / 404 不存在 / 422 参数校验
"""

import pytest


# ===================== 正常路径测试 =====================

class TestCreateTask:
    """POST /tasks — 创建任务"""

    @pytest.mark.asyncio
    async def test_create_with_all_fields(self, async_client):
        """创建带所有字段的任务"""
        # 先创建目标
        r = await async_client.post("/api/v1/goals", json={"title": "关联目标"})
        assert r.status_code == 201
        goal_id = r.json()["id"]

        response = await async_client.post("/api/v1/tasks", json={
            "title": "编写测试",
            "description": "为 CRUD 接口编写单元测试",
            "goal_id": goal_id,
            "priority": "high",
            "due_date": "2026-07-01T00:00:00Z",
            "estimated_minutes": 60,
        })
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "编写测试"
        assert data["goal_id"] == goal_id
        assert data["priority"] == "high"
        assert data["estimated_minutes"] == 60
        assert data["status"] == "todo"

        # 清理
        await async_client.delete(f"/api/v1/tasks/{data['id']}")
        await async_client.delete(f"/api/v1/goals/{goal_id}")

    @pytest.mark.asyncio
    async def test_create_minimal(self, async_client):
        """只传必填字段"""
        response = await async_client.post("/api/v1/tasks", json={
            "title": "最小任务",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "最小任务"
        assert data["priority"] == "medium"  # 默认值
        assert data["status"] == "todo"
        assert data["goal_id"] is None

        await async_client.delete(f"/api/v1/tasks/{data['id']}")

    @pytest.mark.asyncio
    async def test_create_without_goal(self, async_client):
        """不关联目标的任务（独立任务）"""
        response = await async_client.post("/api/v1/tasks", json={
            "title": "独立任务",
            "priority": "low",
        })
        assert response.status_code == 201
        assert response.json()["goal_id"] is None

        created = response.json()
        await async_client.delete(f"/api/v1/tasks/{created['id']}")


class TestListTasks:
    """GET /tasks — 获取任务列表"""

    @pytest.mark.asyncio
    async def test_list_empty(self, async_client):
        """无任务时返回空列表"""
        response = await async_client.get("/api/v1/tasks")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_list_with_pagination(self, async_client):
        """分页参数"""
        response = await async_client.get("/api/v1/tasks?offset=0&limit=5")
        assert response.status_code == 200
        assert response.json()["limit"] == 5

    @pytest.mark.asyncio
    async def test_list_filter_by_status(self, async_client):
        """按状态过滤"""
        r = await async_client.post("/api/v1/tasks", json={"title": "状态过滤测试"})
        assert r.status_code == 201
        task_id = r.json()["id"]

        response = await async_client.get("/api/v1/tasks?status=todo")
        assert response.status_code == 200
        data = response.json()
        assert any(t["id"] == task_id for t in data["items"])

        # 过滤 done 不应包含它
        response = await async_client.get("/api/v1/tasks?status=done")
        ids = [t["id"] for t in response.json()["items"]]
        assert task_id not in ids

        await async_client.delete(f"/api/v1/tasks/{task_id}")

    @pytest.mark.asyncio
    async def test_list_filter_by_priority(self, async_client):
        """按优先级过滤"""
        r = await async_client.post("/api/v1/tasks", json={
            "title": "高优先级", "priority": "high",
        })
        task_id = r.json()["id"]

        response = await async_client.get("/api/v1/tasks?priority=high")
        assert response.status_code == 200
        assert any(t["id"] == task_id for t in response.json()["items"])

        await async_client.delete(f"/api/v1/tasks/{task_id}")

    @pytest.mark.asyncio
    async def test_list_filter_by_goal_id(self, async_client):
        """按 goal_id 过滤"""
        # 创建目标和任务
        r_goal = await async_client.post("/api/v1/goals", json={"title": "过滤目标"})
        goal_id = r_goal.json()["id"]

        r_task = await async_client.post("/api/v1/tasks", json={
            "title": "关联任务", "goal_id": goal_id,
        })
        task_id = r_task.json()["id"]

        response = await async_client.get(f"/api/v1/tasks?goal_id={goal_id}")
        assert response.status_code == 200
        assert any(t["id"] == task_id for t in response.json()["items"])

        await async_client.delete(f"/api/v1/tasks/{task_id}")
        await async_client.delete(f"/api/v1/goals/{goal_id}")


class TestGetTask:
    """GET /tasks/{id} — 获取任务详情"""

    @pytest.mark.asyncio
    async def test_get_existing(self, async_client):
        """获取存在的任务"""
        r = await async_client.post("/api/v1/tasks", json={"title": "详情任务"})
        task_id = r.json()["id"]

        response = await async_client.get(f"/api/v1/tasks/{task_id}")
        assert response.status_code == 200
        assert response.json()["title"] == "详情任务"

        await async_client.delete(f"/api/v1/tasks/{task_id}")

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, async_client):
        """获取不存在的任务 → 404"""
        response = await async_client.get("/api/v1/tasks/99999")
        assert response.status_code == 404


class TestUpdateTask:
    """PUT /tasks/{id} — 更新任务"""

    @pytest.mark.asyncio
    async def test_update_all_fields(self, async_client):
        """更新所有可修改字段"""
        r = await async_client.post("/api/v1/tasks", json={
            "title": "旧任务", "priority": "low",
        })
        task_id = r.json()["id"]

        response = await async_client.put(f"/api/v1/tasks/{task_id}", json={
            "title": "新任务",
            "description": "更新后的描述",
            "priority": "high",
            "status": "in_progress",
            "estimated_minutes": 120,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "新任务"
        assert data["description"] == "更新后的描述"
        assert data["priority"] == "high"
        assert data["status"] == "in_progress"
        assert data["estimated_minutes"] == 120

        await async_client.delete(f"/api/v1/tasks/{task_id}")

    @pytest.mark.asyncio
    async def test_update_nonexistent(self, async_client):
        """更新不存在的任务 → 404"""
        response = await async_client.put("/api/v1/tasks/99999", json={
            "title": "不存在",
        })
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_empty_body(self, async_client):
        """更新时没有字段 → 400"""
        r = await async_client.post("/api/v1/tasks", json={"title": "空更新"})
        task_id = r.json()["id"]

        response = await async_client.put(f"/api/v1/tasks/{task_id}", json={})
        assert response.status_code == 400

        await async_client.delete(f"/api/v1/tasks/{task_id}")

    @pytest.mark.asyncio
    async def test_update_change_goal(self, async_client):
        """修改关联的目标"""
        r1 = await async_client.post("/api/v1/goals", json={"title": "旧目标"})
        r2 = await async_client.post("/api/v1/goals", json={"title": "新目标"})
        goal1_id = r1.json()["id"]
        goal2_id = r2.json()["id"]

        r = await async_client.post("/api/v1/tasks", json={
            "title": "换目标", "goal_id": goal1_id,
        })
        task_id = r.json()["id"]

        # 换到 goal2
        response = await async_client.put(f"/api/v1/tasks/{task_id}", json={
            "goal_id": goal2_id,
        })
        assert response.status_code == 200
        assert response.json()["goal_id"] == goal2_id

        await async_client.delete(f"/api/v1/tasks/{task_id}")
        await async_client.delete(f"/api/v1/goals/{goal1_id}")
        await async_client.delete(f"/api/v1/goals/{goal2_id}")


class TestDeleteTask:
    """DELETE /tasks/{id} — 删除任务"""

    @pytest.mark.asyncio
    async def test_delete_existing(self, async_client):
        """删除存在的任务 → 204"""
        r = await async_client.post("/api/v1/tasks", json={"title": "待删除"})
        task_id = r.json()["id"]

        response = await async_client.delete(f"/api/v1/tasks/{task_id}")
        assert response.status_code == 204

        # 确认已删除
        response = await async_client.get(f"/api/v1/tasks/{task_id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, async_client):
        """删除不存在的任务 → 404"""
        response = await async_client.delete("/api/v1/tasks/99999")
        assert response.status_code == 404


# ===================== 异常路径测试 =====================

class TestUnauthorized:
    """未认证请求"""

    @pytest.mark.asyncio
    async def test_list_without_auth(self, async_client):
        """不带 token 获取列表"""
        original_headers = async_client.headers.copy()
        async_client.headers.pop("Authorization", None)

        response = await async_client.get("/api/v1/tasks")
        assert response.status_code in (401, 403)

        async_client.headers.update(original_headers)

    @pytest.mark.asyncio
    async def test_create_without_auth(self, async_client):
        """不带 token 创建任务"""
        original_headers = async_client.headers.copy()
        async_client.headers.pop("Authorization", None)

        response = await async_client.post("/api/v1/tasks", json={"title": "非法创建"})
        assert response.status_code in (401, 403)

        async_client.headers.update(original_headers)

    @pytest.mark.asyncio
    async def test_create_with_nonexistent_goal(self, async_client):
        """创建任务关联不存在的目标 → 404"""
        response = await async_client.post("/api/v1/tasks", json={
            "title": "无效关联",
            "goal_id": 99999,
        })
        assert response.status_code == 404


class TestValidation:
    """参数校验"""

    @pytest.mark.asyncio
    async def test_create_empty_title(self, async_client):
        """创建任务 title 为空 → 422"""
        response = await async_client.post("/api/v1/tasks", json={"title": ""})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_missing_title(self, async_client):
        """缺少必填字段 → 422"""
        response = await async_client.post("/api/v1/tasks", json={})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_invalid_priority(self, async_client):
        """无效优先级应返回 422 校验错误"""
        response = await async_client.post("/api/v1/tasks", json={
            "title": "测试优先级",
            "priority": "urgent",  # 无效值
        })
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_title_too_long(self, async_client):
        """title 超过 255 → 422"""
        response = await async_client.post("/api/v1/tasks", json={
            "title": "x" * 256,
        })
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_negative_estimated_minutes(self, async_client):
        """estimated_minutes 为负数或 0 → 422"""
        response = await async_client.post("/api/v1/tasks", json={
            "title": "负数时间",
            "estimated_minutes": -1,
        })
        assert response.status_code == 422

        response = await async_client.post("/api/v1/tasks", json={
            "title": "零时间",
            "estimated_minutes": 0,
        })
        assert response.status_code == 422
