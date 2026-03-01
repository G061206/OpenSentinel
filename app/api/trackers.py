"""Tracker 管理 API。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.api.deps import get_db_session
from app.models.enums import TrackerStatus
from app.schemas.tracker import ActionResponse, TrackerCreate, TrackerRead, TrackerUpdate
from app.services.tracker_service import TrackerService
from app.workers.tasks import run_tracker_once

router = APIRouter(prefix="/api/v1/trackers", tags=["trackers"])


@router.post("", response_model=TrackerRead)
def create_tracker(payload: TrackerCreate, session: Session = Depends(get_db_session)):
    """创建跟踪任务。"""

    return TrackerService.create(session, payload)


@router.get("", response_model=list[TrackerRead])
def list_trackers(session: Session = Depends(get_db_session)):
    """返回全部任务列表。"""

    return TrackerService.list(session)


@router.get("/{tracker_id}", response_model=TrackerRead)
def get_tracker(tracker_id: int, session: Session = Depends(get_db_session)):
    """读取单个任务详情。"""

    tracker = TrackerService.get(session, tracker_id)
    if not tracker:
        raise HTTPException(status_code=404, detail="tracker not found")
    return tracker


@router.patch("/{tracker_id}", response_model=TrackerRead)
def update_tracker(tracker_id: int, payload: TrackerUpdate, session: Session = Depends(get_db_session)):
    """更新任务字段。"""

    tracker = TrackerService.get(session, tracker_id)
    if not tracker:
        raise HTTPException(status_code=404, detail="tracker not found")
    return TrackerService.update(session, tracker, payload)


@router.post("/{tracker_id}/pause", response_model=TrackerRead)
def pause_tracker(tracker_id: int, session: Session = Depends(get_db_session)):
    """暂停任务。"""

    tracker = TrackerService.get(session, tracker_id)
    if not tracker:
        raise HTTPException(status_code=404, detail="tracker not found")
    return TrackerService.set_status(session, tracker, TrackerStatus.paused)


@router.post("/{tracker_id}/resume", response_model=TrackerRead)
def resume_tracker(tracker_id: int, session: Session = Depends(get_db_session)):
    """恢复任务。"""

    tracker = TrackerService.get(session, tracker_id)
    if not tracker:
        raise HTTPException(status_code=404, detail="tracker not found")
    return TrackerService.set_status(session, tracker, TrackerStatus.active)


@router.post("/{tracker_id}/run", response_model=ActionResponse)
def run_tracker_now(tracker_id: int, session: Session = Depends(get_db_session)):
    """手动立即触发一次执行（强制执行）。"""

    tracker = TrackerService.get(session, tracker_id)
    if not tracker:
        raise HTTPException(status_code=404, detail="tracker not found")
    if tracker.id is None:
        raise HTTPException(status_code=400, detail="tracker id invalid")
    run_tracker_once.delay(tracker.id, force=True)
    return ActionResponse(ok=True, message="run task dispatched")


@router.delete("/{tracker_id}", response_model=ActionResponse)
def delete_tracker(tracker_id: int, session: Session = Depends(get_db_session)):
    """删除任务。"""

    tracker = TrackerService.get(session, tracker_id)
    if not tracker:
        raise HTTPException(status_code=404, detail="tracker not found")
    TrackerService.delete(session, tracker)
    return ActionResponse(ok=True, message="tracker deleted")
