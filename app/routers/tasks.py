"""任务路由：创建 / 列表 / 详情 / 澄清 / 取消 / 报告 / 历史事件。

所有接口都强制走 `AuthContext.tenant_id` 过滤，跨租户访问一律 404。
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.db import get_session
from app.deps import AuthContext, enforce_rate_limit
from app.observability import TASKS_CREATED
from app.schemas import (
    ClarifySubmit,
    ReportOut,
    TaskCreate,
    TaskDetail,
    TaskEventOut,
    TaskSummary,
)
from app.services import task_service

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _to_summary(task: models.Task) -> TaskSummary:
    return TaskSummary(
        id=task.id,
        goal=task.goal,
        status=task.status,
        created_at=task.created_at,
        started_at=task.started_at,
        finished_at=task.finished_at,
        stats=task.stats,
        error=task.error or "",
        has_report=bool(task.report_md),
    )


def _to_detail(task: models.Task) -> TaskDetail:
    return TaskDetail(
        **_to_summary(task).model_dump(),
        enriched_goal=task.enriched_goal or "",
        clarify_questions=task.clarify_questions,
        clarify_answers=task.clarify_answers,
        plan_json=task.plan_json,
    )


@router.post("", response_model=TaskDetail, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    ctx: AuthContext = Depends(enforce_rate_limit),
    session: AsyncSession = Depends(get_session),
) -> TaskDetail:
    """创建调研任务。

    信息不足时不会直接开跑，而是返回 `pending_clarify` 与澄清问题，
    前端回答后调 `/clarify` 继续。
    """
    task = await task_service.create_task(
        session,
        tenant_id=ctx.tenant_id,
        user_id=ctx.user_id,
        goal=payload.goal,
        skip_clarify=payload.skip_clarify,
    )
    TASKS_CREATED.labels(str(ctx.tenant_id)).inc()
    await session.refresh(task)
    return _to_detail(task)


@router.get("", response_model=list[TaskSummary])
async def list_tasks(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    ctx: AuthContext = Depends(enforce_rate_limit),
    session: AsyncSession = Depends(get_session),
) -> list[TaskSummary]:
    tasks = await task_service.list_tasks(
        session, ctx.tenant_id, status_filter=status_filter, limit=limit, offset=offset,
    )
    return [_to_summary(t) for t in tasks]


@router.get("/{task_id}", response_model=TaskDetail)
async def get_task(
    task_id: uuid.UUID,
    ctx: AuthContext = Depends(enforce_rate_limit),
    session: AsyncSession = Depends(get_session),
) -> TaskDetail:
    task = await task_service.get_task(session, ctx.tenant_id, task_id)
    return _to_detail(task)


@router.post("/{task_id}/clarify", response_model=TaskDetail)
async def submit_clarify(
    task_id: uuid.UUID,
    payload: ClarifySubmit,
    ctx: AuthContext = Depends(enforce_rate_limit),
    session: AsyncSession = Depends(get_session),
) -> TaskDetail:
    """提交澄清答案并开始运行。"""
    task = await task_service.get_task(session, ctx.tenant_id, task_id)
    task = await task_service.submit_clarify(
        session, task, [a.model_dump() for a in payload.answers],
    )
    await session.refresh(task)
    return _to_detail(task)


@router.post("/{task_id}/cancel", response_model=TaskDetail)
async def cancel_task(
    task_id: uuid.UUID,
    ctx: AuthContext = Depends(enforce_rate_limit),
    session: AsyncSession = Depends(get_session),
) -> TaskDetail:
    """取消任务（运行的由 worker 在下一个进度事件处中止）。"""
    task = await task_service.get_task(session, ctx.tenant_id, task_id)
    task = await task_service.cancel_task(session, task)
    await session.refresh(task)
    return _to_detail(task)


@router.get("/{task_id}/report", response_model=ReportOut)
async def get_report(
    task_id: uuid.UUID,
    ctx: AuthContext = Depends(enforce_rate_limit),
    session: AsyncSession = Depends(get_session),
) -> ReportOut:
    """取报告正文。任务未完成或没有报告时返回 409/404。"""
    task = await task_service.get_task(session, ctx.tenant_id, task_id)
    if not task.report_md:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"任务尚未产出报告（当前状态：{task.status}）",
        )
    return ReportOut(
        task_id=task.id,
        goal=task.goal,
        markdown=task.report_md,
        observations=task.observations_json,
    )


@router.get("/{task_id}/events", response_model=list[TaskEventOut])
async def list_events(
    task_id: uuid.UUID,
    after_seq: int = Query(default=0, ge=0),
    limit: int = Query(default=500, ge=1, le=2000),
    ctx: AuthContext = Depends(enforce_rate_limit),
    session: AsyncSession = Depends(get_session),
) -> list[TaskEventOut]:
    """历史进度事件（刷新页面 / 断线重连后回放）。"""
    await task_service.get_task(session, ctx.tenant_id, task_id)   # 越权检查
    stmt = (
        select(models.TaskEvent)
        .where(
            models.TaskEvent.task_id == task_id,
            models.TaskEvent.tenant_id == ctx.tenant_id,
            models.TaskEvent.seq > after_seq,
        )
        .order_by(models.TaskEvent.seq.asc())
        .limit(limit)
    )
    events = (await session.execute(stmt)).scalars().all()
    return [
        TaskEventOut(
            seq=e.seq, stage=e.stage, level=e.level,
            message=e.message, payload=e.payload, created_at=e.created_at,
        )
        for e in events
    ]
