"""
认证相关的 Pydantic 请求/响应模型

FastAPI 用 Pydantic 做自动校验:
- 前端发来的 JSON → Pydantic 自动转为 Python 对象并校验类型
- 返回给前端的 Python 对象 → Pydantic 自动转为 JSON
"""

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


# ===================== 请求模型 =====================

class UserRegisterRequest(BaseModel):
    """用户注册请求

    EmailStr 自动校验邮箱格式，密码最少 6 位
    """
    email: EmailStr
    username: str = Field(min_length=2, max_length=50, description="用户名，2-50 个字符")
    password: str = Field(min_length=6, max_length=128, description="密码，最少 6 位")


class UserLoginRequest(BaseModel):
    """用户登录请求"""
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    """刷新 token 请求"""
    refresh_token: str


# ===================== 响应模型 =====================

class TokenResponse(BaseModel):
    """认证成功返回的 token 信息

    token_type 固定为 "bearer"，符合 RFC 6750 标准
    """
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """用户信息响应（不含密码）

    用于 /users/me 等接口返回用户数据
    """
    id: int
    email: str
    username: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    # 允许从 ORM 对象自动转换
    model_config = {"from_attributes": True}
