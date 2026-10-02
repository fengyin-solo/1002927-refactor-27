"""场车管理业务规则：只声明本模块的字段与状态差异，取数/校验/流转走统一基类。"""
from __future__ import annotations

from app.services.base import BaseModuleService

MODULE = "forklift"
REQUIRED_FIELDS = ["车辆编号", "车辆类型", "动力类型"]
STATUS_ORDER = ["正常", "维修中", "待年检", "已报废"]
ACTION_RULES = {"安排维修": "维修中", "安排年检": "待年检", "申请报废": "已报废"}
NEGATIVE_ACTIONS = frozenset([])


class ForkliftService(BaseModuleService):
    module = MODULE
    required_fields = tuple(REQUIRED_FIELDS)
    status_order = tuple(STATUS_ORDER)
    action_rules = dict(ACTION_RULES)
    negative_actions = NEGATIVE_ACTIONS
    entity_label = "场内车辆"
