"""安全阀校验业务规则：只声明本模块的字段与状态差异，取数/校验/流转走统一基类。"""
from __future__ import annotations

from app.services.base import BaseModuleService

MODULE = "safetyvalve"
REQUIRED_FIELDS = ["安全阀编号", "所属设备", "公称通径"]
STATUS_ORDER = ["校验合格", "即将到期", "待校验", "已报废"]
ACTION_RULES = {"安排校验": "待校验", "登记合格": "校验合格", "申请报废": "已报废"}
NEGATIVE_ACTIONS = frozenset([])


class SafetyvalveService(BaseModuleService):
    module = MODULE
    required_fields = tuple(REQUIRED_FIELDS)
    status_order = tuple(STATUS_ORDER)
    action_rules = dict(ACTION_RULES)
    negative_actions = NEGATIVE_ACTIONS
    entity_label = "安全阀"
