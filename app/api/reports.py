"""报告查询 API。"""

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.api.deps import get_db_session
from app.models.report import Report

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.get("")
def list_reports(tracker_id: int | None = None, session: Session = Depends(get_db_session)):
    """按时间倒序返回报告列表，可按 tracker_id 过滤。"""

    stmt = select(Report).order_by(Report.created_at.desc())
    if tracker_id is not None:
        stmt = stmt.where(Report.tracker_id == tracker_id)
    reports = list(session.exec(stmt).all())
    return reports
