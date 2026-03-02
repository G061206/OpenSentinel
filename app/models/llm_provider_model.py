"""LLM Provider 配置 ORM 模型。"""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel

from app.models.enums import LLMProviderType


class LLMProviderConfig(SQLModel, table=True):
    """保存可选 LLM 提供商配置。"""

    __tablename__ = "llm_providers"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    provider_type: LLMProviderType = Field(default=LLMProviderType.mock, index=True)
    api_key: str = ""
    model: str = ""
    base_url: str = ""
    is_default: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
