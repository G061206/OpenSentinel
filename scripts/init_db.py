"""本地初始化数据库表结构并迁移旧数据的脚本入口。"""

import app.models  # noqa: F401 — 确保所有模型注册到 metadata

from sqlmodel import Session

from app.core.database import engine, init_db
from app.models.llm_provider_model import LLMProviderConfig
from app.models.rss_source import RSSSource
from app.models.system_config import SystemConfig
from app.models.enums import LLMProviderType
from app.services.llm_provider_service import LLMProviderService


def migrate_from_system_config():
    """将旧 SystemConfig 中的 LLM 和 RSS 配置迁移到新表。"""

    with Session(engine) as session:
        # 读取旧配置
        from sqlmodel import select
        config = session.exec(select(SystemConfig).order_by(SystemConfig.id.asc())).first()
        if not config:
            print("  no system_config found, skip migration")
            return

        # 迁移 LLM Provider（如果新表为空）
        existing_providers = LLMProviderService.list(session)
        if not existing_providers and config.llm_provider and config.llm_provider != "mock":
            try:
                provider_type = LLMProviderType(config.llm_provider)
            except ValueError:
                provider_type = LLMProviderType.custom

            provider = LLMProviderConfig(
                name=f"迁移-{config.llm_provider}",
                provider_type=provider_type,
                api_key=config.llm_api_key or "",
                model=config.llm_model or "",
                is_default=True,
            )
            session.add(provider)
            session.commit()
            print(f"  migrated LLM provider: {config.llm_provider}")

        # 迁移全局 RSS 源
        if config.global_rss_urls:
            count = 0
            for url in config.global_rss_urls:
                url = url.strip()
                if not url:
                    continue
                existing = session.exec(select(RSSSource).where(RSSSource.url == url)).first()
                if existing:
                    continue
                source = RSSSource(
                    name=url.split("/")[-1] or url,
                    url=url,
                    category="全局迁移",
                )
                session.add(source)
                count += 1
            if count:
                session.commit()
                print(f"  migrated {count} global RSS sources")


if __name__ == "__main__":
    # 创建全部表
    init_db()
    print("database initialized")

    # 尝试迁移旧数据
    print("checking for data migration...")
    migrate_from_system_config()
    print("done")
