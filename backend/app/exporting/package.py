"""导出包序列化：把投影后的行写成兼容既有模板的 CSV 文件。

只用标准库；UTF-8 BOM 让 Excel 直接打开不乱码。表头顺序严格沿用模块声明，
文件名沿用各模块既有的《xxx清单》命名，外部系统和老模板不受影响。
"""
from __future__ import annotations

import csv
import io
from typing import Any

from app.exporting.catalog import ModuleSpec


def render_csv(spec: ModuleSpec, rows: list[dict[str, Any]]) -> bytes:
    """按模块表头顺序渲染导出内容；行内缺失值已在取数层统一回填。"""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(spec.columns), extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({name: row.get(name, "") for name in spec.columns})
    # utf-8-sig：Excel 打开既有模板时靠 BOM 识别中文编码。
    return buffer.getvalue().encode("utf-8-sig")


def package_name(spec: ModuleSpec, suffix: str = "csv") -> str:
    return f"{spec.file_stem}.{suffix}"
