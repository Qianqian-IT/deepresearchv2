"""服务层配置：全部来自环境变量（pydantic-settings），仓库内不保存任何密钥。

用法：
    from app.settings import get_settings
    settings = get_settings()

本地开发可放一份 `.env`（已在 .gitignore 中忽略）；生产用 K8s Secret / 环境变量注入。
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """企业多租户服务配置。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- 基础 ----
    app_name: str = "DeepResearch Enterprise"
    app_env: str = "local"                       # local / staging / prod
    debug: bool = False
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "*"                      # 逗号分隔；生产请收紧为前端域名

    # ---- 数据层 ----
    database_url: str = "postgresql+asyncpg://dr:dr@localhost:5432/deepresearch"
    db_echo: bool = False

    # ---- Redis（Celery broker / 配额计数 / 进度 pub-sub）----
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = ""                  # 留空则复用 redis_url
    celery_result_backend: str = ""              # 留空则复用 redis_url

    # ---- 认证与加密 ----
    jwt_secret_key: str = "CHANGE_ME_IN_PRODUCTION"   # 生产必须覆盖
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 12                 # 12 小时
    byok_encryption_key: str = ""                     # Fernet key；留空则用 jwt_secret_key 派生

    # ---- 配额与限流（多租户资源保护）----
    max_concurrent_tasks_per_tenant: int = 3          # 同一租户同时运行的任务数
    max_tasks_per_day_per_tenant: int = 200           # 每租户每日任务上限
    rate_limit_per_minute: int = 120                  # 单租户 API 每分钟请求上限

    # ---- 产物存储 ----
    storage_backend: str = "db"                       # db / s3
    s3_endpoint_url: str = ""                         # MinIO: http://minio:9000
    s3_bucket: str = "deepresearch"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_region: str = "us-east-1"

    # ---- 调研执行默认值（可被租户 BYOK 覆盖）----
    default_llm_provider: str = "deepseek"
    default_llm_model: str = ""                       # 留空用 deepresearchv2.config 默认
    default_llm_base_url: str = ""                    # 留空用 deepresearchv2.config 默认（可指内网网关）
    research_task_timeout_seconds: int = 1800         # 单任务硬超时（30 分钟）
    research_soft_timeout_seconds: int = 1500
    sse_heartbeat_seconds: int = 15                   # SSE 心跳，防网关断长连接

    @field_validator("byok_encryption_key", "jwt_secret_key")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        return (v or "").strip()

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def broker_url(self) -> str:
        return self.celery_broker_url or self.redis_url

    @property
    def result_backend(self) -> str:
        return self.celery_result_backend or self.redis_url


@lru_cache
def get_settings() -> Settings:
    """单例配置（lru_cache 保证同进程内只解析一次）。"""
    return Settings()
