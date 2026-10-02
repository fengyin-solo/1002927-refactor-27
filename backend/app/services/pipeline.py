"""压力管道业务规则：只声明本模块的字段与状态差异，取数/校验/流转走统一基类。"""
from __future__ import annotations

from app.services.base import BaseModuleService

MODULE = "pipeline"
REQUIRED_FIELDS = ["管道编号", "管道级别", "设计压力"]
STATUS_ORDER = ["正常", "壁厚减薄", "待检验", "已报废"]
ACTION_RULES = {"记录减薄": "壁厚减薄", "安排检验": "待检验", "申请报废": "已报废"}
NEGATIVE_ACTIONS = frozenset([])


class PipelineService(BaseModuleService):
    module = MODULE
    required_fields = tuple(REQUIRED_FIELDS)
    status_order = tuple(STATUS_ORDER)
    action_rules = dict(ACTION_RULES)
    negative_actions = NEGATIVE_ACTIONS
    entity_label = "压力管道"
