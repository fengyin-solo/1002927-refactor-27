"""维保合同业务规则：只声明本模块的字段与状态差异，取数/校验/流转走统一基类。"""
from __future__ import annotations

from app.services.base import BaseModuleService

MODULE = "contract"
REQUIRED_FIELDS = ["合同编号", "签约单位", "维保范围"]
STATUS_ORDER = ["待签约", "执行中", "即将到期", "已终止"]
ACTION_RULES = {"签订合同": "执行中", "到期续签": "执行中", "终止合同": "已终止"}
NEGATIVE_ACTIONS = frozenset([])


class ContractService(BaseModuleService):
    module = MODULE
    required_fields = tuple(REQUIRED_FIELDS)
    status_order = tuple(STATUS_ORDER)
    action_rules = dict(ACTION_RULES)
    negative_actions = NEGATIVE_ACTIONS
    entity_label = "维保合同"
