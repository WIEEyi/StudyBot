"""
WebSocket 端点 — AI 学习计划生成

客户端连接: ws://localhost:8000/api/v1/ws/plan?token=<access_token>
消息协议:
- 客户端发送: {"action": "generate_plan", "goal_id": 1}
- 服务端推送: {"event": "thinking"|"milestone"|"task"|"complete"|"error", ...}
"""

import json
import logging
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.security import decode_token
from app.models.user import User
from app.agents.planner_agent import run_planner

logger = logging.getLogger(__name__)


async def _authenticate_ws(websocket: WebSocket, token: str) -> User | None:
    """WebSocket 认证"""
    if not token:
        await websocket.close(code=4001, reason="认证失败：请提供 access token")
        return None

    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        await websocket.close(code=4001, reason="认证失败：token 无效或已过期")
        return None

    user_id = payload.get("sub")
    if user_id is None:
        await websocket.close(code=4001, reason="认证失败：token 格式错误")
        return None

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


async def websocket_plan(websocket: WebSocket):
    """学习计划生成 WebSocket 端点"""
    token = websocket.query_params.get("token")
    user = await _authenticate_ws(websocket, token)
    if user is None:
        return

    await websocket.accept()
    logger.info("WebSocket 连接建立: user_id=%s", user.id)

    async def stream_callback(event_name: str, data: dict):
        try:
            if "event" not in data:
                data = {"event": event_name, **data}
            await websocket.send_json(data)
        except Exception as e:
            logger.warning("WebSocket 推送失败: %s", e)

    try:
        while True:
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                logger.info("WebSocket 超时: user_id=%s", user.id)
                await websocket.close(code=4000, reason="连接超时（30 秒无消息）")
                return

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await stream_callback("error", {
                    "event": "error", "message": "无效的 JSON 格式",
                })
                continue

            action = msg.get("action")

            if action == "generate_plan":
                goal_id = msg.get("goal_id")
                if not isinstance(goal_id, int) or goal_id < 1:
                    await stream_callback("error", {
                        "event": "error", "message": "无效的 goal_id",
                    })
                    continue

                logger.info("开始生成学习计划: user_id=%s, goal_id=%s", user.id, goal_id)

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
                            "event": "error", "message": f"服务器内部错误: {str(e)}",
                        })

            elif action is None:
                await stream_callback("error", {"event": "error", "message": "缺少 action 字段"})
            else:
                await stream_callback("error", {"event": "error", "message": f"无效的操作: {action}"})

    except WebSocketDisconnect:
        logger.info("WebSocket 客户端断开: user_id=%s", user.id)
    except Exception as e:
        logger.error("WebSocket 异常: %s", e, exc_info=True)
        try:
            await websocket.close(code=4000, reason="服务器内部错误")
        except Exception:
            pass
