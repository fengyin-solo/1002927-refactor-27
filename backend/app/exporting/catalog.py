"""导出取数口径：字段清单、空值填法、范围筛选与表头顺序只维护这一份。

- FieldSpec 描述一个字段怎么取、空值怎么填；字段清单全平台唯一。
- ModuleSpec 描述一个业务模块用哪些字段、按什么文件模板导出。
- select_rows / project_rows 是列表页与导出入口共用的同一份取数写法，
  页面选中的范围和导出走的是同一个 scope，不会再出现条数对不上的情况。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from app.store import store

#: 空值统一填法：None、空串、纯空白都按缺失处理，导出模板里一律填这个占位。
EMPTY_PLACEHOLDER = "—"


@dataclass(frozen=True)
class FieldSpec:
    """一个导出字段的取数与填法。字段清单只在这里维护一次。"""

    name: str
    empty: str = EMPTY_PLACEHOLDER
    # 取数键与展示字段不一致时（例如状态列），在这里声明源键。
    source: str | None = None
    # 该字段允许按页面输入做等值/包含筛选。
    filterable: bool = True

    def read(self, row: dict[str, Any]) -> Any:
        value = row.get(self.source or self.name)
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return value

    def fill(self, row: dict[str, Any]) -> Any:
        """按统一口径填值：缺失（None/空串/纯空白）回填占位符。"""
        value = self.read(row)
        return self.empty if value is None else value

    def matches(self, row: dict[str, Any], needle: str) -> bool:
        value = self.read(row)
        return value is not None and needle in str(value)


@dataclass(frozen=True)
class ModuleSpec:
    """业务模块只声明自己用哪些字段、模板文件叫什么，不再各写一套取数。"""

    key: str
    label: str
    # 表头顺序即既有导出模板的列顺序，改动顺序会破坏模板兼容，不要随意调整。
    columns: tuple[str, ...]
    keyword_field: str
    # 既有导出文件名：保持不变，兼容老的下载链接与外部系统约定。
    file_stem: str
    filter_fields: tuple[str, ...] = ()
    statuses: tuple[str, ...] = ()
    sheet_title: str = ""

    @property
    def fields(self) -> list[FieldSpec]:
        return [FIELD_REGISTRY[name] for name in self.columns]


# 状态列在数据行里的源键是 status，展示表头各模块不同，因此单独登记。
def _status_field(header: str) -> FieldSpec:
    return FieldSpec(name=header, source="status")


_FROZEN: dict[str, FieldSpec] = {}


def _spec(
    key: str,
    label: str,
    columns: list[str],
    keyword_field: str,
    *,
    file_stem: str | None = None,
    status_header: str | None = None,
    filter_fields: tuple[str, ...] | None = None,
    statuses: tuple[str, ...] = (),
) -> ModuleSpec:
    status_header = status_header or columns[-1]
    for name in columns[:-1]:
        _FROZEN.setdefault(name, FieldSpec(name=name))
    _FROZEN.setdefault(status_header, _status_field(status_header))
    return ModuleSpec(
        key=key,
        label=label,
        columns=tuple(columns),
        keyword_field=keyword_field,
        file_stem=file_stem or f"{label}清单",
        filter_fields=filter_fields or tuple(columns[:3]),
        statuses=statuses,
        sheet_title=label,
    )


MODULE_SPECS: dict[str, ModuleSpec] = {}

# 注意：columns 的顺序就是既有导出模板表头与文件列顺序，保持不动。
_MODULE_DEFS: list[ModuleSpec] = [
    _spec("register", "使用登记",
          ["设备编号", "设备名称", "设备种类", "使用单位", "安装地点", "投用日期", "登记证号", "登记状态"],
          "设备编号", file_stem="使用登记清单", status_header="登记状态",
          statuses=("待登记", "已登记", "停用中", "已注销")),
    _spec("boiler", "锅炉管理",
          ["锅炉编号", "锅炉型号", "额定蒸发量", "工作压力", "燃料类型", "使用年限", "司炉人员", "锅炉状态"],
          "锅炉编号", statuses=("正常运行", "低负荷", "检修中", "已停炉")),
    _spec("pressurevessel", "压力容器",
          ["容器编号", "容器类别", "设计压力", "工作温度", "介质名称", "容积", "安全附件", "容器状态"],
          "容器编号", statuses=("正常", "超压运行", "检验中", "已停用")),
    _spec("pipeline", "压力管道",
          ["管道编号", "管道级别", "设计压力", "输送介质", "管道长度", "敷设方式", "检验日期", "管道状态"],
          "管道编号", statuses=("正常", "壁厚减薄", "待检验", "已报废")),
    _spec("elevator", "电梯管理",
          ["电梯编号", "电梯类型", "额定载重", "层站数", "维保单位", "上次维保", "下次维保日", "电梯状态"],
          "电梯编号", statuses=("正常运行", "维保中", "困人", "检修中")),
    _spec("crane", "起重机械",
          ["起重机编号", "起重机类型", "额定起重量", "跨度", "工作级别", "操作人员", "上次年检", "起重机状态"],
          "起重机编号", file_stem="起重机械清单",
          statuses=("正常", "超载运行", "检验中", "已停用")),
    _spec("forklift", "场车管理",
          ["车辆编号", "车辆类型", "动力类型", "核定载重", "行驶区域", "驾驶员", "年检日期", "车辆状态"],
          "车辆编号", statuses=("正常", "维修中", "待年检", "已报废")),
    _spec("inspection", "定期检验",
          ["检验编号", "被检设备", "检验类别", "检验机构", "计划检验日", "实际检验日", "检验结论", "检验状态"],
          "检验编号", file_stem="定期检验清单",
          statuses=("待检验", "检验中", "合格", "不合格")),
    _spec("maintenance", "维保记录",
          ["维保编号", "维保设备", "维保单位", "维保内容", "维保日期", "维保人员", "更换部件", "维保状态"],
          "维保编号", statuses=("待维保", "维保中", "已完成", "需返工")),
    _spec("hazard", "隐患排查",
          ["隐患编号", "所在设备", "隐患类别", "隐患等级", "发现日期", "整改措施", "整改期限", "隐患状态"],
          "隐患编号", file_stem="隐患排查清单",
          statuses=("待整改", "整改中", "待验收", "已消除")),
    _spec("accident", "事故管理",
          ["事故编号", "事故设备", "事故类型", "伤亡情况", "直接损失", "发生时间", "调查结论", "事故状态"],
          "事故编号", statuses=("待上报", "已上报", "调查中", "已结案")),
    _spec("operator", "作业人员",
          ["人员编号", "姓名", "证书类别", "证书编号", "发证日期", "复审日期", "所属单位", "证书状态"],
          "人员编号", statuses=("持证有效", "即将到期", "已过期", "已注销")),
    _spec("training", "培训考核",
          ["培训编号", "培训内容", "培训对象", "培训日期", "培训讲师", "考核方式", "考核结果", "培训状态"],
          "培训编号", file_stem="培训考核清单",
          statuses=("待培训", "培训中", "已考核", "已归档")),
    _spec("safetyvalve", "安全阀校验",
          ["安全阀编号", "所属设备", "公称通径", "整定压力", "校验日期", "下次校验日", "校验结论", "安全阀状态"],
          "安全阀编号", statuses=("校验合格", "即将到期", "待校验", "已报废")),
    _spec("gauge", "压力表检定",
          ["压力表编号", "所属设备", "量程范围", "精度等级", "检定日期", "下次检定日", "检定结论", "仪表状态"],
          "压力表编号", file_stem="压力表检定清单",
          statuses=("检定合格", "即将到期", "待检定", "已停用")),
    _spec("sparepart", "备件管理",
          ["备件编号", "备件名称", "规格型号", "适用设备", "存放位置", "最低保有量", "当前余量", "备件状态"],
          "备件编号", statuses=("充足", "不足", "待采购", "已停用")),
    _spec("emergency", "应急演练",
          ["演练编号", "演练主题", "演练类型", "参与单位", "演练日期", "演练评估", "改进措施", "演练状态"],
          "演练编号", statuses=("待组织", "已组织", "已完成", "已复盘")),
    _spec("energyeff", "能效监测",
          ["记录编号", "设备类型", "耗能量", "单耗指标", "对标基准", "偏差比率", "记录月份", "能效状态"],
          "记录编号", statuses=("达标", "轻微偏差", "显著偏差", "已调整")),
    _spec("archive", "档案管理",
          ["档案编号", "所属设备", "档案类别", "归档日期", "借阅人", "借阅日期", "归还日期", "档案状态"],
          "档案编号", statuses=("在库", "借出中", "已归还", "已销毁")),
    _spec("contract", "维保合同",
          ["合同编号", "签约单位", "维保范围", "合同金额", "签约日期", "到期日期", "是否续签", "合同状态"],
          "合同编号", statuses=("待签约", "执行中", "即将到期", "已终止")),
]

for _m in _MODULE_DEFS:
    MODULE_SPECS[_m.key] = _m

FIELD_REGISTRY: dict[str, FieldSpec] = dict(_FROZEN)


# --------------------------------------------------------------------------- #
# 统一取数范围（scope）：页面列表与导出入口共用这一份筛选口径。
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Scope:
    """一次取数的范围：同一组参数在列表页和导出里得到的行集合必须一致。"""

    module: str
    keyword: str | None = None
    status: str | None = None
    field_filters: dict[str, str] = field(default_factory=dict)

    def cache_key(self) -> str:
        parts = [self.module, self.keyword or "", self.status or ""]
        for name in sorted(self.field_filters):
            parts.append(f"{name}={self.field_filters[name]}")
        return "|".join(parts)


def build_scope(module: str, params: dict[str, Any] | Iterable[tuple[str, str]] | None = None) -> Scope:
    """从查询参数构造取数范围。

    接受两种入参：FastAPI 的 Query 字典，或 URLSearchParams 之类的键值对。
    页面上选中的字段（前三个可筛选列）与状态都收敛到这里，未知字段直接忽略。
    """
    spec = require_spec(module)
    if params is None:
        raw: dict[str, str] = {}
    elif isinstance(params, dict):
        raw = {str(k): str(v) for k, v in params.items() if v is not None}
    else:
        raw = {str(k): str(v) for k, v in params if v is not None}

    def clean(value: str | None) -> str | None:
        value = (value or "").strip()
        return value or None

    field_filters = {
        name: needle
        for name in spec.filter_fields
        if (needle := clean(raw.get(name)))
    }
    return Scope(
        module=module,
        keyword=clean(raw.get("keyword")),
        status=clean(raw.get("status")),
        field_filters=field_filters,
    )


def select_rows(scope: Scope) -> list[dict[str, Any]]:
    """按统一范围取原始行（带稳定 id 排序），列表分页和导出都从这里取数。"""
    spec = require_spec(scope.module)
    rows = list(store.rows(scope.module))
    rows.sort(key=lambda row: int(row.get("id", 0)))

    if scope.keyword:
        field = FIELD_REGISTRY[spec.keyword_field]
        rows = [row for row in rows if field.matches(row, scope.keyword)]
    if scope.status:
        rows = [row for row in rows if str(row.get("status") or "") == scope.status]
    for name, needle in scope.field_filters.items():
        field = FIELD_REGISTRY[name]
        rows = [row for row in rows if field.matches(row, needle)]
    return rows


def project_row(spec: ModuleSpec, row: dict[str, Any]) -> dict[str, Any]:
    """按模块声明的字段清单与统一填法投影一行：表头 -> 填好的值。"""
    return {field.name: field.fill(row) for field in spec.fields}


def project_rows(module: str, rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    spec = require_spec(module)
    return [project_row(spec, row) for row in rows]


def require_spec(module: str) -> ModuleSpec:
    try:
        return MODULE_SPECS[module]
    except KeyError:
        raise KeyError(f"未知业务模块：{module}") from None
