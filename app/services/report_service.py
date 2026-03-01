"""报告生成服务。"""

from datetime import datetime, timezone

from app.adapters.llm_provider import extract_facts
from app.models.enums import EventLevel
from app.models.tracker import TrackerTask


class ReportService:
    """将评估结果与证据组织为 markdown 报告。"""

    @staticmethod
    def build_alert_report(
        tracker: TrackerTask,
        level: EventLevel,
        new_items: list[dict],
        llm_provider: str,
        llm_api_key: str,
        llm_model: str,
    ) -> tuple[str, dict]:
        """生成实时预警报告与结构化负载。"""

        llm_payload = extract_facts(
            llm_provider,
            tracker.question,
            new_items,
            api_key=llm_api_key,
            model=llm_model,
        )
        ts = datetime.now(timezone.utc).isoformat()

        lines = [
            f"# {tracker.title} 实时预警",
            "",
            f"- 当前状态: **{level.value}**",
            f"- 问题: {tracker.question}",
            f"- 新增证据数: {len(new_items)}",
            f"- 生成时间: {ts}",
            "",
            "## 关键证据",
        ]
        for item in new_items[:5]:
            lines.append(f"- [{item['title'] or item['url']}]({item['url']})")

        if not new_items:
            lines.append("- 本周期未发现新增证据")

        return "\n".join(lines), {"llm": llm_payload, "new_items": new_items}
