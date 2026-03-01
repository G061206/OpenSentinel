"""LLM 适配层（当前为 mock 实现）。"""

import json
import re
from typing import Any

import httpx

from app.core.config import get_settings


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
