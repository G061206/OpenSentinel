"""调度判定服务测试。"""

from datetime import datetime, timezone

from app.services.schedule_service import ScheduleService


def test_schedule_first_run_is_due():
    """首次执行（last_run_at 为空）应判定为到期。"""

    now = datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc)
    assert ScheduleService.should_dispatch("*/15 * * * *", None, now=now) is True


def test_schedule_every_minutes_due():
    """every N minutes 表达式在时间到达后应触发。"""

    now = datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc)
    last = datetime(2026, 3, 1, 9, 40, tzinfo=timezone.utc)
    assert ScheduleService.should_dispatch("every 15 minutes", last, now=now) is True


def test_schedule_daily_not_due_yet():
    """daily HH:MM 在当天目标时间前不应触发。"""

    now = datetime(2026, 3, 1, 8, 30, tzinfo=timezone.utc)
    last = datetime(2026, 2, 28, 10, 0, tzinfo=timezone.utc)
    assert ScheduleService.should_dispatch("daily 09:00", last, now=now) is False
