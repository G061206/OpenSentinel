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
        source_profile={"web_urls": []},
        delivery_channels={"wecom_webhook_url": ""},
    )
    session.add(tracker)
    session.commit()
    session.refresh(tracker)

    monkeypatch.setattr(
        "app.services.ingestion_service.IngestionService.collect",
        lambda *args, **kwargs: [
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
    # Mock RSS sources for tracker (empty list)
    monkeypatch.setattr(
        "app.services.rss_source_service.RSSSourceService.get_sources_for_tracker",
        lambda session, tid: [],
    )
    # Mock LLM provider lookup
    monkeypatch.setattr(
        "app.services.llm_provider_service.LLMProviderService.get",
        lambda session, pid: None,
    )
    monkeypatch.setattr(
        "app.services.llm_provider_service.LLMProviderService.get_default",
        lambda session: None,
    )

    result = TrackerRunService.run_once(session, tracker)
    assert result["new_items"] == 1
    assert result["relevant_items"] == 1
    assert "metrics" in result
    assert "collect_ms" in result["metrics"]
    assert result["delivered"] is True


def test_tracker_run_skips_delivery_when_no_relevant(session, monkeypatch):
    """有新增但无相关新闻时应跳过推送。"""

    tracker = TrackerTask(
        title="run",
        question="Q",
        status=TrackerStatus.active,
        source_profile={"web_urls": []},
        delivery_channels={"wecom_webhook_url": ""},
    )
    session.add(tracker)
    session.commit()
    session.refresh(tracker)

    monkeypatch.setattr(
        "app.services.ingestion_service.IngestionService.collect",
        lambda *args, **kwargs: [
            {
                "source_type": "rss",
                "source_name": "src",
                "url": "https://example.com/z",
                "title": "Z",
                "content": "content",
                "published_at": None,
            }
        ],
    )
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
    monkeypatch.setattr(
        "app.services.report_service.ReportService.analyze_event_progress",
        lambda *args, **kwargs: {
            "total_new_items": 1,
            "relevant_items": [],
            "relevance": {"provider_mode": "mock_fallback"},
            "progress": {"suggested_level": "NORMAL", "confidence": 0.1},
        },
    )

    called = {"deliver": 0}
    monkeypatch.setattr(
        "app.services.delivery_service.DeliveryService.deliver",
        lambda *_: called.update(deliver=called["deliver"] + 1) or True,
    )

    result = TrackerRunService.run_once(session, tracker)
    assert result["new_items"] == 1
    assert result["relevant_items"] == 0
    assert "metrics" in result
    assert result["delivered"] is False
    assert result["deduped"] is True
    assert called["deliver"] == 0
