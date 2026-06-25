"""
FastAPI 应用入口

这是整个后端的启动文件。定义了:
1. FastAPI 应用实例
2. 生命周期事件 (启动/关闭时执行的逻辑)
3. CORS 中间件
4. 路由注册
5. 健康检查接口

启动命令:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.rate_limiter import limiter
from app.config import get_settings
from app.core.database import engine
from app.core.logging_config import setup_logging
from app.models import Base  # noqa: F401 — 导入所有 ORM 模型，注册到 Base.metadata

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理

    启动时 (yield 之前): 初始化数据库连接池等资源
    关闭时 (yield 之后): 释放连接池等资源

    @asynccontextmanager 将函数分成两部分:
    - yield 之前 = 启动逻辑
    - yield 之后 = 关闭逻辑
    """
    # ===== 启动时 =====
    # 初始化日志系统（必须在最开始调用）
    setup_logging()

    logger.info("[启动] %s 启动中...", settings.APP_NAME)
    logger.info("   环境: %s", settings.APP_ENV)
    logger.info("   数据库: %s", settings.DATABASE_URL.split('@')[1])  # 隐藏用户名密码
    logger.info("   Redis: %s", settings.REDIS_URL)

    # 测试数据库连接 + 自动建表
    try:
        async with engine.begin() as conn:
            # 执行一个简单查询验证连接
            # text() 是 SQLAlchemy 的原始 SQL 文本构造器
            # engine.begin() 自动开启事务，退出时 commit 或 rollback
            await conn.execute(text("SELECT 1"))
            logger.info("[OK] 数据库连接成功")

            # 数据库迁移由 Alembic 管理（不再用 create_all）
            # 首次部署或结构变更时执行: docker compose exec backend alembic upgrade head
    except Exception as e:
        logger.error("[ERROR] 数据库连接失败: %s", e)
        raise

    yield  # ← 应用运行期间的逻辑在这里执行

    # ===== 关闭时 =====
    logger.info("[关闭] 正在关闭...")
    # 关闭数据库引擎，释放连接池中的所有连接
    await engine.dispose()
    logger.info("[OK] 数据库连接已关闭")


# --- 创建 FastAPI 应用 ---
app = FastAPI(
    title=settings.APP_NAME,
    description="个人学习与任务调度 AI Agent",
    version="0.1.0",
    lifespan=lifespan,   # 注册生命周期管理
)

# --- CORS 中间件 ---
# 允许前端 (Next.js 运行在 localhost:3000) 跨域请求后端 API
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # 允许的前端地址列表
    allow_credentials=True,              # 允许携带 Cookie/Authorization 头
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin"],
)


# --- 限流器注册 ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# --- 全局异常处理器 ---
# 捕获未处理的异常，防止泄露敏感信息（堆栈、DB URL 等）

@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """数据库异常 — 返回通用错误信息，不暴露 SQL 细节"""
    logger.error("数据库异常 [%s %s]: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "数据库操作失败，请稍后重试"},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """兜底异常 — 捕获所有未处理的异常，防止信息泄露"""
    logger.error("未处理异常 [%s %s]: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误，请稍后重试"},
    )


# --- 注册路由 ---
from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.goals import router as goals_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.quizzes import router as quizzes_router
from app.api.v1.concepts import router as concepts_router
from app.api.v1.documents import router as documents_router
from app.api.v1.review_cards import router as review_cards_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.qa import router as qa_router
from app.api.v1.ws import websocket_plan
from app.api.v1.scheduler import router as scheduler_router
from app.api.v1.achievements import router as achievements_router
from app.api.v1.learning_path import router as learning_path_router

app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(goals_router, prefix="/api/v1")
app.include_router(tasks_router, prefix="/api/v1")
app.include_router(quizzes_router, prefix="/api/v1")
app.include_router(concepts_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(review_cards_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(qa_router, prefix="/api/v1")
app.include_router(scheduler_router, prefix="/api/v1")
app.include_router(achievements_router, prefix="/api/v1")
app.include_router(learning_path_router, prefix="/api/v1")

# WebSocket 路由
app.websocket("/api/v1/ws/plan")(websocket_plan)

# --- 健康检查接口 ---
# 最简单的接口: 返回应用是否在运行
# Docker / K8s 可以用这个接口做存活探针
@app.get("/health")
async def health_check():
    """健康检查 - 返回应用运行状态"""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
    }


# --- 根路径 ---
@app.get("/")
async def root():
    """根路径 - 返回 API 欢迎信息"""
    return {
        "message": f"欢迎使用 {settings.APP_NAME} API",
        "docs": "/docs",           # FastAPI 自动生成的 Swagger 文档
        "health": "/health",
    }
