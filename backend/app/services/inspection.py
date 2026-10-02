"""定期检验业务规则：只声明本模块的字段与状态差异，取数/校验/流转走统一基类。"""
from __future__ import annotations

from app.services.base import BaseModuleService

MODULE = "inspection"
REQUIRED_FIELDS = ["检验编号", "被检设备", "检验类别"]
STATUS_ORDER = ["待检验", "检验中", "合格", "不合格"]
ACTION_RULES = {"安排检验": "检验中", "录入结论": "合格", "下达整改": "不合格"}
NEGATIVE_ACTIONS = frozenset([])


class InspectionService(BaseModuleService):
    module = MODULE
    required_fields = tuple(REQUIRED_FIELDS)
    status_order = tuple(STATUS_ORDER)
    action_rules = dict(ACTION_RULES)
    negative_actions = NEGATIVE_ACTIONS
    entity_label = "检验任务"
