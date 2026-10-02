"""电梯管理业务规则：只声明本模块的字段与状态差异，取数/校验/流转走统一基类。"""
from __future__ import annotations

from app.services.base import BaseModuleService

MODULE = "elevator"
REQUIRED_FIELDS = ["电梯编号", "电梯类型", "额定载重"]
STATUS_ORDER = ["正常运行", "维保中", "困人", "检修中"]
ACTION_RULES = {"安排维保": "维保中", "困人救援": "检修中", "故障检修": "正常运行"}
NEGATIVE_ACTIONS = frozenset([])


class ElevatorService(BaseModuleService):
    module = MODULE
    required_fields = tuple(REQUIRED_FIELDS)
    status_order = tuple(STATUS_ORDER)
    action_rules = dict(ACTION_RULES)
    negative_actions = NEGATIVE_ACTIONS
    entity_label = "电梯"
