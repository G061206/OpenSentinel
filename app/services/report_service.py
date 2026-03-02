"""报告生成服务。"""

from datetime import datetime, timezone
from typing import Any

from app.adapters.llm_provider import filter_relevant_news, judge_event_progress
from app.models.enums import EventLevel
from app.models.tracker import TrackerTask


class ReportService:
    """将评估结果与证据组织为 markdown 报告。"""

    @staticmethod
    def analyze_event_progress(
        question: str,
        new_items: list[dict[str, Any]],
        llm_provider: str,
        llm_api_key: str,
        llm_model: str,
    ) -> dict[str, Any]:
        """先筛相关新闻，再基于全文判断事件进展。"""

        if not new_items:
            return {
                "total_new_items": 0,
                "relevant_items": [],
                "relevance": {
                    "question": question,
                    "total_items": 0,
                    "relevant_count": 0,
                    "decisions": [],
                    "provider": (llm_provider or "mock").strip().lower(),
                    "provider_mode": "skipped",
                },
                "progress": {
                    "question": question,
                    "suggested_level": "NORMAL",
                    "confidence": 0.0,
                    "summary": "no new items",
                    "key_facts": [],
                    "contradictions": [],
                    "provider": (llm_provider or "mock").strip().lower(),
                    "provider_mode": "skipped",
                },
            }

        relevance = filter_relevant_news(
            llm_provider,
            question,
            new_items,
            api_key=llm_api_key,
            model=llm_model,
        )
        relevant_items = relevance.get("relevant_items", [])
        if not isinstance(relevant_items, list):
            relevant_items = []

        progress = judge_event_progress(
            llm_provider,
            question,
            relevant_items,
            api_key=llm_api_key,
            model=llm_model,
        )

        return {
            "total_new_items": len(new_items),
            "relevant_items": relevant_items,
            "relevance": relevance,
            "progress": progress,
        }

    @staticmethod
    def build_alert_report(
        tracker: TrackerTask,
        level: EventLevel,
        new_items: list[dict],
        llm_provider: str,
        llm_api_key: str,
        llm_model: str,
        analysis: dict[str, Any] | None = None,
    ) -> tuple[str, dict]:
        """生成实时预警报告与结构化负载。"""

        pipeline = analysis or ReportService.analyze_event_progress(
            tracker.question,
            new_items,
            llm_provider,
            llm_api_key,
            llm_model,
        )
        relevant_items = pipeline.get("relevant_items", [])
        if not isinstance(relevant_items, list):
            relevant_items = []
        progress = pipeline.get("progress", {})
        suggested_level = progress.get("suggested_level", "NORMAL") if isinstance(progress, dict) else "NORMAL"
        confidence = progress.get("confidence", 0) if isinstance(progress, dict) else 0
        ts = datetime.now(timezone.utc).isoformat()

        lines = [
            f"# {tracker.title} 实时预警",
            "",
            f"- 当前状态: **{level.value}**",
            f"- LLM 建议状态: **{suggested_level}**（置信度 {confidence}）",
            f"- 问题: {tracker.question}",
            f"- 新增证据数: {len(new_items)}",
            f"- 相关新闻数: {len(relevant_items)}",
            f"- 生成时间: {ts}",
            "",
            "## 关键证据",
        ]
        for item in relevant_items[:5]:
            lines.append(f"- [{item['title'] or item['url']}]({item['url']})")

        if not relevant_items:
            lines.append("- 本周期未发现新增证据")

        payload = {
            "llm": {
                "relevance": pipeline.get("relevance", {}),
                "progress": progress,
            },
            "new_items": new_items,
            "relevant_items": relevant_items,
        }
        return "\n".join(lines), payload
