"""能效监测业务规则：只声明本模块的字段与状态差异，取数/校验/流转走统一基类。"""
from __future__ import annotations

from app.services.base import BaseModuleService

MODULE = "energyeff"
REQUIRED_FIELDS = ["记录编号", "设备类型", "耗能量"]
STATUS_ORDER = ["达标", "轻微偏差", "显著偏差", "已调整"]
ACTION_RULES = {"记录偏差": "轻微偏差", "分析原因": "显著偏差", "调整优化": "已调整"}
NEGATIVE_ACTIONS = frozenset([])


class EnergyeffService(BaseModuleService):
    module = MODULE
    required_fields = tuple(REQUIRED_FIELDS)
    status_order = tuple(STATUS_ORDER)
    action_rules = dict(ACTION_RULES)
    negative_actions = NEGATIVE_ACTIONS
    entity_label = "能效记录"
