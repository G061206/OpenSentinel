"""企业微信群机器人 Webhook 适配器。"""

import re

import httpx


def send_markdown(webhook_url: str, content: str, timeout_seconds: int = 10) -> bool:
    """发送 markdown 消息到企业微信群机器人。"""

    if not webhook_url:
        return False

    payload = {
        "msgtype": "markdown",
        "markdown": {"content": content},
    }
    with httpx.Client(timeout=timeout_seconds) as client:
        response = client.post(webhook_url, json=payload)
    return response.status_code == 200


def markdown_to_text(content: str) -> str:
    """把 markdown 报告转换为普通文本，兼容普通微信显示。"""

    text = content or ""
    # [title](url) -> title url
    text = re.sub(r"\[([^\]]+)\]\(([^\)]+)\)", r"\1 \2", text)
    # 去掉标题标记与粗体标记
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = text.replace("**", "")
    # 压缩多余空行
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def send_text(webhook_url: str, content: str, timeout_seconds: int = 10) -> bool:
    """发送 text 消息到企业微信群机器人。"""

    if not webhook_url:
        return False

    payload = {
        "msgtype": "text",
        "text": {"content": content},
    }
    with httpx.Client(timeout=timeout_seconds) as client:
        response = client.post(webhook_url, json=payload)
    return response.status_code == 200
