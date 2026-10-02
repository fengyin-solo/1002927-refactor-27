"""业务服务注册表：导出中心通过它复用各模块的列表过滤口径。

各模块的取数范围（关键字、状态过滤）只在各自的 service 里实现一次；
导出、页面列表、回填都经由这里的同一份服务实例取数。
"""
from __future__ import annotations

from typing import Any

from app.services.accident import AccidentService
from app.services.archive import ArchiveService
from app.services.boiler import BoilerService
from app.services.contract import ContractService
from app.services.crane import CraneService
from app.services.elevator import ElevatorService
from app.services.emergency import EmergencyService
from app.services.energyeff import EnergyeffService
from app.services.forklift import ForkliftService
from app.services.gauge import GaugeService
from app.services.hazard import HazardService
from app.services.inspection import InspectionService
from app.services.maintenance import MaintenanceService
from app.services.operator import OperatorService
from app.services.pipeline import PipelineService
from app.services.pressurevessel import PressurevesselService
from app.services.register import RegisterService
from app.services.safetyvalve import SafetyvalveService
from app.services.sparepart import SparepartService
from app.services.training import TrainingService

SERVICES: dict[str, Any] = {
    "register": RegisterService(),
    "boiler": BoilerService(),
    "pressurevessel": PressurevesselService(),
    "pipeline": PipelineService(),
    "elevator": ElevatorService(),
    "crane": CraneService(),
    "forklift": ForkliftService(),
    "inspection": InspectionService(),
    "maintenance": MaintenanceService(),
    "hazard": HazardService(),
    "accident": AccidentService(),
    "operator": OperatorService(),
    "training": TrainingService(),
    "safetyvalve": SafetyvalveService(),
    "gauge": GaugeService(),
    "sparepart": SparepartService(),
    "emergency": EmergencyService(),
    "energyeff": EnergyeffService(),
    "archive": ArchiveService(),
    "contract": ContractService(),
}
