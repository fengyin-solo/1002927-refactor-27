"""导出批次：断点续取、同批去重、存量回填都在这里收口。

批次（job）记录一份导出的"取数口径"——模块 + 范围参数（Scope.cache_key），
以及已经取到第几行（cursor）。规则：

1. 同一批重复导出只生成一份：以 (module, scope_key, 回填代次) 作为幂等键，
   已完成的批次直接复用，不重新取数、不重复落盘。
2. 取数断在一半可从断掉的那一行接着取：每次只取一个分片，cursor 记录已取
   行数（有序行集合上的偏移），taken_ids 记录已取的原始行 id 做去重保险；
   中途失败已落盘的行不重取。
3. 旧的导出包不再改动：批次一旦 done，其文件内容只读；换口径后的存量回填
   走"回填代次（backfill_generation）"，为老批次生成新一代的包，老包保留。

批次与导出包落盘到 settings.export_dir（默认 var/exports），重启不丢。
当前数据仓库是内存实现，续取时按相同 scope 重新选行、用 cursor 里的已取 id
集合去重，保证接着取而不是从头来。
"""
from __future__ import annotations

import csv
import io
import json
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from app.config import settings
from app.exporting.catalog import (
    ModuleSpec,
    Scope,
    build_scope,
    project_rows,
    require_spec,
    select_rows,
)
from app.exporting.package import package_name, render_csv

#: 单个分片取多少行；取数中断后最多重取这一个分片。
DEFAULT_CHUNK_SIZE = 500

#: 当前取数口径代次。口径调整（字段清单/填法/范围变化）时 +1，
#: 用于区分"按老口径导出的存量包"和"按新口径回填的包"。
CURRENT_GENERATION = 1


@dataclass
class ExportJob:
    id: str
    module: str
    scope_key: str
    scope_params: dict[str, str]
    status: str = "running"  # running / done / failed
    total: int = 0
    cursor: int = 0  # 已写入的行数（也是下一分片的起始偏移）
    chunk_size: int = DEFAULT_CHUNK_SIZE
    generation: int = CURRENT_GENERATION
    backfill_of: str | None = None  # 回填时指向原批次 id
    file_name: str = ""
    error: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    # 已取原始行 id，断点重取时跳过；空列表表示尚未取过。
    taken_ids: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ExportJobStore:
    """批次持久化 + 内存索引。线程锁保证同一批并发导出只落一份。"""

    def __init__(self, export_dir: Path | None = None) -> None:
        self.root = (export_dir or Path(settings.export_dir)).resolve()
        self.jobs_dir = self.root / "jobs"
        self.files_dir = self.root / "files"
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.files_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._jobs: dict[str, ExportJob] = {}
        self._index: dict[tuple[str, str, int], str] = {}
        self._load()

    # ------------------------------------------------------------------ #
    # 持久化
    # ------------------------------------------------------------------ #
    def _job_path(self, job_id: str) -> Path:
        return self.jobs_dir / f"{job_id}.json"

    def _load(self) -> None:
        for path in sorted(self.jobs_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                job = ExportJob(**data)
            except (TypeError, ValueError):
                continue
            self._jobs[job.id] = job
            if job.status == "done":
                self._index[self._idem_key(job)] = job.id

    def _save(self, job: ExportJob) -> None:
        job.updated_at = time.time()
        self._job_path(job.id).write_text(
            json.dumps(job.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _idem_key(job: ExportJob) -> tuple[str, str, int]:
        # 同模块 + 同范围 + 同口径代次即"同一批"，回填批次只是带了来源标记，
        # 不再另开一份普通导出（同一批重复导出只生成一份）。
        return job.module, job.scope_key, job.generation

    # ------------------------------------------------------------------ #
    # 查询
    # ------------------------------------------------------------------ #
    def get(self, job_id: str) -> ExportJob | None:
        return self._jobs.get(job_id)

    def require(self, job_id: str) -> ExportJob:
        job = self.get(job_id)
        if job is None:
            raise KeyError(f"导出批次 {job_id} 不存在")
        return job

    def list_jobs(self, module: str | None = None) -> list[ExportJob]:
        jobs = self._jobs.values()
        if module:
            jobs = [job for job in jobs if job.module == module]
        return sorted(jobs, key=lambda job: job.created_at, reverse=True)

    def file_path(self, job: ExportJob) -> Path:
        return self.files_dir / job.id / job.file_name

    # ------------------------------------------------------------------ #
    # 创建 / 续取
    # ------------------------------------------------------------------ #
    def open_or_resume(
        self,
        module: str,
        scope: Scope,
        *,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        backfill_of: str | None = None,
        generation: int = CURRENT_GENERATION,
    ) -> ExportJob:
        """按幂等键打开批次：同一批重复导出直接返回既有批次。

        - 已完成：原样返回（只生成一份）。
        - 取数中断（running/failed）：返回该批次，随后可继续取下一分片。
        - 新范围：建立新批次并把表头与全量计数写好。
        """
        spec = require_spec(module)
        idem = (module, scope.cache_key(), generation)
        with self._lock:
            existing_id = self._index.get(idem)
            if existing_id:
                existing = self.require(existing_id)
                # 代次/口径可能已漂移（如批次被回填升级），命中陈旧索引时不沿用。
                if self._idem_key(existing) == idem:
                    return existing
                self._index.pop(idem, None)
            # running/failed 的同口径批次也要复用，保证断了以后接着取。
            for job in self._jobs.values():
                if self._idem_key(job) == idem and job.status in {"running", "failed"}:
                    return job

            rows = select_rows(scope)
            job = ExportJob(
                id=self._new_id(module),
                module=module,
                scope_key=scope.cache_key(),
                scope_params=dict(scope.field_filters) | {
                    "keyword": scope.keyword or "",
                    "status": scope.status or "",
                },
                total=len(rows),
                chunk_size=max(1, min(chunk_size, 5000)),
                generation=generation,
                backfill_of=backfill_of,
                file_name=package_name(spec),
            )
            self._init_file(spec, job)
            self._jobs[job.id] = job
            self._save(job)
            return job

    def fetch_chunk(self, job_id: str) -> ExportJob:
        """取一个分片并追加写入；可反复调用直到 status == done。"""
        with self._lock:
            job = self.require(job_id)
            if job.status == "done":
                return job
            spec = require_spec(job.module)
            scope = build_scope(job.module, job.scope_params)
            try:
                rows = select_rows(scope)
                if job.total != len(rows):
                    # 范围行数漂移（数据新增）时以当前快照为准，续取仍然不重复。
                    job.total = len(rows)
                taken = set(job.taken_ids)
                # 行集合按 id 有序、续取只追加，cursor 就是全集中的偏移；
                # taken 作去重保险，避免异常重试把同一行写两遍。
                window = rows[job.cursor: job.cursor + job.chunk_size]
                chunk = [row for row in window if int(row.get("id", 0)) not in taken]
                projected = project_rows(job.module, chunk)
                self._append_rows(job, projected)
                job.taken_ids.extend(int(row.get("id", 0)) for row in chunk)
                job.cursor += len(chunk)
                if job.cursor >= job.total:
                    job.status = "done"
                    self._index[self._idem_key(job)] = job.id
                self._save(job)
            except Exception as exc:  # 断在一半：保留进度，标记失败待续取
                job.status = "failed"
                job.error = str(exc)
                self._save(job)
            return job

    def run_to_end(self, job_id: str, *, max_chunks: int = 10000) -> ExportJob:
        """循环取完整个批次（后台/脚本回填用）；同样尊重断点。"""
        job = self.require(job_id)
        rounds = 0
        while job.status != "done" and rounds < max_chunks:
            job = self.fetch_chunk(job_id)
            rounds += 1
        return job

    # ------------------------------------------------------------------ #
    # 存量回填：旧包不动，按新口径生成新一代
    # ------------------------------------------------------------------ #
    def backfill(self, module: str | None = None) -> list[ExportJob]:
        """对所有老代次的已完成批次按当前口径重新取数生成新包。

        旧批次文件只读不改；新批次 backfill_of 指向旧批次。已回填过的不重复生成。
        """
        sources = [
            job for job in self.list_jobs(module)
            if job.status == "done"
            and job.backfill_of is None
            and job.generation < CURRENT_GENERATION
        ]
        # 已经有新一代包的原始批次不再重复回填；回填批次自身也不会再次回填。
        backfilled_sources = {
            job.backfill_of
            for job in self._jobs.values()
            if job.backfill_of and job.generation >= CURRENT_GENERATION
        }
        created: list[ExportJob] = []
        for old in sources:
            if old.id in backfilled_sources:
                continue
            scope = build_scope(old.module, old.scope_params)
            new_job = self.open_or_resume(
                old.module,
                scope,
                backfill_of=old.id,
                generation=CURRENT_GENERATION,
            )
            created.append(self.run_to_end(new_job.id))
        return created

    # ------------------------------------------------------------------ #
    # 文件写入
    # ------------------------------------------------------------------ #
    def _new_id(self, module: str) -> str:
        stamp = time.strftime("%Y%m%d%H%M%S")
        suffix = f"{threading.get_ident() % 10000:04d}"
        candidate = f"{module}-{stamp}-{suffix}"
        serial = 1
        while candidate in self._jobs:
            serial += 1
            candidate = f"{module}-{stamp}-{suffix}-{serial}"
        return candidate

    def _init_file(self, spec: ModuleSpec, job: ExportJob) -> None:
        target_dir = self.files_dir / job.id
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / job.file_name).write_bytes(render_csv(spec, []))

    def _append_rows(self, job: ExportJob, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        path = self.file_path(job)
        spec = require_spec(job.module)
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=list(spec.columns))
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in spec.columns})
        with path.open("ab") as handle:
            handle.write(buffer.getvalue().encode("utf-8"))


job_store = ExportJobStore()
