import json
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.sap.base import SAPJobService
from app.sap.mock_sap import MockSAPJobService
from app.ai.provider import get_ai_service
from app.db.models import (
    JobModel, JobRunModel, JobStepModel, JobLogModel,
    JobParameterModel, JobEventModel, FailureAnalysisModel
)
from app.schemas.job import JobEventPayload, JobRunDetailSchema, FailureAnalysisSchema
from app.policies.remediation_policy import JobRemediationPolicy
from app.services.remediation_service import RemediationService

logger = logging.getLogger(__name__)

class JobResolutionAgent:
    """
    Autonomous SAP Job Failure Resolution Agent - Core Orchestrator.
    Handles event ingestion, job investigation, status recognition (FAILED / SUCCESS),
    and AI failure classification.
    """
    def __init__(self, db: Session, sap_service: SAPJobService = None):
        self.db = db
        self.sap = sap_service or MockSAPJobService()
        self.ai = get_ai_service()

    async def process_job_event(self, payload: JobEventPayload, auto_remediate: bool = False) -> dict:
        # 1. Idempotency & Deduplication
        platform_val = getattr(payload, "platform", None) or getattr(self.sap, "platform_name", "MOCK_SAP") or "MOCK_SAP"
        idempotency_key = f"{platform_val}:{payload.job_name}:{payload.job_run_count}:{payload.event_type}"
        existing_event = self.db.query(JobEventModel).filter_by(idempotency_key=idempotency_key).first()
        if existing_event:
            logger.info(f"Event already processed: {idempotency_key}")
            return {
                "status": "DUPLICATE_IGNORED",
                "idempotency_key": idempotency_key,
                "message": "Event already processed by Agent"
            }

        # Record event in DB
        event_record = JobEventModel(
            event_id=f"EVT-{int(datetime.now(timezone.utc).timestamp()*1000)}",
            event_type=payload.event_type,
            job_name=payload.job_name,
            run_count=payload.job_run_count,
            platform=platform_val,
            idempotency_key=idempotency_key,
            payload_json=json.dumps(payload.model_dump()),
            processed=False
        )
        self.db.add(event_record)
        self.db.commit()

        # 2. Investigate Job (Fetch details, status, steps, logs, params from SAP via tools)
        from app.tools.sap_tools import set_sap_service, get_job_status_tool, get_job_info_tool
        from app.tools.ai_tools import analyze_job_failure_tool

        set_sap_service(self.sap)
        status_info = await get_job_status_tool.ainvoke({"job_name": payload.job_name, "run_count": payload.job_run_count})
        job_details_dict = await get_job_info_tool.ainvoke({"job_name": payload.job_name, "run_count": payload.job_run_count})
        job_details: JobRunDetailSchema = JobRunDetailSchema(**job_details_dict)
        job_details.platform = platform_val

        # Recognized status
        recognized_status = job_details.status  # e.g. FAILED or SUCCESS

        # 3. Persist Job & JobRun state in local DB
        job_model = self.db.query(JobModel).filter_by(job_name=payload.job_name).first()
        if not job_model:
            job_model = JobModel(
                job_name=payload.job_name,
                description=job_details.job_text or f"SAP Application Job {payload.job_name}",
                environment=job_details.environment,
                platform=platform_val,
                restart_allowed=job_details.restart_allowed,
                max_retries=job_details.max_retries
            )
            self.db.add(job_model)
            self.db.flush()
        else:
            job_model.platform = platform_val

        run_model = self.db.query(JobRunModel).filter_by(
            job_name=payload.job_name,
            run_count=payload.job_run_count
        ).first()

        if not run_model:
            run_model = JobRunModel(
                job_name=payload.job_name,
                run_count=payload.job_run_count,
                platform=platform_val,
                status=recognized_status,
                return_code=job_details.return_code,
                failed_step_number=job_details.failed_step_number,
                job_user=job_details.job_user,
                job_text=job_details.job_text,
                retry_count=job_details.retry_count
            )
            self.db.add(run_model)
            self.db.flush()
        else:
            run_model.platform = platform_val
            run_model.status = recognized_status
            run_model.return_code = job_details.return_code
            run_model.failed_step_number = job_details.failed_step_number

        # Sync steps
        self.db.query(JobStepModel).filter_by(job_run_id=run_model.id).delete()
        for step in job_details.steps:
            self.db.add(JobStepModel(
                job_run_id=run_model.id,
                step_number=step.step_number,
                step_name=step.step_name,
                program_name=step.program_name,
                status=step.status,
                return_code=step.return_code
            ))

        # Sync logs
        self.db.query(JobLogModel).filter_by(job_run_id=run_model.id).delete()
        for log in job_details.logs:
            self.db.add(JobLogModel(
                job_run_id=run_model.id,
                severity=log.severity,
                step_number=log.step_number,
                message=log.message,
                is_error_highlight=log.is_error_highlight
            ))

        # Sync parameters
        self.db.query(JobParameterModel).filter_by(job_run_id=run_model.id).delete()
        for p in job_details.parameters:
            self.db.add(JobParameterModel(
                job_run_id=run_model.id,
                param_name=p.param_name,
                param_value=p.param_value
            ))

        # 4. If status is FAILED, trigger AI Failure Analysis via tool
        ai_analysis_dict = None
        if recognized_status == "FAILED":
            ai_analysis_dict = await analyze_job_failure_tool.ainvoke({
                "job_details_dict": job_details.model_dump(),
                "logs_list": [l.model_dump() for l in job_details.logs],
                "parameters_list": [p.model_dump() for p in job_details.parameters]
            })
            analysis_schema = FailureAnalysisSchema(**ai_analysis_dict)

            # Save or update analysis record
            existing_analysis = self.db.query(FailureAnalysisModel).filter_by(job_run_id=run_model.id).first()
            if existing_analysis:
                existing_analysis.platform = platform_val
                existing_analysis.failure_category = analysis_schema.failure_category
                existing_analysis.confidence = analysis_schema.confidence
                existing_analysis.root_cause_summary = analysis_schema.root_cause_summary
                existing_analysis.evidence_json = json.dumps(analysis_schema.evidence)
                existing_analysis.recommended_action = analysis_schema.recommended_action
                existing_analysis.restart_mode = analysis_schema.restart_mode
                existing_analysis.restart_strategy = analysis_schema.restart_strategy
                existing_analysis.reason = analysis_schema.reason
            else:
                self.db.add(FailureAnalysisModel(
                    job_run_id=run_model.id,
                    platform=platform_val,
                    failure_category=analysis_schema.failure_category,
                    confidence=analysis_schema.confidence,
                    root_cause_summary=analysis_schema.root_cause_summary,
                    evidence_json=json.dumps(analysis_schema.evidence),
                    recommended_action=analysis_schema.recommended_action,
                    restart_mode=analysis_schema.restart_mode,
                    restart_strategy=analysis_schema.restart_strategy,
                    reason=analysis_schema.reason
                ))

            if auto_remediate:
                remediation_service = RemediationService(self.db, self.sap)
                remediation_record = await remediation_service.execute_remediation(
                    job_name=payload.job_name,
                    run_count=payload.job_run_count
                )

        event_record.processed = True
        self.db.commit()

        return {
            "status": "PROCESSED",
            "job_name": payload.job_name,
            "run_count": payload.job_run_count,
            "recognized_status": run_model.status,
            "failed_step": job_details.failed_step_number,
            "ai_analysis": ai_analysis_dict,
            "remediation_status": remediation_record.status if 'remediation_record' in locals() else None
        }
