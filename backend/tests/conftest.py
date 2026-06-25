"""
测试共享 fixtures

提供:
- async_client: 带认证 header 的 httpx 异步客户端 (function 级别)
- test_user: 当前测试用的用户数据

架构说明:
- 使用 httpx.AsyncClient + ASGITransport 直接测试 ASGI 应用
- function 级别：每个测试独立创建 client + engine，彻底避免 event loop 冲突
- 通过 dependency_overrides 注入测试 engine 的 session
- 第一个测试注册用户，后续测试尝试登录（用户已存在）

运行:
    docker compose exec backend pytest -v
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# 设置测试环境（必须在 app 导入之前）
os.environ["APP_ENV"] = "test"

import uuid
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config import get_settings
from app.main import app
from app.core.database import get_db

settings = get_settings()

# 共享的测试用户凭据
SHARED_EMAIL = f"test_{uuid.uuid4().hex[:8]}@example.com"
SHARED_USERNAME = f"testuser_{uuid.uuid4().hex[:8]}"
SHARED_PASSWORD = "testpass123"

# 标记：第一个测试是否已完成注册
_registered = False

# 禁用 FastAPI 默认 lifespan（避免使用模块级 engine）
# 数据库生命周期由 fixture 中的 test_engine 管理
app.router.lifespan_context = None


@pytest_asyncio.fixture  # function scope
async def async_client():
    """创建带认证的异步 HTTP 客户端

    每个 test function 获得独立的 client + engine
    """
    global _registered

    # 为当前测试创建独立的数据库引擎
    test_engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_size=5,
        max_overflow=10,
    )
    TestSessionLocal = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_get_db():
        async with TestSessionLocal() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 注册或登录测试用户
        if not _registered:
            response = await client.post("/api/v1/auth/register", json={
                "email": SHARED_EMAIL,
                "username": SHARED_USERNAME,
                "password": SHARED_PASSWORD,
            })
            assert response.status_code == 201, f"注册失败: {response.text}"
            _registered = True
        else:
            response = await client.post("/api/v1/auth/login", json={
                "email": SHARED_EMAIL,
                "password": SHARED_PASSWORD,
            })
            if response.status_code != 200:
                # 登录失败则尝试注册（可能不同 engine 找不到用户）
                response = await client.post("/api/v1/auth/register", json={
                    "email": SHARED_EMAIL,
                    "username": SHARED_USERNAME,
                    "password": SHARED_PASSWORD,
                })
            assert response.status_code in (200, 201), f"认证失败: {response.text}"

        token = response.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"

        yield client

    # cleanup: 关闭当前测试的 engine
    await test_engine.dispose()
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
def test_user():
    """返回测试用户的基本信息"""
    return {
        "email": SHARED_EMAIL,
        "username": SHARED_USERNAME,
        "password": SHARED_PASSWORD,
    }
