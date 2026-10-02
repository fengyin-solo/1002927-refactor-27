"""导出任务存储：每个导出批次的元数据、断点与产物文件。

目录布局（默认 backend/var/exports）：
    <job_id>/meta.json    任务元数据与断点 cursor，每写一块落一次
    <job_id>/data.part    写入中的 CSV；完成后原子改名为正式文件
    <job_id>/<file_name>  正式导出包，落地后不再改动（回填会另起新版本目录）

job_id 由模块与签名派生，同一批（同模块、同范围、同口径版本）永远落到同一个
任务目录，重复导出只生成一份。
"""
from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[2] / "var" / "exports"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class ExportJob:
    """一次导出批次：cursor 是断点，记录已确认写盘的数据行数（不含表头）。"""

    id: str
    module: str
    filters: dict[str, Any]
    signature: str
    rules_version: int
    file_name: str
    status: str = "running"  # running / done / failed
    cursor: int = 0
    last_id: int | None = None  # 已写入的最后一行业务 id，换数据库后可按 id 续取
    total: int | None = None
    error: str | None = None
    superseded_by: str | None = None  # 回填后指向新口径任务，旧包本身不动
    created_at: str = field(default_factory=_now)
    finished_at: str | None = None

    def describe(self) -> dict[str, Any]:
        return asdict(self)


class JobStore:
    """任务目录的读写与索引；进程内缓存，落盘用写临时文件再改名。"""

    def __init__(self, base_dir: Path | str = BASE_DIR) -> None:
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._run_locks: dict[str, threading.Lock] = {}
        self._jobs: dict[str, ExportJob] = {}
        self._by_signature: dict[str, str] = {}
        self._load()

    # ---- 目录与文件 ----
    def job_dir(self, job: ExportJob) -> Path:
        return self._base / job.id

    def part_path(self, job: ExportJob) -> Path:
        return self.job_dir(job) / "data.part"

    def final_path(self, job: ExportJob) -> Path:
        return self.job_dir(job) / job.file_name

    # ---- 查询 ----
    def get(self, job_id: str) -> ExportJob | None:
        return self._jobs.get(job_id)

    def all(self) -> list[ExportJob]:
        return sorted(self._jobs.values(), key=lambda job: job.created_at)

    def lock_for(self, job_id: str) -> threading.Lock:
        with self._lock:
            return self._run_locks.setdefault(job_id, threading.Lock())

    # ---- 写入 ----
    def get_or_create(
        self,
        *,
        module: str,
        filters: dict[str, Any],
        signature: str,
        rules_version: int,
        file_name: str,
    ) -> tuple[ExportJob, bool]:
        """按签名取任务；没有才建。同一批重复导出只会有这一条任务。"""
        with self._lock:
            job_id = self._by_signature.get(signature)
            if job_id is not None:
                return self._jobs[job_id], False
            job = ExportJob(
                id=f"{module}-{signature[:12]}",
                module=module,
                filters=filters,
                signature=signature,
                rules_version=rules_version,
                file_name=file_name,
            )
            self._jobs[job.id] = job
            self._by_signature[signature] = job.id
            self.job_dir(job).mkdir(parents=True, exist_ok=True)
            self.save(job)
            return job, True

    def save(self, job: ExportJob) -> None:
        self.job_dir(job).mkdir(parents=True, exist_ok=True)
        tmp = self.job_dir(job) / "meta.json.tmp"
        tmp.write_text(json.dumps(job.describe(), ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.job_dir(job) / "meta.json")

    def mark_superseded(self, old_id: str, new_id: str) -> None:
        old = self._jobs[old_id]
        old.superseded_by = new_id
        self.save(old)

    # ---- 启动时重建索引 ----
    def _load(self) -> None:
        for meta in sorted(self._base.glob("*/meta.json")):
            try:
                payload = json.loads(meta.read_text(encoding="utf-8"))
                job = ExportJob(**payload)
            except (TypeError, ValueError):
                continue
            self._jobs[job.id] = job
            self._by_signature[job.signature] = job.id
