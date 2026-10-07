# Phase 2 — Environment Switch: Mock SAP vs SAP BTP

## Goal

Phase 1 is complete.

The application currently has:
- working Mock SAP behavior
- working real SAP BTP Job Scheduling Service integration

For Phase 2, **do not combine the two data sources**.

Add one environment switch in the top-right UI beside the existing `Agent ONLINE` indicator:

```text
Agent ONLINE    [ Mock SAP | SAP BTP ]
```

Only one platform is active at a time.

---

## 1. Architecture

```text
                    Job Resolution Agent
                            |
                       JobPlatform
                     /            \
                    /              \
              Mock SAP           SAP BTP
              Adapter             Adapter
                 |                  |
                 v                  v
            Mock data       Real BTP Job Scheduler
```

The agent/business logic must depend on the common `JobPlatform` abstraction, not directly on either implementation.

Create/standardize:

```python
class JobPlatform:
    async def get_jobs(...): ...
    async def get_job(...): ...
    async def get_logs(...): ...
    async def get_status(...): ...
    async def run_or_restart_job(...): ...
    async def validate_job(...): ...
```

Implement:

```text
MockSAPJobPlatform
BTPJobSchedulingPlatform
```

Do not spread `if platform == ...` logic throughout the application.

---

## 2. Top-right environment switch

Add a compact segmented/toggle control beside:

```text
Agent ONLINE
```

Example:

```text
Agent ONLINE     [ Mock SAP | SAP BTP ]
```

Use the existing application's visual language.

Do not redesign the dashboard or existing screens.

The currently selected environment must be obvious.

Optional subtle text:

```text
Environment: MOCK SAP
```

or:

```text
Environment: SAP BTP
```

---

## 3. Mock SAP mode

When `Mock SAP` is selected:

```text
UI Environment = MOCK SAP
Backend Platform = MockSAPJobPlatform
```

Use the existing Mock SAP implementation and its existing data/scenarios.

Keep support for multi-step jobs.

Example:

```text
Step 1 → SUCCESS
Step 2 → SUCCESS
Step 3 → FAILED
Step 4 → NOT EXECUTED
```

The existing Mock SAP restart strategy behavior remains available:

```text
RESTART_FROM_START
RESTART_FROM_FAILED_STEP
DO_NOT_RESTART
```

Do not call SAP BTP APIs in this mode.

---

## 4. SAP BTP mode

When `SAP BTP` is selected:

```text
UI Environment = SAP BTP
Backend Platform = BTPJobSchedulingPlatform
```

Use the existing real SAP BTP Job Scheduling Service integration.

Use only real BTP job/schedule/run information.

Do not use Mock SAP fallback data.

Do not silently switch to Mock SAP if SAP BTP is unavailable.

Show a proper connection/error state instead.

---

## 5. BTP jobs are single-step for the current POC

The current BTP jobs are HTTP-action jobs from SAP BTP Job Scheduling Service.

Do not invent multi-step execution semantics for them.

For the current BTP mode, treat the job as:

```text
Job
└── Step 1 / whole HTTP action
```

Therefore:

### Safe BTP failure

```text
FAILED
 ↓
Policy approves retry
 ↓
RESTART_FROM_START
```

### Unsafe BTP failure

```text
FAILED
 ↓
Policy rejects
 ↓
DO_NOT_RESTART
 ↓
ESCALATE
```

Do not show `RESTART_FROM_FAILED_STEP` for BTP jobs unless the actual BTP integration later provides genuine step-level restart information.

---

## 6. Mock SAP multi-step strategy

For Mock SAP, keep the richer strategy:

```text
FAILED JOB
    |
    v
Does the job have multiple meaningful steps?
    |
    +-- NO  → RESTART_FROM_START
    |
    +-- YES
          |
          v
       Inspect failed step
          |
          +-- safely restartable → RESTART_FROM_FAILED_STEP
          |
          +-- not safely restartable → RESTART_FROM_START
```

And always allow:

```text
unsafe/non-retryable failure
        ↓
DO_NOT_RESTART
        ↓
ESCALATE
```

---

## 7. Platform selection must be backend-aware

Do not make the switch visual-only.

The selected environment must control which backend service handles requests.

Example:

```text
Frontend
   ↓
selected platform
   ↓
Backend
   ↓
JobPlatform
   ↓
MockSAPJobPlatform OR BTPJobSchedulingPlatform
```

The backend must know which platform an execution belongs to.

---

## 8. Runtime configuration

Keep existing SAP credentials/configuration in environment variables.

Example:

```env
JOB_PLATFORM=sap_btp

SAP_BASE_URL=
SAP_CLIENT_ID=
SAP_CLIENT_SECRET=
```

The browser must never receive the SAP client secret or OAuth token.

If the project already has a configuration abstraction, extend it rather than creating a second configuration system.

---

## 9. UI data separation

When `Mock SAP` is selected:

```text
Failed Jobs → Mock only
Success Jobs → Mock only
History → Mock only
Remediations → Mock only
```

When `SAP BTP` is selected:

```text
Failed Jobs → BTP only
Success Jobs → BTP only
History → BTP only
Remediations → BTP only
```

Never show:

```text
Mock jobs + BTP jobs
```

in one operational list.

---

## 10. Platform-aware history

Every persisted job/run/remediation/history record must contain its platform/source.

Examples:

```text
platform = MOCK_SAP
```

or:

```text
platform = SAP_BTP
```

Use a source-aware identity such as:

```text
platform + provider_job_id + run_id
```

or the equivalent already used by the project.

Do not assume a job name alone is globally unique across both platforms.

---

## 11. Environment switching during an active remediation

If an SAP BTP remediation is running and the user switches to Mock SAP:

- the BTP remediation must continue in the backend
- the Mock SAP UI should now show only Mock SAP data
- the BTP execution must retain `platform = SAP_BTP`

If the user later switches back to SAP BTP, the latest BTP execution state must still be available.

Do not use the current UI selection to overwrite the platform identity of existing executions.

---

## 12. Backend unavailable behavior

### SAP BTP selected + backend/SAP unavailable

Show:

```text
SAP BTP connection unavailable.

Unable to retrieve jobs from SAP BTP.

[Retry]
```

Do not show Mock SAP data.

### Mock SAP selected

Use existing Mock SAP behavior.

### Neither platform configured

Show:

```text
No job platform configured.
```

Do not silently select Mock SAP.

---

## 13. Failed Jobs simulator

Keep the current simulator UI design.

Only change its data source based on selected environment.

### Mock SAP selected

Show current Mock failed jobs.

### SAP BTP selected

Show real BTP failed job executions from the backend.

Do not show hardcoded frontend jobs as fallback.

If the backend is unavailable:

```text
No failed jobs available.

Backend is not connected.
Start the backend to retrieve jobs.

[Retry]
```

If backend is connected but there are no failures:

```text
No failed jobs currently available.
```

---

## 14. Success/Resolved list

The success/resolved list must also be platform-specific.

If a BTP failure is successfully remediated:

```text
BTP Failed
   ↓
BTP Remediation
   ↓
BTP Success
```

The job moves from BTP failed to BTP success/resolved.

If a Mock job succeeds:

```text
Mock Failed
   ↓
Mock Remediation
   ↓
Mock Success
```

Do not move a job between platform lists.

---

## 15. Restart strategy display

Show the strategy selected by the backend.

For BTP:

```text
Restart Strategy
RESTART_FROM_START
```

For Mock:

```text
Restart Strategy
RESTART_FROM_FAILED_STEP
```

or:

```text
RESTART_FROM_START
```

or:

```text
DO_NOT_RESTART
```

The UI must also show:

```text
AI Recommendation
Final Policy Decision
Reason
Actual Action
```

Example BTP:

```text
AI Recommendation:
Restart

Final Policy Decision:
Restart from beginning

Reason:
BTP job is currently modeled as a single-step HTTP execution.

Action:
BTP retry/re-execution
```

Example Mock:

```text
AI Recommendation:
Restart from failed step

Final Policy Decision:
Restart from failed step

Reason:
Step 3 is independently restartable and previous steps are safe to retain.
```

---

## 16. No UI redesign

Do not redesign:

- dashboard layout
- sidebar
- existing cards
- existing charts
- existing simulator structure
- Job Details structure
- colors
- typography
- existing modal styling

Only add:

```text
Environment switch
```

and small source/environment indicators where necessary.

---

## 17. Existing Phase 1 must remain working

After this change, both modes must support:

```text
Job retrieval
→ Status recognition
→ Logs/details
→ AI diagnosis
```

Mock SAP must continue behaving as it did before.

SAP BTP must continue using the real BTP Job Scheduling integration.

---

## 18. Phase 2 behavior

### Mock SAP

```text
Failure
 ↓
AI diagnosis
 ↓
Policy
 ↓
Restart strategy
   ├── START
   ├── FAILED STEP
   └── DO NOT RESTART
 ↓
Execute
 ↓
Monitor
 ↓
Validate
 ↓
Success / Escalate
```

### SAP BTP

```text
Failure
 ↓
AI diagnosis
 ↓
Policy
 ↓
Restart strategy
   ├── START
   └── DO NOT RESTART
 ↓
Execute supported BTP retry/re-execution
 ↓
Monitor
 ↓
Validate
 ↓
Success / Escalate
```

Do not claim that BTP Job Scheduling Service provides S/4HANA `JobRestart` semantics.

---

## 19. Important SAP distinction

This project currently uses:

```text
SAP BTP Job Scheduling Service
```

It is NOT currently integrating with:

```text
S/4HANA
BC_EXT_APPJOB_MANAGEMENT
```

Do not add S/4HANA now.

That will be considered separately later.

---

## 20. Testing

### Test 1 — Mock

Switch to Mock SAP.

Expected:

```text
Only Mock jobs
```

### Test 2 — BTP

Switch to SAP BTP.

Expected:

```text
Only real BTP jobs
```

### Test 3 — repeated switching

```text
Mock → BTP → Mock → BTP
```

Expected:

- no stale cross-platform data
- no duplicates
- correct lists
- correct history

### Test 4 — BTP unavailable

Expected:

```text
Error/empty state
```

not Mock jobs.

### Test 5 — BTP safe failure

Expected:

```text
Failure
→ AI diagnosis
→ policy approval
→ RESTART_FROM_START
→ monitor
→ validate
```

### Test 6 — BTP severe failure

Expected:

```text
Failure
→ policy rejection
→ DO_NOT_RESTART
→ ESCALATED
```

### Test 7 — Mock multi-step failure

Expected:

```text
Failure at Step 3
→ policy
→ RESTART_FROM_FAILED_STEP
```

when the step metadata makes that safe.

### Test 8 — active remediation + switch

Start BTP remediation, switch to Mock SAP, verify BTP execution continues, then switch back and confirm BTP state is intact.

---

## 21. Implementation order

First inspect the existing code and identify:

1. Current BTP adapter
2. Current Mock SAP adapter
3. JobPlatform/service abstraction
4. Current environment/configuration
5. Current frontend job fetching
6. Current Job Details
7. Current remediation service
8. Current history models
9. Existing real-time mechanism

Then implement:

```text
1. Standardize JobPlatform abstraction
2. Register Mock and BTP implementations
3. Add top-right environment switch
4. Route backend requests through selected platform
5. Add platform to persisted execution/history records
6. Enforce platform-specific lists
7. Keep BTP single-step behavior
8. Keep Mock multi-step behavior
9. Add environment-specific Phase 2 rules
10. Add tests
```

Do not rewrite working Phase 1 code unnecessarily.

Do not introduce Redis/Celery.

---

## 22. Final acceptance criteria

The implementation is complete when:

```text
[✓] One Mock SAP / SAP BTP switch exists beside Agent ONLINE.
[✓] Only one platform is active at a time.
[✓] Mock SAP uses existing Mock data.
[✓] SAP BTP uses real BTP Job Scheduling data.
[✓] Mock and BTP data are never mixed.
[✓] BTP jobs are treated as single-step for this POC.
[✓] Safe BTP retry uses RESTART_FROM_START.
[✓] Unsafe BTP failures are escalated.
[✓] Mock SAP retains multi-step restart behavior.
[✓] History is platform-aware.
[✓] Active executions retain their original platform.
[✓] BTP unavailability never falls back to Mock.
[✓] No frontend hardcoded jobs are used as an API fallback.
[✓] Existing UI remains visually unchanged except for the environment switch/source indicator.
[✓] Phase 1 still works in both modes.
```

## Final desired UX

Top-right:

```text
Agent ONLINE    [ Mock SAP | SAP BTP ]
```

Mock selected:

```text
Mock SAP
→ existing Mock jobs
→ multi-step scenarios
→ restart from beginning / failed step
→ existing simulator behavior
```

BTP selected:

```text
SAP BTP
→ real BTP jobs
→ real BTP statuses/logs
→ AI diagnosis
→ policy
→ safe retry from beginning
→ monitor
→ validate
```

There must be **no hybrid mode**.
