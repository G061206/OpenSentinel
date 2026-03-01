"""去重服务测试。"""

from app.models.raw_item import RawItem
from app.services.dedup_service import DedupService


def test_dedup_filters_existing_url_and_hash(session):
    """已存在 URL/哈希应被过滤，只保留新增条目。"""

    session.add(
        RawItem(
            tracker_id=1,
            source_type="rss",
            source_name="src",
            url="https://example.com/a",
            title="A",
            content="x",
            stable_hash="hash-a",
        )
    )
    session.commit()

    incoming = [
        {
            "source_type": "rss",
            "source_name": "src",
            "url": "https://example.com/a",
            "title": "A",
            "content": "x",
            "stable_hash": "hash-a",
        },
        {
            "source_type": "rss",
            "source_name": "src",
            "url": "https://example.com/b",
            "title": "B",
            "content": "y",
            "stable_hash": "hash-b",
        },
    ]

    new_items = DedupService.filter_new_items(session, 1, incoming)
    assert len(new_items) == 1
    assert new_items[0]["url"] == "https://example.com/b"
