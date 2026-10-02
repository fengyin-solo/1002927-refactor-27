"""培训考核接口：登记、筛选、状态流转走模块路由工厂，导出走统一 /api/exports。"""
from __future__ import annotations

from app.exporting.catalog import require_spec
from app.routers._factory import build_module_router
from app.services.training import TrainingService

service = TrainingService()

# 兼容旧引用：字段清单与表头以 app.exporting.catalog 为唯一维护点。
_spec = require_spec("training")
LIST_FIELDS = list(_spec.columns)
STATUSES = list(_spec.statuses)

router = build_module_router(
    prefix="/api/training",
    tag="培训考核",
    service=service,
)
