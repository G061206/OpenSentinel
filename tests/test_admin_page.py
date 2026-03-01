"""管理后台页面测试。"""

from sqlmodel import select

from app.models.system_config import SystemConfig
from app.models.tracker import TrackerTask
from app.models.tracker_run_log import TrackerRunLog

def test_admin_page_loads(client):
    """首页应可正常访问并包含标题。"""

    resp = client.get("/admin")
    assert resp.status_code == 200
    assert "OpenSentinel 管理台" in resp.text


def test_admin_config_page_save(client, session):
    """配置页可保存 LLM provider 与全局 RSS 源。"""

    resp = client.get("/admin/config")
    assert resp.status_code == 200
    assert "系统配置" in resp.text

    save_resp = client.post(
        "/admin/config",
        data={
            "llm_provider": "openrouter",
            "llm_api_key": "test-key",
            "llm_model": "openai/gpt-4o-mini",
            "global_rss_urls": "https://example.com/a.xml\nhttps://example.com/b.xml",
        },
    )
    assert save_resp.status_code == 200
    assert "配置已保存" in save_resp.text

    config = session.exec(select(SystemConfig)).first()
    assert config is not None
    assert config.llm_provider == "openrouter"
    assert config.llm_model == "openai/gpt-4o-mini"
    assert len(config.global_rss_urls) == 2


def test_admin_tracker_logs_page(client, session):
    """任务日志页可查看对应 tracker 的执行记录。"""

    tracker = TrackerTask(title="log-test", question="Q")
    session.add(tracker)
    session.commit()
    session.refresh(tracker)
    assert tracker.id is not None

    log = TrackerRunLog(
        tracker_id=tracker.id,
        trigger="manual",
        status="success",
        message="completed",
    )
    session.add(log)
    session.commit()

    resp = client.get(f"/admin/trackers/{tracker.id}/logs")
    assert resp.status_code == 200
    assert "任务执行日志" in resp.text
    assert "completed" in resp.text
