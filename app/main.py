"""FastAPI 应用入口。"""

from fastapi import FastAPI

from app.api.admin import router as admin_router
from app.api.reports import router as reports_router
from app.api.trackers import router as trackers_router
from app.core.config import get_settings
from app.core.database import init_db
from app.core.logging import setup_logging

# 确保所有模型被导入，以便 SQLModel.metadata.create_all 能创建所有表
import app.models  # noqa: F401

settings = get_settings()

app = FastAPI(title=settings.app_name)


@app.on_event("startup")
def on_startup() -> None:
    """进程启动时初始化日志与数据库表结构。"""

    setup_logging()
    init_db()


@app.get("/healthz")
def healthz():
    """健康检查接口，用于探针与运维检查。"""

    return {"ok": True}


app.include_router(trackers_router)
app.include_router(reports_router)
app.include_router(admin_router)
