"""
日志系统配置

提供统一的应用日志配置，支持:
1. 控制台输出（stdout，Docker logs 可见）
2. 文件输出（/app/logs/ 目录）
3. 日志级别由 APP_DEBUG 配置控制

使用方式:
    在 main.py 中调用 setup_logging() 即可初始化
    其他模块: import logging; logger = logging.getLogger(__name__)
"""

import logging
import sys
from pathlib import Path
from app.config import get_settings

# 日志格式：时间 | 级别 | 模块 | 消息
# 例如: 2026-06-01 17:30:00 | INFO     | app.main | 数据库连接成功
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 需要清理 handler 的 logger 名称列表（这些 logger 被 uvicorn / SQLAlchemy 预设了 handler）
LOGGERS_TO_CLEAR = ("uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy.engine")


def _clear_logger_handlers(logger_name: str) -> None:
    """递归清除指定 logger 及其所有子 logger 的 handler"""
    logger = logging.getLogger(logger_name)
    logger.handlers.clear()
    logger.propagate = True
    # 遍历 logging 管理器，找到所有以 logger_name 开头的子 logger
    manager = logger.manager
    for name, child_logger in manager.loggerDict.items():
        if name.startswith(logger_name + "."):
            if isinstance(child_logger, logging.Logger):
                child_logger.handlers.clear()
                child_logger.propagate = True


def setup_logging() -> None:
    """初始化应用日志系统

    在 FastAPI lifespan 启动阶段调用一次即可。
    - 开发环境 (APP_DEBUG=true): 全局设为 DEBUG
    - 生产环境 (APP_DEBUG=false): 全局设为 INFO
    """
    settings = get_settings()

    # 确定日志级别
    level = logging.DEBUG if settings.APP_DEBUG else logging.INFO

    # 获取根 logger，清空所有已有 handler
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    # 清除 uvicorn / SQLAlchemy 等库预设的 logger handler，统一走 root logger
    # 否则日志会输出两份（各自的格式 + 我们的格式）
    for name in LOGGERS_TO_CLEAR:
        _clear_logger_handlers(name)

    # --- 控制台 handler ---
    # 输出到 stdout，Docker 用 `docker compose logs` 可见
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    root_logger.addHandler(console_handler)

    # --- 文件 handler ---
    # 持久化到磁盘，容器重启不丢失（日志目录在 bind mount 的 /app 下）
    log_dir = Path("/app/logs")
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(
        log_dir / "app.log",
        encoding="utf-8",
        mode="a",  # 追加模式，不覆盖历史日志
    )
    file_handler.setLevel(logging.DEBUG)  # 文件始终记录 DEBUG 级别
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    root_logger.addHandler(file_handler)

    # 降低第三方库的日志级别（避免噪音）
    # sqlalchemy.engine: echo=True 时由 SQLAlchemy 决策输出级别，不在此强制 WARNING
    logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO if settings.APP_DEBUG else logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
