"""任务执行日志 ORM 模型。"""

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class TrackerRunLog(SQLModel, table=True):
    """记录每次任务执行过程与结果，便于排障与审计。"""

    __tablename__ = "tracker_run_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    tracker_id: int = Field(index=True)
    trigger: str = Field(default="schedule", index=True)
    force: bool = Field(default=False, index=True)
    status: str = Field(default="running", index=True)
    message: str = Field(default="")
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    ended_at: Optional[datetime] = Field(default=None, index=True)
