"""导出中心自检：取数口径、幂等、断点续取、存量回填。

直接跑：python tests/test_exporting.py
或被 pytest 收集：pytest tests/test_exporting.py
"""
from __future__ import annotations

import csv
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.exporting import fields  # noqa: E402
from app.exporting.jobs import JobStore  # noqa: E402
from app.exporting.service import ExportService  # noqa: E402
from app.services import SERVICES  # noqa: E402


def make_service(tmp: str) -> ExportService:
    return ExportService(JobStore(Path(tmp) / "exports"))


def read_csv(path: Path) -> list[list[str]]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return list(csv.reader(fh))


def test_headers_and_fill_rules() -> None:
    """表头顺序与声明一致；空值按目录里的填法补齐。"""
    with tempfile.TemporaryDirectory() as tmp:
        service = make_service(tmp)
        # 只填必填字段登记一条压力表，其余字段留空，检验填法
        entry, missing = SERVICES["gauge"].create_entry(
            {"压力表编号": "GAUG-9001", "所属设备": "自检设备", "量程范围": "0-1.6MPa"}
        )
        assert not missing and entry

        job = service.export("gauge")
        assert job.status == "done"
        rows = read_csv(service.jobs.final_path(job))
        assert rows[0] == fields.MODULE_FIELDS["gauge"], "表头顺序必须与原清单一致"

        last = dict(zip(rows[0], rows[-1]))
        assert last["压力表编号"] == "GAUG-9001"
        assert last["精度等级"] == "—", "文本空值填 —"
        assert last["检定日期"] == "", "日期空值填空串"
        assert last["仪表状态"] == "—"


def test_scope_matches_page_list() -> None:
    """导出范围与页面列表走同一份过滤：同条件条数必须一致。"""
    with tempfile.TemporaryDirectory() as tmp:
        service = make_service(tmp)
        for module, status in (("gauge", "待检定"), ("boiler", "检修中"), ("gauge", None)):
            job = service.export(module, status=status)
            rows = read_csv(service.jobs.final_path(job))
            _, expected = SERVICES[module].list_entries(status=status, page=1, size=100000)
            assert len(rows) - 1 == expected, f"{module} status={status} 导出条数与列表不一致"


def test_idempotent_same_batch() -> None:
    """同一批重复导出只生成一份；不同范围才算另一批。"""
    with tempfile.TemporaryDirectory() as tmp:
        service = make_service(tmp)
        first = service.export("boiler")
        second = service.export("boiler")
        assert first.id == second.id
        csvs = list((Path(tmp) / "exports").glob("*/**/*.csv"))
        assert len(csvs) == 1, "同一批只能有一份导出包"

        other = service.export("boiler", status="检修中")
        assert other.id != first.id, "范围不同就是另一批"
        assert len(service.jobs.all()) == 2


def test_resume_from_broken_row() -> None:
    """断在一半能从断掉的那一行接着取，最终文件完整、无重复行。"""
    import app.exporting.service as svc_module

    with tempfile.TemporaryDirectory() as tmp:
        service = make_service(tmp)
        _, expected_total = SERVICES["gauge"].list_entries(page=1, size=100000)
        old_chunk, old_write = svc_module.CHUNK_SIZE, ExportService._write_chunk
        calls = {"n": 0}

        def flaky_write(self, writer, headers, chunk):
            calls["n"] += 1
            if calls["n"] == 2:
                raise RuntimeError("模拟取数中断")
            return old_write(self, writer, headers, chunk)

        try:
            svc_module.CHUNK_SIZE = 2
            ExportService._write_chunk = flaky_write
            broken = service.export("gauge")
            assert broken.status == "failed"
            assert broken.cursor == 2, "第一块 2 行已落断点"
        finally:
            svc_module.CHUNK_SIZE = old_chunk
            ExportService._write_chunk = old_write

        # 换一个服务实例（模拟进程重启）再导同一批，应从断掉的那一行续取
        resumed = make_service(tmp).export("gauge")
        assert resumed.id == broken.id and resumed.status == "done"
        rows = read_csv(make_service(tmp).jobs.final_path(resumed))
        assert len(rows) - 1 == resumed.total == expected_total
        ids = [row[0] for row in rows[1:]]
        assert len(ids) == len(set(ids)), "续取不能重复写行"


def test_backfill_keeps_old_packages() -> None:
    """口径升级后存量导出按新口径回填；旧包字节不变、可重复回填。"""
    with tempfile.TemporaryDirectory() as tmp:
        service = make_service(tmp)
        old_job = service.export("gauge")
        old_path = service.jobs.final_path(old_job)
        old_bytes = old_path.read_bytes()

        fields.RULES_VERSION += 1  # 模拟口径调整
        try:
            renewed = service.backfill()
            assert len(renewed) == 1
            new_job = renewed[0]
            assert new_job.id != old_job.id and new_job.rules_version == fields.RULES_VERSION

            again = service.backfill()
            assert again == [], "已回填过的不能重复回填"

            assert old_path.read_bytes() == old_bytes, "旧导出包不能被改动"
            assert service.jobs.get(old_job.id).superseded_by == new_job.id
            assert service.jobs.final_path(new_job).exists()
        finally:
            fields.RULES_VERSION -= 1


def test_preview_json_same_rules() -> None:
    """JSON 预览与 CSV 导出同一份口径（兼容既有调用）。"""
    with tempfile.TemporaryDirectory() as tmp:
        service = make_service(tmp)
        items, total = service.preview("gauge")
        _, expected = SERVICES["gauge"].list_entries(page=1, size=100000)
        assert total == len(items) == expected
        assert set(items[0]) == set(fields.MODULE_FIELDS["gauge"])


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"\n{len(tests)} 项自检全部通过")
