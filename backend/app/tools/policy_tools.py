from typing import Dict, Any
from langchain_core.tools import tool
from app.policies.remediation_policy import JobRemediationPolicy, PolicyDecisionSchema
from app.schemas.job import FailureAnalysisSchema, JobRunDetailSchema

_policy_engine = JobRemediationPolicy()

@tool
def evaluate_remediation_policy_tool(
    analysis_dict: Dict[str, Any],
    job_details_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Evaluates deterministic safety and remediation policy guardrails.
    Evaluates retry allowlists, AI confidence threshold (>= 90%), restart_allowed permission flag, and retry limits.
    Returns APPROVED / JOB_RESTART or REJECTED / ESCALATE policy decision.
    """
    analysis = FailureAnalysisSchema(**analysis_dict)
    job_details = JobRunDetailSchema(**job_details_dict)
    decision: PolicyDecisionSchema = _policy_engine.evaluate(analysis, job_details)
    return decision.model_dump()
