"""Celery 应用与 Beat 调度配置。"""

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "opensentinel",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# 统一使用 UTC，避免跨时区调度偏差。
celery_app.conf.timezone = "UTC"
# 周期性扫描活跃任务，并在任务内部按各自 schedule 决定是否执行。
celery_app.conf.beat_schedule = {
    "dispatch-active-trackers": {
        "task": "app.workers.tasks.dispatch_active_trackers",
        "schedule": crontab(minute=f"*/{settings.beat_scan_interval_minutes}"),
    }
}

# 自动发现 worker 任务函数。
celery_app.autodiscover_tasks(["app.workers"])
