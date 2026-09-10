"""数据层：async engine、session 工厂、声明式 Base。

- 应用（FastAPI）用 `get_session()` 依赖注入拿 session
- worker（Celery，同步上下文）用 `session_scope()` 同步上下文管理器
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.settings import get_settings


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""


_settings = get_settings()

# --- 异步（API 侧）---
async_engine = create_async_engine(
    _settings.database_url,
    echo=_settings.db_echo,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)
AsyncSessionLocal = async_sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False,
)

# --- 同步（Celery worker 侧）---
# 把 asyncpg 驱动换成 psycopg，复用同一个 DATABASE_URL
_sync_url = _settings.database_url.replace("+asyncpg", "+psycopg")
sync_engine = create_engine(_sync_url, echo=_settings.db_echo, pool_pre_ping=True)
SyncSessionLocal = sessionmaker(sync_engine, class_=Session, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI 依赖：每个请求一个 session。"""
    async with AsyncSessionLocal() as session:
        yield session


@contextmanager
def session_scope() -> Iterator[Session]:
    """worker 内使用的同步 session 上下文（自动提交 / 回滚 / 关闭）。"""
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@asynccontextmanager
async def async_session_scope() -> AsyncIterator[AsyncSession]:
    """异步 session 上下文（脚本 / 生命周期钩子用）。"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
