"""多信源采集服务。"""

import logging

from tenacity import Retrying, stop_after_attempt, wait_fixed

from app.adapters.rss import fetch_rss
from app.adapters.webpage import fetch_webpage
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class IngestionService:
    @staticmethod
    def collect(source_profile: dict, extra_rss_urls: list[str] | None = None) -> list[dict]:
        """从 source_profile 中定义的信源采集内容。

        重试粒度是单个 URL，这样某个信源失败不会影响其他已成功
        的采集结果，也不会导致全量重拉。
        """
        settings = get_settings()
        retrier = Retrying(
            stop=stop_after_attempt(settings.default_retry_times),
            wait=wait_fixed(1),
            reraise=True,
        )
        items: list[dict] = []
        rss_urls = list(source_profile.get("rss_urls", []))
        if extra_rss_urls:
            rss_urls.extend(extra_rss_urls)
        # 去重并保持顺序，避免同一 RSS 重复抓取。
        rss_urls = list(dict.fromkeys([url for url in rss_urls if url]))

        for rss_url in rss_urls:
            try:
                fetched = retrier(fetch_rss, rss_url)
                for item in fetched:
                    items.append(item.__dict__)
            except Exception:
                logger.exception("Failed to fetch RSS after retries: %s", rss_url)

        for web_url in source_profile.get("web_urls", []):
            try:
                item = retrier(
                    fetch_webpage, web_url, timeout_seconds=settings.default_fetch_timeout_seconds
                )
                if item:
                    items.append(item.__dict__)
            except Exception:
                logger.exception("Failed to fetch webpage after retries: %s", web_url)

        return items
