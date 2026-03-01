"""消息投递服务测试。"""

from app.services.delivery_service import DeliveryService


def test_delivery_uses_text_by_default(monkeypatch):
    """默认格式应走 text 发送。"""

    sent = {"mode": ""}

    monkeypatch.setattr("app.services.delivery_service.send_text", lambda *_: sent.update(mode="text") or True)
    monkeypatch.setattr("app.services.delivery_service.send_markdown", lambda *_: sent.update(mode="md") or True)

    ok = DeliveryService.deliver({"wecom_webhook_url": "https://example.com/webhook"}, "# title")
    assert ok is True
    assert sent["mode"] == "text"
