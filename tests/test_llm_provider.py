"""LLM Provider 适配器测试。"""

from app.adapters.llm_provider import extract_facts


def test_extract_facts_openrouter_real_mode(monkeypatch):
    """openrouter 分支成功时应返回 real 模式。"""

    monkeypatch.setattr(
        "app.adapters.llm_provider._openai_compatible_extract",
        lambda **_: {"question": "q", "fact_count": 1, "key_facts": [{"title": "t", "url": "u", "fact": "f"}]},
    )
    result = extract_facts("openrouter", "q", [], api_key="k", model="m")
    assert result["provider"] == "openrouter"
    assert result["provider_mode"] == "real"
    assert result["fact_count"] == 1


def test_extract_facts_bailian_fallback(monkeypatch):
    """bailian 分支异常时应回退到 mock。"""

    def _raise(**_):
        raise RuntimeError("network error")

    monkeypatch.setattr("app.adapters.llm_provider._openai_compatible_extract", _raise)
    result = extract_facts("bailian", "q", [], api_key="k", model="m")
    assert result["provider"] == "bailian"
    assert result["provider_mode"] == "mock_fallback"
    assert "error" in result
