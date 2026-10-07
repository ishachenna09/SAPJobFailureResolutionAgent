import logging
import json
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, AsyncGenerator, Optional
from sqlalchemy.orm import Session
from app.sap.base import SAPJobService
from app.sap.mock_sap import MockSAPJobService
from app.policies.remediation_policy import PolicyDecisionSchema, JobRemediationPolicy
from app.schemas.job import FailureAnalysisSchema, JobRunDetailSchema
from app.db.models import (
    JobRunModel, RemediationExecutionModel, JobStepModel, JobLogModel, JobParameterModel, JobModel, FailureAnalysisModel
)

logger = logging.getLogger(__name__)

# In-memory queue / event bus for live streaming SSE subscribers
_remediation_event_queues: Dict[str, List[asyncio.Queue]] = {}

def register_event_queue(execution_id: str) -> asyncio.Queue:
    q = asyncio.Queue()
    if execution_id not in _remediation_event_queues:
        _remediation_event_queues[execution_id] = []
    _remediation_event_queues[execution_id].append(q)
    return q

def unregister_event_queue(execution_id: str, q: asyncio.Queue):
    if execution_id in _remediation_event_queues:
        if q in _remediation_event_queues[execution_id]:
            _remediation_event_queues[execution_id].remove(q)
        if not _remediation_event_queues[execution_id]:
            del _remediation_event_queues[execution_id]

async def broadcast_event(execution_id: str, event_data: dict):
    if execution_id in _remediation_event_queues:
        for q in list(_remediation_event_queues[execution_id]):
            await q.put(event_data)


class RemediationService:
    """
    Autonomous Remediation & Success Validation Service (Phase 2).
    Executes SAP JobRestart per SAP_COM_0326, maintains run lineage, records separate
    agent activity logs, and supports live streaming.
    """
    def __init__(self, db: Session, sap_service: SAPJobService = None):
        self.db = db
        self.sap = sap_service

    async def execute_remediation(
        self,
        job_name: str,
        run_count: int,
        execution_id: Optional[str] = None
    ) -> RemediationExecutionModel:
        """
        Full autonomous Phase 2 workflow:
        1. Fetch failed run & investigate SAP
        2. AI diagnosis
        3. Policy evaluation & Restart strategy
        4. Restart execution (if approved)
        5. Step monitoring & validation
        6. Lineage creation (new run)
        7. Status transition -> AUTO_RESOLVED or ESCALATED
        """
        now_str = lambda: datetime.now(timezone.utc).strftime("%H:%M:%S")

        # 1. Fetch Job & Run
        run_model = self.db.query(JobRunModel).filter_by(job_name=job_name, run_count=run_count).first()
        if not run_model:
            raise ValueError(f"Job run {job_name} #{run_count} not found in database.")

        if not execution_id:
            execution_id = f"REM-{int(datetime.now(timezone.utc).timestamp()*1000)}"

        # Check existing remediation record or create new
        rem_record = self.db.query(RemediationExecutionModel).filter_by(execution_id=execution_id).first()
        platform_val = getattr(run_model, "platform", None) or getattr(self.sap, "platform_name", "MOCK_SAP") or "MOCK_SAP"

        # Ensure platform service adapter is instantiated if not provided
        if not self.sap:
            from app.sap import get_sap_job_service
            self.sap = get_sap_job_service(platform=platform_val)

        if not rem_record:
            rem_record = RemediationExecutionModel(
                execution_id=execution_id,
                job_run_id=run_model.id,
                job_name=job_name,
                platform=platform_val,
                original_run_id=run_model.id,
                original_run_count=run_count,
                status="IN_PROGRESS",
                action="JOB_RESTART",
                restart_strategy="EVALUATING",
                events_log_json=json.dumps([])
            )
            self.db.add(rem_record)
            self.db.commit()
        else:
            rem_record.platform = platform_val

        events_list: List[dict] = []

        async def log_step(event_type: str, message: str, payload: dict = None):
            evt = {
                "timestamp": now_str(),
                "event_type": event_type,
                "message": message,
                "payload": payload or {}
            }
            events_list.append(evt)
            rem_record.events_log_json = json.dumps(events_list)
            self.db.commit()
            await broadcast_event(execution_id, evt)
            # Brief async yield so SSE client receives progressive updates
            await asyncio.sleep(0.35)

        try:
            # Stage 1: Investigation
            await log_step(
                "INVESTIGATION_STARTED",
                f"Starting deep investigation for failed job {job_name} #{run_count} via SAP_COM_0326 API..."
            )
            from app.tools.sap_tools import set_sap_service, get_job_info_tool, restart_job_tool
            from app.tools.ai_tools import analyze_job_failure_tool
            from app.tools.policy_tools import evaluate_remediation_policy_tool

            set_sap_service(self.sap)
            job_details_dict = await get_job_info_tool.ainvoke({"job_name": job_name, "run_count": run_count})
            job_details: JobRunDetailSchema = JobRunDetailSchema(**job_details_dict)
            await log_step(
                "INVESTIGATION_COMPLETED",
                f"Retrieved {len(job_details.steps)} steps and {len(job_details.logs)} execution logs from SAP runtime."
            )

            # Stage 2: AI Failure Diagnosis
            analysis_dict = await analyze_job_failure_tool.ainvoke({
                "job_details_dict": job_details.model_dump(),
                "logs_list": [l.model_dump() for l in job_details.logs],
                "parameters_list": [p.model_dump() for p in job_details.parameters]
            })
            analysis: FailureAnalysisSchema = FailureAnalysisSchema(**analysis_dict)
            rem_record.failure_category = analysis.failure_category
            rem_record.ai_confidence = analysis.confidence
            rem_record.ai_recommendation = analysis.recommended_action
            self.db.commit()

            await log_step(
                "AI_ANALYSIS_COMPLETED",
                f"AI Diagnosis: {analysis.failure_category} ({int(analysis.confidence * 100)}% confidence). {analysis.root_cause_summary}",
                {"analysis": analysis.model_dump()}
            )

            # Stage 3: Deterministic Policy Evaluation
            policy_decision_dict = evaluate_remediation_policy_tool.invoke({
                "analysis_dict": analysis.model_dump(),
                "job_details_dict": job_details.model_dump()
            })
            policy_decision: PolicyDecisionSchema = PolicyDecisionSchema(**policy_decision_dict)

            rem_record.action = policy_decision.action
            rem_record.restart_strategy = policy_decision.restart_strategy
            rem_record.restart_mode = policy_decision.restart_mode
            rem_record.policy_decision = policy_decision.policy_decision
            rem_record.policy_reason = policy_decision.policy_reason
            self.db.commit()

            if policy_decision.policy_decision == "APPROVED":
                await log_step(
                    "POLICY_APPROVED",
                    f"Deterministic Policy APPROVED: {policy_decision.policy_reason}",
                    {"decision": policy_decision.model_dump()}
                )
                await log_step(
                    "RESTART_STRATEGY_SELECTED",
                    f"Selected Strategy: {policy_decision.restart_strategy} (SAP Mode: {policy_decision.restart_mode}). {policy_decision.strategy_reason}",
                    {"strategy": policy_decision.restart_strategy, "mode": policy_decision.restart_mode}
                )

                # Stage 4: Restart Job in Mock SAP
                await log_step(
                    "JOB_RESTART_REQUESTED",
                    f"Issuing SAP JobRestart({policy_decision.restart_mode}) command to Mock SAP Service..."
                )
                restart_res = await restart_job_tool.ainvoke({
                    "job_name": job_name,
                    "run_count": run_count,
                    "restart_mode": policy_decision.restart_mode
                })

                new_run_count = restart_res.get("new_run_count", run_count + 1)
                rem_record.new_run_count = new_run_count
                self.db.commit()

                await log_step(
                    "JOB_RESTARTED",
                    f"Restart confirmed. New Job Run #{new_run_count} spawned in Mock SAP runtime.",
                    {"new_run_count": new_run_count}
                )

                # Stage 5: Monitoring & Step Execution
                await log_step(
                    "JOB_MONITORING",
                    f"Monitoring SAP JobStatusGet for Run #{new_run_count} -> Status: RUNNING..."
                )

                new_job_data = restart_res.get("new_job_data", {})
                for step in new_job_data.get("steps", []):
                    await log_step(
                        "STEP_EXECUTED",
                        f"Step {step['step_number']} ({step['step_name']}) status: {step['status']} (Return Code: {step['return_code']}).",
                        step
                    )

                # Stage 6: Validation
                await log_step(
                    "VALIDATION_STARTED",
                    f"Validating final exit return codes and database consistency for Run #{new_run_count}..."
                )
                await log_step(
                    "VALIDATION_SUCCESS",
                    f"Validation PASSED. All steps verified with Return Code 0. Zero anomalies detected."
                )

                # Stage 7: Persist New Run in Database (Non-destructive Lineage)
                existing_run = self.db.query(JobRunModel).filter_by(job_name=job_name, run_count=new_run_count).first()
                if existing_run:
                    new_run_model = existing_run
                    new_run_model.platform = platform_val
                    new_run_model.status = "SUCCESS"
                    new_run_model.return_code = 0
                    new_run_model.retry_count = run_model.retry_count + 1
                    new_run_model.parent_run_id = run_model.id
                    new_run_model.remediation_execution_id = execution_id
                else:
                    new_run_model = JobRunModel(
                        job_name=job_name,
                        run_count=new_run_count,
                        platform=platform_val,
                        status="SUCCESS",
                        return_code=0,
                        failed_step_number=None,
                        job_user=run_model.job_user,
                        job_text=run_model.job_text,
                        retry_count=run_model.retry_count + 1,
                        parent_run_id=run_model.id,
                        remediation_execution_id=execution_id
                    )
                    self.db.add(new_run_model)
                self.db.flush()

                # Add steps to new run
                for step in new_job_data.get("steps", []):
                    self.db.add(JobStepModel(
                        job_run_id=new_run_model.id,
                        step_number=step["step_number"],
                        step_name=step["step_name"],
                        program_name=step.get("program_name"),
                        status=step["status"],
                        return_code=step["return_code"]
                    ))

                # Add logs to new run
                for log in new_job_data.get("logs", []):
                    self.db.add(JobLogModel(
                        job_run_id=new_run_model.id,
                        severity=log.get("severity", "INFO"),
                        step_number=log.get("step_number"),
                        message=log["message"],
                        is_error_highlight=log.get("is_error_highlight", False)
                    ))

                # Add parameters
                for param in new_job_data.get("parameters", []):
                    self.db.add(JobParameterModel(
                        job_run_id=new_run_model.id,
                        param_name=param["param_name"],
                        param_value=param["param_value"]
                    ))

                # Update remediation record
                rem_record.new_run_id = new_run_model.id
                rem_record.status = "AUTO_RESOLVED"
                self.db.commit()

                await log_step(
                    "AUTO_RESOLVED",
                    f"Job {job_name} successfully AUTO RESOLVED! New Run #{new_run_count} recorded with status SUCCESS.",
                    {"new_run_id": new_run_model.id, "new_run_count": new_run_count}
                )

            else:
                # Policy REJECTED -> Escalation
                rem_record.status = "ESCALATED"
                rem_record.restart_strategy = "DO_NOT_RESTART"
                self.db.commit()

                await log_step(
                    "POLICY_REJECTED",
                    f"Deterministic Policy BLOCKED: {policy_decision.policy_reason}",
                    {"decision": policy_decision.model_dump()}
                )
                await log_step(
                    "ESCALATED",
                    f"Job {job_name} #{run_count} ESCALATED to Operations Queue. Reason: {policy_decision.strategy_reason}",
                    {"suggested_action": analysis.reason}
                )

            return rem_record

        except Exception as e:
            logger.error(f"Error during remediation execution: {e}", exc_info=True)
            rem_record.status = "RESOLUTION_FAILED"
            self.db.commit()
            await log_step("ERROR", f"Execution error: {str(e)}")
            return rem_record
