from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from app.schemas.job import JobRunDetailSchema, JobStepSchema, JobLogSchema, JobParameterSchema

class SAPJobService(ABC):
    platform_name: str = "MOCK_SAP"

    @abstractmethod
    async def get_job_status(self, job_name: str, run_count: int) -> Dict[str, Any]:
        """Maps to SAP JobStatusGet"""
        pass

    @abstractmethod
    async def get_job_info(self, job_name: str, run_count: int) -> JobRunDetailSchema:
        """Maps to SAP JobinfoGet"""
        pass

    @abstractmethod
    async def get_job_logs(self, job_name: str, run_count: int) -> List[JobLogSchema]:
        """Maps to SAP JobHeaderSet / log expansion"""
        pass

    @abstractmethod
    async def get_job_parameters(self, job_name: str, run_count: int) -> List[JobParameterSchema]:
        """Maps to SAP JobParamValuesGet"""
        pass

    @abstractmethod
    async def restart_job(self, job_name: str, run_count: int, restart_mode: str = "E") -> Dict[str, Any]:
        """Maps to SAP JobRestart"""
        pass

# Standardized alias required by Phase 2 spec Section 1
JobPlatform = SAPJobService

