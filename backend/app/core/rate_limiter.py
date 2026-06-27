"""
API 限流器

全局 SlowAPI 实例，供 main.py 和各路由模块共享。
测试模式下 (APP_ENV=test) 自动禁用限流。
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from app.config import get_settings

settings = get_settings()

# 测试模式下使用固定 key（不限制），生产模式按 IP 限流
_key_func = (lambda _: "test") if settings.APP_ENV == "test" else get_remote_address

limiter = Limiter(
    key_func=_key_func,
    enabled=settings.APP_ENV != "test",
)
