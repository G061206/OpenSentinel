"""RSS 信源相关请求/响应模型。"""

from pydantic import BaseModel


class RSSSourceCreate(BaseModel):
    """创建 RSS 信源请求体。"""

    name: str
    url: str
    category: str = ""


class RSSSourceRead(RSSSourceCreate):
    """RSS 信源读取模型。"""

    id: int
