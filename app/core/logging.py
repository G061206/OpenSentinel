"""API 与 Worker 共用的日志初始化与上下文工具。"""

from __future__ import annotations

import contextvars
import json
import logging
from datetime import datetime, timezone

from app.core.config import get_settings

_request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")
_run_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("run_id", default="")


class _ContextFilter(logging.Filter):
    """向每条日志注入 request_id 与 run_id。"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        record.run_id = get_run_id()
        return True


class _JsonFormatter(logging.Formatter):
    """输出结构化 JSON 日志，便于检索与聚合。"""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", ""),
            "run_id": getattr(record, "run_id", ""),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


def bind_request_id(request_id: str) -> None:
    """在当前上下文绑定 request_id。"""

    _request_id_var.set(request_id)


def clear_request_id() -> None:
    """清空当前上下文中的 request_id。"""

    _request_id_var.set("")


def get_request_id() -> str:
    """读取当前上下文 request_id。"""

    return _request_id_var.get()


def bind_run_id(run_id: str) -> None:
    """在当前上下文绑定 run_id。"""

    _run_id_var.set(run_id)


def clear_run_id() -> None:
    """清空当前上下文中的 run_id。"""

    _run_id_var.set("")


def get_run_id() -> str:
    """读取当前上下文 run_id。"""

    return _run_id_var.get()


def setup_logging() -> None:
    """按配置初始化统一日志格式（文本或 JSON）。"""

    settings = get_settings()
    level_name = (settings.log_level or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler()
    if settings.log_json:
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s [%(name)s] [request_id=%(request_id)s run_id=%(run_id)s] %(message)s"
            )
        )
    handler.addFilter(_ContextFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
