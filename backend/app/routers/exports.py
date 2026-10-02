"""统一导出入口：创建/续取批次、下载导出包、查询批次、存量回填。

范围参数与列表页完全一致（keyword/status/前三个字段名），由前端把页面上
选中的条件原样带过来，走的是 build_scope 这同一份取数口径。
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse

from app.exporting.catalog import MODULE_SPECS, build_scope, require_spec
from app.exporting.jobs import DEFAULT_CHUNK_SIZE, job_store

router = APIRouter(prefix="/api/exports", tags=["统一导出"])

_PUBLIC_JOB_FIELDS = (
    "id", "module", "status", "total", "cursor", "generation", "backfill_of",
    "file_name", "error", "created_at", "updated_at", "scope_params",
)


def _job_view(job) -> dict[str, object]:
    data = {name: getattr(job, name) for name in _PUBLIC_JOB_FIELDS}
    data["done"] = job.status == "done"
    data["download_url"] = f"/api/exports/{job.id}/download"
    return data


@router.get("/modules")
def list_export_modules() -> dict[str, object]:
    """各模块的导出声明：文件名、表头顺序、可筛选字段、状态集合。前端按此渲染。"""
    return {
        "modules": [
            {
                "module": spec.key,
                "label": spec.label,
                "file_name": spec.file_stem + ".csv",
                "columns": list(spec.columns),
                "filter_fields": list(spec.filter_fields),
                "statuses": list(spec.statuses),
                "keyword_field": spec.keyword_field,
            }
            for spec in MODULE_SPECS.values()
        ]
    }


@router.post("")
def create_export(
    request: Request,
    module: str = Query(..., description="业务模块标识，与 /api/{module} 一致"),
    chunk_size: int = Query(default=DEFAULT_CHUNK_SIZE, ge=1, le=5000),
) -> dict[str, object]:
    """按页面选中范围建立（或复用）导出批次并取第一个分片。

    同模块同范围重复调用只返回同一批次；未取完时继续调用
    POST /api/exports/{job_id}/resume 从断掉的行接着取。
    """
    require_spec(module)
    scope = build_scope(module, request.query_params)
    job = job_store.open_or_resume(module, scope, chunk_size=chunk_size)
    if job.status != "done":
        job = job_store.fetch_chunk(job.id)
    return _job_view(job)


@router.post("/{job_id}/resume")
def resume_export(job_id: str) -> dict[str, object]:
    """从断点再取一个分片；已完成则原样返回。"""
    try:
        job = job_store.require(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    return _job_view(job_store.fetch_chunk(job.id))


@router.get("/{job_id}")
def get_export(job_id: str) -> dict[str, object]:
    try:
        job = job_store.require(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    return _job_view(job)


@router.get("")
def list_exports(module: str | None = None) -> dict[str, object]:
    """已生成的导出批次（含老批次与回填批次）。"""
    return {"jobs": [_job_view(job) for job in job_store.list_jobs(module)]}


@router.get("/{job_id}/download")
def download_export(job_id: str) -> FileResponse:
    """下载导出包；老批次文件保持原样，回填批次是另一份新文件。"""
    try:
        job = job_store.require(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    if job.status != "done":
        raise HTTPException(status_code=409, detail="导出尚未完成，请先续取到完成再下载")
    path = job_store.file_path(job)
    if not path.exists():
        raise HTTPException(status_code=410, detail="导出包文件已被移除，无法下载")
    return FileResponse(
        path,
        media_type="text/csv; charset=utf-8",
        filename=job.file_name,
    )


@router.post("/backfill")
def backfill_exports(module: str | None = Query(default=None)) -> dict[str, object]:
    """换口径后对存量已导出批次按新口径回填：老包不动，另生成新一代导出包。"""
    if module is not None:
        require_spec(module)
    created = job_store.backfill(module)
    return {
        "backfilled": len(created),
        "jobs": [_job_view(job) for job in created],
    }
