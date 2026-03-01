"""内容归一化服务。"""

from app.services.hash_service import stable_hash


class NormalizationService:
    """清洗原始内容并输出统一结构。"""

    @staticmethod
    def normalize(raw_items: list[dict]) -> list[dict]:
        """生成标准字段并计算 stable_hash。"""

        normalized = []
        for item in raw_items:
            title = (item.get("title") or "").strip()
            content = (item.get("content") or "").strip()
            url = (item.get("url") or "").strip()
            if not url:
                continue
            normalized.append(
                {
                    "source_type": item.get("source_type", "unknown"),
                    "source_name": item.get("source_name", "unknown"),
                    "url": url,
                    "title": title,
                    "content": content,
                    "published_at": item.get("published_at"),
                    "stable_hash": stable_hash(url, title, content[:500]),
                }
            )
        return normalized
