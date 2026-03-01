"""系统配置管理服务。"""

from datetime import datetime, timezone

from sqlmodel import Session, select

from app.models.system_config import SystemConfig


class SystemConfigService:
    """提供系统配置的读取与更新能力。"""

    @staticmethod
    def get_or_create(session: Session) -> SystemConfig:
        """读取第一条系统配置，不存在则创建默认配置。"""

        config = session.exec(select(SystemConfig).order_by(SystemConfig.id.asc())).first()
        if config:
            return config

        config = SystemConfig()
        session.add(config)
        session.commit()
        session.refresh(config)
        return config

    @staticmethod
    def update(
        session: Session,
        *,
        llm_provider: str,
        llm_api_key: str,
        llm_model: str,
        global_rss_urls: list[str],
    ) -> SystemConfig:
        """更新系统配置并返回最新记录。"""

        config = SystemConfigService.get_or_create(session)
        config.llm_provider = (llm_provider or "mock").strip() or "mock"
        config.llm_api_key = (llm_api_key or "").strip()
        config.llm_model = (llm_model or "").strip()
        config.global_rss_urls = global_rss_urls
        config.updated_at = datetime.now(timezone.utc)
        session.add(config)
        session.commit()
        session.refresh(config)
        return config
