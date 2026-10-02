"""存量导出回填脚本：换过取数口径后，把已导出的存量批次按新口径重取一遍。

用法（后端目录下）：
    python -m app.scripts.backfill             # 回填所有模块
    python -m app.scripts.backfill gauge       # 只回填指定模块

旧的导出包不会被改动，回填结果是带 backfill_of 标记的新一代导出包，
与接口 POST /api/exports/backfill 走同一套逻辑。
"""
from __future__ import annotations

import sys

from app.exporting.jobs import CURRENT_GENERATION, job_store


def main(argv: list[str]) -> int:
    module = argv[1] if len(argv) > 1 else None
    print(f"当前取数口径代次：{CURRENT_GENERATION}")
    created = job_store.backfill(module)
    if not created:
        print("没有需要回填的存量导出（或已全部回填过）。")
        return 0
    for job in created:
        print(f"  {job.module}: {job.id} <- {job.backfill_of}，{job.cursor}/{job.total} 行，文件：{job.file_name}")
    print(f"回填完成，共生成 {len(created)} 份新口径导出包；旧导出包保持原样。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
