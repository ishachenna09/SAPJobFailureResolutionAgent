from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

# Event schema
class JobEventPayload(BaseModel):
    event_type: str = Field(..., description="e.g. SAP_JOB_FAILED or SAP_JOB_STATUS_CHANGE")
    job_name: str
    job_run_count: int
    platform: str = Field("MOCK_SAP", description="MOCK_SAP or SAP_BTP")
    status: Optional[str] = Field(None, description="Current job status e.g. FAILED, SUCCESS")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

# SAP Job details & steps
class JobStepSchema(BaseModel):
    step_number: int
    step_name: str
    program_name: Optional[str] = None
    status: str
    return_code: int = 0
    start_time: Optional[str] = None
    end_time: Optional[str] = None

class JobLogSchema(BaseModel):
    timestamp: str
    severity: str
    step_number: Optional[int] = None
    message: str
    is_error_highlight: bool = False

class JobParameterSchema(BaseModel):
    param_name: str
    param_value: str

class FailureAnalysisSchema(BaseModel):
    failure_category: str
    confidence: float
    root_cause_summary: str
    evidence: List[str]
    recommended_action: str
    restart_mode: str = "E"
    restart_strategy: str = "RESTART_FROM_FAILED_STEP" # RESTART_FROM_FAILED_STEP, RESTART_FROM_START, DO_NOT_RESTART
    reason: str
    platform: str = "MOCK_SAP"

class JobRunDetailSchema(BaseModel):
    id: int
    job_name: str
    run_count: int
    platform: str = "MOCK_SAP"
    status: str
    start_time: str
    end_time: Optional[str] = None
    return_code: int
    failed_step_number: Optional[int] = None
    job_user: str
    job_text: Optional[str] = None
    retry_count: int
    parent_run_id: Optional[int] = None
    remediation_execution_id: Optional[str] = None
    environment: str = "MOCK"
    restart_allowed: bool = True
    max_retries: int = 2
    steps: List[JobStepSchema] = []
    logs: List[JobLogSchema] = []
    parameters: List[JobParameterSchema] = []
    analysis: Optional[FailureAnalysisSchema] = None

class JobRunSummarySchema(BaseModel):
    id: int
    job_name: str
    run_count: int
    platform: str = "MOCK_SAP"
    status: str
    start_time: str
    failed_step_number: Optional[int] = None
    return_code: int
    failure_category: Optional[str] = None
    retry_count: int
    parent_run_id: Optional[int] = None
    remediation_execution_id: Optional[str] = None

