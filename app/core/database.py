"""数据库引擎与会话工具。"""

from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url, echo=False, pool_pre_ping=True)


def init_db() -> None:
    """根据 SQLModel 元数据创建表（MVP 启动阶段使用）。"""

    SQLModel.metadata.create_all(engine)
    _ensure_compatible_columns()


def _ensure_compatible_columns() -> None:
    """为历史数据库补齐必要字段，避免旧库启动报错。"""

    inspector = inspect(engine)
    if "tracker_tasks" not in inspector.get_table_names():
        return

    columns = {c["name"] for c in inspector.get_columns("tracker_tasks")}
    statements: list[str] = []

    if "llm_provider_id" not in columns:
        statements.append("ALTER TABLE tracker_tasks ADD COLUMN llm_provider_id INTEGER")

    if not statements:
        return

    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))


def get_session():
    """为后台任务或脚本提供数据库会话。"""

    with Session(engine) as session:
        yield session
