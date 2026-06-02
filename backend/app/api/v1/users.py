"""
用户接口

- GET /users/me: 获取当前登录用户信息
"""

import logging
from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.auth import UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["用户"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """获取当前用户信息

    从 JWT token 中解析用户 ID，查询数据库返回用户信息。
    密码字段不会出现在响应中（由 UserResponse schema 控制）。
    """
    return current_user
