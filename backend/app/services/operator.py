"""作业人员业务规则：只声明本模块的字段与状态差异，取数/校验/流转走统一基类。"""
from __future__ import annotations

from app.services.base import BaseModuleService

MODULE = "operator"
REQUIRED_FIELDS = ["人员编号", "姓名", "证书类别"]
STATUS_ORDER = ["持证有效", "即将到期", "已过期", "已注销"]
ACTION_RULES = {"安排复审": "持证有效", "登记过期": "已过期", "注销证书": "已注销"}
NEGATIVE_ACTIONS = frozenset([])


class OperatorService(BaseModuleService):
    module = MODULE
    required_fields = tuple(REQUIRED_FIELDS)
    status_order = tuple(STATUS_ORDER)
    action_rules = dict(ACTION_RULES)
    negative_actions = NEGATIVE_ACTIONS
    entity_label = "作业人员"
