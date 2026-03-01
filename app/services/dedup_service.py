"""去重服务。"""

from sqlmodel import Session, select

from app.models.raw_item import RawItem


class DedupService:
    """基于 URL 与稳定哈希进行基础去重。"""

    @staticmethod
    def filter_new_items(session: Session, tracker_id: int, normalized_items: list[dict]) -> list[dict]:
        """过滤已经存在的条目，仅返回新增证据。"""

        results: list[dict] = []
        for item in normalized_items:
            exists = session.exec(
                select(RawItem).where(
                    RawItem.tracker_id == tracker_id,
                    (RawItem.url == item["url"]) | (RawItem.stable_hash == item["stable_hash"]),
                )
            ).first()
            if not exists:
                results.append(item)
        return results
