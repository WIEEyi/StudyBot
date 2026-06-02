"""
SQLAlchemy 声明式基类

所有 ORM 模型继承此 Base，统一管理表结构。
提供了公共列 Mixin: id、创建时间、更新时间。
"""

from datetime import datetime
from sqlalchemy import Integer, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """所有模型的声明式基类"""
    pass


class TimestampMixin:
    """公共时间戳 Mixin

    提供:
    - id: 自增主键
    - created_at: 创建时间（数据库自动填充）
    - updated_at: 更新时间（数据库自动更新）
    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),  # 让数据库填充默认值
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),  # 每次更新自动刷新
    )
