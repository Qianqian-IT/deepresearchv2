"""SSE 进度推流。

跨副本原理：worker 把事件 publish 到 Redis channel，任意 API 副本订阅后转发给前端；
因此 API 无状态、可随便扩副本，SSE 照样能收到进度。

鉴权说明：浏览器原生 EventSource 不能自定义请求头，所以支持 `?token=<JWT>`；
同时兼容标准的 `Authorization: Bearer` 头（给 curl / 服务端调用用）。
"""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Query, Request
from sse_starlette.sse import EventSourceResponse

from app.db import async_session_scope
from app.deps import resolve_auth_context
from app.models import TERMINAL_STATUSES
from app.observability import SSE_CONNECTIONS
from app.redis_client import get_redis, task_channel
from app.services import task_service
from app.settings import get_settings
from sqlalchemy import select

from app import models

router = APIRouter(prefix="/api/tasks", tags=["stream"])

_END_STAGES = {"done", "error", "cancelled"}


def _extract_bearer(request: Request) -> str | None:
    raw = request.headers.get("authorization", "")
    if raw.lower().startswith("bearer "):
        return raw[7:].strip()
    return None


def _sse(payload: dict) -> dict:
    return {"event": "progress", "data": json.dumps(payload, ensure_ascii=False)}


@router.get("/{task_id}/stream")
async def stream_task(
    request: Request,
    task_id: uuid.UUID,
    token: str | None = Query(default=None, description="EventSource 无法带头，故支持 query 传令牌"),
    after_seq: int = Query(default=0, ge=0, description="断线重连：从该序号之后继续"),
):
    """订阅任务进度（SSE）。"""
    settings = get_settings()

    # --- 鉴权与越权检查用短 session，绝不能把连接开在整个推流期间 ---
    async with async_session_scope() as session:
        ctx = await resolve_auth_context(_extract_bearer(request) or token, request, session)
        await task_service.get_task(session, ctx.tenant_id, task_id)
        tenant_id = ctx.tenant_id

    async def event_generator():
        SSE_CONNECTIONS.inc()
        last_seq = after_seq
        client = get_redis()
        pubsub = client.pubsub()
        # 先订阅再回放：避免"回放结束 ~ 订阅开始"之间的事件丢失（重复由 last_seq 去重）
        await pubsub.subscribe(task_channel(task_id))
        try:
            async with async_session_scope() as session:
                rows = (await session.execute(
                    select(models.TaskEvent)
                    .where(
                        models.TaskEvent.task_id == task_id,
                        models.TaskEvent.tenant_id == tenant_id,
                        models.TaskEvent.seq > after_seq,
                    )
                    .order_by(models.TaskEvent.seq.asc())
                    .limit(2000)
                )).scalars().all()
                status_val = (await session.execute(
                    select(models.Task.status).where(models.Task.id == task_id)
                )).scalar_one_or_none()

            for row in rows:
                last_seq = row.seq
                yield _sse({
                    "seq": row.seq, "stage": row.stage, "level": row.level,
                    "message": row.message, "payload": row.payload,
                    "ts": row.created_at.isoformat() if row.created_at else None,
                })

            if status_val in TERMINAL_STATUSES:
                yield _sse({"seq": last_seq, "stage": "eof", "message": "任务已结束"})
                return

            # --- 实时转发 ---
            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=settings.sse_heartbeat_seconds,
                )
                if message is None:
                    # 心跳：防止反代/网关掐断长连接
                    yield {"event": "ping", "data": "{}"}
                    continue
                try:
                    event = json.loads(message["data"])
                except (TypeError, json.JSONDecodeError):
                    continue
                if int(event.get("seq", 0)) <= last_seq:
                    continue
                last_seq = int(event.get("seq", last_seq))
                yield _sse(event)
                if event.get("stage") in _END_STAGES:
                    break
        finally:
            try:
                await pubsub.unsubscribe(task_channel(task_id))
                await pubsub.aclose()
            except Exception:   # noqa: BLE001 - 客户端断开时忽略清理异常
                pass

    return EventSourceResponse(event_generator(), ping=settings.sse_heartbeat_seconds)
