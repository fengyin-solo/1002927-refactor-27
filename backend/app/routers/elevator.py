"""电梯管理接口：维护电梯，覆盖安排维保、困人救援、故障检修等动作。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.exporting.routes import bind_export_route
from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.elevator import ElevatorService

router = APIRouter(prefix="/api/elevator", tags=["电梯管理"])

service = ElevatorService()

STATUSES = ["正常运行", "维保中", "困人", "检修中"]

bind_export_route(router, "elevator")


@router.get("", response_model=PageResult[dict])
def list_entries(
    keyword: str | None = Query(default=None, description="按电梯编号检索"),
    status: str | None = Query(default=None, description="正常运行、维保中、困人、检修中"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按电梯编号与状态过滤电梯管理列表；没有数据时返回空页，不报错。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    items, total = service.list_entries(keyword=keyword, status=status, page=page, size=size)
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条电梯明细；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"电梯 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记一条电梯，缺字段时说明原因而不是静默丢弃。"""
    entry, missing = service.create_entry(payload.values)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
    return ActionResult(ok=True, message="电梯已登记", entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: EntryPayload) -> ActionResult:
    """对单条电梯执行安排维保、困人救援、故障检修；不允许的动作会被拦下并说明原因。"""
    action = str(payload.values.get("action") or "").strip()
    entry, message = service.run_action(entry_id, action)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)

