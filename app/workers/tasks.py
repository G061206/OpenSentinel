"""Celery 任务：任务执行与任务分发。"""

from datetime import datetime, timezone

import redis
from redis.exceptions import LockNotOwnedError
from celery.utils.log import get_task_logger
from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.database import engine
from app.models.enums import TrackerStatus
from app.models.tracker import TrackerTask
from app.models.tracker_run_log import TrackerRunLog
from app.services.schedule_service import ScheduleService
from app.services.tracker_run_service import TrackerRunService
from app.workers.celery_app import celery_app

logger = get_task_logger(__name__)

_TRACKER_LOCK_TIMEOUT = 600  # 10 分钟


def _finish_run_log(
    session: Session,
    run_log: TrackerRunLog,
    *,
    status: str,
    message: str,
    payload: dict | None = None,
) -> None:
    """结束一条任务执行日志并提交。"""

    run_log.status = status
    run_log.message = message
    run_log.payload = payload or {}
    run_log.ended_at = datetime.now(timezone.utc)
    session.add(run_log)
    session.commit()


@celery_app.task(name="app.workers.tasks.run_tracker_once")
def run_tracker_once(tracker_id: int, force: bool = False) -> dict:
    """执行单个 tracker，并用分布式锁防止并发重复执行。"""

    # 分布式锁：防止同一 tracker 在多 worker 并发执行。
    settings = get_settings()
    lock_client = redis.from_url(settings.redis_url)
    lock_key = f"opensentinel:tracker_lock:{tracker_id}"
    lock = lock_client.lock(lock_key, timeout=_TRACKER_LOCK_TIMEOUT)

    if not lock.acquire(blocking=False):
        with Session(engine) as session:
            run_log = TrackerRunLog(
                tracker_id=tracker_id,
                trigger="manual" if force else "schedule",
                force=force,
                status="skipped",
                message="already_running",
                started_at=datetime.now(timezone.utc),
                ended_at=datetime.now(timezone.utc),
            )
            session.add(run_log)
            session.commit()
        logger.info("tracker %d is already running, skipping", tracker_id)
        return {"ok": False, "reason": "already_running"}

    try:
        with Session(engine) as session:
            run_log = TrackerRunLog(
                tracker_id=tracker_id,
                trigger="manual" if force else "schedule",
                force=force,
                status="running",
                message="started",
                started_at=datetime.now(timezone.utc),
            )
            session.add(run_log)
            session.commit()

            tracker = session.get(TrackerTask, tracker_id)
            if not tracker:
                _finish_run_log(
                    session,
                    run_log,
                    status="failed",
                    message="tracker_not_found",
                )
                return {"ok": False, "reason": "tracker_not_found"}
            if tracker.status != TrackerStatus.active and not force:
                _finish_run_log(
                    session,
                    run_log,
                    status="skipped",
                    message="tracker_not_active",
                )
                return {"ok": False, "reason": "tracker_not_active"}

            try:
                # last_run_at 在 TrackerRunService.run_once 成功提交时更新。
                result = TrackerRunService.run_once(session, tracker)
                _finish_run_log(
                    session,
                    run_log,
                    status="success",
                    message="completed",
                    payload=result,
                )
                logger.info("tracker run finished: %s", result)
                return {"ok": True, **result}
            except Exception as exc:
                logger.exception("tracker run failed: %s", tracker_id)
                _finish_run_log(
                    session,
                    run_log,
                    status="failed",
                    message=str(exc),
                )
                return {"ok": False, "reason": "run_failed", "error": str(exc)}
    finally:
        try:
            lock.release()
        except LockNotOwnedError:
            logger.warning("lock for tracker %d expired before release", tracker_id)


@celery_app.task(name="app.workers.tasks.dispatch_active_trackers")
def dispatch_active_trackers() -> dict:
    """扫描 active 任务，按各自 schedule 分发执行。"""

    now = datetime.now(timezone.utc)
    dispatched = 0
    with Session(engine) as session:
        trackers = list(session.exec(select(TrackerTask).where(TrackerTask.status == TrackerStatus.active)).all())
        for tracker in trackers:
            if ScheduleService.should_dispatch(tracker.schedule, tracker.last_run_at, now=now):
                run_tracker_once.delay(tracker.id)
                dispatched += 1
    return {"ok": True, "dispatched": dispatched, "scanned": len(trackers)}
