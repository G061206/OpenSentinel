"""Worker 日志辅助函数测试。"""

from datetime import datetime, timezone

from app.workers.tasks import _compute_duration_ms


def test_compute_duration_ms_handles_mixed_tz():
    """started_at naive、ended_at aware 时也能返回耗时。"""

    started = datetime(2026, 3, 3, 10, 0, 0)
    ended = datetime(2026, 3, 3, 10, 0, 1, tzinfo=timezone.utc)
    duration = _compute_duration_ms(started, ended)
    assert duration is not None
    assert duration >= 1000
