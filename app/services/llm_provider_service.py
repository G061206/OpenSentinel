"""LLM Provider 管理服务。"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Session, select

from app.models.llm_provider_model import LLMProviderConfig
from app.schemas.llm_provider import LLMProviderCreate


class LLMProviderService:
    """封装 LLM Provider 的增删查与默认切换。"""

    @staticmethod
    def list(session: Session) -> list[LLMProviderConfig]:
        """按创建时间倒序返回 Provider 列表。"""

        return list(
            session.exec(select(LLMProviderConfig).order_by(LLMProviderConfig.created_at.desc())).all()
        )

    @staticmethod
    def get(session: Session, provider_id: int) -> LLMProviderConfig | None:
        """按主键查询单个 Provider。"""

        return session.get(LLMProviderConfig, provider_id)

    @staticmethod
    def get_default(session: Session) -> LLMProviderConfig | None:
        """读取默认 Provider；若未设置，回退到第一条。"""

        default = session.exec(
            select(LLMProviderConfig).where(LLMProviderConfig.is_default.is_(True))
        ).first()
        if default:
            return default
        return session.exec(select(LLMProviderConfig).order_by(LLMProviderConfig.id.asc())).first()

    @staticmethod
    def create(session: Session, data: LLMProviderCreate) -> LLMProviderConfig:
        """创建 Provider，必要时处理默认项唯一性。"""

        payload = data.model_dump()
        provider = LLMProviderConfig(**payload)

        existing = LLMProviderService.list(session)
        if not existing:
            provider.is_default = True

        if provider.is_default:
            for p in existing:
                if p.is_default:
                    p.is_default = False
                    p.updated_at = datetime.now(timezone.utc)
                    session.add(p)

        session.add(provider)
        session.commit()
        session.refresh(provider)
        return provider

    @staticmethod
    def set_default(session: Session, provider: LLMProviderConfig) -> LLMProviderConfig:
        """将指定 Provider 设为默认。"""

        providers = LLMProviderService.list(session)
        for p in providers:
            should_default = p.id == provider.id
            if p.is_default != should_default:
                p.is_default = should_default
                p.updated_at = datetime.now(timezone.utc)
                session.add(p)

        session.commit()
        session.refresh(provider)
        return provider

    @staticmethod
    def delete(session: Session, provider: LLMProviderConfig) -> None:
        """删除 Provider；若删除的是默认项则尝试补默认。"""

        deleting_default = provider.is_default
        provider_id = provider.id

        session.delete(provider)
        session.commit()

        if deleting_default and provider_id is not None:
            remaining = session.exec(select(LLMProviderConfig).order_by(LLMProviderConfig.id.asc())).first()
            if remaining:
                remaining.is_default = True
                remaining.updated_at = datetime.now(timezone.utc)
                session.add(remaining)
                session.commit()
