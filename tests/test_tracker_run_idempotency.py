"""任务执行幂等测试。"""

from app.models.enums import TrackerStatus
from app.models.tracker import TrackerTask
from app.services.tracker_run_service import TrackerRunService


def test_tracker_run_dedupes_same_evidence(session, monkeypatch):
    """同一证据重复出现时，应避免重复推送。"""

    tracker = TrackerTask(
        title="idem",
        question="Q",
        status=TrackerStatus.active,
        source_profile={"web_urls": []},
        delivery_channels={"wecom_webhook_url": ""},
    )
    session.add(tracker)
    session.commit()
    session.refresh(tracker)

    payload = [
        {
            "source_type": "rss",
            "source_name": "src",
            "url": "https://example.com/a",
            "title": "A",
            "content": "content",
            "published_at": None,
        }
    ]
    monkeypatch.setattr(
        "app.services.ingestion_service.IngestionService.collect",
        lambda *args, **kwargs: payload,
    )

    # Mock RSS sources and LLM provider
    monkeypatch.setattr(
        "app.services.rss_source_service.RSSSourceService.get_sources_for_tracker",
        lambda session, tid: [],
    )
    monkeypatch.setattr(
        "app.services.llm_provider_service.LLMProviderService.get",
        lambda session, pid: None,
    )
    monkeypatch.setattr(
        "app.services.llm_provider_service.LLMProviderService.get_default",
        lambda session: None,
    )

    delivery_calls = {"count": 0}

    def _deliver(*_):
        delivery_calls["count"] += 1
        return True

    monkeypatch.setattr("app.services.delivery_service.DeliveryService.deliver", _deliver)

    first = TrackerRunService.run_once(session, tracker)
    second = TrackerRunService.run_once(session, tracker)

    assert first["deduped"] is False
    assert second["deduped"] is True
    assert delivery_calls["count"] == 1
