"""FastAPI 应用入口。"""

import logging
import time
from uuid import uuid4

from fastapi import FastAPI
from fastapi import Request

from app.api.admin import router as admin_router
from app.api.reports import router as reports_router
from app.api.trackers import router as trackers_router
from app.core.config import get_settings
from app.core.database import init_db
from app.core.logging import bind_request_id, clear_request_id, setup_logging

# 确保所有模型被导入，以便 SQLModel.metadata.create_all 能创建所有表
import app.models  # noqa: F401

settings = get_settings()

app = FastAPI(title=settings.app_name)
logger = logging.getLogger(__name__)


@app.on_event("startup")
def on_startup() -> None:
    """进程启动时初始化日志与数据库表结构。"""

    setup_logging()
    init_db()


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """记录每个请求的基础访问日志并透传 request_id。"""

    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    bind_request_id(request_id)
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = int((time.perf_counter() - started) * 1000)
        logger.exception(
            "request failed method=%s path=%s duration_ms=%d",
            request.method,
            request.url.path,
            duration_ms,
        )
        clear_request_id()
        raise

    duration_ms = int((time.perf_counter() - started) * 1000)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request completed method=%s path=%s status=%d duration_ms=%d",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    clear_request_id()
    return response


@app.get("/healthz")
def healthz():
    """健康检查接口，用于探针与运维检查。"""

    return {"ok": True}


app.include_router(trackers_router)
app.include_router(reports_router)
app.include_router(admin_router)
