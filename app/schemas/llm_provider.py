"""LLM Provider 相关请求模型。"""

from pydantic import BaseModel

from app.models.enums import LLMProviderType


class LLMProviderCreate(BaseModel):
    """创建 LLM Provider 请求体。"""

    name: str
    provider_type: LLMProviderType = LLMProviderType.mock
    api_key: str = ""
    model: str = ""
    base_url: str = ""
    is_default: bool = False


class LLMProviderRead(LLMProviderCreate):
    """LLM Provider 读取模型。"""

    id: int
