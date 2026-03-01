"""单次任务执行主流程服务。"""

from datetime import datetime, timezone

from sqlmodel import Session, select

from app.models.raw_item import RawItem
from app.models.report import Report
from app.models.tracker import TrackerTask
from app.services.dedup_service import DedupService
from app.services.delivery_service import DeliveryService
from app.services.evaluation_service import EvaluationService
from app.services.ingestion_service import IngestionService
from app.services.normalization_service import NormalizationService
from app.services.report_service import ReportService
from app.services.hash_service import stable_hash
from app.services.system_config_service import SystemConfigService


class TrackerRunService:
    """串联采集、归一化、去重、评估、报告、投递全链路。"""

    @staticmethod
    def run_once(session: Session, tracker: TrackerTask) -> dict:
        """执行一次 tracker 并返回执行结果摘要。"""

        if tracker.id is None:
            raise ValueError("tracker id is required")

        system_config = SystemConfigService.get_or_create(session)
        previous_level = tracker.current_level
        raw_items = IngestionService.collect(
            tracker.source_profile,
            extra_rss_urls=system_config.global_rss_urls,
        )
        normalized_items = NormalizationService.normalize(raw_items)
        new_items = DedupService.filter_new_items(session, tracker.id, normalized_items)

        for item in new_items:
            session.add(RawItem(tracker_id=tracker.id, **item))

        level = EvaluationService.evaluate(tracker.alert_rules, new_items, previous_level=previous_level)
        now = datetime.now(timezone.utc)
        tracker.current_level = level
        tracker.updated_at = now
        tracker.last_run_at = now

        # 无新增且状态不变：跳过生成与推送，避免噪声。
        if not new_items and level == previous_level:
            session.add(tracker)
            session.commit()
            return {
                "tracker_id": tracker.id,
                "new_items": 0,
                "level": level.value,
                "delivered": False,
                "deduped": True,
            }

        markdown, payload = ReportService.build_alert_report(
            tracker,
            level,
            new_items,
            llm_provider=system_config.llm_provider,
            llm_api_key=system_config.llm_api_key,
            llm_model=system_config.llm_model,
        )
        evidence_fingerprint = stable_hash(*sorted([item["stable_hash"] for item in new_items]), level.value)
        dedupe_key = f"alert:{tracker.id}:{evidence_fingerprint}"
        existing = session.exec(select(Report).where(Report.dedupe_key == dedupe_key)).first()
        # 相同证据指纹已经生成过报告：直接复用结果，避免重复推送。
        if existing:
            session.add(tracker)
            session.commit()
            return {
                "tracker_id": tracker.id,
                "new_items": len(new_items),
                "level": level.value,
                "delivered": existing.delivered,
                "deduped": True,
            }

        report = Report(
            tracker_id=tracker.id,
            report_type="alert",
            level=level,
            markdown=markdown,
            payload=payload,
            dedupe_key=dedupe_key,
        )
        session.add(report)

        delivered = DeliveryService.deliver(tracker.delivery_channels, markdown)
        report.delivered = delivered

        session.add(tracker)
        session.add(report)
        session.commit()

        return {
            "tracker_id": tracker.id,
            "new_items": len(new_items),
            "level": level.value,
            "delivered": delivered,
            "deduped": False,
        }
