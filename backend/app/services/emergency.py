"""应急演练业务规则：只声明本模块的字段与状态差异，取数/校验/流转走统一基类。"""
from __future__ import annotations

from app.services.base import BaseModuleService

MODULE = "emergency"
REQUIRED_FIELDS = ["演练编号", "演练主题", "演练类型"]
STATUS_ORDER = ["待组织", "已组织", "已完成", "已复盘"]
ACTION_RULES = {"组织演练": "已组织", "完成演练": "已完成", "复盘总结": "已复盘"}
NEGATIVE_ACTIONS = frozenset([])


class EmergencyService(BaseModuleService):
    module = MODULE
    required_fields = tuple(REQUIRED_FIELDS)
    status_order = tuple(STATUS_ORDER)
    action_rules = dict(ACTION_RULES)
    negative_actions = NEGATIVE_ACTIONS
    entity_label = "演练记录"
