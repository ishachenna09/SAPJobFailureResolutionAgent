import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.database import Base
from app.schemas.job import JobEventPayload
from app.agents.job_resolution_agent import JobResolutionAgent
from app.services.remediation_service import RemediationService
from app.sap.mock_sap import MockSAPJobService
from app.db.models import JobRunModel, RemediationExecutionModel, JobModel
from app.api.jobs import get_job_history, list_job_runs

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
async def test_failed_job_ingestion_preserves_failed_state(db):
    agent = JobResolutionAgent(db)
    payload = JobEventPayload(
        event_type="SAP_JOB_FAILED",
        job_name="Z_CUSTOMER_LOAD",
        job_run_count=1001,
        status="FAILED"
    )
    result = await agent.process_job_event(payload, auto_remediate=False)
    assert result["status"] == "PROCESSED"
    assert result["recognized_status"] == "FAILED"
    assert result["ai_analysis"]["failure_category"] == "TRANSIENT_DATABASE_LOCK"

    run = db.query(JobRunModel).filter_by(job_name="Z_CUSTOMER_LOAD", run_count=1001).first()
    assert run is not None
    assert run.status == "FAILED"
    assert run.return_code == 8

@pytest.mark.asyncio
async def test_safe_remediation_lineage_and_restart_from_failed_step(db):
    agent = JobResolutionAgent(db)
    mock_sap = MockSAPJobService()
    # 1. Ingest failed event
    await agent.process_job_event(
        JobEventPayload(
            event_type="SAP_JOB_FAILED",
            job_name="Z_CUSTOMER_LOAD",
            job_run_count=1001,
            status="FAILED"
        ),
        auto_remediate=False
    )

    orig_run = db.query(JobRunModel).filter_by(job_name="Z_CUSTOMER_LOAD", run_count=1001).first()
    assert orig_run.status == "FAILED"

    # 2. Trigger Phase 2 Remediation
    rem_service = RemediationService(db, mock_sap)
    rem_record = await rem_service.execute_remediation("Z_CUSTOMER_LOAD", 1001)

    assert rem_record.status == "AUTO_RESOLVED"
    assert rem_record.restart_strategy == "RESTART_FROM_FAILED_STEP"
    assert rem_record.restart_mode == "E"

    # 3. Assert original run remains FAILED in database (Never overwritten!)
    db.refresh(orig_run)
    assert orig_run.status == "FAILED"
    assert orig_run.return_code == 8

    # 4. Assert new run #1002 was created as SUCCESS with parent lineage
    new_run = db.query(JobRunModel).filter_by(job_name="Z_CUSTOMER_LOAD", run_count=1002).first()
    assert new_run is not None
    assert new_run.status == "SUCCESS"
    assert new_run.return_code == 0
    assert new_run.parent_run_id == orig_run.id
    assert new_run.remediation_execution_id == rem_record.execution_id

@pytest.mark.asyncio
async def test_restart_from_start_strategy(db):
    agent = JobResolutionAgent(db)
    mock_sap = MockSAPJobService()
    mock_sap.ensure_job_registered("Z_SETTLEMENT_RUN", 5001, scenario="RESTART_FROM_START")

    # Ingest failure
    await agent.process_job_event(
        JobEventPayload(
            event_type="SAP_JOB_FAILED",
            job_name="Z_SETTLEMENT_RUN",
            job_run_count=5001,
            status="FAILED"
        ),
        auto_remediate=False
    )

    rem_service = RemediationService(db, mock_sap)
    rem_record = await rem_service.execute_remediation("Z_SETTLEMENT_RUN", 5001)

    assert rem_record.status == "AUTO_RESOLVED"
    assert rem_record.restart_strategy == "RESTART_FROM_START"
    assert rem_record.restart_mode == "A"

    new_run = db.query(JobRunModel).filter_by(job_name="Z_SETTLEMENT_RUN", run_count=5002).first()
    assert new_run is not None
    assert new_run.status == "SUCCESS"
    assert len(new_run.steps) == 3

@pytest.mark.asyncio
async def test_authorization_failure_blocks_and_escalates(db):
    agent = JobResolutionAgent(db)
    mock_sap = MockSAPJobService()

    await agent.process_job_event(
        JobEventPayload(
            event_type="SAP_JOB_FAILED",
            job_name="Z_FIN_POSTING",
            job_run_count=2001,
            status="FAILED"
        ),
        auto_remediate=False
    )

    rem_service = RemediationService(db, mock_sap)
    rem_record = await rem_service.execute_remediation("Z_FIN_POSTING", 2001)

    assert rem_record.status == "ESCALATED"
    assert rem_record.restart_strategy == "DO_NOT_RESTART"
    assert rem_record.policy_decision == "REJECTED"

    # Original run remains FAILED, no new run spawned
    orig_run = db.query(JobRunModel).filter_by(job_name="Z_FIN_POSTING", run_count=2001).first()
    assert orig_run.status == "FAILED"
    new_run = db.query(JobRunModel).filter_by(job_name="Z_FIN_POSTING", run_count=2002).first()
    assert new_run is None

@pytest.mark.asyncio
async def test_retry_exhaustion_blocks_and_escalates(db):
    agent = JobResolutionAgent(db)
    mock_sap = MockSAPJobService()

    # Ingest transient DB lock but set retry_count equal to max_retries
    await agent.process_job_event(
        JobEventPayload(
            event_type="SAP_JOB_FAILED",
            job_name="Z_CUSTOMER_LOAD",
            job_run_count=1001,
            status="FAILED"
        ),
        auto_remediate=False
    )

    # Artificially exhaust retries
    orig_run = db.query(JobRunModel).filter_by(job_name="Z_CUSTOMER_LOAD", run_count=1001).first()
    orig_run.retry_count = 2
    db.commit()

    # In mock SAP also update
    mock_sap.jobs_db["Z_CUSTOMER_LOAD:1001"]["retry_count"] = 2

    rem_service = RemediationService(db, mock_sap)
    rem_record = await rem_service.execute_remediation("Z_CUSTOMER_LOAD", 1001)

    assert rem_record.status == "ESCALATED"
    assert rem_record.policy_decision == "REJECTED"
    assert "Retry Limit Check" in rem_record.policy_reason

@pytest.mark.asyncio
async def test_job_history_and_lineage_api(db):
    agent = JobResolutionAgent(db)
    mock_sap = MockSAPJobService()

    # Ingest and remediate
    await agent.process_job_event(
        JobEventPayload(
            event_type="SAP_JOB_FAILED",
            job_name="Z_CUSTOMER_LOAD",
            job_run_count=1001,
            status="FAILED"
        ),
        auto_remediate=False
    )

    rem_service = RemediationService(db, mock_sap)
    await rem_service.execute_remediation("Z_CUSTOMER_LOAD", 1001)

    # Query history endpoint
    history_resp = get_job_history("Z_CUSTOMER_LOAD", 1001, db=db)
    assert history_resp["job_name"] == "Z_CUSTOMER_LOAD"
    assert len(history_resp["history"]) == 2

    run1 = history_resp["history"][0]
    assert run1["run_count"] == 1001
    assert run1["status"] == "FAILED"
    assert run1["failure_category"] == "TRANSIENT_DATABASE_LOCK"
    assert run1["restart_strategy"] == "RESTART_FROM_FAILED_STEP"

    run2 = history_resp["history"][1]
    assert run2["run_count"] == 1002
    assert run2["status"] == "SUCCESS"
    assert run2["parent_run_id"] == run1["run_id"]
