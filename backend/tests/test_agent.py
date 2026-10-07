import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.database import Base
from app.schemas.job import JobEventPayload
from app.agents.job_resolution_agent import JobResolutionAgent

# Use in-memory SQLite for quick tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

@pytest.mark.asyncio
async def test_agent_auto_remediates_transient_db_lock(db):
    agent = JobResolutionAgent(db)
    payload = JobEventPayload(
        event_type="SAP_JOB_FAILED",
        job_name="Z_CUSTOMER_LOAD",
        job_run_count=1001,
        status="FAILED"
    )
    result = await agent.process_job_event(payload, auto_remediate=True)
    
    assert result["status"] == "PROCESSED"
    assert result["job_name"] == "Z_CUSTOMER_LOAD"
    assert result["remediation_status"] == "AUTO_RESOLVED"
    assert result["ai_analysis"]["failure_category"] == "TRANSIENT_DATABASE_LOCK"

@pytest.mark.asyncio
async def test_agent_escalates_authorization_failure(db):
    agent = JobResolutionAgent(db)
    payload = JobEventPayload(
        event_type="SAP_JOB_FAILED",
        job_name="Z_FIN_POSTING",
        job_run_count=2001,
        status="FAILED"
    )
    result = await agent.process_job_event(payload, auto_remediate=True)
    
    assert result["status"] == "PROCESSED"
    assert result["job_name"] == "Z_FIN_POSTING"
    assert result["remediation_status"] == "ESCALATED"
    assert result["ai_analysis"]["failure_category"] == "AUTHORIZATION_ERROR"

@pytest.mark.asyncio
async def test_agent_recognizes_successful_job(db):
    agent = JobResolutionAgent(db)
    payload = JobEventPayload(
        event_type="SAP_JOB_COMPLETED",
        job_name="Z_INVOICE_BATCH",
        job_run_count=4001,
        status="SUCCESS"
    )
    result = await agent.process_job_event(payload, auto_remediate=False)
    
    assert result["status"] == "PROCESSED"
    assert result["job_name"] == "Z_INVOICE_BATCH"
    assert result["recognized_status"] == "SUCCESS"
    assert result["ai_analysis"] is None

@pytest.mark.asyncio
async def test_agent_event_deduplication(db):
    agent = JobResolutionAgent(db)
    payload = JobEventPayload(
        event_type="SAP_JOB_FAILED",
        job_name="Z_CUSTOMER_LOAD",
        job_run_count=1001,
        status="FAILED"
    )
    res1 = await agent.process_job_event(payload, auto_remediate=False)
    assert res1["status"] == "PROCESSED"
    
    res2 = await agent.process_job_event(payload, auto_remediate=False)
    assert res2["status"] == "DUPLICATE_IGNORED"
