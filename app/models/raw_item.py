"""证据条目 ORM 模型（原始抓取后归一化结果）。"""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class RawItem(SQLModel, table=True):
    """表示一条与任务关联的归一化信源内容。"""

    __tablename__ = "raw_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    tracker_id: int = Field(index=True)
    source_type: str = Field(index=True)
    source_name: str = ""
    url: str = Field(index=True)
    title: str = ""
    content: str = ""
    published_at: Optional[datetime] = None
    stable_hash: str = Field(index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
