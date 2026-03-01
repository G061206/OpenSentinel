"""API 与 Worker 共用的日志初始化。"""

import logging


def setup_logging() -> None:
    """配置带时间戳的统一日志格式。"""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
