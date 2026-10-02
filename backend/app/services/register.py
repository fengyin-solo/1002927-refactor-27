"""使用登记业务规则：只声明本模块的字段与状态差异，取数/校验/流转走统一基类。"""
from __future__ import annotations

from app.services.base import BaseModuleService

MODULE = "register"
REQUIRED_FIELDS = ["设备编号", "设备名称", "设备种类"]
STATUS_ORDER = ["待登记", "已登记", "停用中", "已注销"]
ACTION_RULES = {"办理登记": "已登记", "申请停用": "停用中", "申请注销": "已注销"}
NEGATIVE_ACTIONS = frozenset([])


class RegisterService(BaseModuleService):
    module = MODULE
    required_fields = tuple(REQUIRED_FIELDS)
    status_order = tuple(STATUS_ORDER)
    action_rules = dict(ACTION_RULES)
    negative_actions = NEGATIVE_ACTIONS
    entity_label = "设备登记"
