"""导出取数：全平台唯一一份实现。

各模块导出入口、页面选中范围、存量回填都走这里：
- 范围过滤复用各模块服务的 list_entries，与页面列表是同一条取数路径；
- 字段投影与空值填法来自 exporting.fields 的唯一目录；
- 分块写盘、每块落一次断点，中断后从断掉的那一行接着取；
- 签名 = 模块 + 范围 + 口径版本 + 字段清单，同一批重复导出只生成一份。
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections.abc import Iterator
from typing import Any

from app.exporting import fields
from app.exporting.jobs import ExportJob, JobStore
from app.services import SERVICES

# 每块行数：写盘与落断点的粒度，也是断点续取的对齐单位。
CHUNK_SIZE = 200


def build_signature(module: str, filters: dict[str, Any]) -> str:
    payload = {
        "module": module,
        "filters": filters,
        "rules_version": fields.RULES_VERSION,
        "fields": fields.MODULE_FIELDS[module],
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


class ExportService:
    def __init__(self, store: JobStore | None = None) -> None:
        self._store = store or JobStore()

    @property
    def jobs(self) -> JobStore:
        return self._store

    # ---- 对外入口 ----
    def export(self, module: str, *, keyword: str | None = None, status: str | None = None) -> ExportJob:
        """幂等入口：同一批（同模块、同范围、同口径）重复导出只生成一份。"""
        self._check_module(module)
        filters = {"keyword": keyword or None, "status": status or None}
        signature = build_signature(module, filters)
        job, _created = self._store.get_or_create(
            module=module,
            filters=filters,
            signature=signature,
            rules_version=fields.RULES_VERSION,
            file_name=fields.MODULE_FILE_NAMES[module],
        )
        return self._run(job)

    def preview(self, module: str, *, keyword: str | None = None, status: str | None = None) -> tuple[list[dict[str, Any]], int]:
        """不落盘地按同一口径取数，给需要 JSON 的既有调用方用。"""
        self._check_module(module)
        headers = fields.headers_for(module)
        rows = [self._project(row, headers) for row in self._iter_source_rows(module, keyword, status)]
        return rows, len(rows)

    def backfill(self, module: str | None = None) -> list[ExportJob]:
        """把旧口径的存量导出按当前口径重跑一遍；旧导出包保留不动。

        只处理已完成且尚未被回填过的任务；新包落在新的任务目录里，
        旧任务记 superseded_by 指向新任务。可重复调用，不会重复回填。
        """
        renewed: list[ExportJob] = []
        for job in self._store.all():
            if module is not None and job.module != module:
                continue
            if job.status != "done" or job.rules_version >= fields.RULES_VERSION or job.superseded_by:
                continue
            new_job = self.export(job.module, **job.filters)
            self._store.mark_superseded(job.id, new_job.id)
            renewed.append(new_job)
        return renewed

    # ---- 取数与投影（唯一一份） ----
    def _iter_source_rows(self, module: str, keyword: str | None, status: str | None) -> Iterator[dict[str, Any]]:
        service = SERVICES[module]
        page = 1
        while True:
            items, _total = service.list_entries(keyword=keyword, status=status, page=page, size=CHUNK_SIZE)
            if not items:
                return
            yield from items
            if len(items) < CHUNK_SIZE:
                return
            page += 1

    def _project(self, row: dict[str, Any], headers: list[str]) -> dict[str, Any]:
        return {field: self._value(row, field) for field in headers}

    def _value(self, row: dict[str, Any], field: str) -> Any:
        value = row.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            return fields.spec_for(field).empty_value
        return value

    # ---- 执行：分块写盘 + 断点续取 ----
    def _run(self, job: ExportJob) -> ExportJob:
        with self._store.lock_for(job.id):
            if job.status == "done":
                return job
            job.status = "running"
            job.error = None
            try:
                self._truncate_to_cursor(job)
                self._consume(job)
                self._store.part_path(job).replace(self._store.final_path(job))
                job.status = "done"
                job.finished_at = job.finished_at or self._now()
            except Exception as exc:  # 断在一半：断点已落盘，下次同批导出从这里续
                job.status = "failed"
                job.error = str(exc)
            self._store.save(job)
            return job

    def _consume(self, job: ExportJob) -> None:
        headers = fields.headers_for(job.module)
        keyword = job.filters.get("keyword")
        status = job.filters.get("status")
        part = self._store.part_path(job)
        fresh = job.cursor == 0
        with part.open("a" if not fresh else "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.writer(fh)
            if fresh:
                writer.writerow(headers)
            written = job.cursor
            source = self._iter_source_rows(job.module, keyword, status)
            to_skip = written
            while True:
                chunk = []
                for row in source:
                    if to_skip:
                        to_skip -= 1
                        continue
                    chunk.append(row)
                    if len(chunk) >= CHUNK_SIZE:
                        break
                if not chunk:
                    break
                self._write_chunk(writer, headers, chunk)
                written += len(chunk)
                job.cursor = written
                job.last_id = int(chunk[-1].get("id", job.last_id or 0))
                self._store.save(job)  # 每块落一次断点
                if len(chunk) < CHUNK_SIZE:
                    break
            job.total = written

    def _write_chunk(self, writer: Any, headers: list[str], chunk: list[dict[str, Any]]) -> None:
        for row in chunk:
            writer.writerow([self._value(row, field) for field in headers])

    def _truncate_to_cursor(self, job: ExportJob) -> None:
        """续取前把 part 截到断点位置：断点之后可能躺着没来得及确认的行。"""
        part = self._store.part_path(job)
        if not part.exists():
            job.cursor = 0
            return
        with part.open(newline="", encoding="utf-8-sig") as fh:
            rows = list(csv.reader(fh))
        keep = 1 + job.cursor  # 表头 + 已确认写盘的数据行
        if len(rows) <= keep:
            return
        with part.open("w", newline="", encoding="utf-8-sig") as fh:
            csv.writer(fh).writerows(rows[:keep])

    # ---- 杂项 ----
    def _check_module(self, module: str) -> None:
        if module not in fields.MODULE_FIELDS:
            raise KeyError(f"模块「{module}」没有登记导出字段")
        if module not in SERVICES:
            raise KeyError(f"模块「{module}」没有注册业务服务")

    def _now(self) -> str:
        from datetime import datetime

        return datetime.now().isoformat(timespec="seconds")


export_service = ExportService()
