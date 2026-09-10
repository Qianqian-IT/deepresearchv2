"""可观测：结构化日志（structlog）+ Prometheus 指标。

密钥脱敏是硬要求：这里注册一个 processor，把形如 sk-xxx / tvly-xxx 的串统一打码，
防止密钥通过异常栈或调试日志泄漏。
"""

from __future__ import annotations

import logging
import re
import uuid

import structlog
from fastapi import Request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

# ============================================================
# 脱敏
# ============================================================

_SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"tvly-[A-Za-z0-9_\-]{8,}"),
]


def _mask_text(text: str) -> str:
    for pat in _SECRET_PATTERNS:
        text = pat.sub("****REDACTED****", text)
    return text


def redact_processor(logger, method_name, event_dict):  # noqa: ANN001
    """structlog processor：对消息与常见字段做密钥打码。"""
    if "event" in event_dict and isinstance(event_dict["event"], str):
        event_dict["event"] = _mask_text(event_dict["event"])
    for key in ("error", "detail", "message", "exc_info"):
        val = event_dict.get(key)
        if isinstance(val, str):
            event_dict[key] = _mask_text(val)
    return event_dict


# ============================================================
# 日志
# ============================================================

def setup_logging(level: str = "INFO") -> None:
    """初始化 structlog（JSON 输出，便于日志平台采集）。"""
    logging.basicConfig(format="%(message)s", level=getattr(logging, level.upper(), logging.INFO))
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            redact_processor,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "app"):
    return structlog.get_logger(name)


def bind_request_context(tenant_id: str | None = None, user_id: str | None = None,
                         task_id: str | None = None) -> None:
    """把租户/用户/任务绑定到当前上下文，后续日志自动带上。"""
    ctx = {}
    if tenant_id:
        ctx["tenant_id"] = tenant_id
    if user_id:
        ctx["user_id"] = user_id
    if task_id:
        ctx["task_id"] = task_id
    if ctx:
        structlog.contextvars.bind_contextvars(**ctx)


def new_trace_id() -> str:
    return uuid.uuid4().hex[:16]


# ============================================================
# Prometheus 指标
# ============================================================

TASKS_CREATED = Counter(
    "dr_tasks_created_total", "创建的任务数", ["tenant_id"],
)
TASKS_FINISHED = Counter(
    "dr_tasks_finished_total", "结束的任务数", ["status"],
)
TASK_DURATION = Histogram(
    "dr_task_duration_seconds", "任务执行耗时（秒）",
    buckets=(5, 15, 30, 60, 120, 300, 600, 1200, 1800),
)
LLM_TOKENS = Counter(
    "dr_llm_tokens_total", "LLM token 消耗", ["direction"],
)
HTTP_REQUESTS = Counter(
    "dr_http_requests_total", "HTTP 请求数", ["method", "path", "status"],
)
HTTP_LATENCY = Histogram(
    "dr_http_request_duration_seconds", "HTTP 请求耗时（秒）",
    ["method", "path"],
    buckets=(0.01, 0.05, 0.1, 0.3, 0.8, 2, 5, 15),
)

# 供 worker 进程导入使用（Celery 与 API 在不同进程，各自暴露/汇总）
SSE_CONNECTIONS = Counter("dr_sse_connections_total", "SSE 连接数")


def metrics_response():
    """返回 Prometheus 文本格式响应。"""
    return generate_latest(), CONTENT_TYPE_LATEST


async def metrics_middleware(request: Request, call_next):
    """HTTP 指标采集中间件。"""
    import time

    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    path = request.url.path
    # 避免把任务 ID 打进标签导致基数爆炸
    if path.startswith("/api/tasks/") and len(path.split("/")) > 4:
        path = "/api/tasks/{id}"
    HTTP_REQUESTS.labels(request.method, path, str(response.status_code)).inc()
    HTTP_LATENCY.labels(request.method, path).observe(elapsed)
    return response
