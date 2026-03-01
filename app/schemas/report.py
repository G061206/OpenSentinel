"""报告读取模型。"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.enums import EventLevel


class ReportRead(BaseModel):
    """报告 API 返回结构。"""

    id: int
    tracker_id: int
    report_type: str
    level: EventLevel
    markdown: str
    payload: dict[str, Any]
    delivered: bool
    created_at: datetime
