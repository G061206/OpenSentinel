"""网页抓取与正文抽取适配器。"""

from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
import trafilatura


@dataclass
class RawFetchItem:
    """抓取适配器统一输出的数据结构。"""

    source_type: str
    source_name: str
    url: str
    title: str
    content: str
    published_at: datetime | None


def fetch_webpage(url: str, timeout_seconds: int = 20) -> RawFetchItem | None:
    """抓取网页并用 trafilatura 提取正文。"""

    with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        html = response.text

    extracted = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=False,
        output_format="json",
    )
    if not extracted:
        return None

    title = url
    content = ""
    try:
        import json

        payload = json.loads(extracted)
        title = payload.get("title") or url
        content = payload.get("text") or ""
    except Exception:
        content = extracted

    return RawFetchItem(
        source_type="webpage",
        source_name=url,
        url=url,
        title=title,
        content=content,
        published_at=datetime.now(timezone.utc),
    )
