from typing import Dict, Any, List
from langchain_core.tools import tool
from app.ai.provider import get_ai_service
from app.schemas.job import JobRunDetailSchema, JobLogSchema, JobParameterSchema, FailureAnalysisSchema

@tool
async def analyze_job_failure_tool(
    job_details_dict: Dict[str, Any],
    logs_list: List[Dict[str, Any]],
    parameters_list: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Invokes AI diagnosis provider (Gemini / Groq / Fallback) to analyze failed SAP job run logs,
    steps, and parameters to return a structured failure classification schema.
    """
    job_details = JobRunDetailSchema(**job_details_dict)
    logs = [JobLogSchema(**l) for l in logs_list]
    parameters = [JobParameterSchema(**p) for p in parameters_list]
    
    ai_service = get_ai_service()
    analysis: FailureAnalysisSchema = await ai_service.analyze_job_failure(job_details, logs, parameters)
    return analysis.model_dump()
