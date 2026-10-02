"""锅炉管理业务规则：只声明本模块的字段与状态差异，取数/校验/流转走统一基类。"""
from __future__ import annotations

from app.services.base import BaseModuleService

MODULE = "boiler"
REQUIRED_FIELDS = ["锅炉编号", "锅炉型号", "额定蒸发量"]
STATUS_ORDER = ["正常运行", "低负荷", "检修中", "已停炉"]
ACTION_RULES = {"降负荷运行": "低负荷", "停炉检修": "检修中", "恢复运行": "正常运行"}
NEGATIVE_ACTIONS = frozenset([])


class BoilerService(BaseModuleService):
    module = MODULE
    required_fields = tuple(REQUIRED_FIELDS)
    status_order = tuple(STATUS_ORDER)
    action_rules = dict(ACTION_RULES)
    negative_actions = NEGATIVE_ACTIONS
    entity_label = "锅炉"
