"""导出字段目录：全平台唯一一份「取哪些字段、空值怎么填」。

调整取数口径（增删字段、改填法）的步骤：
1. 改 FIELD_CATALOG 或 MODULE_FIELDS；
2. RULES_VERSION 加 1；
3. 调 POST /api/exports/backfill 把存量导出按新口径回填一遍，旧导出包保留不动。

各模块不再各自维护字段清单，只在 MODULE_FIELDS 里声明「我用哪几列」；
声明的顺序就是对外的表头顺序，MODULE_FILE_NAMES 是对外文件名，
两者与既有导出模板保持一致，不要随口径调整改动。
"""
from __future__ import annotations

from dataclasses import dataclass

# 取数口径版本：字段清单或空值填法变化时递增，回填机制据此识别旧口径的导出包。
RULES_VERSION = 1

# 各类型的默认空值填法；单个字段可在 FieldSpec(fill=...) 里覆盖。
KIND_FILLS = {
    "text": "—",
    "date": "",
    "number": "0",
}


@dataclass(frozen=True)
class FieldSpec:
    """一个可导出字段的取数规则：类型决定默认填法，fill 可单独覆盖。"""

    kind: str = "text"
    fill: str | None = None

    @property
    def empty_value(self) -> str:
        if self.fill is not None:
            return self.fill
        return KIND_FILLS[self.kind]


def _build_catalog() -> dict[str, FieldSpec]:
    date_fields = (
        "投用日期 检验日期 上次维保 下次维保日 上次年检 年检日期 计划检验日 实际检验日 "
        "维保日期 发现日期 整改期限 发生时间 发证日期 复审日期 培训日期 校验日期 下次校验日 "
        "检定日期 下次检定日 演练日期 记录月份 归档日期 借阅日期 归还日期 签约日期 到期日期"
    ).split()
    number_fields = (
        "额定蒸发量 工作压力 使用年限 设计压力 工作温度 容积 管道长度 额定载重 层站数 "
        "额定起重量 跨度 核定载重 直接损失 公称通径 整定压力 最低保有量 当前余量 "
        "耗能量 单耗指标 偏差比率 合同金额"
    ).split()
    text_fields = (
        "设备编号 设备名称 设备种类 使用单位 安装地点 登记证号 登记状态 "
        "锅炉编号 锅炉型号 燃料类型 司炉人员 锅炉状态 "
        "容器编号 容器类别 介质名称 安全附件 容器状态 "
        "管道编号 管道级别 输送介质 敷设方式 管道状态 "
        "电梯编号 电梯类型 维保单位 电梯状态 "
        "起重机编号 起重机类型 工作级别 操作人员 起重机状态 "
        "车辆编号 车辆类型 动力类型 行驶区域 驾驶员 车辆状态 "
        "检验编号 被检设备 检验类别 检验机构 检验结论 检验状态 "
        "维保编号 维保设备 维保内容 维保人员 更换部件 维保状态 "
        "隐患编号 所在设备 隐患类别 隐患等级 整改措施 隐患状态 "
        "事故编号 事故设备 事故类型 伤亡情况 调查结论 事故状态 "
        "人员编号 姓名 证书类别 证书编号 所属单位 证书状态 "
        "培训编号 培训内容 培训对象 培训讲师 考核方式 考核结果 培训状态 "
        "安全阀编号 所属设备 校验结论 安全阀状态 "
        "压力表编号 量程范围 精度等级 检定结论 仪表状态 "
        "备件编号 备件名称 规格型号 适用设备 存放位置 备件状态 "
        "演练编号 演练主题 演练类型 参与单位 演练评估 改进措施 演练状态 "
        "记录编号 设备类型 对标基准 能效状态 "
        "档案编号 档案类别 借阅人 档案状态 "
        "合同编号 签约单位 维保范围 是否续签 合同状态"
    ).split()
    catalog: dict[str, FieldSpec] = {}
    for name in date_fields:
        catalog[name] = FieldSpec(kind="date")
    for name in number_fields:
        catalog[name] = FieldSpec(kind="number")
    for name in text_fields:
        catalog[name] = FieldSpec(kind="text")
    return catalog


# 全平台字段清单与空值填法，只维护这一份；同名字段在所有模块里口径一致。
FIELD_CATALOG: dict[str, FieldSpec] = _build_catalog()

# 各模块声明自己导出哪几列；列顺序即对外表头顺序，兼容既有导出模板，不要重排。
MODULE_FIELDS: dict[str, list[str]] = {
    "register": ["设备编号", "设备名称", "设备种类", "使用单位", "安装地点", "投用日期", "登记证号", "登记状态"],
    "boiler": ["锅炉编号", "锅炉型号", "额定蒸发量", "工作压力", "燃料类型", "使用年限", "司炉人员", "锅炉状态"],
    "pressurevessel": ["容器编号", "容器类别", "设计压力", "工作温度", "介质名称", "容积", "安全附件", "容器状态"],
    "pipeline": ["管道编号", "管道级别", "设计压力", "输送介质", "管道长度", "敷设方式", "检验日期", "管道状态"],
    "elevator": ["电梯编号", "电梯类型", "额定载重", "层站数", "维保单位", "上次维保", "下次维保日", "电梯状态"],
    "crane": ["起重机编号", "起重机类型", "额定起重量", "跨度", "工作级别", "操作人员", "上次年检", "起重机状态"],
    "forklift": ["车辆编号", "车辆类型", "动力类型", "核定载重", "行驶区域", "驾驶员", "年检日期", "车辆状态"],
    "inspection": ["检验编号", "被检设备", "检验类别", "检验机构", "计划检验日", "实际检验日", "检验结论", "检验状态"],
    "maintenance": ["维保编号", "维保设备", "维保单位", "维保内容", "维保日期", "维保人员", "更换部件", "维保状态"],
    "hazard": ["隐患编号", "所在设备", "隐患类别", "隐患等级", "发现日期", "整改措施", "整改期限", "隐患状态"],
    "accident": ["事故编号", "事故设备", "事故类型", "伤亡情况", "直接损失", "发生时间", "调查结论", "事故状态"],
    "operator": ["人员编号", "姓名", "证书类别", "证书编号", "发证日期", "复审日期", "所属单位", "证书状态"],
    "training": ["培训编号", "培训内容", "培训对象", "培训日期", "培训讲师", "考核方式", "考核结果", "培训状态"],
    "safetyvalve": ["安全阀编号", "所属设备", "公称通径", "整定压力", "校验日期", "下次校验日", "校验结论", "安全阀状态"],
    "gauge": ["压力表编号", "所属设备", "量程范围", "精度等级", "检定日期", "下次检定日", "检定结论", "仪表状态"],
    "sparepart": ["备件编号", "备件名称", "规格型号", "适用设备", "存放位置", "最低保有量", "当前余量", "备件状态"],
    "emergency": ["演练编号", "演练主题", "演练类型", "参与单位", "演练日期", "演练评估", "改进措施", "演练状态"],
    "energyeff": ["记录编号", "设备类型", "耗能量", "单耗指标", "对标基准", "偏差比率", "记录月份", "能效状态"],
    "archive": ["档案编号", "所属设备", "档案类别", "归档日期", "借阅人", "借阅日期", "归还日期", "档案状态"],
    "contract": ["合同编号", "签约单位", "维保范围", "合同金额", "签约日期", "到期日期", "是否续签", "合同状态"],
}

# 对外文件名：导出包落地与下载都用这个名字，保持与既有模板一致。
MODULE_FILE_NAMES: dict[str, str] = {
    "register": "使用登记清单.csv",
    "boiler": "锅炉管理清单.csv",
    "pressurevessel": "压力容器清单.csv",
    "pipeline": "压力管道清单.csv",
    "elevator": "电梯管理清单.csv",
    "crane": "起重机械清单.csv",
    "forklift": "场车管理清单.csv",
    "inspection": "定期检验清单.csv",
    "maintenance": "维保记录清单.csv",
    "hazard": "隐患排查清单.csv",
    "accident": "事故管理清单.csv",
    "operator": "作业人员清单.csv",
    "training": "培训考核清单.csv",
    "safetyvalve": "安全阀校验清单.csv",
    "gauge": "压力表检定清单.csv",
    "sparepart": "备件管理清单.csv",
    "emergency": "应急演练清单.csv",
    "energyeff": "能效监测清单.csv",
    "archive": "档案管理清单.csv",
    "contract": "维保合同清单.csv",
}


def headers_for(module: str) -> list[str]:
    """模块的导出表头，顺序与既有模板一致。"""
    return list(MODULE_FIELDS[module])


def spec_for(field: str) -> FieldSpec:
    return FIELD_CATALOG[field]


def known_modules() -> list[str]:
    return sorted(MODULE_FIELDS)


def _check_declared_fields() -> None:
    unknown = [
        f"{module}.{field}"
        for module, fields in MODULE_FIELDS.items()
        for field in fields
        if field not in FIELD_CATALOG
    ]
    if unknown:
        raise ValueError(f"以下导出字段未在 FIELD_CATALOG 登记填法：{'、'.join(unknown)}")


_check_declared_fields()
