"""调度表达式解析与到期判断服务。"""

import re
from datetime import datetime, timedelta, timezone

from croniter import croniter


class ScheduleService:
    """支持 cron 与自然语言简写的调度判定。"""

    CRON_PATTERN = re.compile(r"^\s*([^\s]+\s+){4}[^\s]+\s*$")
    EVERY_PATTERN = re.compile(r"^every\s+(\d+)\s+(minute|minutes|hour|hours)$", re.IGNORECASE)
    DAILY_PATTERN = re.compile(r"^daily\s+(\d{1,2}):(\d{2})$", re.IGNORECASE)
    CN_DAILY_PATTERN = re.compile(r"^每天\s*(\d{1,2})\s*点$")

    @staticmethod
    def should_dispatch(schedule: str, last_run_at: datetime | None, now: datetime | None = None) -> bool:
        """判断任务是否到达下次执行时间。"""

        now = now or datetime.now(timezone.utc)
        schedule = (schedule or "*/15 * * * *").strip()

        if last_run_at is None:
            return True

        if ScheduleService.CRON_PATTERN.match(schedule):
            next_time = croniter(schedule, last_run_at).get_next(datetime)
            return next_time <= now

        every_match = ScheduleService.EVERY_PATTERN.match(schedule)
        if every_match:
            value = int(every_match.group(1))
            unit = every_match.group(2).lower()
            delta = timedelta(minutes=value) if "minute" in unit else timedelta(hours=value)
            return last_run_at + delta <= now

        daily_match = ScheduleService.DAILY_PATTERN.match(schedule)
        if daily_match:
            hour = int(daily_match.group(1))
            minute = int(daily_match.group(2))
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target > now:
                return False
            return last_run_at < target

        cn_daily_match = ScheduleService.CN_DAILY_PATTERN.match(schedule)
        if cn_daily_match:
            hour = int(cn_daily_match.group(1))
            target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            if target > now:
                return False
            return last_run_at < target

        return last_run_at + timedelta(minutes=15) <= now
