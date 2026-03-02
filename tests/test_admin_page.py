"""管理后台页面测试。"""

from app.models.tracker import TrackerTask
from app.models.tracker_run_log import TrackerRunLog
from app.models.llm_provider_model import LLMProviderConfig
from app.models.rss_source import RSSSource
from app.models.enums import LLMProviderType


def test_admin_page_loads(client):
    """首页应可正常访问并包含标题。"""

    resp = client.get("/admin")
    assert resp.status_code == 200
    assert "OpenSentinel" in resp.text


def test_admin_panels_tracker_list(client):
    """Tracker 列表面板可正常加载。"""

    resp = client.get("/admin/panels/trackers")
    assert resp.status_code == 200


def test_admin_panels_tracker_form(client):
    """新建 Tracker 表单面板可正常加载。"""

    resp = client.get("/admin/panels/tracker-form")
    assert resp.status_code == 200
    assert "新建跟踪任务" in resp.text


def test_admin_panels_provider_list(client):
    """Provider 列表面板可正常加载。"""

    resp = client.get("/admin/panels/providers")
    assert resp.status_code == 200
    assert "LLM Providers" in resp.text


def test_admin_panels_rss_sources(client):
    """RSS 信源面板可正常加载。"""

    resp = client.get("/admin/panels/rss-sources")
    assert resp.status_code == 200
    assert "RSS 信源管理" in resp.text


def test_admin_create_provider(client, session):
    """可通过表单创建 LLM Provider。"""

    resp = client.post(
        "/admin/providers",
        data={
            "name": "Test Provider",
            "provider_type": "openrouter",
            "api_key": "sk-testkey123",
            "model": "gpt-4o-mini",
            "base_url": "",
            "is_default": "true",
        },
    )
    assert resp.status_code == 200

    provider = session.query(LLMProviderConfig).first()
    assert provider is not None
    assert provider.name == "Test Provider"
    assert provider.provider_type == LLMProviderType.openrouter
    assert provider.is_default is True


def test_admin_create_rss_source(client, session):
    """可通过表单创建 RSS 信源。"""

    resp = client.post(
        "/admin/rss-sources",
        data={
            "name": "Test Feed",
            "url": "https://example.com/feed.xml",
            "category": "科技",
            "bulk_urls": "",
        },
    )
    assert resp.status_code == 200

    source = session.query(RSSSource).first()
    assert source is not None
    assert source.url == "https://example.com/feed.xml"
    assert source.category == "科技"


def test_admin_create_tracker_with_provider_and_rss(client, session):
    """可通过表单创建关联 Provider 和 RSS 源的任务。"""

    # 先创建 Provider 和 RSS 源
    provider = LLMProviderConfig(
        name="P1", provider_type=LLMProviderType.mock, is_default=True
    )
    session.add(provider)
    rss = RSSSource(name="Feed1", url="https://example.com/a.xml")
    session.add(rss)
    session.commit()
    session.refresh(provider)
    session.refresh(rss)

    resp = client.post(
        "/admin/trackers",
        data={
            "title": "Test Task",
            "question": "What is happening?",
            "description": "",
            "queries": "keyword1, keyword2",
            "web_urls": "",
            "schedule": "*/15 * * * *",
            "wecom_webhook_url": "",
            "llm_provider_id": str(provider.id),
            "rss_source_ids": str(rss.id),
            "elevated_threshold": "2",
            "crisis_threshold": "4",
            "confirmed_threshold": "6",
        },
    )
    assert resp.status_code == 200

    tracker = session.query(TrackerTask).first()
    assert tracker is not None
    assert tracker.title == "Test Task"
    assert tracker.llm_provider_id == provider.id


def test_admin_tracker_logs_panel(client, session):
    """任务日志面板可查看对应 tracker 的执行记录。"""

    tracker = TrackerTask(title="log-test", question="Q")
    session.add(tracker)
    session.commit()
    session.refresh(tracker)

    log = TrackerRunLog(
        tracker_id=tracker.id,
        trigger="manual",
        status="success",
        message="completed",
    )
    session.add(log)
    session.commit()

    resp = client.get(f"/admin/panels/tracker-logs/{tracker.id}")
    assert resp.status_code == 200
    assert "completed" in resp.text
