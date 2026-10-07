import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from app.sap.btp_sap import BTPJobSchedulingService
from app.sap.sap_auth import SAPAuthClient
from app.schemas.job import JobRunDetailSchema

@pytest.mark.asyncio
async def test_sap_auth_client_token_caching():
    auth = SAPAuthClient(
        base_url="https://mock-btp.authentication.sap.com",
        client_id="test_client",
        client_secret="test_secret",
        token_url="https://mock-btp.authentication.sap.com/oauth/token"
    )
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "access_token": "mock_bearer_token_12345",
        "expires_in": 3600,
        "token_type": "Bearer"
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        
        token1 = await auth.get_access_token()
        assert token1 == "mock_bearer_token_12345"
        assert mock_post.call_count == 1
        
        # Second call should use cached token without HTTP request
        token2 = await auth.get_access_token()
        assert token2 == "mock_bearer_token_12345"
        assert mock_post.call_count == 1

@pytest.mark.asyncio
async def test_btp_run_classification_success():
    service = BTPJobSchedulingService(base_url="https://job-scheduler.cfapps.sap.com")
    
    raw_job = {"jobId": "JOB-101", "name": "AI_AGENT_SUCCESS_TEST", "description": "Test Success Execution"}
    raw_sched = {"scheduleId": "SCHED-1", "jobId": "JOB-101"}
    raw_run = {
        "runId": "4001",
        "runStatus": "COMPLETED",
        "runState": "SUCCESS",
        "httpStatus": 200,
        "runText": "Execution finished successfully",
        "executionTimestamp": "2026-09-01T12:00:00Z"
    }
    
    detail: JobRunDetailSchema = service.normalize_sap_run(raw_job, raw_sched, raw_run)
    assert detail.job_name == "AI_AGENT_SUCCESS_TEST"
    assert detail.status == "SUCCESS"
    assert detail.return_code == 0
    assert detail.failed_step_number is None

@pytest.mark.asyncio
async def test_btp_run_classification_transient_timeout():
    service = BTPJobSchedulingService(base_url="https://job-scheduler.cfapps.sap.com")
    
    raw_job = {"jobId": "JOB-102", "name": "Z_VENDOR_SYNC", "description": "RFC Sync"}
    raw_sched = {"scheduleId": "SCHED-2", "jobId": "JOB-102"}
    raw_run = {
        "runId": "3001",
        "runStatus": "COMPLETED",
        "runState": "ERROR",
        "httpStatus": 504,
        "runText": "Gateway Timeout: RFC gateway sap_gw_prod lost connection after 15000ms",
        "executionTimestamp": "2026-09-01T12:05:00Z"
    }
    
    detail: JobRunDetailSchema = service.normalize_sap_run(raw_job, raw_sched, raw_run)
    assert detail.job_name == "Z_VENDOR_SYNC"
    assert detail.status == "FAILED"
    assert detail.return_code == 6
    assert detail.failed_step_number == 2

@pytest.mark.asyncio
async def test_btp_run_classification_500_failure():
    service = BTPJobSchedulingService(base_url="https://job-scheduler.cfapps.sap.com")
    
    raw_job = {"jobId": "JOB-103", "name": "AI_AGENT_FAILURE_TEST", "description": "Test Severe Failure"}
    raw_sched = {"scheduleId": "SCHED-3", "jobId": "JOB-103"}
    raw_run = {
        "runId": "5001",
        "runStatus": "COMPLETED",
        "runState": "ERROR",
        "httpStatus": 500,
        "runText": "HTTP 500 Internal Server Error in backend execution",
        "executionTimestamp": "2026-09-01T12:10:00Z"
    }
    
    detail: JobRunDetailSchema = service.normalize_sap_run(raw_job, raw_sched, raw_run)
    assert detail.job_name == "AI_AGENT_FAILURE_TEST"
    assert detail.status == "FAILED"
    assert detail.return_code == 8
    assert detail.failed_step_number == 1

@pytest.mark.asyncio
async def test_btp_run_classification_authorization_error():
    service = BTPJobSchedulingService(base_url="https://job-scheduler.cfapps.sap.com")
    
    raw_job = {"jobId": "JOB-104", "name": "Z_FIN_POSTING", "description": "Financial Posting"}
    raw_sched = {"scheduleId": "SCHED-4", "jobId": "JOB-104"}
    raw_run = {
        "runId": "2001",
        "runStatus": "COMPLETED",
        "runState": "ERROR",
        "httpStatus": 401,
        "runText": "ERROR: AUTHORIZATION_FAILURE - User lacks permission F_BKPF_BUK",
        "executionTimestamp": "2026-09-01T12:15:00Z"
    }
    
    detail: JobRunDetailSchema = service.normalize_sap_run(raw_job, raw_sched, raw_run)
    assert detail.job_name == "Z_FIN_POSTING"
    assert detail.status == "FAILED"
    assert detail.return_code == 12
    assert detail.failed_step_number == 1
    assert detail.restart_allowed is False

@pytest.mark.asyncio
async def test_btp_fetch_recent_executions_flow():
    service = BTPJobSchedulingService(base_url="https://job-scheduler.cfapps.sap.com")
    
    jobs_response = [{"jobId": "J1", "name": "AI_AGENT_SUCCESS_TEST", "description": "Success Test"}]
    schedules_response = [{"scheduleId": "S1", "jobId": "J1"}]
    runs_response = [
        {"runId": "1001", "runStatus": "COMPLETED", "runState": "SUCCESS", "httpStatus": 200, "runText": "OK"}
    ]
    logs_response = [{"logText": "Action executed successfully", "level": "INFO"}]

    async def mock_make_request(method, path, params=None):
        if "jobs/J1/schedules/S1/runs/1001/logs" in path:
            return logs_response
        elif "jobs/J1/schedules/S1/runs" in path:
            return runs_response
        elif "jobs/J1/schedules" in path:
            return schedules_response
        elif "jobs" in path:
            return jobs_response
        return []

    with patch.object(service, "_make_request", side_effect=mock_make_request):
        executions = await service.fetch_recent_executions()
        assert len(executions) == 1
        assert executions[0].job_name == "AI_AGENT_SUCCESS_TEST"
        assert executions[0].status == "SUCCESS"

@pytest.mark.asyncio
async def test_btp_sap_unavailable_error_handling():
    service = BTPJobSchedulingService(base_url="https://job-scheduler.cfapps.sap.com")
    
    with patch.object(service, "_make_request", side_effect=Exception("SAP BTP Gateway Unavailable")):
        executions = await service.fetch_recent_executions()
        assert executions == []
