"""测试共享夹具。"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import StaticPool

# 确保所有 ORM 模型注册到 SQLModel.metadata
from app.models.tracker import TrackerTask  # noqa: F401
from app.models.raw_item import RawItem  # noqa: F401
from app.models.report import Report  # noqa: F401
from app.models.system_config import SystemConfig  # noqa: F401
from app.models.tracker_run_log import TrackerRunLog  # noqa: F401
from app.models.llm_provider_model import LLMProviderConfig  # noqa: F401
from app.models.rss_source import RSSSource  # noqa: F401
from app.models.tracker_rss_link import TrackerRSSLink  # noqa: F401

from app.api.deps import get_db_session
from app.main import app as fastapi_app


@pytest.fixture
def session():
    """提供独立的内存数据库会话。"""

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db:
        yield db


@pytest.fixture
def client(session):
    """提供绑定测试数据库依赖的 FastAPI 测试客户端。"""

    def _override_db():
        yield session

    fastapi_app.dependency_overrides[get_db_session] = _override_db
    with TestClient(fastapi_app, raise_server_exceptions=True) as c:
        yield c
    fastapi_app.dependency_overrides.clear()
