"""日志相关行为测试。"""


def test_healthz_includes_request_id_header(client):
    """每个请求响应应带 X-Request-ID。"""

    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-ID")


def test_healthz_respects_incoming_request_id(client):
    """若请求携带 X-Request-ID，应原样透传。"""

    resp = client.get("/healthz", headers={"X-Request-ID": "rid-test-123"})
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-ID") == "rid-test-123"
