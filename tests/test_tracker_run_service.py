"""任务执行主流程测试。"""

from app.models.enums import TrackerStatus
from app.models.tracker import TrackerTask
from app.services.tracker_run_service import TrackerRunService


def test_tracker_run_once(session, monkeypatch):
    """验证单次执行会产生新增证据并完成投递。"""

    tracker = TrackerTask(
        title="run",
        question="Q",
        status=TrackerStatus.active,
        source_profile={"rss_urls": ["https://example.com/feed.xml"]},
        delivery_channels={"wecom_webhook_url": ""},
    )
    session.add(tracker)
    session.commit()
    session.refresh(tracker)

    monkeypatch.setattr(
        "app.services.ingestion_service.IngestionService.collect",
        lambda _: [
            {
                "source_type": "rss",
                "source_name": "src",
                "url": "https://example.com/a",
                "title": "A",
                "content": "content",
                "published_at": None,
            }
        ],
    )
    monkeypatch.setattr("app.services.delivery_service.DeliveryService.deliver", lambda *_: True)

    result = TrackerRunService.run_once(session, tracker)
    assert result["new_items"] == 1
    assert result["delivered"] is True
