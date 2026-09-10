"""FastAPI 入口：路由装配、中间件、健康检查、指标、前端静态托管。

启动：
    uvicorn app.main:app --host 0.0.0.0 --port 8000
API 无状态：不保存任何任务状态在进程内，可任意多副本部署（配 Nginx/Ingress 负载均衡）。
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.db import async_engine
from app.observability import get_logger, metrics_middleware, metrics_response, setup_logging
from app.redis_client import get_redis
from app.routers import auth, stream, tasks, tenants
from app.settings import get_settings

settings = get_settings()
log = get_logger("app.main")

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动/关闭钩子。"""
    setup_logging(settings.log_level)
    log.info(
        "service_starting",
        app_env=settings.app_env,
        storage_backend=settings.storage_backend,
    )
    yield
    await async_engine.dispose()
    log.info("service_stopped")


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="多租户深度调研服务（BYOK，企业自带模型与搜索密钥）",
    lifespan=lifespan,
    docs_url="/docs" if settings.app_env != "prod" else None,
    redoc_url=None,
)

# ---- 中间件 ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(metrics_middleware)

# ---- 路由 ----
app.include_router(auth.router)
app.include_router(tenants.router)
app.include_router(tasks.router)
app.include_router(stream.router)


@app.get("/health", tags=["ops"])
async def health() -> dict:
    """健康检查：DB 与 Redis 连通性（K8s liveness/readiness 用）。"""
    checks = {"db": "ok", "redis": "ok"}
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:   # noqa: BLE001
        checks["db"] = f"error: {type(e).__name__}"

    try:
        await get_redis().ping()
    except Exception as e:   # noqa: BLE001
        checks["redis"] = f"error: {type(e).__name__}"

    healthy = all(v == "ok" for v in checks.values())
    return {"status": "ok" if healthy else "degraded", "checks": checks}


@app.get("/metrics", tags=["ops"], response_class=PlainTextResponse)
async def metrics():
    """Prometheus 指标端点。"""
    body, _content_type = metrics_response()
    return PlainTextResponse(body, media_type="text/plain; version=0.0.4; charset=utf-8")


# ---- 前端静态托管（必须放在所有 API 路由之后）----
if WEB_DIR.is_dir() and os.environ.get("SERVE_WEB", "1") == "1":
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
