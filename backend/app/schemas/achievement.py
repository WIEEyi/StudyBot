"""
Achievement 成就相关的 Pydantic 模型

与前端 types.ts 中的成就类型对齐。
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class AchievementResponse(BaseModel):
    """单个成就信息"""
    id: int
    code: str
    name: str
    description: str
    icon: str
    category: str
    rarity: str
    threshold: int

    model_config = {"from_attributes": True}


class UserAchievementResponse(BaseModel):
    """用户已获得的成就"""
    id: int
    achievement: AchievementResponse
    progress_value: int
    earned_at: datetime  # created_at 映射为 earned_at

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_model(cls, ua) -> "UserAchievementResponse":
        """从 ORM 对象构建，将 created_at 映射为 earned_at"""
        return cls(
            id=ua.id,
            achievement=AchievementResponse.model_validate(ua.achievement),
            progress_value=ua.progress_value,
            earned_at=ua.created_at,
        )


class AchievementListResponse(BaseModel):
    """成就列表（包含已获得和未获得）"""
    items: list[AchievementResponse]
    earned_codes: list[str]
    total: int
    earned_count: int


class AchievementProgressResponse(BaseModel):
    """成就进度（距离获得的进度）"""
    achievement: AchievementResponse
    current_progress: int
    threshold: int
    percent: float  # 0-100
    is_earned: bool
