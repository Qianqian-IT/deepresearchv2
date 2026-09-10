"""Celery 实例：Redis 作 broker 与结果后端。

可靠性配置说明：
- task_acks_late=True：worker 崩溃时任务会被重新投递（配合 worker_prefetch_multiplier=1）
- worker_prefetch_multiplier=1：一次只领一个任务，长任务场景避免"饿死"其它租户
- task_time_limit / soft_time_limit：调研单任务以分钟计，必须有硬上限兜底
启动：
    celery -A app.workers.celery_app:celery_app worker -Q research -c 4 --loglevel=INFO
"""

from __future__ import annotations

from celery import Celery

from app.settings import get_settings

settings = get_settings()

celery_app = Celery(
    "deepresearch",
    broker=settings.broker_url,
    backend=settings.result_backend,
    include=["app.workers.research_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    task_time_limit=settings.research_task_timeout_seconds,
    task_soft_time_limit=settings.research_soft_timeout_seconds,
    broker_connection_retry_on_startup=True,
    result_expires=7 * 24 * 3600,
    task_default_queue="research",
    task_routes={"research.run": {"queue": "research"}},
)
