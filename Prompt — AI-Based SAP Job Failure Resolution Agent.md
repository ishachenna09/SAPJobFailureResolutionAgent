# Build an AI-Based SAP Job Failure Resolution Agent — End-to-End POC

## 1. Project objective

I need you to design and implement an **AI-based autonomous Job Failure Resolution Agent** as an enterprise POC.

The business problem statement is:

- Batch jobs
- ETL failures
- SAP jobs
- Informatica jobs
- Scheduled tasks

Actions to automate:

1. Check the failed job
2. Analyze the error
3. Restart/re-execute the job when safe
4. Validate whether the restarted job succeeded
5. Update/escalate the ticket/result

Internal ticket analysis indicates that **job failures are one of the largest root-cause categories**.

For this POC, the primary focus is:

> **SAP application/background job failures**

The goal is NOT merely to build a chatbot that tells an operator what to do.

The goal is to build an **autonomous agent capable of detecting a failed SAP job, investigating it, deciding whether it is safe to remediate, restarting/re-executing the job when an approved remediation exists, monitoring the restarted execution, validating success, and escalating when automatic resolution is unsafe or unsuccessful.**

---

# 2. Critical project principles

Follow these principles throughout implementation.

## Principle 1 — Autonomous remediation, not advisory-only

The agent must be capable of actually performing:

```text
Detect failure
→ Investigate
→ Analyze
→ Decide
→ Restart
→ Monitor
→ Validate
→ Resolve / Escalate
```

It must NOT stop at:

```text
"Please restart the job manually."
```

---

## Principle 2 — LLM must NOT directly control SAP

Use the LLM for:

- failure classification
- root-cause interpretation
- extracting meaning from logs
- selecting a remediation candidate from a predefined action set

Do NOT allow the LLM to invent arbitrary SAP API calls or arbitrary operations.

Required architecture:

```text
SAP Event
    ↓
Job Investigation
    ↓
LLM Failure Analysis
    ↓
Structured Decision
    ↓
Deterministic Policy / Safety Engine
    ↓
Approved SAP Operation
```

Example:

```json
{
  "failure_category": "TRANSIENT_DATABASE_LOCK",
  "confidence": 0.96,
  "recommended_action": "RESTART",
  "restart_mode": "E"
}
```

The policy engine must independently decide whether this recommendation is allowed.

---

## Principle 3 — deterministic rules are the source of truth for execution

The LLM explains and classifies.

The policy engine controls execution.

Example:

```text
IF
  failure_category = TRANSIENT_DATABASE_LOCK
  AND confidence >= 0.90
  AND job.restart_allowed = true
  AND retry_count < max_retries
  AND environment_policy permits auto-restart

THEN
  execute SAP JobRestart

ELSE
  escalate
```

Do not allow the LLM to bypass this policy.

---

# 3. SAP environment constraint

I currently do NOT have credentials/access to my company's SAP system.

Therefore:

## We will build the POC using TWO layers

### Layer A — real SAP knowledge/contracts

Use SAP's current official documentation to model the real interface and semantics.

Primary target:

```text
SAP S/4HANA Cloud Public Edition
```

Primary application-job interface:

```text
BC_EXT_APPJOB_MANAGEMENT
```

Relevant documented operations include:

```text
JobHeaderSet
JobTemplateSet
JobStatusGet
JobinfoGet
JobParamValuesGet
JobParamValuesStructGet
JobRestart
JobSchedule
JobScheduleCheck
JobAbort
JobCancel
JobStatusInfoSet
```

The current SAP documentation describes `SAP_COM_0326` as the communication scenario for external application-job scheduling/integration in S/4HANA Cloud Public Edition. `SAP_COM_0064` is deprecated from release 2511 and should not be used as the primary design target. Use `SAP_COM_0326` in documentation/examples. 

### Layer B — local Mock SAP Runtime

Because I don't have a real S/4HANA tenant or company credentials, build a **local Mock SAP Job Runtime**.

The Mock SAP must behave according to the SAP-documented application-job contract and semantics rather than using arbitrary invented APIs.

This means:

```text
Mock SAP API
     ≈
SAP documented API contract
```

The agent must not be tightly coupled to the mock.

---

# 4. Final architecture

Implement this target architecture:

```text
                         ┌──────────────────────┐
                         │     SAP / Mock SAP    │
                         │                      │
                         │ Application Jobs     │
                         │ Job Steps            │
                         │ Job Logs              │
                         │ Parameters           │
                         │ Status               │
                         └──────────┬───────────┘
                                    │
                              JOB FAILURE
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Event / Notification │
                         │ Layer                │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ FastAPI Webhook      │
                         │ /events/job-failed   │
                         └──────────┬───────────┘
                                    │
                                    ▼
                       ┌─────────────────────────┐
                       │ Job Resolution Agent    │
                       │                         │
                       │ 1. Investigate Job      │
                       │ 2. Fetch Details        │
                       │ 3. Fetch Logs           │
                       │ 4. Fetch Parameters     │
                       │ 5. Analyze Failure      │
                       └─────────────┬───────────┘
                                     │
                                     ▼
                           ┌──────────────────┐
                           │   LLM Analyzer   │
                           └────────┬─────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Structured Decision │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Deterministic Policy │
                         │ / Safety Engine      │
                         └──────────┬───────────┘
                                    │
                    ┌───────────────┴────────────────┐
                    │                                │
              AUTO REMEDIATION                 HUMAN ESCALATION
                    │                                │
                    ▼                                ▼
             SAP JobRestart                    Diagnosis + Evidence
                    │
                    ▼
             Monitor Execution
                    │
                    ▼
           Validate Job/Step Status
               /          \
          SUCCESS          FAILURE
             │                │
             ▼                ▼
          RESOLVED         ESCALATE
```

---

# 5. Event-driven architecture requirement

I specifically want an **event-driven design**, not a polling-only solution.

Conceptually:

```text
SAP Job
   ↓
FAILED
   ↓
SAP event/message mechanism
   ↓
Event broker / queue
   ↓
Agent webhook
```

For the POC, because actual SAP Event Mesh/S/4HANA integration may not be available, implement a local event mechanism that behaves the same way.

For example:

```text
Mock SAP
   ↓
Job state changes to FAILED
   ↓
Generate SAP_JOB_FAILED event
   ↓
POST /events/sap/job-failed
   ↓
FastAPI Agent
```

Design the event interface so that a real SAP event/messaging connector can replace the mock later.

Do NOT claim that the local webhook itself is SAP Event Mesh.

Clearly separate:

```text
POC event simulator
```

from:

```text
Production SAP event integration
```

---

# 6. Mock SAP requirements

Create a complete local Mock SAP service using FastAPI.

It must support realistic application-job behavior.

Each job should contain:

```text
job_name
job_run_count
job_status
job_text
created_at
scheduled_at
start_time
end_time
job_user
steps
logs
parameters
retry_count
restart_allowed
environment
```

Supported statuses should include at least:

```text
SCHEDULED
READY
RUNNING
COMPLETED
FAILED
ABORTED
CANCELLED
```

Each job should have multiple steps.

Example:

```text
Z_CUSTOMER_LOAD

Step 1 → SUCCESS
Step 2 → SUCCESS
Step 3 → FAILED
Step 4 → NOT_EXECUTED
```

The mock should simulate:

- successful job
- transient failure
- repeated failure
- failure after restart
- successful restart
- non-retryable failure

---

# 7. Mock SAP API design

Create endpoints that model the SAP application-job API contract.

At minimum provide mock equivalents for:

```text
GET  /sap/opu/odata/.../JobStatusGet
GET  /sap/opu/odata/.../JobinfoGet
GET  /sap/opu/odata/.../JobHeaderSet
GET  /sap/opu/odata/.../JobTemplateSet
GET  /sap/opu/odata/.../JobParamValuesGet
POST /sap/opu/odata/.../JobRestart
POST /sap/opu/odata/.../JobSchedule
POST /sap/opu/odata/.../JobScheduleCheck
POST /sap/opu/odata/.../JobAbort
POST /sap/opu/odata/.../JobCancel
```

The exact internal implementation can be simplified, but the external contract should resemble SAP.

Document clearly which fields are modeled after SAP and which are POC-only additions.

---

# 8. JobRestart behavior

Model SAP's restart semantics.

Support:

```text
restart_mode = E
```

Meaning:

```text
restart from failed step
```

and:

```text
restart_mode = A
```

Meaning:

```text
restart after failed step
```

Example:

Original execution:

```text
Step 1 → SUCCESS
Step 2 → SUCCESS
Step 3 → FAILED
Step 4 → NOT_EXECUTED
```

When:

```text
JobRestart(mode="E")
```

simulate:

```text
Step 1 → already completed
Step 2 → already completed
Step 3 → RUNNING
Step 3 → SUCCESS
Step 4 → SUCCESS
```

When:

```text
JobRestart(mode="A")
```

simulate the documented "continue after failed step" behavior.

Document any simplifications.

---

# 9. Failure scenarios

Build multiple predefined scenarios.

At minimum:

### Scenario 1 — transient database lock

```text
Error:
DATABASE_LOCK_TIMEOUT
```

Expected behavior:

```text
AI classification:
TRANSIENT_DATABASE_LOCK

Policy:
AUTO_RESTART_ALLOWED

Action:
JobRestart(E)

Result:
SUCCESS
```

---

### Scenario 2 — transient network/RFC error

```text
Error:
RFC_TIMEOUT
```

Expected:

```text
classify
→ retry if policy allows
→ restart
→ validate
```

---

### Scenario 3 — authorization failure

```text
Error:
AUTHORIZATION_FAILURE
```

Expected:

```text
AI:
AUTHORIZATION_ERROR

Policy:
DO NOT AUTO RESTART

Result:
ESCALATE
```

---

### Scenario 4 — invalid business data

```text
Error:
INVALID_MASTER_DATA
```

Expected:

```text
DO NOT AUTO RESTART
ESCALATE
```

---

### Scenario 5 — repeated failure

```text
attempt 1 → FAILED
attempt 2 → FAILED
```

Expected:

```text
MAX_RETRIES_REACHED
→ STOP AUTOMATION
→ ESCALATE
```

---

### Scenario 6 — ABAP/program error

Example:

```text
ABAP_PROGRAM_ERROR
```

Expected:

```text
No automatic restart by default
→ escalate
```

---

# 10. LLM failure analyzer

Create an `AIService` abstraction so different providers can be configured.

Example:

```python
class AIService:
    async def analyze_job_failure(
        self,
        job_details,
        logs,
        parameters
    ):
        ...
```

The LLM must return structured JSON.

Example:

```json
{
  "failure_category": "TRANSIENT_DATABASE_LOCK",
  "root_cause_summary": "The job failed because a required database resource was temporarily locked.",
  "confidence": 0.96,
  "recommended_action": "RESTART",
  "restart_mode": "E",
  "reason": "The error is classified as transient and the job can safely retry from the failed step."
}
```

Use structured-output validation with Pydantic.

Never trust free-form LLM output.

---

# 11. Failure classification taxonomy

Create an initial deterministic/LLM-assisted taxonomy:

```text
TRANSIENT_DATABASE_LOCK
TRANSIENT_DATABASE_ERROR
NETWORK_TIMEOUT
RFC_ERROR
EXTERNAL_SYSTEM_TIMEOUT
AUTHORIZATION_ERROR
INVALID_BUSINESS_DATA
MISSING_CONFIGURATION
ABAP_PROGRAM_ERROR
SYSTEM_RESOURCE_ERROR
UNKNOWN_ERROR
```

Classify each into:

```text
AUTO_RESTART_CANDIDATE
MANUAL_REVIEW_REQUIRED
NON_RETRYABLE
```

Make this configurable rather than hard-coded everywhere.

---

# 12. Policy engine

Create a dedicated service:

```python
class JobRemediationPolicy:
    def evaluate(self, analysis, job):
        ...
```

The policy should check:

```text
failure category
LLM confidence
restart_allowed
current retry count
maximum retry count
environment
job criticality
restart mode
```

Example configuration:

```yaml
max_retries: 2

auto_restart_categories:
  - TRANSIENT_DATABASE_LOCK
  - NETWORK_TIMEOUT
  - RFC_ERROR

manual_categories:
  - AUTHORIZATION_ERROR
  - INVALID_BUSINESS_DATA
  - ABAP_PROGRAM_ERROR
  - UNKNOWN_ERROR
```

Make this external configuration.

---

# 13. Agent orchestration

Implement a Job Resolution workflow like:

```text
handle_job_failure_event()
        ↓
validate_event()
        ↓
deduplicate_event()
        ↓
get_job_status()
        ↓
get_job_info()
        ↓
get_logs()
        ↓
get_parameters()
        ↓
AI analysis
        ↓
Pydantic validation
        ↓
policy decision
        ↓
if AUTO_RESTART:
      JobRestart
      ↓
      monitor
      ↓
      validate
else:
      create escalation result
```

Use clear service boundaries.

---

# 14. Monitoring and validation

After restart:

```text
JobRestart
   ↓
RUNNING
   ↓
poll
   ↓
RUNNING
   ↓
poll
   ↓
COMPLETED / FAILED
```

Do not treat HTTP 200 from `JobRestart` as proof that the job succeeded.

Success must be determined by job status and step/application return codes.

Use:

```text
JobStatusGet
JobinfoGet
```

to validate.

Success should mean something like:

```text
job status = COMPLETED
AND
all required steps completed
AND
application return code indicates success
```

Document exactly how the POC defines success.

---

# 15. Event handling requirements

Implement:

```text
POST /events/sap/job-failed
```

Example payload:

```json
{
  "event_type": "SAP_JOB_FAILED",
  "job_name": "Z_CUSTOMER_LOAD",
  "job_run_count": "1001",
  "timestamp": "2026-08-20T10:30:00Z"
}
```

The endpoint must:

1. validate payload
2. acknowledge quickly
3. prevent duplicate processing
4. queue/background the resolution
5. record an execution ID

Do not perform the entire AI/remediation process synchronously inside the webhook request.

---

# 16. Queue/background processing

Use a lightweight queue.

For the POC choose one:

```text
Redis + Celery
```

or:

```text
Redis Streams
```

or a simple async worker if you want minimum infrastructure.

Prefer the simplest reliable approach.

The architecture should permit replacement with SAP Event Mesh later.

---

# 17. Database

Use PostgreSQL.

Create tables/models for at least:

```text
jobs
job_runs
job_steps
job_logs
job_events
failure_analyses
remediation_attempts
execution_history
```

Important audit data:

```text
job_name
run_count
failure_category
raw_error
AI_analysis
confidence
policy_decision
restart_mode
restart_attempt
restart_timestamp
final_status
validation_result
```

We need an audit trail for every autonomous action.

---

# 18. Deduplication/idempotency

This is mandatory.

The same event may arrive more than once.

Use something like:

```text
job_name + job_run_count + event_type
```

as an idempotency key.

The agent must not restart the same failed execution twice because the event was delivered twice.

---

# 19. Security

Design the real-SAP connector so that credentials are never hardcoded.

Use environment variables or a secrets manager.

Example:

```env
SAP_BASE_URL=
SAP_CLIENT_ID=
SAP_CLIENT_SECRET=
SAP_USERNAME=
SAP_PASSWORD=
```

Do not commit secrets.

For Mock SAP, use local auth if helpful, but make the real adapter ready for authenticated SAP HTTP calls.

Clearly document:

```text
POC authentication
vs
real SAP authentication
```

---

# 20. Real SAP integration abstraction

Create:

```text
SAPJobService
    |
    ├── MockSAPJobService
    |
    └── S4HANAJobService
```

The production-oriented implementation should use an HTTP client such as `httpx`.

Example:

```python
class S4HANAJobService(SAPJobService):
    ...
```

Map:

```text
get_status()
      → SAP JobStatusGet

get_details()
      → SAP JobinfoGet

get_logs()
      → SAP JobHeaderSet / related log expansion

get_parameters()
      → JobParamValuesGet / structured equivalent

restart_job()
      → JobRestart

schedule_job()
      → JobSchedule
```

Do not pretend this is connected to real SAP unless credentials are actually configured.

---

# 21. SAP BTP usage

We do NOT have a company's SAP S/4HANA credentials.

Use SAP BTP Trial only for developer-side SAP experimentation and learning.

Potentially use:

```text
SAP BTP
SAP BTP ABAP Environment
ABAP Cloud
SAP API/event development concepts
```

Do not claim BTP ABAP Environment is the same as S/4HANA.

The project must remain fully runnable locally without BTP access.

---

# 22. Do not depend on SAP Event Mesh for the local POC

If Event Mesh is not available in the free environment, do not block development.

Implement:

```text
Local event producer
+
FastAPI webhook
```

and make the event interface replaceable.

Later:

```text
SAP Event / Event Mesh
        ↓
same webhook/consumer layer
```

This is an architectural abstraction, not a claim that the local mock is Event Mesh.

---

# 23. Frontend

Build a small React UI to visualize the POC.

Pages/components:

### Dashboard

Show:

```text
Total jobs
Failed jobs
Auto-resolved
Escalated
Currently running remediation
Success rate
```

### Job Failure Detail

Show:

```text
Job name
Run count
Failed step
Status
Error/logs
AI diagnosis
Confidence
Recommended action
Policy decision
```

### Remediation Timeline

Example:

```text
10:00:01 Job failed
10:00:02 Failure event received
10:00:03 Logs retrieved
10:00:05 AI analysis completed
10:00:05 Policy approved restart
10:00:06 Restart requested
10:00:07 Job running
10:00:12 Job completed
10:00:13 Validation successful
10:00:13 Automatically resolved
```

### Escalated Failure

Show:

```text
Why automation was blocked
AI diagnosis
Evidence/logs
Recommended human action
Retry history
```

---

# 24. Technology stack

# Backend
  Python 3.12+
  FastAPI
  Pydantic
  httpx
  SQLAlchemy
  Alembic

# Background processing
  FastAPI BackgroundTasks

# Database
  PostgreSQL

# Frontend
  React
  TypeScript
  Tailwind css
  Lucid React
  Vite

# AI
  Groq 
  Gemini 
  Fallback loop 
  through an AIService abstraction

# Mock SAP
  FastAPI


Do NOT build mock SAP as a completely separate technology stack unnecessarily.

---

# 25. Repository structure

Create a professional structure similar to:

```text
sap-job-resolution-agent/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   │
│   │   ├── api/
│   │   │   ├── events.py
│   │   │   ├── jobs.py
│   │   │   └── health.py
│   │   │
│   │   ├── agents/
│   │   │   └── job_resolution_agent.py
│   │   │
│   │   ├── ai/
│   │   │   ├── base.py
│   │   │   └── provider.py
│   │   │
│   │   ├── sap/
│   │   │   ├── base.py
│   │   │   ├── mock_sap.py
│   │   │   └── s4hana.py
│   │   │
│   │   ├── policies/
│   │   │   └── remediation_policy.py
│   │   │
│   │   ├── services/
│   │   │   ├── investigation.py
│   │   │   ├── remediation.py
│   │   │   ├── monitoring.py
│   │   │   └── validation.py
│   │   │
│   │   ├── models/
│   │   ├── schemas/
│   │   └── workers/
│   │
│   ├── tests/
│   │
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   └── package.json
│
├── mock-sap/
│   ├── seed/
│   └── README.md
│
├── docs/
│   ├── architecture.md
│   ├── sap-api-mapping.md
│   ├── event-flow.md
│   ├── remediation-rules.md
│   └── real-sap-integration.md
│
├── docker-compose.yml
├── .env.example
├── README.md
└── Makefile
```

You can simplify this if necessary, but keep clear separation between:

```text
Agent
SAP adapter
Mock SAP
AI
Policy
Remediation
Validation
```

---

# 26. Docker

Make the POC easy to run:

```text
docker compose up
```

Services should ideally include:

```text
backend
frontend
postgres
redis
mock-sap
```

The system should be runnable without a real SAP account.

---

# 27. Required APIs in the application

At minimum:

```text
POST /events/sap/job-failed

GET /api/jobs
GET /api/jobs/{job_name}/{run_count}
GET /api/jobs/{job_name}/{run_count}/logs

POST /api/jobs/{job_name}/{run_count}/analyze
POST /api/jobs/{job_name}/{run_count}/restart

GET /api/executions/{execution_id}
GET /api/executions/{execution_id}/timeline
```

Mock SAP endpoints should live separately, for example:

```text
GET  /mock-sap/...
POST /mock-sap/...
```

or use SAP-like URL paths as documented above.

Keep mock-specific APIs separate from the agent's public APIs.

---

# 28. Demonstration flow

The final demo must support this exact scenario:

## Demo 1 — successful automatic resolution

1. Start a job in Mock SAP.
2. Job fails at Step 3 because of a transient database lock.
3. Mock SAP generates a failure event.
4. Agent receives event.
5. Agent retrieves job details.
6. Agent retrieves logs.
7. Agent retrieves parameters.
8. LLM classifies the failure.
9. Policy engine allows automatic restart.
10. Agent calls `JobRestart(E)`.
11. Mock SAP transitions job through RUNNING.
12. Failed step succeeds.
13. Remaining steps succeed.
14. Agent validates success.
15. UI displays `AUTO RESOLVED`.

## Demo 2 — unsafe failure

1. Job fails with authorization error.
2. Event received.
3. Agent analyzes.
4. Policy rejects auto-remediation.
5. No restart occurs.
6. UI displays `ESCALATED`.
7. Timeline shows why automation was blocked.

## Demo 3 — repeated failure

1. Job fails due to transient error.
2. Agent restarts.
3. Restart fails again.
4. Agent retries only according to policy.
5. Maximum retry count reached.
6. Agent stops.
7. Escalation generated.

---

# 29. Testing requirements

Create automated tests for:

### Unit tests

- failure classification
- Pydantic AI response validation
- policy decisions
- retry count
- idempotency
- restart mode
- validation logic

### Integration tests

```text
event
→ investigation
→ AI/mock response
→ policy
→ restart
→ monitoring
→ validation
```

### Failure tests

Test:

```text
network failure
SAP API timeout
duplicate event
invalid job
restart API failure
job remains running
job fails after restart
LLM returns malformed JSON
LLM confidence below threshold
```

---

# 30. Observability

Every remediation attempt must have structured logs.

Include:

```text
correlation_id
execution_id
job_name
run_count
event_id
failure_category
policy_decision
restart_attempt
final_status
```

Use structured JSON logs where possible.

---

# 31. No hallucinated SAP details

This is extremely important.

When implementing SAP integration:

- Use official SAP documentation.
- Do not invent SAP endpoint names.
- Do not invent field names.
- Do not invent authentication methods.
- Do not state that an event exists unless verified in official SAP documentation.
- Clearly label anything simulated.
- If SAP documentation differs by release/version, document the version.
- Prefer current official SAP Help Portal documentation over blogs/videos.

When uncertain about a SAP API, STOP and verify using the official documentation before coding it.

---

# 32. SAP resources to use

Use these as authoritative references:

### SAP External Application Job Integration / SAP_COM_0326

https://help.sap.com/docs/SAP_S4HANA_CLOUD/0f69f8fb28ac4bf48d2b57b9637e81fa/c0b4cf403f394cf3985e917f63d42952.html

This documents `SAP_COM_0326`, communication arrangement setup and the external application-job integration. SAP currently marks it as the successor to `SAP_COM_0064`. 

### SAP BTP — External Job Scheduling Operations

https://help.sap.com/docs/btp/sap-business-technology-platform/operations-for-external-job-scheduling-service

Use this as the primary reference for:

```text
JobStatusGet
JobinfoGet
JobHeaderSet
JobRestart
JobSchedule
JobScheduleCheck
JobAbort
JobCancel
parameters
```

### SAP BTP Trial

https://help.sap.com/docs/btp/sap-business-technology-platform/trial-accounts-and-free-tier

Use BTP Trial for developer experimentation. SAP's current documentation says trial accounts are for exploration and have restricted resources/services. 

### SAP BTP Cloud Foundry Trial Setup

https://help.sap.com/docs/btp/sap-business-technology-platform/getting-started-with-trial-account-in-cloud-foundry-environment

### SAP BTP ABAP Environment

https://help.sap.com/docs/ABAP_ENVIRONMENT/abap-environment

Use this for ABAP Cloud development and SAP-side experimentation. SAP describes BTP ABAP Environment as an environment for developing ABAP Cloud applications and extensions. 

### SAP Developers

https://developers.sap.com/

### SAP S/4HANA Cloud Public Edition Trial

https://www.sap.com/products/erp/s4hana/trial.html

Use this only for exploration where useful. Do not assume it provides unrestricted production-like API/integration capabilities.

---

# 33. Very important distinction about SAP BTP

Do NOT implement the project under the assumption:

```text
BTP Trial = S/4HANA
```

Instead:

```text
SAP BTP
    ↓
developer/integration/extension environment

S/4HANA
    ↓
ERP system containing application jobs
```

For this POC:

```text
BTP Trial
+
Local Mock SAP
+
Job Resolution Agent
```

is acceptable.

Later:

```text
BTP / Agent
+
Real company S/4HANA
```

will replace the mock.

---

# 34. Production migration design

Make the project easy to migrate from mock to real SAP.

Current:

```text
Job Resolution Agent
       ↓
MockSAPJobService
       ↓
Local Mock SAP
```

Future:

```text
Job Resolution Agent
       ↓
S4HANAJobService
       ↓
Real SAP
```

The agent business logic should not change.

Only:

```text
event connector
SAP adapter
authentication/configuration
```

should need to change.

---

# 35. Future extensibility

Although MVP is SAP, design interfaces that later allow:

```text
SAP
Informatica
ETL
Windows Scheduled Tasks
Linux jobs
Batch systems
```

For example:

```python
class JobPlatform(Protocol):
    ...
```

Then:

```text
SAPJobPlatform
InformaticaJobPlatform
GenericBatchJobPlatform
```

But DO NOT implement all of these now.

MVP = SAP only.

---

# 36. Ticket integration

The original business problem says "Update ticket".

Do not make ServiceNow a dependency of MVP.

For now create an abstract interface:

```python
class TicketService:
    async def update_resolution(...):
        ...
```

and provide:

```text
MockTicketService
```

that stores the resolution.

Later it can become:

```text
ServiceNowTicketService
```

or another ITSM implementation.

---

# 37. Non-functional requirements

The POC should demonstrate:

### Safety

No unauthorized autonomous restart.

### Idempotency

No duplicate restart because of duplicate events.

### Auditability

Every autonomous decision is recorded.

### Explainability

Show:

```text
what failed
why it failed
what AI concluded
why policy allowed/blocked action
what operation was executed
whether execution succeeded
```

### Configurability

Retry counts, retryable errors, job criticality, etc. must be configuration-driven.

### Testability

Mock SAP must support deterministic scenarios.

### Replaceability

Mock SAP must be replaceable with real SAP without changing the agent logic.

---

# 38. Deliverables I expect from you

Do not just generate code.

Provide:

1. Architecture diagram.
2. Detailed repository structure.
3. Complete backend implementation.
4. Complete Mock SAP implementation.
5. Complete event generator.
6. AI analyzer.
7. Policy engine.
8. SAP adapter interface.
9. Mock SAP adapter.
10. Real SAP adapter skeleton.
11. Job restart implementation.
12. Job monitoring implementation.
13. Job validation implementation.
14. Database models/migrations.
15. React dashboard.
16. Docker Compose.
17. `.env.example`.
18. Unit tests.
19. Integration tests.
20. API documentation.
21. SAP API mapping document.
22. Setup instructions.
23. Demo scenarios.
24. Production migration guide.

---

# 39. Implementation method

Do NOT try to generate the entire project blindly in one step.

Implement incrementally in this order:

```text
PHASE 1
Project skeleton
        ↓
PHASE 2
Mock SAP job model/API
        ↓
PHASE 3
Mock SAP event generator
        ↓
PHASE 4
FastAPI event receiver
        ↓
PHASE 5
SAP adapter abstraction
        ↓
PHASE 6
Job investigation service
        ↓
PHASE 7
LLM failure analyzer
        ↓
PHASE 8
Policy engine
        ↓
PHASE 9
Restart/remediation engine
        ↓
PHASE 10
Monitoring/validation
        ↓
PHASE 11
Database/audit trail
        ↓
PHASE 12
React dashboard
        ↓
PHASE 13
Dockerization
        ↓
PHASE 14
Tests
        ↓
PHASE 15
Real SAP connector skeleton
```

After every phase:

- explain what was implemented
- show files changed
- show how to run it
- show expected output
- provide tests
- do not proceed if the current phase is broken

---

# 40. First task

Start ONLY with:

## Phase 1 — architecture + project skeleton + Mock SAP design

Before generating the rest of the project, provide:

1. Final architecture.
2. Component responsibilities.
3. Repository structure.
4. Data model.
5. Mock SAP API design mapped to real SAP documented operations.
6. Event payload design.
7. Failure scenarios.
8. Implementation plan.
9. Required dependencies.
10. Environment setup instructions.

Then implement the Phase 1 skeleton.

Do NOT use fake SAP API names that are unsupported by SAP documentation.

Where something is simulated, explicitly mark it:

```text
[MOCK / POC ONLY]
```

Where something corresponds to a documented SAP interface, mark it:

```text
[SAP DOCUMENTED]
```

The final system must be runnable locally with:

```bash
docker compose up
```

and the first end-to-end demo should eventually be:

```text
Mock SAP Job
→ Job Failure
→ SAP_JOB_FAILED event
→ Agent receives event
→ Agent reads job/logs
→ AI analyzes
→ Policy approves
→ JobRestart(E)
→ Job runs
→ Validation succeeds
→ AUTO RESOLVED
```

Do not build ServiceNow into the core MVP.

Do not wait for company SAP credentials.

Do not claim that the Mock SAP is a real SAP system.

Build the architecture so the mock can later be replaced by a real SAP S/4HANA integration using the documented application-job interfaces.