"""Tracker API 测试。"""

def test_create_and_list_tracker(client):
    """验证创建任务后可在列表中查询到。"""

    payload = {
        "title": "Test Tracker",
        "question": "Will event happen?",
        "description": "desc",
        "queries": ["keyword"],
        "source_profile": {"rss_urls": ["https://example.com/feed.xml"]},
        "schedule": "*/15 * * * *",
        "alert_rules": {"elevated_threshold": 2},
        "delivery_channels": {"wecom_webhook_url": ""},
        "priority": 50,
    }
    resp = client.post("/api/v1/trackers", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Test Tracker"

    list_resp = client.get("/api/v1/trackers")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1
