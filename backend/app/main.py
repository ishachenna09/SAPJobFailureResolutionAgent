from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from app.config import settings
from app.db.database import engine, Base, SessionLocal
from app.api.events import router as events_router
from app.api.jobs import router as jobs_router
from app.api.mock_sap import router as mock_sap_router
from app.schemas.job import JobEventPayload
from app.agents.job_resolution_agent import JobResolutionAgent

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Autonomous Agent for SAP Job Failure Recognition & Resolution"
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(events_router)
app.include_router(jobs_router)
app.include_router(mock_sap_router)

@app.on_event("startup")
async def startup_event():
    # Create DB tables
    Base.metadata.create_all(bind=engine)
    # Auto-migrate any SQLite columns for Phase 2
    from app.db.database import ensure_sqlite_columns
    from app.db.models import (
        JobRunModel, JobModel, RemediationExecutionModel, FailureAnalysisModel,
        JobStepModel, JobLogModel, JobParameterModel, JobEventModel
    )
    ensure_sqlite_columns(engine)
    
    # Auto-seed initial demo events cleanly without duplicates
    db = SessionLocal()
    try:
        # Wipe old database rows to ensure clean state
        db.query(RemediationExecutionModel).delete()
        db.query(FailureAnalysisModel).delete()
        db.query(JobLogModel).delete()
        db.query(JobStepModel).delete()
        db.query(JobParameterModel).delete()
        db.query(JobRunModel).delete()
        db.query(JobModel).delete()
        db.query(JobEventModel).delete()
        db.commit()

        from app.sap import get_mock_sap_service
        mock_sap_service = get_mock_sap_service()
        mock_agent = JobResolutionAgent(db, sap_service=mock_sap_service)
        await mock_agent.process_job_event(JobEventPayload(event_type="SAP_JOB_FAILED", job_name="Z_CUSTOMER_LOAD", job_run_count=1001, platform="MOCK_SAP", status="FAILED"))
        await mock_agent.process_job_event(JobEventPayload(event_type="SAP_JOB_FAILED", job_name="Z_VENDOR_SYNC", job_run_count=3001, platform="MOCK_SAP", status="FAILED"))
        await mock_agent.process_job_event(JobEventPayload(event_type="SAP_JOB_FAILED", job_name="Z_FIN_POSTING", job_run_count=2001, platform="MOCK_SAP", status="FAILED"))
        await mock_agent.process_job_event(JobEventPayload(event_type="SAP_JOB_FAILED", job_name="Z_PAYROLL_RUN", job_run_count=2002, platform="MOCK_SAP", status="FAILED"))
        await mock_agent.process_job_event(JobEventPayload(event_type="SAP_JOB_COMPLETED", job_name="Z_INVOICE_BATCH", job_run_count=4001, platform="MOCK_SAP", status="SUCCESS"))
        await mock_agent.process_job_event(JobEventPayload(event_type="SAP_JOB_COMPLETED", job_name="Z_SALES_REPORT", job_run_count=4002, platform="MOCK_SAP", status="SUCCESS"))

        platform = (settings.JOB_PLATFORM or "").lower()
        if platform == "sap_btp" or platform == "btp":
            print("SAP BTP Job Scheduling Service integration active.")
            try:
                from app.sap.btp_sap import BTPJobSchedulingService
                btp_service = BTPJobSchedulingService()
                btp_agent = JobResolutionAgent(db, sap_service=btp_service)
                btp_runs = await btp_service.fetch_recent_executions()
                for run in btp_runs:
                    evt_type = "SAP_JOB_COMPLETED" if run.status == "SUCCESS" else "SAP_JOB_FAILED"
                    payload = JobEventPayload(
                        event_type=evt_type,
                        job_name=run.job_name,
                        job_run_count=run.run_count,
                        platform="SAP_BTP",
                        status=run.status
                    )
                    await btp_agent.process_job_event(payload)
            except Exception as btp_err:
                print(f"SAP BTP fetch notice during startup: {btp_err}")
    except Exception as e:
        print(f"Startup seeding notice: {e}")
    finally:
        db.close()

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "mode": settings.SAP_MODE
    }
