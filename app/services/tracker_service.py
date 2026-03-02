"""Tracker 任务管理服务。"""

from datetime import datetime, timezone

from sqlmodel import Session, select

from app.models.enums import TrackerStatus
from app.models.tracker import TrackerTask
from app.schemas.tracker import TrackerCreate, TrackerUpdate
from app.services.rss_source_service import RSSSourceService


class TrackerService:
    """封装 tracker 的增删改查与状态切换。"""

    @staticmethod
    def create(session: Session, data: TrackerCreate) -> TrackerTask:
        """创建任务并处理 RSS 关联。"""

        rss_source_ids = data.rss_source_ids
        tracker_data = data.model_dump(exclude={"rss_source_ids"})
        tracker = TrackerTask(**tracker_data)
        session.add(tracker)
        session.commit()
        session.refresh(tracker)

        if rss_source_ids and tracker.id is not None:
            RSSSourceService.set_tracker_sources(session, tracker.id, rss_source_ids)
            session.commit()

        return tracker

    @staticmethod
    def list(session: Session) -> list[TrackerTask]:
        """按创建时间倒序返回任务列表。"""

        return list(session.exec(select(TrackerTask).order_by(TrackerTask.created_at.desc())).all())

    @staticmethod
    def get(session: Session, tracker_id: int) -> TrackerTask | None:
        """按主键查询单个任务。"""

        return session.get(TrackerTask, tracker_id)

    @staticmethod
    def update(session: Session, tracker: TrackerTask, data: TrackerUpdate) -> TrackerTask:
        """更新任务可变字段、RSS 关联并刷新更新时间。"""

        update_data = data.model_dump(exclude_none=True)
        rss_source_ids = update_data.pop("rss_source_ids", None)

        for key, value in update_data.items():
            setattr(tracker, key, value)
        tracker.updated_at = datetime.now(timezone.utc)
        session.add(tracker)

        if rss_source_ids is not None and tracker.id is not None:
            RSSSourceService.set_tracker_sources(session, tracker.id, rss_source_ids)

        session.commit()
        session.refresh(tracker)
        return tracker

    @staticmethod
    def set_status(session: Session, tracker: TrackerTask, status: TrackerStatus) -> TrackerTask:
        """设置任务状态并刷新更新时间。"""

        tracker.status = status
        tracker.updated_at = datetime.now(timezone.utc)
        session.add(tracker)
        session.commit()
        session.refresh(tracker)
        return tracker

    @staticmethod
    def delete(session: Session, tracker: TrackerTask) -> None:
        """删除任务及其 RSS 关联。"""

        if tracker.id is not None:
            RSSSourceService.set_tracker_sources(session, tracker.id, [])
        session.delete(tracker)
        session.commit()
