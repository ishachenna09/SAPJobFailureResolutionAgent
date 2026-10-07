# SAP Job Failure Resolution Agent — UI Specification

## 1. Purpose

Build a professional operations dashboard for an **AI-based autonomous SAP Job Failure Resolution Agent**.

The application is not primarily a chatbot.

Its primary purpose is to let an operations/support user:

- Monitor SAP/application jobs
- See failures detected by the agent
- Understand what failed and why
- See what the AI analyzed
- See why the policy engine did or did not allow automation
- Watch autonomous restart/remediation progress
- Validate whether the job succeeded after remediation
- Review escalated failures requiring human intervention
- Inspect logs, job steps, parameters, and remediation history
- Optionally ask the agent questions about a job

### Core principle

The UI must make it obvious that:

> The agent does not merely recommend a restart. It can autonomously investigate, restart when policy permits, monitor the new execution, validate success, and report the final outcome.

---

# 2. Target users

## Primary user — Operations / Support Engineer

Main responsibilities:

- Monitor failed jobs
- Review automatic resolutions
- Investigate escalations
- Review logs and agent reasoning
- Take action when automation is blocked

## Secondary user — SAP / Platform Administrator

Main responsibilities:

- Review SAP-related failures
- Investigate authorization/configuration/system issues
- Review repeated failures
- Validate or manually resolve escalations

---

# 3. UI philosophy

Do NOT make the product look like a generic AI chatbot.

The main UI should feel like an:

> **Enterprise Job Operations + Autonomous Remediation Console**

The visual hierarchy should prioritize:

1. Current operational state
2. Failed jobs
3. Agent actions
4. Resolution status
5. Human intervention
6. Technical evidence
7. AI explanation

The interface should communicate confidence without hiding uncertainty.

---

# 4. Recommended application structure

```text
Application
│
├── Dashboard
│
├── Jobs
│   ├── All Jobs
│   ├── Failed
│   ├── Running
│   └── Resolved
│
├── Remediations
│   ├── In Progress
│   ├── Auto Resolved
│   └── Escalated
│
├── Job Details
│   ├── Overview
│   ├── Steps
│   ├── Logs
│   ├── Parameters
│   ├── AI Analysis
│   └── Remediation Timeline
│
├── Escalations
│
├── Agent Activity
│
└── Settings
```

A collapsible left navigation is recommended.

---

# 5. Global layout

Recommended desktop layout:

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ Logo / Product Name          Search             Notifications   User Menu  │
├───────────────┬────────────────────────────────────────────────────────────┤
│               │                                                            │
│ Dashboard     │                     PAGE CONTENT                           │
│               │                                                            │
│ Jobs          │                                                            │
│               │                                                            │
│ Remediations  │                                                            │
│               │                                                            │
│ Escalations   │                                                            │
│               │                                                            │
│ Agent Activity│                                                            │
│               │                                                            │
│ Settings      │                                                            │
│               │                                                            │
└───────────────┴────────────────────────────────────────────────────────────┘
```

Use a responsive layout, but optimize primarily for desktop/laptop operations users.

---

# 6. Header

The top header should contain:

### Left

- Product logo/icon
- Product name:
  `SAP Job Resolution Agent`
- Optional environment badge:
  `MOCK / DEVELOPMENT / SAP CONNECTED`

### Center

Global search:

```text
Search job, run ID, error, execution ID...
```

Search should support:

- Job name
- Run count
- Error text
- Failure category
- Execution ID
- Resolution ID

### Right

- Notification bell
- Agent status
- User/profile menu

Example:

```text
● Agent Online
```

Possible agent states:

```text
● Online
● Degraded
● Offline
```

---

# 7. Dashboard

The dashboard is the primary screen.

## 7.1 Summary cards

Show:

```text
┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│ Jobs Today     │ │ Failed Jobs    │ │ Auto Resolved  │ │ Escalated      │
│      128       │ │       12       │ │        9       │ │        3       │
│ +8% vs yesterday││ 9.4% failure   ││ 75% resolution ││ 25% escalation │
└────────────────┘ └────────────────┘ └────────────────┘ └────────────────┘
```

Additional useful cards:

- Active remediations
- Average resolution time
- Retry success rate
- Jobs currently running
- Jobs waiting for human intervention

---

# 8. Dashboard — recent failures

Main table:

| Column | Description |
|---|---|
| Job | Job name |
| Run | Job run count / execution identifier |
| Status | Current status |
| Failed Step | Step where failure occurred |
| Failure Category | AI classification |
| Agent Action | What agent did |
| Retry | Retry count |
| Final Result | Resolved / Escalated |
| Time | Failure/resolution timestamp |

Example:

```text
Z_CUSTOMER_LOAD
Run 10231
FAILED → AUTO RESOLVED

Failure:
TRANSIENT_DATABASE_LOCK

Action:
Restarted from failed step

Result:
SUCCESS
```

Rows should be clickable.

---

# 9. Dashboard — remediation activity

Show a live operational feed.

Example:

```text
10:31:18  ✓ Z_CUSTOMER_LOAD automatically resolved
10:30:44  ↻ Z_VENDOR_SYNC restart initiated
10:29:11  ! Z_INVOICE_LOAD escalated
10:28:53  ✓ Z_PRODUCT_LOAD validation successful
```

Each activity item should open the related execution.

---

# 10. Dashboard — health visualization

Add one or two useful charts, not a chart-heavy BI dashboard.

Recommended:

### Job outcome

```text
Successful
Auto Resolved
Escalated
Failed
```

### Failure categories

```text
Database Lock
Network Timeout
RFC Error
Authorization
Data Error
Program Error
Other
```

Charts should be simple and readable.

---

# 11. Jobs page

The Jobs page provides a searchable/filterable list.

Filters:

- Date/time range
- Job status
- Failure category
- Agent outcome
- Environment
- Job name
- Auto-remediation allowed
- Retry count

Statuses:

```text
SCHEDULED
READY
RUNNING
COMPLETED
FAILED
ABORTED
CANCELLED
```

Agent outcomes:

```text
NOT_PROCESSED
ANALYZING
AUTO_REMEDIATING
AUTO_RESOLVED
ESCALATED
RESOLUTION_FAILED
```

---

# 12. Job detail page

This is the most important UI in the application.

Recommended layout:

```text
┌──────────────────────────────────────────────────────────────────────┐
│ ← Back   Z_CUSTOMER_LOAD                         Run #10231          │
│                                                                      │
│ 🔴 FAILED              Agent: AUTO-RESOLVING                        │
├──────────────────────────────────────────────────────────────────────┤
│ Overview | Steps | Logs | Parameters | AI Analysis | Remediation     │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│                         CONTENT                                     │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

# 13. Job detail — Overview tab

Show:

### Job metadata

```text
Job Name
Z_CUSTOMER_LOAD

Run Count
10231

Job Text
Daily customer master load

Current Status
FAILED

Environment
MOCK / DEVELOPMENT / SAP

Started
10:25:02

Failed
10:25:19

Failed Step
Step 3

Return Code
8

Retry Count
0 / 2
```

### Current resolution state

Prominent status:

```text
🟡 AUTO REMEDIATION IN PROGRESS
```

or:

```text
🟢 AUTO RESOLVED
```

or:

```text
🔴 ESCALATED
```

---

# 14. Job detail — Steps tab

Show a step timeline/table:

```text
Step  Status      Start      End        Return Code
-----------------------------------------------------
1     ✓ SUCCESS   10:25:02   10:25:05   0
2     ✓ SUCCESS   10:25:05   10:25:11   0
3     ✕ FAILED    10:25:11   10:25:19   8
4     — SKIPPED   —          —          —
```

When the job is restarted:

```text
3     ↻ RETRYING
3     ✓ SUCCESS
4     ✓ SUCCESS
```

Make step changes animate subtly in live mode.

---

# 15. Job detail — Logs tab

Display logs in a technical log viewer.

Requirements:

- Monospace font
- Timestamp
- Severity
- Step number
- Message
- Search
- Copy
- Expand/collapse
- Highlight detected error
- Filter ERROR/WARN/INFO

Example:

```text
10:25:11 INFO  Step 3 started
10:25:17 INFO  Acquiring database resource
10:25:19 ERROR DATABASE_LOCK_TIMEOUT
10:25:19 ERROR Resource XYZ is currently locked
10:25:19 ERROR Transaction rolled back
```

The AI-detected evidence should be visually highlighted but MUST remain traceable to the original log.

---

# 16. Job detail — Parameters tab

Show the parameters used by the execution.

Example:

```text
Parameter              Value
--------------------------------------------
Company Code            1000
Posting Date            2026-08-20
Customer Group          ALL
Execution Mode          DELTA
```

For sensitive data:

- mask values when appropriate
- never show credentials/secrets

---

# 17. Job detail — AI Analysis tab

This should explain the diagnosis clearly.

Example:

```text
┌─────────────────────────────────────────────────────────┐
│ AI FAILURE ANALYSIS                                     │
├─────────────────────────────────────────────────────────┤
│ Failure Category                                        │
│ TRANSIENT_DATABASE_LOCK                                 │
│                                                         │
│ Confidence                                              │
│ ███████████████████░ 96%                                │
│                                                         │
│ Root Cause                                               │
│ The job failed because a required database resource     │
│ was temporarily locked.                                 │
│                                                         │
│ Evidence                                                 │
│ • DATABASE_LOCK_TIMEOUT                                 │
│ • Transaction rolled back                               │
│ • Failure occurred during Step 3                       │
│                                                         │
│ Recommended Action                                      │
│ Restart from failed step (E)                            │
└─────────────────────────────────────────────────────────┘
```

Important:

The UI must distinguish:

```text
AI RECOMMENDATION
```

from:

```text
POLICY DECISION
```

The AI does not have authority to execute.

---

# 18. Job detail — Policy Decision

Show a separate decision card.

Example:

```text
┌─────────────────────────────────────────────────────────┐
│ POLICY DECISION                                         │
├─────────────────────────────────────────────────────────┤
│ ✅ AUTOMATIC REMEDIATION APPROVED                       │
│                                                         │
│ Why?                                                    │
│                                                         │
│ ✓ Failure category is retryable                         │
│ ✓ Confidence >= 90%                                     │
│ ✓ Job allows restart                                    │
│ ✓ Retry count 0 / 2                                     │
│ ✓ Environment policy allows auto-restart                │
│                                                         │
│ Selected action                                         │
│ JOB_RESTART                                              │
│                                                         │
│ Restart mode                                            │
│ E — from failed step                                   │
└─────────────────────────────────────────────────────────┘
```

This is important for auditability and trust.

---

# 19. Job detail — Remediation timeline

This should be one of the most visually impressive parts of the UI.

Example:

```text
● 10:31:02  Job failed
│
● 10:31:03  Failure event received
│
● 10:31:03  Job details retrieved
│
● 10:31:04  Job logs retrieved
│
● 10:31:05  AI analysis completed
│
● 10:31:05  Failure classified as TRANSIENT_DATABASE_LOCK
│
● 10:31:05  Policy approved automatic restart
│
● 10:31:06  JobRestart(E) requested
│
● 10:31:07  Job entered RUNNING state
│
● 10:31:15  Failed step completed successfully
│
● 10:31:18  Job completed
│
✓ 10:31:18  Validation successful
│
✓ 10:31:18  AUTO RESOLVED
```

Each event can expand to show technical details.

---

# 20. Live remediation state

When remediation is happening, show a prominent banner:

```text
🟡 Agent is automatically resolving this failure
```

Then show:

```text
Investigation       ✓
AI Analysis         ✓
Policy Check        ✓
Restart             ✓
Monitoring          ●
Validation          ○
```

Progress states:

```text
○ NOT STARTED
● IN PROGRESS
✓ COMPLETED
✕ FAILED
```

Do not claim success until validation actually succeeds.

---

# 21. Success state

When the job succeeds after restart:

```text
┌───────────────────────────────────────────────────────────┐
│                     ✓ AUTO RESOLVED                       │
│                                                           │
│ Z_CUSTOMER_LOAD completed successfully after automatic   │
│ remediation.                                              │
│                                                           │
│ Original run: 10231                                      │
│ Retry run:    10232                                      │
│ Restart mode: E                                          │
│ Retry count:  1                                          │
│                                                           │
│ Validation: SUCCESS                                      │
└───────────────────────────────────────────────────────────┘
```

Provide:

- View execution
- View logs
- View remediation timeline
- Copy resolution summary

---

# 22. Escalation state

When automatic remediation is unsafe:

```text
┌───────────────────────────────────────────────────────────┐
│                    ⚠ ESCALATED                            │
├───────────────────────────────────────────────────────────┤
│ Automatic restart was blocked.                            │
│                                                           │
│ Reason:                                                   │
│ Authorization failures are classified as non-retryable.  │
│                                                           │
│ AI diagnosis:                                             │
│ User/service account lacks required authorization.        │
│                                                           │
│ Suggested human action:                                   │
│ Review SAP authorization/role configuration.              │
└───────────────────────────────────────────────────────────┘
```

Buttons:

```text
[Assign]
[Mark Resolved]
[Retry Manually]
[View Logs]
```

If a real SAP environment is not connected, buttons should remain appropriately disabled or operate only on mock data.

---

# 23. Remediations page

Show all agent remediation executions.

Columns:

```text
Execution ID
Job
Failure
AI Decision
Policy Decision
Action
Attempt
Status
Duration
```

Example:

```text
REM-000123
Z_CUSTOMER_LOAD
DB LOCK
RESTART
APPROVED
JobRestart(E)
1
AUTO RESOLVED
16 sec
```

Filters:

- In progress
- Auto resolved
- Escalated
- Failed
- Date
- Failure category

---

# 24. Escalations page

Show only cases requiring human action.

Columns:

```text
Job
Failure Category
Reason
Severity
Age
Suggested Action
Assigned To
Status
```

Severity:

```text
LOW
MEDIUM
HIGH
CRITICAL
```

Use conservative severity rules. Do not let the LLM freely invent business severity without deterministic mapping/configuration.

---

# 25. Agent Activity page

Show the agent's operational activity.

Example:

```text
Time       Agent Action                         Job
-----------------------------------------------------------
10:31:06   Restart requested                   Z_CUSTOMER_LOAD
10:31:05   Policy approved restart             Z_CUSTOMER_LOAD
10:31:05   Failure classified                  Z_CUSTOMER_LOAD
10:30:44   Logs retrieved                      Z_VENDOR_SYNC
10:30:43   Job failure received                Z_VENDOR_SYNC
```

This is useful for demonstrating autonomy.

---

# 26. Optional Agent Chat

Add an optional side panel or separate page called:

```text
Ask Agent
```

Example questions:

```text
Why did Z_CUSTOMER_LOAD fail?

What did the agent do?

Why was this job restarted?

Why was Z_VENDOR_SYNC escalated?

Show me the failed step.

Show me the evidence for the root cause.

How many retries have happened?
```

The chatbot must answer from application/job data.

It should NOT execute arbitrary operations from natural-language instructions.

For example:

User:
> Restart every failed production job.

Agent:
> I can explain eligible jobs, but autonomous actions are governed by configured remediation policies. I cannot bypass those policies.

---

# 27. Notifications

Provide notifications for:

- Job automatically resolved
- Escalation created
- Remediation failed
- Maximum retries reached
- Agent unavailable
- SAP connection unavailable
- Mock SAP unavailable

Example notification:

```text
✓ Job Resolved

Z_CUSTOMER_LOAD was automatically restarted and completed successfully.

[View Job]
```

---

# 28. Settings page

Sections:

### Agent

```text
Agent status
AI provider
Confidence threshold
```

### Remediation policy

```text
Maximum retries
Retryable failure categories
Restart mode defaults
Environment restrictions
```

### SAP connection

Show:

```text
Mock SAP
Connected

or

SAP S/4HANA
Not Connected
```

Never display secrets.

### Event source

Show:

```text
LOCAL MOCK EVENT SOURCE
```

or:

```text
SAP EVENT / MESSAGE SOURCE
```

depending on environment.

---

# 29. Mock environment indicator

Because this POC may operate without real SAP, make the environment obvious.

Top banner:

```text
⚠ DEVELOPMENT MODE — MOCK SAP
```

When real SAP is connected:

```text
● SAP CONNECTED — TEST ENVIRONMENT
```

Never make mock behavior look indistinguishable from production SAP.

This is important for trust.

---

# 30. Human approval mode

Although the core POC should demonstrate autonomous remediation, add a configurable policy:

```text
Automation Mode

○ Fully Autonomous
○ Approval Required
○ Diagnosis Only
```

For the POC:

```text
Fully Autonomous
```

should be used for approved transient failures.

Approval Required should show:

```text
Agent recommends:
RESTART

Reason:
Transient database lock

[Approve Restart]
[Deny]
```

This allows future enterprise deployment to introduce additional controls without redesigning the UI.

---

# 31. Color/status semantics

Use consistent status semantics.

Recommended:

```text
Success       → Green
Running       → Blue
In Progress   → Blue
Warning       → Amber
Escalated     → Orange
Failed        → Red
Neutral       → Gray
```

Do not rely only on color. Always include:

- icon
- text
- status badge

Example:

```text
🟢 SUCCESS
🔵 RUNNING
🟠 ESCALATED
🔴 FAILED
```

---

# 32. Component design

Create reusable components:

```text
AppShell
Sidebar
Topbar
EnvironmentBadge
MetricCard
JobTable
JobStatusBadge
FailureCategoryBadge
ResolutionStatusBadge
JobOverviewCard
JobStepsTable
LogViewer
ParameterTable
AIAnalysisCard
PolicyDecisionCard
RemediationTimeline
RemediationProgress
EscalationCard
NotificationPanel
AgentChat
SearchBar
FilterBar
EmptyState
LoadingState
ErrorState
ConfirmationDialog
```

---

# 33. API/data requirements for frontend

The frontend should consume backend APIs.

Recommended endpoints:

```text
GET  /api/dashboard/summary

GET  /api/jobs
GET  /api/jobs/{job_name}/{run_count}
GET  /api/jobs/{job_name}/{run_count}/steps
GET  /api/jobs/{job_name}/{run_count}/logs
GET  /api/jobs/{job_name}/{run_count}/parameters

GET  /api/jobs/{job_name}/{run_count}/analysis
GET  /api/jobs/{job_name}/{run_count}/remediation

GET  /api/remediations
GET  /api/escalations
GET  /api/agent/activity

GET  /api/executions/{execution_id}
GET  /api/executions/{execution_id}/timeline
```

For live updates, prefer:

```text
WebSocket
```

or:

```text
Server-Sent Events (SSE)
```

for remediation timeline updates.

---

# 34. Real-time UX

When a remediation is in progress, the UI should update without page refresh.

Example:

```text
Job failed
     ↓
UI changes to:
"Investigation in progress..."

     ↓
AI analysis completed

     ↓
UI changes to:
"Automatic restart approved"

     ↓
UI changes to:
"Restart requested"

     ↓
"Job running"

     ↓
"Validation in progress"

     ↓
"Auto resolved"
```

Use SSE or WebSocket.

For the POC, SSE is acceptable and simpler if full bidirectional communication is unnecessary.

---

# 35. Loading/error/empty states

Every screen must have:

### Loading

```text
Loading job details...
```

### Error

```text
Unable to retrieve job details.

[Retry]
```

### Empty

```text
No failed jobs found.
```

### SAP unavailable

```text
SAP connection unavailable.

The dashboard is showing the last known state.

[Retry Connection]
```

### Mock mode

```text
This environment is using Mock SAP.
```

---

# 36. Accessibility

Use:

- keyboard navigation
- visible focus states
- sufficient contrast
- labels for icons
- accessible tables
- accessible dialogs
- no color-only meaning

---

# 37. Responsive behavior

Desktop is primary.

Tablet should remain usable.

Mobile can be supported but does not need the full desktop information density.

On smaller widths:

- collapse sidebar
- turn large tables into cards
- stack dashboard metrics
- make logs horizontally scrollable
- preserve remediation status at the top

---

# 38. Visual style

Recommended visual direction:

### Style

Modern enterprise operations console.

Think:

```text
clean
professional
technical
calm
high information density
not flashy
not consumer/social
```

Avoid:

- excessive gradients
- giant decorative illustrations
- gaming-style dashboards
- overly bright neon UI
- unnecessary animations

Use subtle animations only for live remediation progress.

---

# 39. Suggested design tokens

Create a centralized theme.

Example:

```text
font:
  Inter / system UI

radius:
  small: 6px
  medium: 10px
  large: 14px

spacing:
  4 / 8 / 12 / 16 / 24 / 32

card:
  subtle border
  light shadow

status:
  success
  info
  warning
  danger
  neutral
```

Do not hard-code styles across individual components.

---

# 40. Recommended frontend stack

Use:

```text
React
TypeScript
Vite
```

Recommended libraries:

```text
React Router
TanStack Query
Zustand or Context
Tailwind CSS
Recharts
Lucide React
```

Use a component library if helpful, but keep the UI consistent.

---

# 41. Key user journey

The most important journey is:

```text
USER OPENS DASHBOARD
        ↓
Sees failed job
        ↓
Clicks job
        ↓
Sees failure details
        ↓
Sees agent investigating
        ↓
Sees AI diagnosis
        ↓
Sees policy approval
        ↓
Sees restart executing
        ↓
Sees job running
        ↓
Sees validation
        ↓
Sees AUTO RESOLVED
```

The user should understand the entire story without reading source code.

---

# 42. Failure journey

Second key journey:

```text
JOB FAILS
   ↓
EVENT RECEIVED
   ↓
ANALYZE
   ↓
AUTHORIZATION ERROR
   ↓
POLICY BLOCKS RESTART
   ↓
ESCALATED
   ↓
USER REVIEWS
```

---

# 43. Demo mode

Add a development-only Demo Controls section.

This is especially important because no real SAP credentials are available.

Buttons:

```text
[Simulate Successful Job]

[Simulate Database Lock Failure]

[Simulate Network Timeout]

[Simulate Authorization Failure]

[Simulate Repeated Failure]

[Clear Demo Data]
```

When the user clicks:

```text
Simulate Database Lock Failure
```

the system should execute the complete event-driven flow.

This makes the POC easy to demonstrate to stakeholders.

---

# 44. Demo flow for presentation

The preferred live demonstration:

## Start

Dashboard:

```text
12 failed
9 auto-resolved
3 escalated
```

Click:

```text
[Simulate Database Lock Failure]
```

Then show:

```text
Z_CUSTOMER_LOAD
FAILED
```

Watch timeline:

```text
Event received
↓
Investigation
↓
AI classification
↓
Policy approved
↓
Restart
↓
Running
↓
Completed
↓
Validation
↓
AUTO RESOLVED
```

Then demonstrate:

```text
[Simulate Authorization Failure]
```

and show:

```text
AI diagnosis
↓
Policy blocks restart
↓
ESCALATED
```

This demonstrates both sides of the autonomous agent.

---

# 45. UI does not control business authority

Important rule:

The UI must never bypass backend policy.

For example, do not implement:

```text
Frontend button
  ↓
Directly call SAP JobRestart
```

Instead:

```text
Frontend
   ↓
Backend API
   ↓
Policy / Authorization
   ↓
SAP Adapter
   ↓
SAP
```

All authoritative remediation decisions belong to the backend.

---

# 46. Security UX

Never display:

- SAP passwords
- API secrets
- client secrets
- authorization tokens

Mask sensitive parameters when required.

The UI can show:

```text
SAP Connection:
CONNECTED

Authentication:
Configured

Credentials:
••••••••
```

Do not expose raw credentials through frontend APIs.

---

# 47. Audit UX

Every autonomous action should be explainable.

For each remediation show:

```text
Who:
Agent

What:
JobRestart

Why:
Transient database lock

Policy:
Auto-restart permitted

Evidence:
Log lines / failure code

When:
2026-08-20 10:31:06

Result:
Successful
```

This is essential for enterprise trust.

---

# 48. Final acceptance criteria for UI

The UI is complete when:

- Dashboard shows current job health.
- Failed jobs are visible.
- Job details can be inspected.
- Logs are readable.
- Parameters are readable/masked appropriately.
- AI diagnosis is visible.
- AI recommendation is separated from policy decision.
- Automatic remediation progress is visible in real time.
- Restart is clearly shown as an agent action.
- Validation result is clearly shown.
- Auto-resolved jobs are distinguishable from normal successful jobs.
- Escalations are clearly shown.
- Human intervention reasons are understandable.
- Demo failure scenarios can be triggered.
- UI works fully against Mock SAP.
- No real SAP credentials are required for local development.
- Mock SAP is clearly labeled.
- UI never bypasses backend policy.
- The design can later connect to a real SAP backend without changing the user journey.

---

# 49. Implementation instruction for Claude / Antigravity

Build the UI **after the backend API contracts are defined**, but do not wait for the entire backend to be finished.

Use mock frontend data/interfaces during UI development and then connect them to the FastAPI endpoints.

Implement in this order:

```text
1. App shell
2. Navigation
3. Dashboard
4. Jobs table
5. Job details
6. Logs viewer
7. Steps viewer
8. AI Analysis
9. Policy Decision
10. Remediation Timeline
11. Escalation view
12. Remediation list
13. Agent activity
14. Notifications
15. Optional Agent Chat
16. Demo Controls
17. SSE/WebSocket live updates
18. Loading/error/empty states
19. Accessibility
20. Responsive behavior
```

Do not create a chatbot-first interface.

The application must clearly communicate:

> **Detect → Diagnose → Decide → Restart → Monitor → Validate → Resolve/Escalate**

This sequence is the core product experience.

---

# 50. Final product concept

The final interface should feel like:

> **An autonomous SAP operations center where the human monitors the agent rather than manually troubleshooting every failed job.**

The core screen should make this immediately understandable:

```text
                    JOB FAILURE
                         ↓
                     DETECTED
                         ↓
                     ANALYZING
                         ↓
                 POLICY DECISION
                  /            \
             AUTO FIX          ESCALATE
                ↓                   ↓
            RESTART              HUMAN
                ↓
             MONITOR
                ↓
            VALIDATE
             /      \
        SUCCESS      FAILURE
           ↓             ↓
      AUTO RESOLVED   ESCALATED
```

The UI is successful when a stakeholder can look at a single job and answer:

1. What failed?
2. Why did it fail?
3. What did the AI conclude?
4. Was automatic remediation allowed?
5. What action did the agent execute?
6. Did the restarted job succeed?
7. If not, why was it escalated?
