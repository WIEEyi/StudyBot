"""
Redis 客户端管理

提供异步 Redis 连接池，供缓存、限流、JWT 黑名单等功能使用。
使用 redis.asyncio 实现非阻塞的 Redis 操作。

核心概念:
- 连接池 (ConnectionPool): 预创建一组 TCP 连接，用的时候借一个，用完还回去
- Redis 逻辑数据库: 默认 0 号库，可通过 URL 中的 /0, /1 等切换
"""

import redis.asyncio as aioredis
from app.config import get_settings

settings = get_settings()

# --- 创建 Redis 连接池 ---
# max_connections=10: 同时最多 10 个连接
# decode_responses=True: 自动将 bytes 解码为 str，不用手动 decode('utf-8')
# 连接池是线程/协程安全的，可以在多处同时使用
redis_pool = aioredis.ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=10,
    decode_responses=True,
)


async def get_redis() -> aioredis.Redis:
    """获取 Redis 客户端

    从连接池获取一个连接，返回 Redis 实例。
    使用完毕后连接会自动归还给连接池（无需手动释放）。

    用法:
        redis = await get_redis()
        await redis.setex("key", 3600, "value")  # 设置带过期时间的键
        value = await redis.get("key")            # 获取值

    注意: 这个函数每次调用会从连接池取一个新连接，
    但如果频繁操作，应该复用同一个 Redis 实例。
    """
    return aioredis.Redis(connection_pool=redis_pool)
