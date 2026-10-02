"""备件管理业务规则：只声明本模块的字段与状态差异，取数/校验/流转走统一基类。"""
from __future__ import annotations

from app.services.base import BaseModuleService

MODULE = "sparepart"
REQUIRED_FIELDS = ["备件编号", "备件名称", "规格型号"]
STATUS_ORDER = ["充足", "不足", "待采购", "已停用"]
ACTION_RULES = {"办理领用": "不足", "采购入仓": "充足", "停用备件": "已停用"}
NEGATIVE_ACTIONS = frozenset(["停用备件"])


class SparepartService(BaseModuleService):
    module = MODULE
    required_fields = tuple(REQUIRED_FIELDS)
    status_order = tuple(STATUS_ORDER)
    action_rules = dict(ACTION_RULES)
    negative_actions = NEGATIVE_ACTIONS
    entity_label = "备件"
