"""培训考核业务规则：只声明本模块的字段与状态差异，取数/校验/流转走统一基类。"""
from __future__ import annotations

from app.services.base import BaseModuleService

MODULE = "training"
REQUIRED_FIELDS = ["培训编号", "培训内容", "培训对象"]
STATUS_ORDER = ["待培训", "培训中", "已考核", "已归档"]
ACTION_RULES = {"组织培训": "培训中", "组织考核": "已考核", "归档": "已归档"}
NEGATIVE_ACTIONS = frozenset([])


class TrainingService(BaseModuleService):
    module = MODULE
    required_fields = tuple(REQUIRED_FIELDS)
    status_order = tuple(STATUS_ORDER)
    action_rules = dict(ACTION_RULES)
    negative_actions = NEGATIVE_ACTIONS
    entity_label = "培训记录"
