"""RSS 信源 ORM 模型。"""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class RSSSource(SQLModel, table=True):
    """保存可复用的 RSS 信源。"""

    __tablename__ = "rss_sources"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    url: str = Field(index=True)
    category: str = Field(default="", index=True)
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
