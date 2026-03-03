"""Celery 任务：任务执行与任务分发。"""

from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

import redis
from redis.exceptions import LockNotOwnedError
from celery.utils.log import get_task_logger
from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.database import engine
from app.core.logging import bind_run_id, clear_run_id, setup_logging
from app.models.enums import TrackerStatus
from app.models.tracker import TrackerTask
from app.models.tracker_run_log import TrackerRunLog
from app.services.schedule_service import ScheduleService
from app.services.tracker_run_service import TrackerRunService
from app.workers.celery_app import celery_app

logger = get_task_logger(__name__)
setup_logging()

_TRACKER_LOCK_TIMEOUT = 600  # 10 分钟


def _compute_duration_ms(started_at: datetime, ended_at: datetime) -> int | None:
    """计算耗时，兼容可能出现的 naive/aware 时间对象。"""

    start = started_at
    end = ended_at
    if start.tzinfo is None and end.tzinfo is not None:
        start = start.replace(tzinfo=timezone.utc)
    if start.tzinfo is not None and end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    try:
        return max(0, int((end - start).total_seconds() * 1000))
    except Exception:
        return None


def _finish_run_log(
    session: Session,
    run_log: TrackerRunLog,
    *,
    status: str,
    message: str,
    error_type: str = "",
    payload: dict | None = None,
) -> None:
    """结束一条任务执行日志并提交。"""

    run_log.status = status
    run_log.message = message
    run_log.error_type = error_type
    ended_at = datetime.now(timezone.utc)
    run_log.ended_at = ended_at
    run_log.duration_ms = _compute_duration_ms(run_log.started_at, ended_at)
    run_log.payload = payload or {}
    session.add(run_log)
    session.commit()


def _finalize_running_log_if_needed(run_log_id: int | None, reason: str = "finalize_guard") -> None:
    """兜底收口仍处于 running 状态的日志，避免面板长期悬挂。"""

    if not run_log_id:
        return

    with Session(engine) as session:
        run_log = session.get(TrackerRunLog, run_log_id)
        if not run_log:
            return
        if run_log.status != "running" or run_log.ended_at is not None:
            return

        ended_at = datetime.now(timezone.utc)
        run_log.status = "failed"
        run_log.message = reason
        run_log.error_type = "RunFinalizeGuard"
        run_log.ended_at = ended_at
        run_log.duration_ms = _compute_duration_ms(run_log.started_at, ended_at)
        session.add(run_log)
        session.commit()


@celery_app.task(name="app.workers.tasks.run_tracker_once")
def run_tracker_once(tracker_id: int, force: bool = False) -> dict:
    """执行单个 tracker，并用分布式锁防止并发重复执行。"""

    run_id = str(uuid4())
    bind_run_id(run_id)
    started = perf_counter()
    run_log_id: int | None = None

    # 分布式锁：防止同一 tracker 在多 worker 并发执行。
    settings = get_settings()
    lock_client = redis.from_url(settings.redis_url)
    lock_key = f"opensentinel:tracker_lock:{tracker_id}"
    lock = lock_client.lock(lock_key, timeout=_TRACKER_LOCK_TIMEOUT)

    if not lock.acquire(blocking=False):
        with Session(engine) as session:
            run_log = TrackerRunLog(
                tracker_id=tracker_id,
                run_id=run_id,
                trigger="manual" if force else "schedule",
                force=force,
                status="skipped",
                message="already_running",
                error_type="AlreadyRunning",
                started_at=datetime.now(timezone.utc),
                ended_at=datetime.now(timezone.utc),
                duration_ms=0,
                payload={"reason": "already_running"},
            )
            session.add(run_log)
            session.commit()
            run_log_id = run_log.id
        logger.info("tracker %d is already running, skipping", tracker_id)
        clear_run_id()
        return {"ok": False, "reason": "already_running", "run_id": run_id}

    try:
        with Session(engine) as session:
            run_log = TrackerRunLog(
                tracker_id=tracker_id,
                run_id=run_id,
                trigger="manual" if force else "schedule",
                force=force,
                status="running",
                message="started",
                started_at=datetime.now(timezone.utc),
                payload={"tracker_id": tracker_id, "force": force},
            )
            session.add(run_log)
            session.commit()

            logger.info("tracker run started tracker_id=%d force=%s", tracker_id, force)

            tracker = session.get(TrackerTask, tracker_id)
            if not tracker:
                _finish_run_log(
                    session,
                    run_log,
                    status="failed",
                    message="tracker_not_found",
                    error_type="TrackerNotFound",
                    payload={"tracker_id": tracker_id},
                )
                return {"ok": False, "reason": "tracker_not_found", "run_id": run_id}
            if tracker.status != TrackerStatus.active and not force:
                _finish_run_log(
                    session,
                    run_log,
                    status="skipped",
                    message="tracker_not_active",
                    error_type="TrackerNotActive",
                    payload={"tracker_id": tracker_id, "status": tracker.status.value},
                )
                return {"ok": False, "reason": "tracker_not_active", "run_id": run_id}

            try:
                # last_run_at 在 TrackerRunService.run_once 成功提交时更新。
                result = TrackerRunService.run_once(session, tracker, force=force)
                _finish_run_log(
                    session,
                    run_log,
                    status="success",
                    message="completed",
                    payload=result,
                )
                logger.info(
                    "tracker run finished tracker_id=%d new_items=%s relevant_items=%s delivered=%s duration_ms=%d",
                    tracker_id,
                    result.get("new_items"),
                    result.get("relevant_items"),
                    result.get("delivered"),
                    int((perf_counter() - started) * 1000),
                )
                return {"ok": True, "run_id": run_id, **result}
            except Exception as exc:
                logger.exception("tracker run failed: %s", tracker_id)
                _finish_run_log(
                    session,
                    run_log,
                    status="failed",
                    message=str(exc),
                    error_type=exc.__class__.__name__,
                    payload={"tracker_id": tracker_id},
                )
                return {"ok": False, "reason": "run_failed", "error": str(exc), "run_id": run_id}
    finally:
        try:
            lock.release()
        except LockNotOwnedError:
            logger.warning("lock for tracker %d expired before release", tracker_id)
        _finalize_running_log_if_needed(run_log_id)
        clear_run_id()


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
    logger.info("dispatch finished scanned=%d dispatched=%d", len(trackers), dispatched)
    return {"ok": True, "dispatched": dispatched, "scanned": len(trackers)}
