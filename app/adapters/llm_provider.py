"""LLM 适配层。"""

import json
import re
from typing import Any

import httpx

from app.core.config import get_settings

_EVENT_LEVELS = {"NORMAL", "WATCH", "ELEVATED", "CRISIS", "CONFIRMED"}


def extract_facts_mock(question: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    """模拟结构化事实抽取，便于在无真实模型时联调。"""

    key_facts = []
    for item in items[:5]:
        key_facts.append(
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "fact": item.get("content", "")[:180],
            }
        )
    return {
        "question": question,
        "fact_count": len(key_facts),
        "key_facts": key_facts,
    }


def _extract_json_text(content: str) -> dict[str, Any] | None:
    """从模型文本中提取 JSON 对象。"""

    content = (content or "").strip()
    if not content:
        return None

    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    fenced = re.search(r"```json\s*(\{[\s\S]*\})\s*```", content, flags=re.IGNORECASE)
    if fenced:
        try:
            parsed = json.loads(fenced.group(1))
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return None
    return None


def _build_evidence_lines(items: list[dict[str, Any]], limit: int = 8) -> str:
    """把证据条目压缩成模型输入文本。"""

    lines: list[str] = []
    for idx, item in enumerate(items[:limit], start=1):
        title = (item.get("title") or "").strip()
        url = (item.get("url") or "").strip()
        content = (item.get("content") or "").strip().replace("\n", " ")[:500]
        lines.append(f"{idx}. title={title}; url={url}; content={content}")
    return "\n".join(lines)


def _build_title_lines(items: list[dict[str, Any]], limit: int = 20) -> str:
    """把标题候选压缩成模型输入文本。"""

    lines: list[str] = []
    for idx, item in enumerate(items[:limit], start=1):
        title = (item.get("title") or "").strip()
        url = (item.get("url") or "").strip()
        source = (item.get("source_name") or "").strip()
        content = (item.get("content") or "").strip().replace("\n", " ")[:180]
        lines.append(f"{idx}. title={title}; source={source}; url={url}; snippet={content}")
    return "\n".join(lines)


def _tokenize_for_match(text: str) -> list[str]:
    """用于 mock 相关性匹配的轻量分词。"""

    lowered = (text or "").lower()
    chunks = re.split(r"[^\w\u4e00-\u9fff]+", lowered)
    tokens = [c for c in chunks if len(c) >= 2]
    seen: set[str] = set()
    unique: list[str] = []
    for token in tokens:
        if token not in seen:
            seen.add(token)
            unique.append(token)
    return unique


def _openai_compatible_extract(
    *,
    base_url: str,
    api_key: str,
    model: str,
    question: str,
    items: list[dict[str, Any]],
    timeout_seconds: int,
    extra_headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """调用 OpenAI 兼容接口做结构化事实抽取。"""

    if not api_key:
        raise ValueError("llm api key is required")
    if not model:
        raise ValueError("llm model is required")

    system_prompt = (
        "你是事件分析助手。只输出 JSON，不要输出其他文本。"
        "JSON schema: {\"fact_count\":int,\"key_facts\":[{\"title\":str,\"url\":str,\"fact\":str}]}"
    )
    user_prompt = (
        f"问题: {question}\n"
        "请基于以下证据提取关键事实，fact 字段尽量短，最多 120 字。\n"
        f"证据:\n{_build_evidence_lines(items)}"
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)

    payload = {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
    }

    url = f"{base_url.rstrip('/')}/chat/completions"
    with httpx.Client(timeout=timeout_seconds) as client:
        resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()

    content = ""
    try:
        content = data["choices"][0]["message"]["content"]
    except Exception as exc:
        raise ValueError(f"invalid llm response: {exc}") from exc

    parsed = _extract_json_text(content)
    if not parsed:
        raise ValueError("llm response is not valid json object")

    key_facts = parsed.get("key_facts", [])
    if not isinstance(key_facts, list):
        key_facts = []
    normalized_facts: list[dict[str, Any]] = []
    for fact in key_facts[:8]:
        if not isinstance(fact, dict):
            continue
        normalized_facts.append(
            {
                "title": str(fact.get("title", ""))[:300],
                "url": str(fact.get("url", ""))[:1000],
                "fact": str(fact.get("fact", ""))[:300],
            }
        )

    return {
        "question": question,
        "fact_count": len(normalized_facts),
        "key_facts": normalized_facts,
    }


def _openai_compatible_json_call(
    *,
    base_url: str,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    timeout_seconds: int,
    extra_headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """调用 OpenAI 兼容接口并提取 JSON 对象。"""

    if not api_key:
        raise ValueError("llm api key is required")
    if not model:
        raise ValueError("llm model is required")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)

    payload = {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
    }

    url = f"{base_url.rstrip('/')}/chat/completions"
    with httpx.Client(timeout=timeout_seconds) as client:
        resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()

    try:
        content = data["choices"][0]["message"]["content"]
    except Exception as exc:
        raise ValueError(f"invalid llm response: {exc}") from exc

    parsed = _extract_json_text(content)
    if not parsed:
        raise ValueError("llm response is not valid json object")
    return parsed


def _call_provider_json(
    *,
    provider: str,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
) -> dict[str, Any]:
    """按 provider 分派 OpenAI 兼容 JSON 调用。"""

    settings = get_settings()
    selected = (provider or "mock").strip().lower()
    if selected == "openrouter":
        return _openai_compatible_json_call(
            base_url=settings.openrouter_base_url,
            api_key=api_key or settings.openrouter_api_key or settings.llm_api_key,
            model=model or settings.openrouter_model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            timeout_seconds=settings.llm_timeout_seconds,
            extra_headers={
                "HTTP-Referer": settings.openrouter_app_url,
                "X-Title": settings.app_name,
            },
        )
    if selected == "bailian":
        return _openai_compatible_json_call(
            base_url=settings.bailian_base_url,
            api_key=api_key or settings.bailian_api_key or settings.llm_api_key,
            model=model or settings.bailian_model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            timeout_seconds=settings.llm_timeout_seconds,
        )
    raise ValueError(f"provider '{selected}' does not support real call")


def _filter_relevant_news_mock(question: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    """mock 版标题相关性筛选。"""

    question_tokens = _tokenize_for_match(question)
    decisions: list[dict[str, Any]] = []
    relevant_items: list[dict[str, Any]] = []

    for idx, item in enumerate(items, start=1):
        title = (item.get("title") or "").strip().lower()
        snippet = (item.get("content") or "").strip().lower()[:300]
        text = f"{title} {snippet}"
        overlap = [t for t in question_tokens if t in text]
        score = min(1.0, 0.35 + 0.12 * len(overlap)) if overlap else 0.2
        is_relevant = bool(overlap) or not question_tokens
        decisions.append(
            {
                "index": idx,
                "is_relevant": is_relevant,
                "score": round(score, 3),
                "reason": "keyword_overlap" if overlap else "low_signal",
                "matched_aspects": overlap[:6],
            }
        )
        if is_relevant:
            relevant_items.append(item)

    return {
        "question": question,
        "total_items": len(items),
        "relevant_count": len(relevant_items),
        "decisions": decisions,
        "relevant_items": relevant_items,
    }


def filter_relevant_news(
    provider: str,
    question: str,
    items: list[dict[str, Any]],
    api_key: str = "",
    model: str = "",
) -> dict[str, Any]:
    """先看标题/摘要筛选与事件问题相关的新闻。"""

    selected = (provider or "mock").strip().lower()
    system_prompt = (
        "你是新闻相关性筛选器。仅输出 JSON。"
        "输出 schema: {\"decisions\":[{\"index\":int,\"is_relevant\":bool,\"score\":float,\"reason\":str,\"matched_aspects\":[str]}]}"
    )
    user_prompt = (
        f"任务问题: {question}\n"
        "请基于以下新闻标题与摘要判断是否与任务问题直接相关。"
        "score 范围 0~1，尽量保守，不要把泛相关误判为直接相关。\n"
        f"候选:\n{_build_title_lines(items)}"
    )

    try:
        parsed = _call_provider_json(
            provider=selected,
            api_key=api_key,
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        raw_decisions = parsed.get("decisions", [])
        decisions: list[dict[str, Any]] = []
        relevant_items: list[dict[str, Any]] = []

        if isinstance(raw_decisions, list):
            for row in raw_decisions:
                if not isinstance(row, dict):
                    continue
                idx_raw = row.get("index")
                if not isinstance(idx_raw, int):
                    continue
                if idx_raw < 1 or idx_raw > len(items):
                    continue
                is_relevant = bool(row.get("is_relevant", False))
                score = row.get("score", 0)
                try:
                    score = float(score)
                except Exception:
                    score = 0.0
                score = max(0.0, min(1.0, score))

                decision = {
                    "index": idx_raw,
                    "is_relevant": is_relevant,
                    "score": score,
                    "reason": str(row.get("reason", ""))[:200],
                    "matched_aspects": row.get("matched_aspects", []) if isinstance(row.get("matched_aspects", []), list) else [],
                }
                decisions.append(decision)
                if is_relevant:
                    relevant_items.append(items[idx_raw - 1])

        if not decisions:
            raise ValueError("empty relevance decisions")

        return {
            "question": question,
            "total_items": len(items),
            "relevant_count": len(relevant_items),
            "decisions": decisions,
            "relevant_items": relevant_items,
            "provider": selected,
            "provider_mode": "real",
        }
    except Exception as exc:
        payload = _filter_relevant_news_mock(question, items)
        payload["provider"] = selected
        payload["provider_mode"] = "mock_fallback"
        payload["error"] = str(exc)
        return payload


def _judge_event_progress_mock(question: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    """mock 版事件进展判断。"""

    n = len(items)
    if n >= 6:
        level = "CONFIRMED"
    elif n >= 4:
        level = "CRISIS"
    elif n >= 2:
        level = "ELEVATED"
    elif n >= 1:
        level = "WATCH"
    else:
        level = "NORMAL"

    key_facts = []
    for item in items[:5]:
        key_facts.append(
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "fact": (item.get("content", "") or "")[:180],
            }
        )

    return {
        "question": question,
        "suggested_level": level,
        "confidence": min(0.95, 0.35 + 0.1 * n),
        "summary": "mock progress judgement",
        "key_facts": key_facts,
        "contradictions": [],
    }


def judge_event_progress(
    provider: str,
    question: str,
    relevant_items: list[dict[str, Any]],
    api_key: str = "",
    model: str = "",
) -> dict[str, Any]:
    """基于相关新闻全文判断事件进展。"""

    selected = (provider or "mock").strip().lower()
    system_prompt = (
        "你是事件进展判断助手。仅输出 JSON，不输出解释文本。"
        "输出 schema: {\"suggested_level\":\"NORMAL|WATCH|ELEVATED|CRISIS|CONFIRMED\",\"confidence\":float,\"summary\":str,\"key_facts\":[{\"title\":str,\"url\":str,\"fact\":str}],\"contradictions\":[str]}"
    )
    user_prompt = (
        f"任务问题: {question}\n"
        "请基于以下相关新闻正文判断事件进展。若证据不足应给出较低置信度。\n"
        f"证据:\n{_build_evidence_lines(relevant_items)}"
    )

    try:
        parsed = _call_provider_json(
            provider=selected,
            api_key=api_key,
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        suggested_level = str(parsed.get("suggested_level", "NORMAL")).upper()
        if suggested_level not in _EVENT_LEVELS:
            suggested_level = "NORMAL"
        confidence_raw = parsed.get("confidence", 0)
        try:
            confidence = float(confidence_raw)
        except Exception:
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))

        key_facts = parsed.get("key_facts", [])
        if not isinstance(key_facts, list):
            key_facts = []
        normalized_facts: list[dict[str, Any]] = []
        for fact in key_facts[:8]:
            if not isinstance(fact, dict):
                continue
            normalized_facts.append(
                {
                    "title": str(fact.get("title", ""))[:300],
                    "url": str(fact.get("url", ""))[:1000],
                    "fact": str(fact.get("fact", ""))[:300],
                }
            )

        contradictions = parsed.get("contradictions", [])
        if not isinstance(contradictions, list):
            contradictions = []

        return {
            "question": question,
            "suggested_level": suggested_level,
            "confidence": confidence,
            "summary": str(parsed.get("summary", ""))[:800],
            "key_facts": normalized_facts,
            "contradictions": [str(item)[:200] for item in contradictions[:8]],
            "provider": selected,
            "provider_mode": "real",
        }
    except Exception as exc:
        payload = _judge_event_progress_mock(question, relevant_items)
        payload["provider"] = selected
        payload["provider_mode"] = "mock_fallback"
        payload["error"] = str(exc)
        return payload


def extract_facts(
    provider: str,
    question: str,
    items: list[dict[str, Any]],
    api_key: str = "",
    model: str = "",
) -> dict[str, Any]:
    """按 provider 分派结构化抽取实现。"""

    settings = get_settings()
    selected = (provider or "mock").strip().lower()

    try:
        if selected == "openrouter":
            result = _openai_compatible_extract(
                base_url=settings.openrouter_base_url,
                api_key=api_key or settings.openrouter_api_key or settings.llm_api_key,
                model=model or settings.openrouter_model,
                question=question,
                items=items,
                timeout_seconds=settings.llm_timeout_seconds,
                extra_headers={
                    "HTTP-Referer": settings.openrouter_app_url,
                    "X-Title": settings.app_name,
                },
            )
            result["provider"] = "openrouter"
            result["provider_mode"] = "real"
            return result

        if selected == "bailian":
            result = _openai_compatible_extract(
                base_url=settings.bailian_base_url,
                api_key=api_key or settings.bailian_api_key or settings.llm_api_key,
                model=model or settings.bailian_model,
                question=question,
                items=items,
                timeout_seconds=settings.llm_timeout_seconds,
            )
            result["provider"] = "bailian"
            result["provider_mode"] = "real"
            return result
    except Exception as exc:
        payload = extract_facts_mock(question, items)
        payload["provider"] = selected
        payload["provider_mode"] = "mock_fallback"
        payload["error"] = str(exc)
        return payload

    payload = extract_facts_mock(question, items)
    payload["provider"] = selected
    payload["provider_mode"] = "mock_fallback"
    return payload
