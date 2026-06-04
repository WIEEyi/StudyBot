"""
WebSocket 端点

提供实时通信接口，当前支持:
- WS /api/v1/ws/plan — AI 学习计划生成（PlannerAgent 进度流）

认证: JWT access_token 通过 query param `token` 传入。
"""

import json
import logging
import asyncio
from fastapi import WebSocket, WebSocketDisconnect, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.security import decode_token
from app.models.user import User
from app.agents.planner_agent import run_planner

logger = logging.getLogger(__name__)


# ===================== 认证辅助 =====================

async def _authenticate_ws(websocket: WebSocket, token: str) -> User | None:
    """WebSocket 认证: 解析 JWT token 并返回 User 对象

    认证失败时自动关闭连接（code 4001），返回 None。
    """
    if not token:
        await websocket.close(code=4001, reason="认证失败：请提供 access token")
        return None

    # 解码 JWT
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        await websocket.close(code=4001, reason="认证失败：token 无效或已过期")
        return None

    user_id = payload.get("sub")
    if user_id is None:
        await websocket.close(code=4001, reason="认证失败：token 格式错误")
        return None

    # 查询用户
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()

        if user is None:
            await websocket.close(code=4001, reason="认证失败：用户不存在")
            return None

        if not user.is_active:
            await websocket.close(code=4001, reason="认证失败：账户已被禁用")
            return None

    logger.info("WebSocket 认证成功: user_id=%s", user.id)
    return user


# ===================== WebSocket 端点 =====================

async def websocket_plan(websocket: WebSocket):
    """学习计划生成 WebSocket 端点

    客户端连接: ws://localhost:8000/api/v1/ws/plan?token=<access_token>

    消息协议:
    - 客户端发送: {"action": "generate_plan", "goal_id": 1}
    - 服务端推送: {"event": "thinking"|"milestone"|"task"|"complete"|"error", ...}

    超时: 30 秒无消息自动关闭连接
    """
    # 获取 token 并认证
    token = websocket.query_params.get("token")
    user = await _authenticate_ws(websocket, token)
    if user is None:
        return  # 认证失败，连接已关闭

    # 接受连接（必须在认证之后，否则 FastAPI 不会发送实际握手的响应）
    await websocket.accept()
    logger.info("WebSocket 连接建立: user_id=%s", user.id)

    async def stream_callback(event_name: str, data: dict):
        """PlannerAgent 的 stream_callback，向客户端推送事件"""
        try:
            # 如果 data 已经包含 event 字段，直接发送
            # 否则使用 event_name 构造
            if "event" not in data:
                data = {"event": event_name, **data}
            await websocket.send_json(data)
        except Exception as e:
            logger.warning("WebSocket 推送失败: %s", e)

    try:
        while True:
            # 接收客户端消息，30 秒超时
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                logger.info("WebSocket 超时: user_id=%s", user.id)
                await websocket.close(code=4000, reason="连接超时（30 秒无消息）")
                return

            # 解析 JSON
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await stream_callback("error", {
                    "event": "error",
                    "message": "无效的 JSON 格式",
                })
                continue

            action = msg.get("action")

            # --- 处理 generate_plan ---
            if action == "generate_plan":
                goal_id = msg.get("goal_id")
                if not isinstance(goal_id, int) or goal_id < 1:
                    await stream_callback("error", {
                        "event": "error",
                        "message": "无效的 goal_id，需要正整数",
                    })
                    continue

                logger.info("开始生成学习计划: user_id=%s, goal_id=%s", user.id, goal_id)

                # 在独立的 DB session 中运行 PlannerAgent
                async with AsyncSessionLocal() as db:
                    try:
                        await run_planner(
                            goal_id=goal_id,
                            user_id=user.id,
                            db_session=db,
                            stream_callback=stream_callback,
                        )
                    except Exception as e:
                        logger.error("PlannerAgent 运行异常: %s", e, exc_info=True)
                        await db.rollback()
                        await stream_callback("error", {
                            "event": "error",
                            "message": f"服务器内部错误: {str(e)}",
                        })

            elif action is None:
                await stream_callback("error", {
                    "event": "error",
                    "message": "缺少 action 字段",
                })
            else:
                await stream_callback("error", {
                    "event": "error",
                    "message": f"无效的操作: {action}",
                })

    except WebSocketDisconnect:
        logger.info("WebSocket 客户端断开: user_id=%s", user.id)
    except Exception as e:
        logger.error("WebSocket 异常: %s", e, exc_info=True)
        try:
            await websocket.close(code=4000, reason="服务器内部错误")
        except Exception:
            pass
