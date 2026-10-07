# AI-Based SAP Job Failure Resolution Agent — End-to-End POC

Autonomous Agent based application for enterprise SAP application job monitoring, failure investigation, status recognition, AI diagnosis, and policy-governed remediation.

## Phase 1 Completed Features

- **Layer A (Real SAP Knowledge/Contracts)**: Standard SAP S/4HANA `SAP_COM_0326` application-job interface semantics (`JobStatusGet`, `JobinfoGet`, `JobHeaderSet`, `JobParamValuesGet`, `JobRestart`).
- **Layer B (Local Mock SAP Runtime)**: Complete mock service generating realistic SAP jobs (`Z_CUSTOMER_LOAD` DB lock failure, `Z_FIN_POSTING` auth error, `Z_INVOICE_BATCH` success).
- **Autonomous Job Status Recognition Engine**:
  - Event Webhook ingestion (`POST /events/sap/job-failed`, `POST /events/sap/job-status`).
  - Idempotency & deduplication keys (`job_name:run_count:event_type`).
  - Automatic SAP job detail, step timeline, parameter, and monospace log retrieval.
  - Job status recognition (`FAILED` / `SUCCESS` / `RUNNING`).
- **AI Failure Classifier**: Structured Pydantic schema validation for failure taxonomy (`TRANSIENT_DATABASE_LOCK`, `AUTHORIZATION_ERROR`, `RFC_ERROR`, `UNKNOWN_ERROR`).
- **Enterprise Operations Console (React UI)**:
  - Dashboard with summary metric cards, live operational feed, and recent job runs.
  - Job details console with tabs: Overview, Steps, Monospace Logs (with error highlights & search), Parameters, AI Diagnosis.
  - Interactive Job Simulator to trigger live SAP events and observe agent recognition in real time.

---

## Repository Structure

```text
c:\POCs\jobFailureResolutionAgent/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point & CORS
│   │   ├── config.py            # Settings & env vars
│   │   ├── db/                  # SQLite/PostgreSQL models & session
│   │   ├── sap/                 # SAPJobService & MockSAPJobService
│   │   ├── ai/                  # AIService & RuleBased/Gemini provider
│   │   ├── agents/              # JobResolutionAgent core engine
│   │   ├── api/                 # Events, Jobs, Mock SAP routers
│   │   └── schemas/             # Pydantic schemas
│   ├── tests/                   # Automated pytest suite
│   └── requirements.txt
├── frontend/
│   ├── src/                     # React + TypeScript + Tailwind UI
│   ├── index.html
│   ├── vite.config.ts
│   └── package.json
├── Prompt — AI-Based SAP Job Failure Resolution Agent.md
└── UI_SPEC_SAP_Job_Failure_Resolution_Agent.md
```

---

## How to Run Locally

### 1. Start the Backend API

```bash
cd backend
python -m pytest # Run automated tests
uvicorn app.main:app --reload --port 8000
```
Backend API interactive docs: `http://localhost:8000/docs`

### 2. Start the Frontend UI

```bash
cd frontend
npm run dev
```
Open `http://localhost:3000` in your browser.

---

## Demonstration Flow (Phase 1)

1. Open the UI at `http://localhost:3000`.
2. Click **Simulate SAP Job Event**.
3. Select **Scenario 1: Z_CUSTOMER_LOAD (Transient DB Lock)**.
4. Watch the agent instantly ingest the event, query Mock SAP via `SAP_COM_0326`, recognize the status as **FAILED**, and perform AI classification (`TRANSIENT_DATABASE_LOCK`).
5. Select **Scenario 3: Z_INVOICE_BATCH (Normal Execution)**.
6. Watch the agent recognize the status as **SUCCESS**.
