"""档案管理业务规则：只声明本模块的字段与状态差异，取数/校验/流转走统一基类。"""
from __future__ import annotations

from app.services.base import BaseModuleService

MODULE = "archive"
REQUIRED_FIELDS = ["档案编号", "所属设备", "档案类别"]
STATUS_ORDER = ["在库", "借出中", "已归还", "已销毁"]
ACTION_RULES = {"办理借阅": "借出中", "登记归还": "在库", "申请销毁": "已销毁"}
NEGATIVE_ACTIONS = frozenset([])


class ArchiveService(BaseModuleService):
    module = MODULE
    required_fields = tuple(REQUIRED_FIELDS)
    status_order = tuple(STATUS_ORDER)
    action_rules = dict(ACTION_RULES)
    negative_actions = NEGATIVE_ACTIONS
    entity_label = "设备档案"
