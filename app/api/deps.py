"""FastAPI 依赖注入定义。"""

from sqlmodel import Session

from app.core.database import engine


def get_db_session():
    """为每个请求提供数据库会话。"""

    with Session(engine) as session:
        yield session
