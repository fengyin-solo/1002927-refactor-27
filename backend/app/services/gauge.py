"""压力表检定业务规则：只声明本模块的字段与状态差异，取数/校验/流转走统一基类。"""
from __future__ import annotations

from app.services.base import BaseModuleService

MODULE = "gauge"
REQUIRED_FIELDS = ["压力表编号", "所属设备", "量程范围"]
STATUS_ORDER = ["检定合格", "即将到期", "待检定", "已停用"]
ACTION_RULES = {"安排检定": "待检定", "登记合格": "检定合格", "办理停用": "已停用"}
NEGATIVE_ACTIONS = frozenset([])


class GaugeService(BaseModuleService):
    module = MODULE
    required_fields = tuple(REQUIRED_FIELDS)
    status_order = tuple(STATUS_ORDER)
    action_rules = dict(ACTION_RULES)
    negative_actions = NEGATIVE_ACTIONS
    entity_label = "压力表"
