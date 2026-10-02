"""导出端点：各模块的导出入口统一挂到导出中心，另加运维端点。

- bind_export_route：每个业务路由只调一次，导出入口即获得与页面列表
  相同的范围参数（keyword/status），取数走导出中心同一份实现；
- ops_router：导出任务列表、按任务下载（旧口径的包仍可下，不会被改）、
  存量回填。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse

from app.exporting.service import export_service

ops_router = APIRouter(prefix="/api/exports", tags=["导出中心"])


def bind_export_route(router: APIRouter, module: str) -> None:
    """给业务模块路由挂导出入口；要在 /{entry_id} 之前调用，避免被明细路由遮蔽。"""

    @router.get("/export", operation_id=f"export_{module}", summary="导出清单")
    def _export_entries(
        keyword: str | None = Query(default=None, description="按编号检索"),
        status: str | None = Query(default=None, description="按状态过滤"),
        format: str = Query(default="csv", description="csv 下载文件；json 兼容既有调用"),
    ) -> Any:
        try:
            job = export_service.export(module, keyword=keyword, status=status)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        if format == "json":
            items, total = export_service.preview(module, keyword=keyword, status=status)
            return {"module": module, "total": total, "items": items}
        if job.status != "done":
            return JSONResponse(
                status_code=202,
                content={
                    "job_id": job.id,
                    "status": job.status,
                    "cursor": job.cursor,
                    "message": f"导出中断于第 {job.cursor} 行，重新发起同一导出即可从断行续取",
                },
            )
        return FileResponse(
            export_service.jobs.final_path(job),
            filename=job.file_name,
            media_type="text/csv; charset=utf-8",
        )


@ops_router.get("")
def list_export_jobs() -> dict[str, Any]:
    """导出任务一览：哪些已完成、哪些断在一半、哪些还是旧口径。"""
    return {"jobs": [job.describe() for job in export_service.jobs.all()]}


@ops_router.post("/backfill")
def backfill_exports(module: str | None = Query(default=None, description="只回填某个模块；缺省全部")) -> dict[str, Any]:
    """把旧口径的存量导出按当前口径回填一遍；旧导出包保留不动。"""
    renewed = export_service.backfill(module)
    return {
        "ok": True,
        "renewed": [{"old_superseded": True, "job": job.describe()} for job in renewed],
    }


@ops_router.get("/{job_id}/download")
def download_export(job_id: str) -> FileResponse:
    """按任务下载导出包；历史口径的包也照常可下，内容不会被回填改动。"""
    job = export_service.jobs.get(job_id)
    if job is None or job.status != "done":
        raise HTTPException(status_code=404, detail=f"导出任务 {job_id} 不存在或尚未完成")
    return FileResponse(
        export_service.jobs.final_path(job),
        filename=job.file_name,
        media_type="text/csv; charset=utf-8",
    )
