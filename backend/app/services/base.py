"""业务模块服务基类：列表筛选、登记、状态流转的公共写法只保留一份。

各模块服务只声明差异常量（模块名、必填字段、状态序列、动作规则），
取数范围与字段投影统一走 app.exporting.catalog，保证列表页与导出同口径。
"""
from __future__ import annotations

from typing import Any

from app.exporting.catalog import Scope, build_scope, project_rows, select_rows
from app.store import store


class BaseModuleService:
    module: str = ""
    required_fields: tuple[str, ...] = ()
    status_order: tuple[str, ...] = ()
    action_rules: dict[str, str] = {}
    negative_actions: frozenset[str] = frozenset()
    # 登记成功/动作成功时的称呼，如"压力表已登记"。
    entity_label: str = "记录"

    def list_entries(
        self,
        *,
        query_params: Any = None,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        """按页面选中的范围取数并分页。

        query_params 是原始查询参数（Request.query_params 或字典），
        与导出入口使用同一个 build_scope，字段筛选行为完全一致。
        显式传入的 keyword/status 保留给旧调用方，优先级最低。
        """
        if query_params is not None:
            scope = build_scope(self.module, query_params)
        else:
            scope = build_scope(self.module, {"keyword": keyword or "", "status": status or ""})
        rows = select_rows(scope)
        total = len(rows)
        start = max(page - 1, 0) * size
        page_rows = rows[start:start + size]
        return [self._attach_id(raw, projected) for raw, projected in zip(page_rows, project_rows(self.module, page_rows))], total

    def fetch_scope(self, scope: Scope) -> list[dict[str, Any]]:
        """导出/回填用：按统一范围取全量并投影（内部行 id 一并带回，不写入导出文件）。"""
        raw_rows = select_rows(scope)
        return [
            self._attach_id(raw, projected)
            for raw, projected in zip(raw_rows, project_rows(self.module, raw_rows))
        ]

    @staticmethod
    def _attach_id(raw: dict[str, Any], projected: dict[str, Any]) -> dict[str, Any]:
        """列表接口要靠 id 执行动作；导出时按表头列写出，id 不会进入文件。"""
        return {"id": raw.get("id"), **projected}

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        return store.find(self.module, entry_id)

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in self.required_fields if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        rows = store.rows(self.module)
        entry: dict[str, Any] = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry.update({field: values.get(field) for field in self.required_fields})
        entry["status"] = self.status_order[0]
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)
        return entry, []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(self.module, entry_id)
        if entry is None:
            return None, f"{self.entity_label} {entry_id} 不存在或已归档"
        if action not in self.action_rules:
            return None, f"动作「{action}」不属于{self.entity_label}可执行范围"
        target = self.action_rules[action]
        if target not in self.status_order:
            return None, f"目标状态「{target}」不在允许的状态序列里"
        entry["status"] = target
        entry["pending"] = target != self.status_order[-1]
        entry["abnormal"] = action in self.negative_actions
        return entry, f"{self.entity_label}已{action}"
