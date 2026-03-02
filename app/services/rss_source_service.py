"""RSS 信源管理服务。"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Session, delete, func, select

from app.models.rss_source import RSSSource
from app.models.tracker_rss_link import TrackerRSSLink
from app.schemas.rss_source import RSSSourceCreate


class RSSSourceService:
    """封装 RSS 信源与 Tracker 关联管理。"""

    @staticmethod
    def list(session: Session) -> list[RSSSource]:
        """按创建时间倒序返回 RSS 源列表。"""

        return list(session.exec(select(RSSSource).order_by(RSSSource.created_at.desc())).all())

    @staticmethod
    def get(session: Session, source_id: int) -> RSSSource | None:
        """按主键读取单个 RSS 源。"""

        return session.get(RSSSource, source_id)

    @staticmethod
    def create(session: Session, data: RSSSourceCreate) -> RSSSource:
        """创建 RSS 源，URL 已存在时复用已有记录。"""

        clean_url = (data.url or "").strip()
        existing = session.exec(select(RSSSource).where(RSSSource.url == clean_url)).first()
        if existing:
            return existing

        source = RSSSource(
            name=(data.name or clean_url).strip() or clean_url,
            url=clean_url,
            category=(data.category or "").strip(),
        )
        session.add(source)
        session.commit()
        session.refresh(source)
        return source

    @staticmethod
    def bulk_create(session: Session, bulk_urls: str, category: str = "") -> int:
        """批量创建 RSS 源并返回新增数量。"""

        created = 0
        for raw in bulk_urls.replace(",", "\n").splitlines():
            url = raw.strip()
            if not url:
                continue
            existing = session.exec(select(RSSSource).where(RSSSource.url == url)).first()
            if existing:
                continue
            source = RSSSource(
                name=url.split("/")[-1] or url,
                url=url,
                category=(category or "").strip(),
            )
            session.add(source)
            created += 1

        if created:
            session.commit()
        return created

    @staticmethod
    def get_sources_for_tracker(session: Session, tracker_id: int) -> list[RSSSource]:
        """返回某个 Tracker 关联的 RSS 源。"""

        stmt = (
            select(RSSSource)
            .join(TrackerRSSLink, TrackerRSSLink.rss_source_id == RSSSource.id)
            .where(TrackerRSSLink.tracker_id == tracker_id)
            .order_by(RSSSource.created_at.desc())
        )
        return list(session.exec(stmt).all())

    @staticmethod
    def set_tracker_sources(session: Session, tracker_id: int, source_ids: list[int]) -> None:
        """覆盖设置 Tracker 的 RSS 源关联。"""

        valid_ids = list(dict.fromkeys([sid for sid in source_ids if sid > 0]))

        session.exec(delete(TrackerRSSLink).where(TrackerRSSLink.tracker_id == tracker_id))

        if valid_ids:
            existing_ids = set(
                session.exec(select(RSSSource.id).where(RSSSource.id.in_(valid_ids))).all()  # type: ignore[arg-type]
            )
            for sid in valid_ids:
                if sid in existing_ids:
                    session.add(TrackerRSSLink(tracker_id=tracker_id, rss_source_id=sid))

        session.commit()

    @staticmethod
    def get_reference_count(session: Session, source_id: int | None) -> int:
        """统计某个 RSS 源被多少 Tracker 引用。"""

        if not source_id:
            return 0
        count = session.exec(
            select(func.count()).select_from(TrackerRSSLink).where(TrackerRSSLink.rss_source_id == source_id)
        ).one()
        return int(count or 0)

    @staticmethod
    def delete(session: Session, source: RSSSource) -> None:
        """删除 RSS 源并清理其关联记录。"""

        if source.id is not None:
            session.exec(delete(TrackerRSSLink).where(TrackerRSSLink.rss_source_id == source.id))
        source.updated_at = datetime.now(timezone.utc)
        session.delete(source)
        session.commit()
