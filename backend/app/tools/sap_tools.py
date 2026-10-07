from typing import Dict, Any, List, Optional
from langchain_core.tools import tool
from app.sap.base import SAPJobService
from app.sap import get_sap_job_service
from app.schemas.job import JobRunDetailSchema, JobLogSchema, JobParameterSchema

# Module-level SAP service instance
_sap_service: Optional[SAPJobService] = None

def set_sap_service(service: SAPJobService):
    global _sap_service
    _sap_service = service

def get_sap_service() -> SAPJobService:
    global _sap_service
    if _sap_service is None:
        _sap_service = get_sap_job_service()
    return _sap_service

@tool
async def get_job_status_tool(job_name: str, run_count: int) -> Dict[str, Any]:
    """
    Retrieves execution status for a specified SAP job name and run count.
    """
    return await get_sap_service().get_job_status(job_name, run_count)

@tool
async def get_job_info_tool(job_name: str, run_count: int) -> Dict[str, Any]:
    """
    Retrieves full SAP job run details including step status, return codes, logs, and parameters.
    """
    details: JobRunDetailSchema = await get_sap_service().get_job_info(job_name, run_count)
    return details.model_dump()

@tool
async def get_job_logs_tool(job_name: str, run_count: int) -> List[Dict[str, Any]]:
    """
    Retrieves detailed technical execution logs for a specified SAP job run.
    """
    logs: List[JobLogSchema] = await get_sap_service().get_job_logs(job_name, run_count)
    return [l.model_dump() for l in logs]

@tool
async def get_job_parameters_tool(job_name: str, run_count: int) -> List[Dict[str, Any]]:
    """
    Retrieves input runtime parameters configured for a specified SAP job run.
    """
    params: List[JobParameterSchema] = await get_sap_service().get_job_parameters(job_name, run_count)
    return [p.model_dump() for p in params]

@tool
async def restart_job_tool(job_name: str, run_count: int, restart_mode: str = "E") -> Dict[str, Any]:
    """
    Issues SAP JobRestart command.
    Mode 'E' restarts from the failed step; Mode 'A' restarts from the start.
    """
    return await get_sap_service().restart_job(job_name, run_count, restart_mode)
