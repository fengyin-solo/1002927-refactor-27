"""维保记录业务规则：只声明本模块的字段与状态差异，取数/校验/流转走统一基类。"""
from __future__ import annotations

from app.services.base import BaseModuleService

MODULE = "maintenance"
REQUIRED_FIELDS = ["维保编号", "维保设备", "维保单位"]
STATUS_ORDER = ["待维保", "维保中", "已完成", "需返工"]
ACTION_RULES = {"安排维保": "维保中", "开始维保": "已完成", "返工登记": "需返工"}
NEGATIVE_ACTIONS = frozenset([])


class MaintenanceService(BaseModuleService):
    module = MODULE
    required_fields = tuple(REQUIRED_FIELDS)
    status_order = tuple(STATUS_ORDER)
    action_rules = dict(ACTION_RULES)
    negative_actions = NEGATIVE_ACTIONS
    entity_label = "维保记录"
