"""事故管理业务规则：只声明本模块的字段与状态差异，取数/校验/流转走统一基类。"""
from __future__ import annotations

from app.services.base import BaseModuleService

MODULE = "accident"
REQUIRED_FIELDS = ["事故编号", "事故设备", "事故类型"]
STATUS_ORDER = ["待上报", "已上报", "调查中", "已结案"]
ACTION_RULES = {"上报事故": "已上报", "开展调查": "调查中", "结案归档": "已结案"}
NEGATIVE_ACTIONS = frozenset([])


class AccidentService(BaseModuleService):
    module = MODULE
    required_fields = tuple(REQUIRED_FIELDS)
    status_order = tuple(STATUS_ORDER)
    action_rules = dict(ACTION_RULES)
    negative_actions = NEGATIVE_ACTIONS
    entity_label = "事故记录"
