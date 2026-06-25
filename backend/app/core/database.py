"""
数据库连接管理

使用 SQLAlchemy 2.0 异步引擎连接到 PostgreSQL。
核心概念:
- Engine: 数据库连接池，创建成本高，全局只用一个
- async_sessionmaker: 会话工厂，每次请求调用它生成新的数据库会话
- 会话生命周期: async with 块内有效，退出自动关闭

数据流向:
    FastAPI 请求 → get_db() 生成会话 → Service 层用会话操作 DB → 请求结束会话关闭
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.config import get_settings

settings = get_settings()

# --- 创建异步数据库引擎 ---
# echo=False: 不打印 SQL 日志（开发时改为 True 可以看实际执行的 SQL）
# pool_size=10: 连接池大小，同时最多 10 个数据库连接
# 连接池的作用: 避免每次请求都新建连接（TCP 握手昂贵），复用已有连接
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_DEBUG,   # 调试模式下打印 SQL
    pool_size=10,              # 连接池大小
    max_overflow=20,           # 超出 pool_size 时最多额外创建的连接数
)

# --- 创建会话工厂 ---
# expire_on_commit=False: 提交后不回滚对象状态，方便在 commit 后继续访问对象属性
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> "AsyncSession":
    """获取数据库会话的依赖注入函数

    用法: 在 FastAPI 路由中用 Depends(get_db) 注入

    异常安全:
    - 发生异常时自动回滚，确保 session 不留脏数据
    - async with 确保连接始终被归还到连接池
    - 路由函数应显式调用 db.commit() 提交变更

    Example:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
