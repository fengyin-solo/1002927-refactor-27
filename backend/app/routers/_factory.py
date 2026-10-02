"""模块路由工厂：20 个业务模块的 HTTP 形状完全一致，统一在这里生成。

- GET  ""           列表分页，取数范围与导出共用 build_scope
- GET  "/{id}"      明细
- POST ""           登记
- POST "/{id}/actions"  状态流转动作
- GET  "/export"    旧导出入口（保留兼容）：按统一口径返回同样的行集合，
                     新前端请使用 /api/exports 生成可续取、可回填的导出包
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.config import settings
from app.exporting.catalog import build_scope, require_spec
from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.base import BaseModuleService


def build_module_router(*, prefix: str, tag: str, service: BaseModuleService) -> APIRouter:
    module = service.module
    # 注册期即校验模块已在统一字段清单里登记，缺失时直接 fail fast。
    require_spec(module)
    router = APIRouter(prefix=prefix, tags=[tag])

    @router.get("", response_model=PageResult[dict])
    def list_entries(request: Request, page: int = 1, size: int = 20) -> PageResult[dict]:
        """按页面选中范围取列表；范围口径与导出完全一致。"""
        if size > settings.page_size_max:
            raise HTTPException(status_code=400, detail=f"每页最多 {settings.page_size_max} 条，请缩小分页范围")
        items, total = service.list_entries(
            query_params=request.query_params, page=page, size=size
        )
        return PageResult(items=items, total=total, page=page, size=size)

    @router.get("/export")
    def export_entries(request: Request) -> dict[str, Any]:
        """旧导出入口（兼容保留）：范围与字段投影都走统一取数口径。

        返回形状保持 {module,total,items} 不变；生成文件请改用 /api/exports。
        """
        scope = build_scope(module, request.query_params)
        items = service.fetch_scope(scope)
        return {"module": module, "total": len(items), "items": items}

    @router.get("/{entry_id}", response_model=dict)
    def get_entry(entry_id: int) -> dict:
        entry = service.get_entry(entry_id)
        if entry is None:
            raise HTTPException(
                status_code=404,
                detail=f"{service.entity_label} {entry_id} 不存在或已归档",
            )
        return entry

    @router.post("", response_model=ActionResult)
    def create_entry(payload: EntryPayload) -> ActionResult:
        entry, missing = service.create_entry(payload.values)
        if missing:
            return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
        return ActionResult(ok=True, message=f"{service.entity_label}已登记", entry=entry)

    @router.post("/{entry_id}/actions", response_model=ActionResult)
    def run_action(entry_id: int, payload: EntryPayload) -> ActionResult:
        action = str(payload.values.get("action") or "").strip()
        entry, message = service.run_action(entry_id, action)
        if entry is None:
            return ActionResult(ok=False, message=message)
        return ActionResult(ok=True, message=message, entry=entry)

    return router
