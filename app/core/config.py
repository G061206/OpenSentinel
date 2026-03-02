"""从环境变量加载应用配置。"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """统一管理 API、数据库、队列和外部集成配置。"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "OpenSentinel"
    app_env: str = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"
    log_json: bool = False

    database_url: str = "sqlite:///./opensentinel.db"
    redis_url: str = "redis://localhost:6379/0"

    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    beat_scan_interval_minutes: int = 15

    default_fetch_timeout_seconds: int = 20
    default_retry_times: int = 3
    default_rate_limit_per_source: int = 5

    llm_provider: str = "mock"
    llm_api_key: str = ""
    llm_timeout_seconds: int = 25

    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4o-mini"
    openrouter_app_url: str = "https://example.com"

    bailian_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    bailian_api_key: str = ""
    bailian_model: str = "qwen-plus"

    wecom_webhook_url: str = ""
    wecom_message_format: str = "text"


@lru_cache
def get_settings() -> Settings:
    """返回缓存后的配置对象，避免重复解析环境变量。"""

    return Settings()
