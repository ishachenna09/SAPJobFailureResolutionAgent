from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.job import JobEventPayload
from app.agents.job_resolution_agent import JobResolutionAgent

router = APIRouter(prefix="/events/sap", tags=["SAP Events"])

@router.post("/job-failed")
@router.post("/job-status")
async def handle_sap_job_event(payload: JobEventPayload, db: Session = Depends(get_db)):
    """
    Webhook endpoint receiving SAP job status events.
    Autonomous Job Failure Resolution Agent processes event, investigates SAP, and recognizes status.
    """
    agent = JobResolutionAgent(db)
    result = await agent.process_job_event(payload)
    return result
