"""Tracker 与 RSS 信源关联 ORM 模型。"""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class TrackerRSSLink(SQLModel, table=True):
    """保存任务和 RSS 信源的多对多关联。"""

    __tablename__ = "tracker_rss_links"

    id: Optional[int] = Field(default=None, primary_key=True)
    tracker_id: int = Field(foreign_key="tracker_tasks.id", index=True)
    rss_source_id: int = Field(foreign_key="rss_sources.id", index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
