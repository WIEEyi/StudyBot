"""
Auth + Users API 单元测试

覆盖:
- POST /auth/register — 注册
- POST /auth/login — 登录
- POST /auth/refresh — 刷新 Token
- GET /users/me — 获取当前用户
- 异常: 重复注册、错误密码、无效 Token
"""

import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.anyio
class TestRegister:
    """POST /auth/register — 用户注册"""

    async def test_register_success(self, async_client: AsyncClient):
        """正常注册（使用新邮箱）"""
        email = f"auth_new_{uuid.uuid4().hex[:8]}@example.com"
        resp = await async_client.post("/api/v1/auth/register", json={
            "email": email,
            "username": f"authnew_{uuid.uuid4().hex[:6]}",
            "password": "testpass123",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_register_short_password(self, async_client: AsyncClient):
        """密码太短 → 422"""
        resp = await async_client.post("/api/v1/auth/register", json={
            "email": f"short_{uuid.uuid4().hex[:8]}@example.com",
            "username": f"short_{uuid.uuid4().hex[:6]}",
            "password": "12",
        })
        assert resp.status_code == 422

    async def test_register_invalid_email(self, async_client: AsyncClient):
        """无效邮箱 → 422"""
        resp = await async_client.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "username": "bademail",
            "password": "testpass123",
        })
        assert resp.status_code == 422

    async def test_register_missing_fields(self, async_client: AsyncClient):
        """缺少必填字段 → 422"""
        resp = await async_client.post("/api/v1/auth/register", json={
            "email": f"miss_{uuid.uuid4().hex[:8]}@example.com",
            # 缺少 username 和 password
        })
        assert resp.status_code == 422


@pytest.mark.anyio
class TestLogin:
    """POST /auth/login — 用户登录"""

    async def test_login_success(self, async_client: AsyncClient, test_user):
        """正常登录（conftest 已注册用户）"""
        resp = await async_client.post("/api/v1/auth/login", json={
            "email": test_user["email"],
            "password": test_user["password"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_login_wrong_password(self, async_client: AsyncClient, test_user):
        """错误密码 → 401"""
        resp = await async_client.post("/api/v1/auth/login", json={
            "email": test_user["email"],
            "password": "wrong_password",
        })
        assert resp.status_code == 401

    async def test_login_nonexistent_user(self, async_client: AsyncClient):
        """不存在的用户 → 401"""
        resp = await async_client.post("/api/v1/auth/login", json={
            "email": f"nouser_{uuid.uuid4().hex[:8]}@example.com",
            "password": "testpass123",
        })
        assert resp.status_code == 401


@pytest.mark.anyio
class TestRefresh:
    """POST /auth/refresh — 刷新 Token"""

    async def test_refresh_success(self, async_client: AsyncClient, test_user):
        """正常刷新 Token"""
        # 先登录获取 refresh_token
        login_resp = await async_client.post("/api/v1/auth/login", json={
            "email": test_user["email"],
            "password": test_user["password"],
        })
        assert login_resp.status_code == 200
        refresh_token = login_resp.json()["refresh_token"]

        # 刷新
        resp = await async_client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_refresh_invalid_token(self, async_client: AsyncClient):
        """无效 refresh_token → 401"""
        resp = await async_client.post("/api/v1/auth/refresh", json={
            "refresh_token": "invalid_token_here",
        })
        assert resp.status_code == 401


@pytest.mark.anyio
class TestGetMe:
    """GET /users/me — 获取当前用户"""

    async def test_get_me_success(self, async_client: AsyncClient):
        """获取当前用户信息"""
        resp = await async_client.get("/api/v1/users/me")
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert "email" in data
        assert "username" in data
        assert "is_active" in data
        assert data["is_active"] is True

    async def test_get_me_without_auth(self):
        """无认证 → 401/403"""
        from httpx import AsyncClient as AC, ASGITransport
        from app.main import app
        transport = ASGITransport(app=app)
        async with AC(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/users/me")
            assert resp.status_code in (401, 403)

    async def test_get_me_invalid_token(self):
        """无效 Token → 401/403"""
        from httpx import AsyncClient as AC, ASGITransport
        from app.main import app
        transport = ASGITransport(app=app)
        async with AC(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/users/me", headers={
                "Authorization": "Bearer invalid_token",
            })
            assert resp.status_code in (401, 403)
