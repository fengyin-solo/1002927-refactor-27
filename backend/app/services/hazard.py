"""隐患排查业务规则：只声明本模块的字段与状态差异，取数/校验/流转走统一基类。"""
from __future__ import annotations

from app.services.base import BaseModuleService

MODULE = "hazard"
REQUIRED_FIELDS = ["隐患编号", "所在设备", "隐患类别"]
STATUS_ORDER = ["待整改", "整改中", "待验收", "已消除"]
ACTION_RULES = {"安排整改": "整改中", "开始整改": "待验收", "验收消除": "已消除"}
NEGATIVE_ACTIONS = frozenset([])


class HazardService(BaseModuleService):
    module = MODULE
    required_fields = tuple(REQUIRED_FIELDS)
    status_order = tuple(STATUS_ORDER)
    action_rules = dict(ACTION_RULES)
    negative_actions = NEGATIVE_ACTIONS
    entity_label = "隐患记录"
