"""DeepResearch Enterprise 服务层。

分层：
    routers/    HTTP 接口（认证 / 租户 / 任务 / SSE 推流）
    services/   业务逻辑（任务生命周期 / 调研执行）
    workers/    Celery 异步任务
    models.py   ORM（多租户，均带 tenant_id）
"""
