"""Redis 封装：连接、任务进度 pub/sub、多租户配额计数。

为什么用 Redis：
- pub/sub 让 SSE 进度跨 API 副本可见（连到任意副本都能收到同一任务的进度）
- 原子计数做配额/限流，多副本下不会各算各的
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncIterator

import redis
from redis.asyncio import Redis

from app.settings import get_settings

_settings = get_settings()

# --- 连接（进程内单例）---
_async_client: Redis | None = None
_sync_client: redis.Redis | None = None


def get_redis() -> Redis:
    """异步客户端（FastAPI 侧）。"""
    global _async_client
    if _async_client is None:
        _async_client = Redis.from_url(_settings.redis_url, decode_responses=True)
    return _async_client


def get_sync_redis() -> redis.Redis:
    """同步客户端（Celery worker 侧）。"""
    global _sync_client
    if _sync_client is None:
        _sync_client = redis.Redis.from_url(_settings.redis_url, decode_responses=True)
    return _sync_client


# ============================================================
# 任务进度 pub/sub
# ============================================================

def task_channel(task_id: uuid.UUID | str) -> str:
    return f"dr:task:{task_id}"


def publish_event(task_id: uuid.UUID | str, event: dict[str, Any]) -> None:
    """worker 侧：发布一条进度事件（同步）。"""
    event.setdefault("ts", datetime.now(timezone.utc).isoformat())
    get_sync_redis().publish(task_channel(task_id), json.dumps(event, ensure_ascii=False))


async def subscribe_task(task_id: uuid.UUID | str) -> AsyncIterator[dict[str, Any]]:
    """API 侧：订阅某任务的进度事件流（供 SSE 转发）。"""
    client = get_redis()
    pubsub = client.pubsub()
    await pubsub.subscribe(task_channel(task_id))
    try:
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            try:
                yield json.loads(message["data"])
            except (TypeError, json.JSONDecodeError):
                continue
    finally:
        await pubsub.unsubscribe(task_channel(task_id))
        await pubsub.aclose()


# ============================================================
# 配额与限流（多租户资源保护）
# ============================================================

def _conc_key(tenant_id: uuid.UUID | str) -> str:
    return f"dr:quota:conc:{tenant_id}"


def _daily_key(tenant_id: uuid.UUID | str) -> str:
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"dr:quota:daily:{tenant_id}:{day}"


def _rl_key(tenant_id: uuid.UUID | str) -> str:
    minute = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    return f"dr:quota:rl:{tenant_id}:{minute}"


async def acq_concurrency(tenant_id: uuid.UUID | str, limit: int) -> bool:
    """占用一个并发槽；超过 limit 返回 False。

    用 INCR 保证原子性（多副本同时抢占也不会超发）。
    """
    client = get_redis()
    key = _conc_key(tenant_id)
    current = await client.incr(key)
    await client.expire(key, 24 * 3600)   # 兜底过期，防止异常退出导致槽位泄漏
    if current > limit:
        # 抢失败要还回去
        await client.decr(key)
        return False
    return True


async def release_concurrency(tenant_id: uuid.UUID | str) -> None:
    """释放并发槽（API 侧：拒绝任务时回滚 / 取消未运行的任务）。"""
    client = get_redis()
    key = _conc_key(tenant_id)
    remaining = await client.decr(key)
    if remaining < 0:
        await client.set(key, 0)


def release_concurrency_sync(tenant_id: uuid.UUID | str) -> None:
    """释放并发槽（worker 侧：任务结束时调用）。"""
    client = get_sync_redis()
    key = _conc_key(tenant_id)
    remaining = client.decr(key)
    if remaining < 0:
        client.set(key, 0)


async def acq_daily(tenant_id: uuid.UUID | str, limit: int) -> bool:
    """占用一次当日任务额度。"""
    client = get_redis()
    key = _daily_key(tenant_id)
    current = await client.incr(key)
    await client.expire(key, 2 * 24 * 3600)
    if current > limit:
        await client.decr(key)
        return False
    return True


async def hit_rate_limit(tenant_id: uuid.UUID | str, limit_per_minute: int) -> bool:
    """是否触顶每分钟请求限制。返回 True 表示应拒绝（429）。"""
    client = get_redis()
    key = _rl_key(tenant_id)
    current = await client.incr(key)
    if current == 1:
        await client.expire(key, 120)
    return current > limit_per_minute


async def quota_snapshot(tenant_id: uuid.UUID | str, conc_limit: int, daily_limit: int) -> dict:
    """当前配额使用快照（给前端概览卡用）。"""
    client = get_redis()
    conc = int(await client.get(_conc_key(tenant_id)) or 0)
    daily = int(await client.get(_daily_key(tenant_id)) or 0)
    return {
        "concurrent_running": max(conc, 0),
        "concurrent_limit": conc_limit,
        "tasks_today": daily,
        "daily_limit": daily_limit,
    }
