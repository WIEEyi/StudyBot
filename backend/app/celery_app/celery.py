"""
Celery 应用实例

配置 Celery Worker 连接 RabbitMQ 作为 Broker，Redis 作为 Result Backend。

启动 Worker:
    celery -A app.celery_app.celery worker --loglevel=info
"""

from celery import Celery
from app.config import get_settings

settings = get_settings()

celery = Celery(
    "studybot",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Celery 配置
celery.conf.update(
    # 任务序列化
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # 时区
    timezone="UTC",
    enable_utc=True,
    # 任务发现
    include=["app.celery_app.tasks"],
    # Worker 配置
    worker_prefetch_multiplier=4,
    task_acks_late=True,
    # 结果过期（24 小时）
    result_expires=86400,
)
