"""报告 ORM 模型。"""

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.models.enums import EventLevel


class Report(SQLModel, table=True):
    """保存告警/周期报告文本、结构化负载和投递结果。"""

    __tablename__ = "reports"

    id: Optional[int] = Field(default=None, primary_key=True)
    tracker_id: int = Field(index=True)
    report_type: str = Field(index=True)
    level: EventLevel = Field(index=True)
    markdown: str
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    dedupe_key: str = Field(index=True)
    delivered: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
