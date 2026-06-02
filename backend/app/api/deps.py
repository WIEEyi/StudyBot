"""
FastAPI 依赖注入

提供认证相关的全局依赖，在路由中使用 Depends() 注入。

用法:
    @router.get("/me")
    async def get_me(current_user: User = Depends(get_current_user)):
        return current_user
"""

import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User

logger = logging.getLogger(__name__)

# HTTP Bearer 认证方案
# auto_error=True 会在请求没带 token 时自动返回 403
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """从 JWT token 解析当前用户

    处理流程:
    1. 从 Authorization header 提取 Bearer token
    2. 解码 JWT，获取 user_id
    3. 查数据库获取用户对象
    4. 如果 token 无效/用户不存在/账户被禁用，返回 401
    """
    token = credentials.credentials

    # 解码 JWT
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录已过期，请重新登录",
        )

    # 检查 token 类型（防止用 refresh token 当 access token）
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token 类型错误",
        )

    # 获取用户 ID
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token 无效",
        )

    # 查询用户
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="账户已被禁用",
        )

    return user
