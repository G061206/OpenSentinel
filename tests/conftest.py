"""测试共享夹具。"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine

from app.api.deps import get_db_session
from app.main import app


@pytest.fixture
def session():
    """提供独立的内存数据库会话。"""

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db:
        yield db


@pytest.fixture
def client(session):
    """提供绑定测试数据库依赖的 FastAPI 测试客户端。"""

    def _override_db():
        yield session

    app.dependency_overrides[get_db_session] = _override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
