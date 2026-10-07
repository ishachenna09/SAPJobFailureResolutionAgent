# Phase 1 Update — Replace Mock Job Status Fetching with Real SAP BTP Job Scheduling Service

## Context

Phase 1 of the Job Failure Resolution Agent is already implemented and working with Mock SAP.

Current Phase 1 flow:

```text
SAP/Mock SAP execution
        ↓
Agent receives/identifies job
        ↓
Agent investigates job
        ↓
Agent reads job status/logs
        ↓
Agent recognizes SUCCESS / FAILED
        ↓
AI diagnoses root cause for failures
```

I have now created **real SAP BTP Job Scheduling Service jobs** in my SAP BTP Trial account.

I have the following SAP credentials/configuration:

```env
SAP_BASE_URL=
SAP_CLIENT_ID=
SAP_CLIENT_SECRET=
```

The exact values will be supplied through `.env` / environment variables. Never hardcode or expose secrets.

## Objective of this task

Replace the current Phase 1 Mock SAP job-status/run retrieval with the **real SAP BTP Job Scheduling Service REST API**, while preserving the existing Phase 1 agent flow and UI.

This task is ONLY for the Phase 1 SAP integration/status-fetching change.

Do NOT implement autonomous restart/remediation yet. That is Phase 2.

Do NOT redesign the UI.

Do NOT rewrite working Phase 1 logic unnecessarily.

Do NOT remove Mock SAP support.

---

# 1. Target SAP service

Use:

**SAP BTP Job Scheduling Service**

Primary official documentation:

- https://help.sap.com/docs/job-scheduling/sap-job-scheduling-service/rest-apis
- https://help.sap.com/docs/job-scheduling/sap-job-scheduling-service/retrieve-job-schedule
- https://help.sap.com/docs/job-scheduling/sap-job-scheduling-service/retrieve-job-run-logs
- SAP Business Accelerator Hub: https://api.sap.com/api/sap-btpjss-admin-v1/overview

Important:

This is the **SAP BTP Job Scheduling Service**, not the S/4HANA `BC_EXT_APPJOB_MANAGEMENT` API.

Do not mix those APIs.

---

# 2. Keep the existing SAP abstraction

Inspect the current project first.

If the project already has an abstraction such as:

```python
class SAPJobService:
    ...
```

keep it.

Add a real implementation such as:

```python
class BTPJobSchedulingService(SAPJobService):
    ...
```

Architecture:

```text
SAPJobService
     │
     ├── MockSAPJobService
     │       ↓
     │   Local Mock SAP
     │
     └── BTPJobSchedulingService
             ↓
       SAP BTP Job Scheduling Service
```

The agent must depend on the abstraction, not directly on raw SAP HTTP requests.

---

# 3. Configuration

Use environment variables:

```env
JOB_PLATFORM=mock

SAP_BASE_URL=
SAP_CLIENT_ID=
SAP_CLIENT_SECRET=

SAP_JOB_LOOKBACK_MINUTES=30
SAP_JOB_MAX_RUNS=100
```

For real SAP mode:

```env
JOB_PLATFORM=sap_btp
```

For local Mock SAP mode:

```env
JOB_PLATFORM=mock
```

Never expose SAP credentials to React/frontend code.

Never log:

- client secret
- OAuth access token
- authorization header
- other credentials

---

# 4. Authentication

Use the authentication mechanism provided by the SAP BTP Job Scheduling Service instance/service binding.

Do not guess an OAuth token URL if it is already available in the service binding or configuration.

If the current credentials represent OAuth2 client credentials, implement token acquisition using the documented SAP configuration.

Keep token acquisition in a dedicated client/auth service so it can be reused for all SAP requests.

Example conceptual structure:

```python
class SAPAuthClient:
    async def get_access_token(self) -> str:
        ...
```

Cache tokens until expiry when appropriate rather than requesting a new token for every API call.

---

# 5. Real SAP job retrieval flow

The backend should retrieve recent executions from SAP using the documented Job Scheduling Service APIs.

Conceptual flow:

```text
GET /scheduler/jobs
        ↓
GET /scheduler/jobs/{jobId}/schedules
        ↓
GET /scheduler/jobs/{jobId}/schedules/{scheduleId}/runs
        ↓
Normalize SAP run information
        ↓
Existing Phase 1 status classification
        ↓
Existing AI diagnosis for failures
```

SAP documents the job, schedule and run APIs in the Job Scheduling Service REST API documentation.

Do not invent endpoint paths or fields; verify them against the official SAP documentation.

---

# 6. Get jobs

Implement a method equivalent to:

```python
async def get_jobs(...):
    ...
```

It should call the documented SAP Job Scheduling Service jobs endpoint and retrieve the configured jobs.

Preserve SAP job identifiers.

At minimum retain:

```text
jobId
jobName / name, where supplied
job description, where supplied
```

Do not assume that job name is globally unique if SAP supplies a stronger identifier.

---

# 7. Get schedules for each job

For each relevant job, retrieve its schedules using the documented schedules endpoint.

Preserve:

```text
jobId
scheduleId
schedule metadata
```

Do not assume one job has exactly one schedule.

The implementation must support multiple schedules.

---

# 8. Get recent execution/run information

For each relevant schedule, retrieve recent runs using the documented SAP endpoint:

```text
GET /scheduler/jobs/{jobId}/schedules/{scheduleId}/runs
```

Use the SAP run information as the source of truth.

Do not fabricate run statuses in the frontend.

---

# 9. SAP run fields

The implementation should preserve SAP's documented run fields where available, including concepts such as:

```text
runId
runText
httpStatus
executionTimestamp
runStatus
runState
scheduleTimestamp
completionTimestamp
```

SAP's documented examples show successful executions using values such as:

```text
runStatus = COMPLETED
runState = SUCCESS
httpStatus = 200
```

and failed/request-error executions can have states such as:

```text
runState = ERROR
runState = REQUEST_ERROR
```

Use the current official SAP documentation as the source of truth for exact response structure.

Do not assume the raw HTTP response status of the API request is the same thing as the status of the scheduled job execution.

This distinction is critical.

---

# 10. Normalize SAP data into the existing domain model

Do not pass raw SAP JSON throughout the application.

Create a normalized internal model, for example:

```python
class JobExecution:
    provider: str
    job_id: str
    job_name: str
    schedule_id: str
    run_id: str
    status: str
    run_state: str | None
    http_status: int | None
    run_text: str | None
    execution_timestamp: datetime | None
    completion_timestamp: datetime | None
```

Use the actual existing project's model if one already exists.

Preserve raw SAP data where useful for debugging/audit, but do not make the UI depend directly on SAP-specific response structure.

---

# 11. Status classification

Replace the current Mock SAP status source with SAP data, but preserve the current Phase 1 classification behavior.

### Success

A typical SAP success result is:

```text
runState = SUCCESS
runStatus = COMPLETED
httpStatus = 200
```

Treat the documented SAP success state as SUCCESS.

Do NOT define success solely as:

```text
HTTP 200
```

because the HTTP 200 may refer to the API request itself rather than the scheduled job execution.

### Failed

Examples include documented execution states such as:

```text
runState = ERROR
runState = REQUEST_ERROR
```

and/or a non-success execution HTTP status.

Use the execution fields together.

---

# 12. Existing operational rules

Preserve the existing Phase 1 operational rules, but make them consume the normalized real SAP execution data.

## Rule 1 — Successful run

Typical:

```text
runState = SUCCESS
runStatus = COMPLETED
httpStatus = 200
```

Action:

```text
record clean status
skip remediation
```

## Rule 2 — Fixable failure

Recognize only explicitly configured transient failure patterns such as:

```text
504 Gateway Timeout
Network Timeout
Temporary connection failure
```

Use:

```text
httpStatus
runState
runText
```

Do NOT classify every 5xx as fixable.

For this phase, only classify and route to the existing remediation logic; do not execute restart.

## Rule 3 — Severe failure

Examples:

```text
401 Unauthorized
403 Forbidden
500 Internal Error
structural database errors
unknown permanent errors
```

Do not implement restart here.

Route to the existing escalation/diagnosis behavior.

---

# 13. Current real SAP test jobs

I have already created two real SAP BTP Job Scheduling Service jobs.

### Test Job A

```text
AI_AGENT_SUCCESS_TEST
```

Its Action returns:

```text
HTTP 200
```

Expected:

```text
SUCCESS
```

No remediation.

### Test Job B

```text
AI_AGENT_FAILURE_TEST
```

Its Action returns:

```text
HTTP 500
```

Expected for current rules:

```text
FAILED / SEVERE FAILURE
```

No restart in this task.

If a Rule 2 test is later needed, use/create a job whose Action returns:

```text
HTTP 504
```

Expected:

```text
FIXABLE FAILURE
```

Again: do not implement restart in this phase.

---

# 14. Logs

Where required, retrieve execution/run log details using the SAP Job Scheduling Service log APIs documented by SAP.

SAP documents run-log retrieval, including the runs endpoint and schedule/log retrieval options.

Use the existing project's log representation where possible.

The agent should receive meaningful execution information such as:

```text
runText
runState
httpStatus
executionTimestamp
completionTimestamp
```

and additional logs when available.

Do not create frontend-only fake logs.

---

# 15. Pagination

Implement pagination according to the SAP API behavior.

Do not assume all jobs, schedules, or runs fit in a single response.

Respect any documented pagination fields/headers used by the current API.

Do not create an infinite pagination loop.

Stop when the documented next-page mechanism indicates there are no more results.

---

# 16. Recent execution window

The agent should focus on recent executions rather than processing an entire historical database repeatedly.

Use configurable values such as:

```env
SAP_JOB_LOOKBACK_MINUTES=30
SAP_JOB_MAX_RUNS=100
```

Use SAP execution timestamps to determine which runs are recent.

Preserve the existing project's behavior if it already has equivalent filtering.

---

# 17. Deduplication

A scheduled execution must not be processed repeatedly.

Use SAP's `runId` as the execution identity where appropriate.

Persist enough information to determine whether a run has already been processed.

Example:

```text
provider
job_id
schedule_id
run_id
```

must form a stable identity.

If the same run is returned again on a later fetch:

```text
DO NOT create another agent execution
DO NOT create duplicate failure records
DO NOT run duplicate AI analysis
```

This prepares the system for future event-driven automation.

---

# 18. Frontend requirement

Do NOT redesign the existing UI.

Do NOT change the existing visual design.

Do NOT add new dashboards for this task.

Only update the backend data source so the existing UI receives real SAP BTP execution information.

If the existing UI already displays:

```text
jobName
status
runCount
error
timestamp
```

map the normalized SAP data into those existing fields.

Do not expose SAP client secrets to the browser.

---

# 19. Existing SAP Event Simulator behavior

Keep the current simulator UI unchanged unless a tiny data-binding change is required.

When real SAP mode is enabled:

```text
Frontend
   ↓
Backend API
   ↓
BTPJobSchedulingService
   ↓
SAP BTP
```

The frontend must not call SAP directly.

Do not add hardcoded job fallback data.

If SAP mode is configured but SAP is unavailable, return a meaningful backend error/state.

---

# 20. Mock SAP must remain available

Do not delete Mock SAP.

The project must still support:

```env
JOB_PLATFORM=mock
```

This remains necessary for deterministic Phase 2 testing later.

For real SAP:

```env
JOB_PLATFORM=sap_btp
```

The same agent/service interface should work with either implementation.

---

# 21. Error handling

Handle gracefully:

```text
OAuth/token failure
401 from SAP
403 from SAP
SAP API timeout
SAP API unavailable
invalid response
empty jobs
empty schedules
empty runs
pagination failure
rate limiting
```

Do not crash the application because SAP is temporarily unavailable.

Return structured application errors and preserve the existing API contract where possible.

---

# 22. Logging

Backend logs should include operational information such as:

```text
SAP BTP integration enabled
Fetching SAP jobs
Fetching schedules
Fetching recent runs
Received N job executions
Processing run <runId>
Run classification: SUCCESS / FIXABLE / SEVERE
AI analysis started
```

Never log credentials or access tokens.

---

# 23. AI integration

Do not redesign the existing AI analysis.

Only change its input source from Mock SAP to normalized real SAP execution data.

Example inputs:

```text
job name
run id
run state
run status
HTTP status of execution
run text
execution time
completion time
logs/details if available
```

Keep the existing structured AI response format.

Do not implement unrestricted tool execution by the LLM.

---

# 24. Do NOT implement Phase 2 here

Do NOT implement:

```text
JobRestart
automatic restart
restart strategy
restart-from-start
restart-from-failed-step
retry loops
post-restart validation
```

Those belong to Phase 2 after real job status fetching is confirmed.

This task only establishes the real SAP execution/status/log input pipeline for Phase 1.

---

# 25. Tests

Add unit/integration tests using realistic SAP BTP response fixtures.

### Test 1 — SUCCESS

```text
runState = SUCCESS
runStatus = COMPLETED
httpStatus = 200
```

Expected:

```text
SUCCESS
```

### Test 2 — transient timeout

```text
runState = ERROR
httpStatus = 504
runText contains Gateway Timeout
```

Expected:

```text
FIXABLE_FAILURE
```

No restart.

### Test 3 — 500 failure

```text
runState = ERROR
httpStatus = 500
runText contains Internal Error
```

Expected:

```text
SEVERE_FAILURE
```

### Test 4 — authorization

```text
httpStatus = 401
```

Expected:

```text
SEVERE_FAILURE
```

### Test 5 — duplicate run

Same `runId` returned twice.

Expected:

```text
one execution record
one AI analysis
```

### Test 6 — SAP unavailable

Expected:

```text
graceful integration error
```

### Test 7 — pagination

Multiple pages of job/schedule/run results should be handled correctly.

---

# 26. Manual verification

After implementation:

1. Configure `JOB_PLATFORM=sap_btp`.
2. Start the backend.
3. Start the frontend.
4. Open the existing SAP Event Simulator / job view.
5. Confirm jobs are coming from the real SAP BTP API.
6. Confirm `AI_AGENT_SUCCESS_TEST` is recognized as SUCCESS.
7. Confirm `AI_AGENT_FAILURE_TEST` is recognized as FAILED/SEVERE.
8. Confirm the existing AI diagnosis still works for failures.
9. Confirm no duplicate jobs/executions appear.
10. Confirm SAP credentials are not exposed in browser/network responses.
11. Confirm switching back to `JOB_PLATFORM=mock` still works.
12. Confirm the UI design remains unchanged.

---

# 27. Definition of done

The Phase 1 SAP integration update is complete when:

```text
SAP BTP Job Scheduling Service
        ↓
Authenticate
        ↓
Get jobs
        ↓
Get schedules
        ↓
Get recent runs
        ↓
Normalize SAP execution data
        ↓
Recognize SUCCESS / FAILED
        ↓
Existing operational rules
        ↓
Existing AI diagnosis
        ↓
Existing UI
```

and all of the following remain true:

- No hardcoded frontend jobs are used as a fallback.
- No duplicate executions are created.
- Mock SAP still works.
- Real SAP BTP mode works.
- SAP secrets stay backend-only.
- Existing Phase 1 UI remains visually unchanged.
- Existing Phase 1 AI diagnosis remains functional.
- Phase 2 can later consume the preserved SAP `job_id`, `schedule_id`, `run_id`, status and log data.

---

# 28. Final implementation instruction

Before changing code:

1. Inspect the existing Phase 1 codebase.
2. Identify the current Mock SAP adapter.
3. Identify the current job/status domain model.
4. Identify how Phase 1 currently retrieves jobs/logs.
5. Identify existing API endpoints used by the UI.
6. Identify existing database models.
7. Identify existing AI input/output schemas.
8. Identify existing environment/configuration handling.

Then implement the **smallest required change** to add `BTPJobSchedulingService`.

At the end provide:

- files changed
- configuration changes
- new SAP adapter methods
- SAP endpoints used
- data mapping from SAP → internal model
- tests added
- test results
- exact commands to run in Mock mode
- exact commands to run in SAP BTP mode
- any SAP-side configuration that is still required

Do not make unrelated architectural or UI changes.

## Official SAP references

Use official SAP sources as the source of truth:

- SAP Job Scheduling Service REST APIs:
  https://help.sap.com/docs/job-scheduling/sap-job-scheduling-service/rest-apis
- Retrieve Job Schedule:
  https://help.sap.com/docs/job-scheduling/sap-job-scheduling-service/retrieve-job-schedule
- Retrieve Job Run Logs:
  https://help.sap.com/docs/job-scheduling/sap-job-scheduling-service/retrieve-job-run-logs
- SAP Business Accelerator Hub:
  https://api.sap.com/api/sap-btpjss-admin-v1/overview

Do not invent undocumented SAP endpoints, fields, event names, or authentication behavior.

---

# Expected result

After this change, the application should be able to use **real SAP BTP Job Scheduling Service execution data** for Phase 1 instead of depending on Mock SAP, while keeping Mock SAP available for development and Phase 2 testing.

The next phase will build autonomous restart and validation on top of these real execution identifiers and status/log APIs.
