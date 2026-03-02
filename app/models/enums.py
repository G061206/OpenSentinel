"""跟踪任务与报告使用的领域枚举。"""

from enum import Enum


class TrackerStatus(str, Enum):
    """跟踪任务生命周期状态。"""

    active = "active"
    paused = "paused"
    archived = "archived"


class EventLevel(str, Enum):
    """事件升级级别。"""

    NORMAL = "NORMAL"
    WATCH = "WATCH"
    ELEVATED = "ELEVATED"
    CRISIS = "CRISIS"
    CONFIRMED = "CONFIRMED"


class LLMProviderType(str, Enum):
    """LLM 提供商类型。"""

    mock = "mock"
    openai = "openai"
    openrouter = "openrouter"
    bailian = "bailian"
    anthropic = "anthropic"
    custom = "custom"
