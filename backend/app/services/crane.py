"""起重机械业务规则：只声明本模块的字段与状态差异，取数/校验/流转走统一基类。"""
from __future__ import annotations

from app.services.base import BaseModuleService

MODULE = "crane"
REQUIRED_FIELDS = ["起重机编号", "起重机类型", "额定起重量"]
STATUS_ORDER = ["正常", "超载运行", "检验中", "已停用"]
ACTION_RULES = {"降载运行": "超载运行", "安排检验": "检验中", "办理停用": "已停用"}
NEGATIVE_ACTIONS = frozenset([])


class CraneService(BaseModuleService):
    module = MODULE
    required_fields = tuple(REQUIRED_FIELDS)
    status_order = tuple(STATUS_ORDER)
    action_rules = dict(ACTION_RULES)
    negative_actions = NEGATIVE_ACTIONS
    entity_label = "起重机"
