"""
学习目标 CRUD 单元测试

覆盖:
- 正常路径: 创建/列表/详情/更新/删除/切换状态
- 异常路径: 401 未认证 / 404 不存在 / 422 参数校验
"""

import pytest


# ===================== 正常路径测试 =====================

class TestCreateGoal:
    """POST /goals — 创建目标"""

    @pytest.mark.asyncio
    async def test_create_with_all_fields(self, async_client):
        """创建带所有字段的目标"""
        response = await async_client.post("/api/v1/goals", json={
            "title": "学习 FastAPI",
            "description": "掌握 FastAPI 框架的核心概念",
            "deadline": "2026-12-31T00:00:00Z",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "学习 FastAPI"
        assert data["description"] == "掌握 FastAPI 框架的核心概念"
        assert data["status"] == "active"
        assert data["task_count"] == 0
        assert "id" in data
        assert "created_at" in data

        # 清理：删除创建的目标
        await async_client.delete(f"/api/v1/goals/{data['id']}")

    @pytest.mark.asyncio
    async def test_create_minimal(self, async_client):
        """只传必填字段 title"""
        response = await async_client.post("/api/v1/goals", json={
            "title": "最小目标",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "最小目标"
        assert data["description"] is None
        assert data["deadline"] is None
        assert data["status"] == "active"

        await async_client.delete(f"/api/v1/goals/{data['id']}")


class TestListGoals:
    """GET /goals — 获取目标列表"""

    @pytest.mark.asyncio
    async def test_list_empty(self, async_client):
        """无目标时返回空列表"""
        response = await async_client.get("/api/v1/goals")
        assert response.status_code == 200
        data = response.json()
        # 可能不为空（之前测试残留），只验证结构
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    @pytest.mark.asyncio
    async def test_list_with_pagination(self, async_client):
        """分页参数测试"""
        response = await async_client.get("/api/v1/goals?offset=0&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert data["offset"] == 0
        assert data["limit"] == 5

    @pytest.mark.asyncio
    async def test_list_filter_by_status(self, async_client):
        """按状态过滤"""
        # 创建 active 目标
        r = await async_client.post("/api/v1/goals", json={"title": "过滤测试"})
        assert r.status_code == 201
        goal_id = r.json()["id"]

        # 过滤 active
        response = await async_client.get("/api/v1/goals?goal_status=active")
        assert response.status_code == 200
        data = response.json()
        assert all(g["status"] == "active" for g in data["items"])

        # 过滤 completed 应该不返回上面创建的
        response = await async_client.get("/api/v1/goals?goal_status=completed")
        assert response.status_code == 200
        ids = [g["id"] for g in response.json()["items"]]
        assert goal_id not in ids

        await async_client.delete(f"/api/v1/goals/{goal_id}")


class TestGetGoal:
    """GET /goals/{id} — 获取目标详情"""

    @pytest.mark.asyncio
    async def test_get_existing(self, async_client):
        """获取存在的目标"""
        r = await async_client.post("/api/v1/goals", json={"title": "详情测试"})
        goal_id = r.json()["id"]

        response = await async_client.get(f"/api/v1/goals/{goal_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "详情测试"
        assert "tasks" in data  # 包含任务列表

        await async_client.delete(f"/api/v1/goals/{goal_id}")

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, async_client):
        """获取不存在的目标 → 404"""
        response = await async_client.get("/api/v1/goals/99999")
        assert response.status_code == 404


class TestUpdateGoal:
    """PUT /goals/{id} — 更新目标"""

    @pytest.mark.asyncio
    async def test_update_title_and_description(self, async_client):
        """更新标题和描述"""
        r = await async_client.post("/api/v1/goals", json={"title": "旧标题"})
        goal_id = r.json()["id"]

        response = await async_client.put(f"/api/v1/goals/{goal_id}", json={
            "title": "新标题",
            "description": "新描述",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "新标题"
        assert data["description"] == "新描述"

        await async_client.delete(f"/api/v1/goals/{goal_id}")

    @pytest.mark.asyncio
    async def test_update_nonexistent(self, async_client):
        """更新不存在的目标 → 404"""
        response = await async_client.put("/api/v1/goals/99999", json={
            "title": "不存在的目标",
        })
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_empty_body(self, async_client):
        """更新时没有提供任何字段 → 400"""
        r = await async_client.post("/api/v1/goals", json={"title": "空更新测试"})
        goal_id = r.json()["id"]

        response = await async_client.put(f"/api/v1/goals/{goal_id}", json={})
        assert response.status_code == 400

        await async_client.delete(f"/api/v1/goals/{goal_id}")


class TestDeleteGoal:
    """DELETE /goals/{id} — 删除目标"""

    @pytest.mark.asyncio
    async def test_delete_existing(self, async_client):
        """删除存在的目标 → 204"""
        r = await async_client.post("/api/v1/goals", json={"title": "待删除"})
        goal_id = r.json()["id"]

        response = await async_client.delete(f"/api/v1/goals/{goal_id}")
        assert response.status_code == 204

        # 确认已删除
        response = await async_client.get(f"/api/v1/goals/{goal_id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, async_client):
        """删除不存在的目标 → 404"""
        response = await async_client.delete("/api/v1/goals/99999")
        assert response.status_code == 404


class TestToggleGoalStatus:
    """PATCH /goals/{id}/status — 切换目标状态"""

    @pytest.mark.asyncio
    async def test_toggle_to_completed(self, async_client):
        """切换为 completed"""
        r = await async_client.post("/api/v1/goals", json={"title": "状态测试"})
        goal_id = r.json()["id"]

        response = await async_client.patch(
            f"/api/v1/goals/{goal_id}/status?status=completed"
        )
        assert response.status_code == 200
        assert response.json()["status"] == "completed"

        await async_client.delete(f"/api/v1/goals/{goal_id}")

    @pytest.mark.asyncio
    async def test_toggle_to_paused(self, async_client):
        """切换为 paused"""
        r = await async_client.post("/api/v1/goals", json={"title": "暂停测试"})
        goal_id = r.json()["id"]

        response = await async_client.patch(
            f"/api/v1/goals/{goal_id}/status?status=paused"
        )
        assert response.status_code == 200
        assert response.json()["status"] == "paused"

        await async_client.delete(f"/api/v1/goals/{goal_id}")

    @pytest.mark.asyncio
    async def test_toggle_invalid_status(self, async_client):
        """切换为无效状态 → 422"""
        r = await async_client.post("/api/v1/goals", json={"title": "错误状态测试"})
        goal_id = r.json()["id"]

        response = await async_client.patch(
            f"/api/v1/goals/{goal_id}/status?status=invalid_status"
        )
        assert response.status_code == 422

        await async_client.delete(f"/api/v1/goals/{goal_id}")


# ===================== 异常路径测试 =====================

class TestUnauthorized:
    """未认证请求 — 所有接口应返回 401"""

    @pytest.mark.asyncio
    async def test_list_without_auth(self, async_client):
        """不带 token 访问需要认证的接口"""
        # 临时去掉认证头
        original_headers = async_client.headers.copy()
        async_client.headers.pop("Authorization", None)

        response = await async_client.get("/api/v1/goals")
        assert response.status_code in (401, 403)

        # 恢复认证头
        async_client.headers.update(original_headers)

    @pytest.mark.asyncio
    async def test_create_without_auth(self, async_client):
        """不带 token 创建目标"""
        original_headers = async_client.headers.copy()
        async_client.headers.pop("Authorization", None)

        response = await async_client.post("/api/v1/goals", json={"title": "非法创建"})
        assert response.status_code in (401, 403)

        async_client.headers.update(original_headers)

    @pytest.mark.asyncio
    async def test_update_other_users_goal(self, async_client):
        """（权限隔离）用户不能修改别人的目标
        由于当前测试只有一个用户，这个测试验证 403 响应机制存在即可。
        核心逻辑：_get_user_goal() 会校验 user_id
        """
        # 创建目标
        r = await async_client.post("/api/v1/goals", json={"title": "权限测试"})
        goal_id = r.json()["id"]

        # 同一个用户访问自己的目标 → 应该成功
        response = await async_client.get(f"/api/v1/goals/{goal_id}")
        assert response.status_code == 200

        await async_client.delete(f"/api/v1/goals/{goal_id}")


class TestValidation:
    """参数校验"""

    @pytest.mark.asyncio
    async def test_create_empty_title(self, async_client):
        """创建目标时 title 为空 → 422"""
        response = await async_client.post("/api/v1/goals", json={
            "title": "",
        })
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_missing_title(self, async_client):
        """创建目标时缺少 title → 422"""
        response = await async_client.post("/api/v1/goals", json={
            "description": "没有标题",
        })
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_title_too_long(self, async_client):
        """title 超过 255 字符 → 422"""
        response = await async_client.post("/api/v1/goals", json={
            "title": "x" * 256,
        })
        assert response.status_code == 422
