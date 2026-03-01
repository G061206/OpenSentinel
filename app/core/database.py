"""数据库引擎与会话工具。"""

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url, echo=False, pool_pre_ping=True)


def init_db() -> None:
    """根据 SQLModel 元数据创建表（MVP 启动阶段使用）。"""

    SQLModel.metadata.create_all(engine)


def get_session():
    """为后台任务或脚本提供数据库会话。"""

    with Session(engine) as session:
        yield session
