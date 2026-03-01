"""系统级配置 ORM 模型。"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class SystemConfig(SQLModel, table=True):
    """保存全局配置（LLM 提供商与全局 RSS 源）。"""

    __tablename__ = "system_configs"

    id: Optional[int] = Field(default=None, primary_key=True)
    llm_provider: str = Field(default="mock", index=True)
    llm_api_key: str = Field(default="")
    llm_model: str = Field(default="")
    global_rss_urls: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
