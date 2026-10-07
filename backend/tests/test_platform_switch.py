import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import SessionLocal, engine, Base
from app.db.models import JobRunModel, JobModel, FailureAnalysisModel, RemediationExecutionModel
from app.schemas.job import FailureAnalysisSchema, JobRunDetailSchema
from app.policies.remediation_policy import JobRemediationPolicy

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    from app.db.database import ensure_sqlite_columns
    Base.metadata.create_all(bind=engine)
    ensure_sqlite_columns(engine)
    db = SessionLocal()
    try:
        db.query(RemediationExecutionModel).delete()
        db.query(FailureAnalysisModel).delete()
        db.query(JobRunModel).delete()
        db.query(JobModel).delete()
        db.commit()

        # Seed 1 Mock SAP job run
        job_mock = JobModel(job_name="Z_MOCK_JOB", platform="MOCK_SAP")
        run_mock = JobRunModel(id=100, job_name="Z_MOCK_JOB", run_count=1, status="FAILED", platform="MOCK_SAP")
        db.add(job_mock)
        db.add(run_mock)

        # Seed 1 SAP BTP job run
        job_btp = JobModel(job_name="AI_AGENT_FAILURE_TEST", platform="SAP_BTP")
        run_btp = JobRunModel(id=200, job_name="AI_AGENT_FAILURE_TEST", run_count=2, status="FAILED", platform="SAP_BTP")
        db.add(job_btp)
        db.add(run_btp)

        db.commit()
    finally:
        db.close()

def test_data_isolation_by_platform():
    # Query stats for MOCK_SAP
    res_mock_stats = client.get("/api/stats?platform=MOCK_SAP")
    assert res_mock_stats.status_code == 200
    assert res_mock_stats.json()["total_jobs"] == 1

    # Query stats for SAP_BTP
    res_btp_stats = client.get("/api/stats?platform=SAP_BTP")
    assert res_btp_stats.status_code == 200
    assert res_btp_stats.json()["total_jobs"] == 1

    # Query jobs list for MOCK_SAP
    res_mock_jobs = client.get("/api/jobs?platform=MOCK_SAP")
    assert res_mock_jobs.status_code == 200
    mock_list = res_mock_jobs.json()
    assert len(mock_list) == 1
    assert mock_list[0]["job_name"] == "Z_MOCK_JOB"

    # Query jobs list for SAP_BTP
    res_btp_jobs = client.get("/api/jobs?platform=SAP_BTP")
    assert res_btp_jobs.status_code == 200
    btp_list = res_btp_jobs.json()
    assert len(btp_list) == 1
    assert btp_list[0]["job_name"] == "AI_AGENT_FAILURE_TEST"

def test_environment_switch_endpoint():
    res_switch = client.post("/api/environment/switch?platform=MOCK_SAP")
    assert res_switch.status_code == 200
    assert res_switch.json()["status"] == "SUCCESS"
    assert res_switch.json()["platform"] == "MOCK_SAP"

def test_btp_single_step_policy_rule():
    policy = JobRemediationPolicy()
    
    # Approved transient failure on BTP -> RESTART_FROM_START
    analysis_transient = FailureAnalysisSchema(
        failure_category="RFC_ERROR",
        confidence=0.95,
        root_cause_summary="BTP HTTP timeout",
        evidence=["504 Gateway Timeout"],
        recommended_action="Restart HTTP action",
        restart_mode="E",
        restart_strategy="RESTART_FROM_FAILED_STEP",
        reason="Retry HTTP call",
        platform="SAP_BTP"
    )
    job_details_btp = JobRunDetailSchema(
        id=200,
        job_name="AI_AGENT_FAILURE_TEST",
        run_count=2,
        platform="SAP_BTP",
        status="FAILED",
        start_time="2026-09-02T12:00:00Z",
        return_code=6,
        job_user="SAP_BTP",
        retry_count=0,
        max_retries=2,
        restart_allowed=True
    )
    decision = policy.evaluate(analysis_transient, job_details_btp)
    assert decision.policy_decision == "APPROVED"
    assert decision.restart_strategy == "RESTART_FROM_START"
    assert decision.restart_mode == "A"

    # Unsafe auth failure on BTP -> DO_NOT_RESTART
    analysis_auth = FailureAnalysisSchema(
        failure_category="AUTHORIZATION_FAILURE",
        confidence=0.98,
        root_cause_summary="User lacks authorization",
        evidence=["401 Unauthorized"],
        recommended_action="Escalate to human",
        restart_mode="NONE",
        restart_strategy="DO_NOT_RESTART",
        reason="Security policy block",
        platform="SAP_BTP"
    )
    decision_auth = policy.evaluate(analysis_auth, job_details_btp)
    assert decision_auth.policy_decision == "REJECTED"
    assert decision_auth.restart_strategy == "DO_NOT_RESTART"
    assert decision_auth.action == "ESCALATE"
