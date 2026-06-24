"""
应用配置管理

使用 pydantic-settings 从 .env 文件和系统环境变量加载配置。
所有配置项都有类型校验，缺失必填项启动时报错。

数据类型流向:
    .env 文件 → Config 类 (自动加载) → app/config.py → 其他模块导入
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置类

    pydantic-settings 会自动按以下优先级查找配置:
    1. 系统环境变量 (最高优先级)
    2. .env 文件
    3. 代码中的默认值 (最低优先级)
    """

    # --- 应用 ---
    APP_NAME: str = "StudyBot"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True

    # --- 数据库 ---
    # asyncpg 是 PostgreSQL 的异步驱动，SQLAlchemy 通过它执行异步 SQL
    DATABASE_URL: str = "postgresql+asyncpg://studybot:studybot123@postgres:5432/studybot"

    # --- Redis ---
    # 格式: redis://主机:端口/数据库编号 (Redis 有 0-15 共 16 个逻辑数据库)
    REDIS_URL: str = "redis://redis:6379/0"

    # --- RabbitMQ ---
    # pyamqp 是 AMQP 协议的 Python 库，Celery 通过它连接 RabbitMQ
    RABBITMQ_URL: str = "pyamqp://guest:guest@rabbitmq:5672//"

    # --- JWT 认证 ---
    JWT_SECRET_KEY: str = "dev-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"  # HMAC-SHA256 对称加密算法
    # access_token 有效期 30 分钟，短时效 → 即使泄露影响也有限
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    # refresh_token 有效期 7 天，用于免登录刷新 access_token
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- LLM (OpenAI 兼容接口) ---
    OPENAI_API_KEY: str = "sk-your-api-key-here"
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o-mini"           # 轻量模型，用于意图路由
    LLM_MODEL_PREMIUM: str = "gpt-4o"        # 强模型，用于 Agent 推理
    EMBEDDING_MODEL: str = "text-embedding-3-small"  # 文本嵌入模型

    # --- Celery ---
    CELERY_BROKER_URL: str = "pyamqp://guest:guest@rabbitmq:5672//"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/1"

    # --- 文件上传 ---
    UPLOAD_DIR: str = "/app/uploads"  # Docker 容器内的上传目录
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 最大上传 50MB

    # --- CORS ---
    # 允许跨域的前端地址（开发时为 Next.js 默认端口 3000）
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    class Config:
        # 指定 .env 文件路径（相对于项目根目录）
        env_file = ".env"
        # 即使 .env 文件不存在也不报错（允许全部用环境变量）
        env_file_encoding = "utf-8"
        # 允许读取额外字段（向后兼容）
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例

    使用 lru_cache 装饰器确保整个应用生命周期内只创建一次 Settings 实例。
    这是一种简单有效的单例模式。
    """
    return Settings()
