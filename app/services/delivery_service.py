"""消息投递服务。"""

from app.adapters.wecom_webhook import markdown_to_text, send_markdown, send_text
from app.core.config import get_settings


class DeliveryService:
    """把报告投递到外部通知渠道。"""

    @staticmethod
    def deliver(delivery_channels: dict, markdown: str) -> bool:
        """读取渠道配置并按格式发送企业微信消息。"""

        settings = get_settings()
        wecom_url = delivery_channels.get("wecom_webhook_url", "")
        message_format = (delivery_channels.get("wecom_message_format") or settings.wecom_message_format).lower()

        if message_format == "markdown":
            return send_markdown(wecom_url, markdown)

        # 默认走 text，提升在普通微信中的可读性。
        return send_text(wecom_url, markdown_to_text(markdown))
