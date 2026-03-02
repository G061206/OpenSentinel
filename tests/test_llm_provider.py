"""LLM Provider 适配器测试。"""

from app.adapters.llm_provider import extract_facts, filter_relevant_news, judge_event_progress


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


def test_filter_relevant_news_real_mode(monkeypatch):
    """相关性筛选成功时应返回 real 模式并映射条目。"""

    monkeypatch.setattr(
        "app.adapters.llm_provider._call_provider_json",
        lambda **_: {
            "decisions": [
                {"index": 1, "is_relevant": True, "score": 0.91, "reason": "match", "matched_aspects": ["x"]},
                {"index": 2, "is_relevant": False, "score": 0.2, "reason": "noise", "matched_aspects": []},
            ]
        },
    )
    items = [
        {"title": "t1", "url": "u1", "content": "c1"},
        {"title": "t2", "url": "u2", "content": "c2"},
    ]
    result = filter_relevant_news("openrouter", "q", items, api_key="k", model="m")
    assert result["provider_mode"] == "real"
    assert result["relevant_count"] == 1
    assert result["relevant_items"][0]["url"] == "u1"


def test_judge_event_progress_fallback(monkeypatch):
    """进展判断失败时应回退 mock。"""

    def _raise(**_):
        raise RuntimeError("network error")

    monkeypatch.setattr("app.adapters.llm_provider._call_provider_json", _raise)
    result = judge_event_progress("bailian", "q", [{"title": "t", "url": "u", "content": "c"}], api_key="k", model="m")
    assert result["provider"] == "bailian"
    assert result["provider_mode"] == "mock_fallback"
    assert result["suggested_level"] in {"WATCH", "ELEVATED", "CRISIS", "CONFIRMED", "NORMAL"}


def test_filter_relevant_news_mock_can_return_empty():
    """mock 筛选在无匹配时不应强行返回相关新闻。"""

    items = [
        {"title": "weather update", "url": "u1", "content": "local rain"},
        {"title": "sports", "url": "u2", "content": "team won"},
    ]
    result = filter_relevant_news("mock", "美国伊朗是否停战", items)
    assert result["provider_mode"] == "mock_fallback"
    assert result["relevant_count"] == 0
    assert result["relevant_items"] == []
