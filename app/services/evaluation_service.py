"""事件等级评估服务。"""

from app.models.enums import EventLevel

# 用数值顺序比较等级高低。
_LEVEL_ORDER: dict[EventLevel, int] = {
    EventLevel.NORMAL: 0,
    EventLevel.WATCH: 1,
    EventLevel.ELEVATED: 2,
    EventLevel.CRISIS: 3,
    EventLevel.CONFIRMED: 4,
}


class EvaluationService:
    @staticmethod
    def evaluate(
        alert_rules: dict,
        new_items: list[dict],
        previous_level: EventLevel = EventLevel.NORMAL,
    ) -> EventLevel:
        """根据新增证据评估事件等级。

        系统只自动升级，不自动降级；降级需由人工重置任务。
        """
        confirmed_threshold = int(alert_rules.get("confirmed_threshold", 6))
        crisis_threshold = int(alert_rules.get("crisis_threshold", 4))
        elevated_threshold = int(alert_rules.get("elevated_threshold", 2))

        n = len(new_items)
        if n >= confirmed_threshold:
            new_level = EventLevel.CONFIRMED
        elif n >= crisis_threshold:
            new_level = EventLevel.CRISIS
        elif n >= elevated_threshold:
            new_level = EventLevel.ELEVATED
        elif n >= 1:
            new_level = EventLevel.WATCH
        else:
            new_level = EventLevel.NORMAL

        # 等级仅允许自动上升，不自动下降。
        if _LEVEL_ORDER.get(new_level, 0) > _LEVEL_ORDER.get(previous_level, 0):
            return new_level
        return previous_level
