"""稳定哈希工具。"""

import hashlib


def stable_hash(*parts: str) -> str:
    """对关键字段生成稳定 SHA-256 哈希。"""

    joined = "|".join([(p or "").strip().lower() for p in parts])
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()
