"""RSS/Atom 信源适配器。"""

from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime

import feedparser


@dataclass
class RawFetchItem:
    """抓取适配器统一输出的数据结构。"""

    source_type: str
    source_name: str
    url: str
    title: str
    content: str
    published_at: datetime | None


def fetch_rss(url: str) -> list[RawFetchItem]:
    """抓取并解析 RSS，返回标准化原始条目列表。"""

    parsed = feedparser.parse(url)
    items: list[RawFetchItem] = []
    for entry in parsed.entries:
        published_at = None
        if getattr(entry, "published", None):
            try:
                published_at = parsedate_to_datetime(entry.published)
            except Exception:
                published_at = None
        items.append(
            RawFetchItem(
                source_type="rss",
                source_name=getattr(parsed.feed, "title", url),
                url=getattr(entry, "link", ""),
                title=getattr(entry, "title", ""),
                content=getattr(entry, "summary", ""),
                published_at=published_at,
            )
        )
    return items
