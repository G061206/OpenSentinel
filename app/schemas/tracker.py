"""Tracker 相关请求/响应模型。"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import EventLevel, TrackerStatus


class TrackerBase(BaseModel):
    """任务公共字段。"""

    title: str
    question: str
    description: str = ""
    queries: list[str] = Field(default_factory=list)
    source_profile: dict[str, Any] = Field(default_factory=dict)
    schedule: str = "*/15 * * * *"
    alert_rules: dict[str, Any] = Field(default_factory=dict)
    delivery_channels: dict[str, Any] = Field(default_factory=dict)
    priority: int = 50


class TrackerCreate(TrackerBase):
    """创建任务请求体。"""

    pass


class TrackerUpdate(BaseModel):
    """更新任务请求体，所有字段均为可选。"""

    title: str | None = None
    question: str | None = None
    description: str | None = None
    queries: list[str] | None = None
    source_profile: dict[str, Any] | None = None
    schedule: str | None = None
    alert_rules: dict[str, Any] | None = None
    delivery_channels: dict[str, Any] | None = None
    status: TrackerStatus | None = None
    priority: int | None = None


class TrackerRead(TrackerBase):
    """任务读取模型。"""

    id: int
    status: TrackerStatus
    current_level: EventLevel
    last_run_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ActionResponse(BaseModel):
    """简单动作响应模型。"""

    ok: bool
    message: str
