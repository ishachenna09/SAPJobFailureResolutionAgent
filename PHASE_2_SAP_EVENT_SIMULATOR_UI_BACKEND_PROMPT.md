# Phase 2 — SAP Event Simulator, Autonomous Execution & Job History

## Context

Phase 1 is already working:

```text
SAP/Mock SAP job fails
→ Failure event
→ Agent investigates Mock SAP
→ Agent recognizes FAILED/SUCCESS
→ AI diagnoses root cause
```

Phase 2 now adds autonomous remediation:

```text
Failure
→ Policy evaluation
→ Restart strategy
→ Restart
→ Monitor
→ Validate
→ AUTO RESOLVED or ESCALATED
```

Do NOT rewrite or break Phase 1.

---

## 1. SAP Event Simulator must use backend data only

When the user clicks **SAP Event Simulator**, the UI must show **only currently failed jobs returned by the backend**.

Do NOT hardcode/demo-seed jobs in the frontend.

Do NOT use fallback data such as:

```javascript
apiJobs || demoJobs
```

If the backend is unavailable:

```text
SAP Event Simulator

No failed jobs available.

Backend is not connected.
Start the backend to retrieve SAP jobs.

[Retry Connection]
```

If the backend is available but there are no failed jobs:

```text
No failed jobs currently available.
```

These are different states and should be displayed differently.

No fake jobs should appear merely because the frontend was started.

---

## 2. Simulator should show failed jobs only

The current simulator shows success scenarios alongside failures. Change this.

The simulator should show:

```text
Failed Jobs
```

Only.

Example:

```text
┌──────────────────────────────────────────────────────────────┐
│ SAP Event Simulator                                      ✕  │
├──────────────────────────────────────────────────────────────┤
│ Failed Jobs                                                   │
│                                                              │
│ Z_CUSTOMER_LOAD                                              │
│ Run #10231                                                   │
│ Failed Step: Step 3                                         │
│ Error: DATABASE_LOCK_TIMEOUT                                │
│ Status: FAILED                          [Run Agent]         │
│                                                              │
│ Z_FIN_POSTING                                                │
│ Run #10232                                                   │
│ Failed Step: Step 1                                         │
│ Error: AUTHORIZATION_FAILURE                                │
│ Status: FAILED                          [Run Agent]         │
│                                                              │
│ Backend: ● Connected                          [Close]       │
└──────────────────────────────────────────────────────────────┘
```

If demo controls are still needed to create failures, keep them separate and clearly label them as:

```text
Developer / Demo Controls
```

Do not mix successful scenarios into the Failed Jobs list.

---

## 3. No duplicate jobs

Use a stable identity such as:

```text
job_name + job_run_count
```

or the project's existing unique job/run identifier.

Never use an array index as identity.

The same failure event must not create duplicate UI entries.

The backend must prevent duplicate remediation executions for the same job/run/event.

The frontend should also avoid inserting duplicate records.

Use an idempotency key such as:

```text
job_name + job_run_count + event_type
```

or the existing unique event ID.

---

## 4. Run Agent action

Every failed job should have:

```text
[ Run Agent ]
```

When clicked:

```text
User
 ↓
POST remediation request for this exact job
 ↓
Agent starts Phase 2
 ↓
Investigation
 ↓
AI diagnosis
 ↓
Policy evaluation
 ↓
Restart strategy
 ↓
Remediation / escalation
```

Do not instantly show SUCCESS.

While processing, disable the button and show:

```text
[ Agent Running... ]
```

Prevent a second click from starting another remediation.

---

## 5. Safety decision must be visible

The UI must show whether the agent is allowed to act.

Example:

```text
Agent Analysis
Failure:
TRANSIENT_DATABASE_LOCK

Confidence:
96%

Policy Decision:
AUTO REMEDIATION ALLOWED

Restart Strategy:
RESTART FROM FAILED STEP
```

Unsafe example:

```text
Agent Analysis
Failure:
AUTHORIZATION_ERROR

Policy Decision:
AUTO REMEDIATION NOT ALLOWED

Action:
ESCALATED TO HUMAN

Reason:
Authorization failures are non-retryable.
```

Clearly distinguish:

```text
AI Recommendation
```

from:

```text
Final Policy Decision
```

The frontend must never make the policy decision.

---

## 6. Restart strategy must support three outcomes

Phase 2 must support:

```text
RESTART_FROM_START
RESTART_FROM_FAILED_STEP
DO_NOT_RESTART
```

Do not hardcode:

```text
restart_mode = E
```

for every job.

The backend must determine the strategy.

The UI must display it.

Example:

```text
Restart Strategy

AI Recommendation:
Restart from failed step

Final Policy Decision:
Restart from failed step

Reason:
Previous successful steps are safe to retain and
the failed step is independently restartable.

SAP Action:
JobRestart(E)
```

Another job may show:

```text
Final Policy Decision:
Restart from beginning

Reason:
Intermediate state must be rebuilt before retrying.
```

Or:

```text
Final Policy Decision:
Do not restart

Reason:
Authorization failure is non-retryable.
```

---

## 7. Running-job execution view

When the user runs the agent, display a dedicated execution view.

Example:

```text
┌──────────────────────────────────────────────────────────────┐
│ Z_CUSTOMER_LOAD — Agent Execution                        ✕ │
├──────────────────────────────────────────────────────────────┤
│ Status: 🟡 REMEDIATION IN PROGRESS                          │
│ Strategy: Restart from failed step                          │
│ Run: #10231                                                 │
│                                                              │
│ Progress                                                     │
│ ✓ Investigation                                             │
│ ✓ AI Analysis                                               │
│ ✓ Policy Evaluation                                         │
│ ✓ Restart Strategy                                          │
│ ● Job Restart                                               │
│ ○ Monitoring                                                │
│ ○ Validation                                                │
│                                                              │
│ LIVE LOGS                                                    │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ 10:31:02 Job restart requested                           │ │
│ │ 10:31:03 Run #10232 created                              │ │
│ │ 10:31:03 Job status = RUNNING                            │ │
│ │ 10:31:06 Step 3 started                                  │ │
│ │ 10:31:08 Step 3 completed                                │ │
│ │ ...                                                      │ │
│ └──────────────────────────────────────────────────────────┘ │
│                                                              │
│                                                       [Close]│
└──────────────────────────────────────────────────────────────┘
```

---

## 8. Critical modal/log UX fix

The current log expansion makes the popup too tall and prevents closing.

Fix this.

### Outer modal

The modal must have a bounded height, for example:

```css
max-height: 80vh;
```

Use a layout:

```text
Modal
├── Header      fixed
├── Body        bounded
│   ├── Job details
│   ├── Agent status
│   ├── Progress
│   └── Logs
└── Footer      fixed
```

The modal must NOT grow indefinitely as logs increase.

### Logs

The log viewer gets its own scroll:

```css
overflow-y: auto;
```

Only the log container should scroll.

Avoid nested scrollbars.

### Close

The header close button must always remain visible.

A footer Close button can also remain visible.

Closing the modal means:

```text
Close UI
≠
Cancel remediation
```

The backend agent continues running.

If the user reopens the job, the latest state must be loaded from the backend.

---

## 9. Live logs and live state

Do not fake the complete execution in frontend state.

Use the existing backend real-time mechanism (SSE/WebSocket if already present).

The UI should receive events such as:

```text
INVESTIGATION_STARTED
AI_ANALYSIS_COMPLETED
POLICY_APPROVED
RESTART_STRATEGY_SELECTED
JOB_RESTARTED
JOB_RUNNING
STEP_STARTED
STEP_COMPLETED
VALIDATION_STARTED
VALIDATION_SUCCESS
AUTO_RESOLVED
ESCALATED
```

The UI should convert these into the progress/timeline/log display.

---

## 10. Successful remediation — move Failed → Success

If the agent successfully resolves:

```text
Failed Job
→ restart
→ monitor
→ validate success
```

then:

1. Remove the job from the active Failed Jobs list.
2. Add it to Success/Resolved Jobs.
3. Preserve the complete history.
4. Preserve the original failed run.
5. Link the failed run to the successful restarted run.

Do NOT delete historical failure data.

---

## 11. Success/Resolved Jobs list

Show a separate Success/Resolved list.

Example:

```text
Z_CUSTOMER_LOAD

✓ SUCCESS

Originally failed:
DATABASE_LOCK_TIMEOUT

Resolved by:
AI Job Resolution Agent

Restart strategy:
Restart from failed step

Original run:
#10231

Successful run:
#10232

Validation:
Passed

Resolution:
Automatically resolved

[View History]
```

This makes it obvious to a human that the current success was the result of remediation.

---

## 12. Mandatory Job History

Every job must have persistent history.

Add a **History** tab/section to Job Details.

Example:

```text
Z_CUSTOMER_LOAD
────────────────────────────────────────

Current Status: SUCCESS

History:

Run #10231
FAILED
Database lock timeout
↓
Agent Execution REM-00041
↓
Restart from failed step
↓
Run #10232
SUCCESS
↓
Validation passed

Previous runs:

Run #10230
SUCCESS

Run #10229
FAILED
Authorization error
ESCALATED
```

The human should be able to answer:

> This job failed earlier. What exactly did the agent do?

---

## 13. History contents

For every agent-handled execution preserve/display:

```text
timestamp
job_name
original_run_id
new_run_id, if any
event_id
failure category
AI diagnosis
AI confidence
policy decision
restart strategy
SAP action
restart attempt
job status changes
technical job logs
agent activity logs
validation result
final outcome
escalation details, if any
```

---

## 14. Original → restarted run lineage

Never overwrite the failed run.

Example:

```text
Original Run #10231
Status: FAILED
        │
        │ remediated by
        ▼
Agent Execution REM-00041
        │
        ▼
Restarted Run #10232
Status: SUCCESS
```

Persist this relationship with fields such as:

```text
parent_run_id
triggered_by_execution_id
remediation_execution_id
```

or the existing project's equivalent fields.

---

## 15. Agent Activity logs vs SAP job logs

Keep these conceptually separate.

### Agent activity

```text
Failure event received
Job investigated
AI analysis completed
Policy approved
Restart strategy selected
Restart executed
Validation completed
```

### SAP job log

```text
Step 3 started
DATABASE_LOCK_TIMEOUT
Step 3 completed
Step 4 started
Step 4 completed
```

The History view should be able to show both.

For example:

```text
AGENT ACTIVITY
10:31:03 Failure event received
10:31:05 AI analysis completed
10:31:05 Policy approved restart
10:31:06 Restart executed
10:31:18 Validation successful

SAP JOB LOG
10:31:06 Step 3 started
10:31:08 Step 3 completed
10:31:10 Step 4 started
10:31:11 Step 4 completed
```

---

## 16. Escalation behavior

If the policy rejects automation:

```text
FAILED
 ↓
AI diagnosis
 ↓
Policy REJECT
 ↓
DO NOT RESTART
 ↓
ESCALATED TO HUMAN
```

The job stays failed/escalated.

It must not move to Success.

Display:

```text
⚠ ESCALATED TO HUMAN

Failure:
AUTHORIZATION_ERROR

Why automation was blocked:
This error is non-retryable.

Suggested human action:
Review SAP authorization/role configuration.
```

Preserve this in history.

---

## 17. Backend is the source of truth

The frontend must not simulate actual job execution.

Frontend:

```text
display state
send user action
receive backend state
```

Backend owns:

```text
AI analysis
policy decision
restart strategy
retry count
restart execution
monitoring
validation
escalation
history
```

The frontend must never implement logic like:

```javascript
if (error === "DATABASE_LOCK_TIMEOUT") restart();
```

---

## 18. Backend API behavior

Use existing project endpoints where possible.

The frontend needs equivalent capabilities for:

```text
GET  /api/jobs?status=FAILED
GET  /api/jobs/{job_name}/{run_count}
GET  /api/jobs/{job_name}/{run_count}/history

POST /api/jobs/{job_name}/{run_count}/remediation

GET  /api/remediations/{execution_id}
GET  /api/remediations/{execution_id}/timeline

GET  /api/escalations
```

Do not create duplicate APIs if equivalents already exist.

The exact endpoint paths should follow the existing project's conventions.

---

## 19. Loading and connection states

### Loading

Show:

```text
Loading failed jobs...
```

Do not display fake scenario cards while waiting for the API.

### Backend down

Show:

```text
No failed jobs available.

Backend is not connected.
Start the backend to retrieve SAP jobs.

[Retry Connection]
```

### Backend up, no failures

Show:

```text
No failed jobs currently available.
```

### Backend returns jobs

Render the returned failed jobs only.

---

## 20. Refresh/live update behavior

The Failed Jobs list must reflect current backend state.

If the agent successfully resolves a job:

```text
Failed Jobs
→ remove job
```

and:

```text
Success/Resolved Jobs
→ add job
```

If another failed event arrives:

```text
Failed Jobs
→ add exactly one new job
```

Never duplicate existing entries.

---

## 21. State-dependent button behavior

### Failed and untouched

```text
[ Run Agent ]
```

### Agent running

```text
[ Agent Running... ]
```

Disabled.

### Auto resolved

```text
✓ Resolved
```

### Escalated

```text
⚠ Escalated
[View Escalation]
```

Do not allow repeated remediation for a currently active execution.

---

## 22. Developer/demo controls

If the project needs controls for creating test failures, keep them separate from the normal operations UI.

Example:

```text
Developer / Demo Controls
-------------------------
[Create DB Lock Failure]
[Create Authorization Failure]
[Create Restart-from-Start Failure]
[Create Success]
```

These controls may create backend/mock-SAP events.

The actual Failed Jobs simulator must still display only backend-returned failed jobs.

No hardcoded frontend scenario data.

---

## 23. Recommended state model

Use explicit backend/remediation states:

```text
RECEIVED
INVESTIGATING
ANALYZING
POLICY_EVALUATION
STRATEGY_SELECTED
RESTARTING
MONITORING
VALIDATING
AUTO_RESOLVED
ESCALATED
RESOLUTION_FAILED
```

Persist state transitions so they appear in history.

---

## 24. Acceptance tests

### A — Frontend without backend

1. Start frontend only.
2. Open SAP Event Simulator.
3. Expected:
   - No jobs.
   - No hardcoded scenario data.
   - Clear disconnected/empty state.
   - Retry button.

### B — Backend running, no failures

Expected:

```text
No failed jobs currently available.
```

### C — Failed job appears

1. Generate failure from backend/mock SAP.
2. Open/refresh simulator.
3. Exactly one failed job appears.

### D — Duplicate event

Emit the same event twice.

Expected:

```text
One job
One execution identity
No duplicate remediation
```

### E — Safe remediation succeeds

1. Select retry-safe failed job.
2. Click Run Agent.
3. Expected:
   - Agent analyzes.
   - Policy approves.
   - Restart strategy displayed.
   - Restart executes.
   - Logs stream.
   - Job monitored.
   - Validation passes.
   - Job removed from Failed.
   - Job added to Success/Resolved.
   - History contains original failure + agent activity + successful run.

### F — Unsafe remediation

1. Select authorization failure.
2. Click Run Agent.
3. Expected:
   - Policy rejects.
   - No restart.
   - Job remains failed.
   - Escalation shown.
   - History records the escalation.

### G — Restart from beginning

Expected:

```text
Strategy = RESTART_FROM_START
```

and all required steps rerun in the mock.

### H — Restart from failed step

Expected:

```text
Strategy = RESTART_FROM_FAILED_STEP
```

Previously successful steps are not rerun in the mock.

### I — Retry exhausted

Expected:

```text
retry limit reached
→ no infinite retries
→ ESCALATED
```

### J — Long logs

1. Start remediation.
2. Generate many log lines.
3. Expected:
   - Modal remains bounded.
   - Log area has its own scrollbar.
   - Header/footer remain accessible.
   - Close button remains visible.

### K — Close while running

1. Start remediation.
2. Close modal.
3. Expected:
   - Modal closes.
   - Backend remediation continues.
   - Reopening shows current state.

### L — History

After successful remediation, Job Details → History must clearly show:

```text
Original failed run
→ failure
→ AI diagnosis
→ policy
→ restart strategy
→ restart
→ new run
→ validation
→ success
```

---

## 25. Implementation order

First inspect the existing implementation.

Identify:

1. Current SAP Event Simulator component
2. Current failed-job API
3. Current Mock SAP models
4. Current agent/remediation services
5. Current DB schema
6. Current Job Detail component
7. Current success/failed job lists
8. Current SSE/WebSocket mechanism
9. Existing history/timeline functionality

Then implement:

```text
1. Remove frontend hardcoded/fallback jobs.
2. Make backend/API the only source of failed jobs.
3. Show failed jobs only in simulator.
4. Add duplicate/idempotency protection.
5. Connect Run Agent to Phase 2 remediation.
6. Display restart strategy.
7. Add live execution progress.
8. Fix fixed-height modal and log scrolling.
9. Close modal without cancelling execution.
10. Move validated successful jobs from Failed → Success.
11. Preserve original failed run.
12. Add original → restarted run lineage.
13. Add per-job History tab.
14. Show agent activity + SAP job logs.
15. Show escalation status/reason.
16. Add loading/backend-down/empty states.
17. Add/execute the acceptance tests above.
```

Do not rewrite working Phase 1 code unnecessarily.

Do not introduce Redis/Celery.

Use the project's existing background-processing and real-time mechanisms.

---

# 26. Final expected experience

The user experience must be:

```text
User clicks SAP Event Simulator
        ↓
Backend returns current FAILED jobs
        ↓
User selects Z_CUSTOMER_LOAD
        ↓
Clicks Run Agent
        ↓
Agent investigates
        ↓
AI diagnoses
        ↓
Policy checks safety
        ↓
Restart strategy selected
        ↓
Agent restarts
        ↓
Live logs/progress
        ↓
Monitor
        ↓
Validate
        ↓
SUCCESS
        ↓
Removed from Failed Jobs
        ↓
Added to Success/Resolved Jobs
        ↓
History retained
        ↓
Human can open History and see:

FAILED
→ AI diagnosis
→ Policy
→ Restart strategy
→ Restarted run
→ Validation
→ SUCCESS
```

For unsafe jobs:

```text
FAILED
→ AI diagnosis
→ Policy rejects
→ NO RESTART
→ ESCALATED TO HUMAN
→ History retained
```

The final UI should feel like an **autonomous operations console**, not a static scenario simulator.
