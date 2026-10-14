from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import random
from app.db.database import get_db
from app.schemas.job import JobEventPayload
from app.agents.job_resolution_agent import JobResolutionAgent
from app.sap import get_mock_sap_service
from app.db.models import JobRunModel

router = APIRouter(prefix="/api/mock-sap", tags=["Mock SAP Operations"])

class TriggerScenarioRequest(BaseModel):
    scenario: str # "TRANSIENT_DB_LOCK", "AUTHORIZATION_FAILURE", "RESTART_FROM_START", "RFC_TIMEOUT", "SUCCESS"
    job_name: Optional[str] = None
    run_count: Optional[int] = None

@router.post("/generate-failure")
@router.post("/trigger")
async def generate_mock_sap_failure(req: TriggerScenarioRequest, db: Session = Depends(get_db)):
    """
    Developer / Demo Controls:
    Emits a mock SAP Job event into Mock SAP and ingests it via Agent investigation.
    Job is stored with FAILED status and ready for autonomous remediation via [Run Agent].
    """
    mock_sap = get_mock_sap_service()

    # Determine unique run count if not supplied
    if req.scenario == "TRANSIENT_DB_LOCK":
        job_name = req.job_name or "Z_CUSTOMER_LOAD"
        base_count = req.run_count or 1001
    elif req.scenario == "AUTHORIZATION_FAILURE":
        job_name = req.job_name or "Z_FIN_POSTING"
        base_count = req.run_count or 2001
    elif req.scenario == "RESTART_FROM_START" or req.scenario == "INTERMEDIATE_STATE_INCONSISTENCY":
        job_name = req.job_name or "Z_SETTLEMENT_RUN"
        base_count = req.run_count or 5001
    elif req.scenario == "RFC_TIMEOUT":
        job_name = req.job_name or "Z_VENDOR_SYNC"
        base_count = req.run_count or 3001
    elif req.scenario == "SUCCESS":
        job_name = req.job_name or "Z_INVOICE_BATCH"
        base_count = req.run_count or 4001
    else:
        job_name = req.job_name or "Z_PAYMENT_RUN"
        base_count = req.run_count or random.randint(6000, 9999)

    # Check if run exists, if so increment to next unique run count
    existing_run = db.query(JobRunModel).filter_by(job_name=job_name, run_count=base_count).first()
    run_count = base_count
    if existing_run:
        max_run = db.query(JobRunModel).filter_by(job_name=job_name).order_by(JobRunModel.run_count.desc()).first()
        run_count = (max_run.run_count + 1) if max_run else (base_count + 1)

    # Register in mock SAP
    mock_sap.ensure_job_registered(job_name, run_count, scenario=req.scenario)

    event_type = "SAP_JOB_COMPLETED" if req.scenario == "SUCCESS" else "SAP_JOB_FAILED"
    status = "SUCCESS" if req.scenario == "SUCCESS" else "FAILED"

    payload = JobEventPayload(
        event_type=event_type,
        job_name=job_name,
        job_run_count=run_count,
        status=status
    )

    agent = JobResolutionAgent(db, sap_service=mock_sap)
    result = await agent.process_job_event(payload, auto_remediate=False)

    return {
        "message": f"SAP {status} event emitted for {job_name} run #{run_count}",
        "job_name": job_name,
        "run_count": run_count,
        "status": status,
        "scenario": req.scenario,
        "agent_result": result
    }
