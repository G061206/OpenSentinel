"""跟踪任务 ORM 模型。"""

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.models.enums import EventLevel, TrackerStatus


class TrackerTask(SQLModel, table=True):
    """保存任务定义、调度配置、告警规则和运行状态。"""

    __tablename__ = "tracker_tasks"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    question: str
    description: str = ""
    queries: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    source_profile: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    schedule: str = "*/15 * * * *"
    alert_rules: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    delivery_channels: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    status: TrackerStatus = Field(default=TrackerStatus.active, index=True)
    priority: int = 50
    current_level: EventLevel = Field(default=EventLevel.NORMAL)
    last_run_at: Optional[datetime] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
