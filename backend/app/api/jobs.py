import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.db.database import get_db, SessionLocal
from app.db.models import (
    JobRunModel, JobModel, FailureAnalysisModel, JobStepModel, JobLogModel,
    JobParameterModel, JobEventModel, RemediationExecutionModel
)
from app.schemas.job import JobRunDetailSchema, JobStepSchema, JobLogSchema, JobParameterSchema, FailureAnalysisSchema
from app.services.remediation_service import RemediationService, register_event_queue, unregister_event_queue

router = APIRouter(prefix="/api", tags=["Jobs & Remediations"])

def _apply_platform_filter(query, model, platform_val: str):
    p = (platform_val or "MOCK_SAP").upper()
    if p in ("SAP_BTP", "BTP"):
        return query.filter(model.platform == "SAP_BTP")
    return query.filter((model.platform == "MOCK_SAP") | (model.platform.is_(None)))

@router.post("/environment/switch")
async def switch_environment(platform: str = Query("MOCK_SAP"), db: Session = Depends(get_db)):
    """
    Switches active platform mode (MOCK_SAP or SAP_BTP) and triggers live fetch for SAP BTP.
    """
    p = (platform or "MOCK_SAP").upper()
    from app.config import settings
    if p in ("SAP_BTP", "BTP"):
        settings.JOB_PLATFORM = "sap_btp"
        try:
            from app.sap.btp_sap import BTPJobSchedulingService
            from app.agents.job_resolution_agent import JobResolutionAgent
            from app.schemas.job import JobEventPayload

            btp_service = BTPJobSchedulingService()
            agent = JobResolutionAgent(db, sap_service=btp_service)
            btp_runs = await btp_service.fetch_recent_executions()
            
            for run in btp_runs:
                evt_type = "SAP_JOB_COMPLETED" if run.status == "SUCCESS" else "SAP_JOB_FAILED"
                payload = JobEventPayload(
                    event_type=evt_type,
                    job_name=run.job_name,
                    job_run_count=run.run_count,
                    platform="SAP_BTP",
                    status=run.status
                )
                await agent.process_job_event(payload)
            return {"status": "SUCCESS", "platform": "SAP_BTP", "runs_fetched": len(btp_runs)}
        except Exception as e:
            return {"status": "ERROR", "platform": "SAP_BTP", "message": f"SAP BTP connection unavailable: {str(e)}"}
    else:
        settings.JOB_PLATFORM = "mock"
        return {"status": "SUCCESS", "platform": "MOCK_SAP"}

@router.get("/stats")
def get_dashboard_stats(platform: str = Query("MOCK_SAP"), db: Session = Depends(get_db)):
    query = db.query(JobRunModel)
    query = _apply_platform_filter(query, JobRunModel, platform)
    total_runs = query.count()

    # Active failed runs = FAILED runs that have not been successfully remediated
    resolved_parent_ids = set()
    success_children_q = db.query(JobRunModel.parent_run_id).filter(
        JobRunModel.parent_run_id.isnot(None),
        JobRunModel.status == "SUCCESS"
    )
    success_children = _apply_platform_filter(success_children_q, JobRunModel, platform).all()
    resolved_parent_ids.update({r[0] for r in success_children if r[0]})

    resolved_remediations_q = db.query(RemediationExecutionModel.job_run_id).filter(
        RemediationExecutionModel.status.in_(["AUTO_RESOLVED", "MANUALLY_RESOLVED"])
    )
    resolved_remediations = _apply_platform_filter(resolved_remediations_q, RemediationExecutionModel, platform).all()
    resolved_parent_ids.update({r[0] for r in resolved_remediations if r[0]})

    all_failed_q = db.query(JobRunModel).filter_by(status="FAILED")
    all_failed = _apply_platform_filter(all_failed_q, JobRunModel, platform).all()
    active_failed_runs = [r for r in all_failed if r.id not in resolved_parent_ids]
    failed_runs = len(active_failed_runs)

    success_q = db.query(JobRunModel).filter_by(status="SUCCESS")
    success_runs = _apply_platform_filter(success_q, JobRunModel, platform).count()

    running_q = db.query(JobRunModel).filter_by(status="RUNNING")
    running_runs = _apply_platform_filter(running_q, JobRunModel, platform).count()

    failure_rate = round((failed_runs / total_runs * 100), 1) if total_runs > 0 else 0.0
    success_rate = round((success_runs / total_runs * 100), 1) if total_runs > 0 else 0.0

    return {
        "total_jobs": total_runs,
        "failed_jobs": failed_runs,
        "successful_jobs": success_runs,
        "running_jobs": running_runs,
        "failure_rate": failure_rate,
        "success_rate": success_rate,
        "agent_status": "ONLINE",
        "platform": platform
    }

@router.get("/jobs")
def list_job_runs(
    status: Optional[str] = Query(None),
    job_name: Optional[str] = Query(None),
    platform: str = Query("MOCK_SAP"),
    active_failed_only: bool = Query(False),
    db: Session = Depends(get_db)
):
    """
    Returns job runs filtered by platform.
    If active_failed_only=True or status=FAILED, excludes failed runs that have already been resolved.
    """
    query = db.query(JobRunModel).order_by(JobRunModel.id.desc())
    query = _apply_platform_filter(query, JobRunModel, platform)
    if status:
        query = query.filter(JobRunModel.status == status)
    if job_name:
        query = query.filter(JobRunModel.job_name.ilike(f"%{job_name}%"))

    runs = query.all()
    result = []

    # Collect IDs of failed runs that have been remediated/resolved
    resolved_parent_ids = set()
    success_children = db.query(JobRunModel.parent_run_id).filter(
        JobRunModel.parent_run_id.isnot(None),
        JobRunModel.status == "SUCCESS"
    ).all()
    resolved_parent_ids.update({r[0] for r in success_children if r[0]})

    resolved_remediations = db.query(RemediationExecutionModel.job_run_id).filter(
        RemediationExecutionModel.status.in_(["AUTO_RESOLVED", "MANUALLY_RESOLVED"])
    ).all()
    resolved_parent_ids.update({r[0] for r in resolved_remediations if r[0]})

    seen_keys = set()
    for r in runs:
        key = (r.job_name, r.run_count)
        if key in seen_keys:
            continue
        seen_keys.add(key)

        is_resolved = (r.id in resolved_parent_ids) or (r.status == "SUCCESS")

        # If active_failed_only or filtering by FAILED status, skip resolved failed runs
        if (active_failed_only or status == "FAILED") and r.status == "FAILED" and is_resolved:
            continue

        analysis = db.query(FailureAnalysisModel).filter_by(job_run_id=r.id).first()
        rem = db.query(RemediationExecutionModel).filter_by(job_run_id=r.id).order_by(RemediationExecutionModel.id.desc()).first()

        result.append({
            "id": r.id,
            "job_name": r.job_name,
            "run_count": r.run_count,
            "status": r.status,
            "start_time": r.start_time.isoformat() if r.start_time else "",
            "failed_step_number": r.failed_step_number,
            "return_code": r.return_code,
            "job_text": r.job_text,
            "job_user": r.job_user,
            "failure_category": analysis.failure_category if analysis else None,
            "retry_count": r.retry_count,
            "parent_run_id": r.parent_run_id,
            "remediation_execution_id": r.remediation_execution_id or (rem.execution_id if rem else None),
            "remediation_status": rem.status if rem else None,
            "is_resolved": is_resolved
        })
    return result

@router.get("/jobs/{job_name}/{run_count}")
def get_job_run_detail(job_name: str, run_count: int, db: Session = Depends(get_db)):
    run = db.query(JobRunModel).filter_by(job_name=job_name, run_count=run_count).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"Job run {job_name} #{run_count} not found")
        
    job_info = db.query(JobModel).filter_by(job_name=job_name).first()
    steps = db.query(JobStepModel).filter_by(job_run_id=run.id).order_by(JobStepModel.step_number).all()
    logs = db.query(JobLogModel).filter_by(job_run_id=run.id).order_by(JobLogModel.id).all()
    params = db.query(JobParameterModel).filter_by(job_run_id=run.id).all()
    analysis = db.query(FailureAnalysisModel).filter_by(job_run_id=run.id).first()
    remediations = db.query(RemediationExecutionModel).filter_by(job_run_id=run.id).all()

    return {
        "id": run.id,
        "job_name": run.job_name,
        "run_count": run.run_count,
        "status": run.status,
        "start_time": run.start_time.isoformat() if run.start_time else "",
        "end_time": run.end_time.isoformat() if run.end_time else None,
        "return_code": run.return_code,
        "failed_step_number": run.failed_step_number,
        "job_user": run.job_user,
        "job_text": run.job_text,
        "retry_count": run.retry_count,
        "parent_run_id": run.parent_run_id,
        "remediation_execution_id": run.remediation_execution_id,
        "environment": job_info.environment if job_info else "MOCK_SAP",
        "restart_allowed": job_info.restart_allowed if job_info else True,
        "max_retries": job_info.max_retries if job_info else 2,
        "steps": [
            {
                "step_number": s.step_number,
                "step_name": s.step_name,
                "program_name": s.program_name,
                "status": s.status,
                "return_code": s.return_code
            } for s in steps
        ],
        "logs": [
            {
                "timestamp": l.timestamp.strftime("%H:%M:%S") if (hasattr(l.timestamp, 'strftime') and l.timestamp) else str(l.timestamp or ""),
                "severity": l.severity,
                "step_number": l.step_number,
                "message": l.message,
                "is_error_highlight": l.is_error_highlight
            } for l in logs
        ],
        "parameters": [
            {
                "param_name": p.param_name,
                "param_value": p.param_value
            } for p in params
        ],
        "analysis": {
            "failure_category": analysis.failure_category,
            "confidence": analysis.confidence,
            "root_cause_summary": analysis.root_cause_summary,
            "evidence": analysis.evidence,
            "recommended_action": analysis.recommended_action,
            "restart_mode": analysis.restart_mode,
            "restart_strategy": analysis.restart_strategy or "RESTART_FROM_FAILED_STEP",
            "reason": analysis.reason
        } if analysis else None,
        "remediations": [
            {
                "execution_id": r.execution_id,
                "action": r.action,
                "restart_strategy": r.restart_strategy,
                "restart_mode": r.restart_mode,
                "policy_decision": r.policy_decision,
                "policy_reason": r.policy_reason,
                "status": r.status,
                "new_run_count": r.new_run_count,
                "created_at": r.created_at.strftime("%H:%M:%S") if r.created_at else ""
            } for r in remediations
        ]
    }

@router.get("/jobs/{job_name}/{run_count}/history")
def get_job_history(job_name: str, run_count: int, db: Session = Depends(get_db)):
    """
    Returns complete chronological history & lineage for a job:
    Original failed run -> Remediation execution -> Restarted successful run.
    """
    runs = db.query(JobRunModel).filter_by(job_name=job_name).order_by(JobRunModel.run_count.asc()).all()
    history_entries = []

    for r in runs:
        analysis = db.query(FailureAnalysisModel).filter_by(job_run_id=r.id).first()
        rem = db.query(RemediationExecutionModel).filter(
            (RemediationExecutionModel.job_run_id == r.id) |
            (RemediationExecutionModel.original_run_id == r.id) |
            (RemediationExecutionModel.new_run_id == r.id)
        ).first()

        logs = db.query(JobLogModel).filter_by(job_run_id=r.id).order_by(JobLogModel.id).all()
        steps = db.query(JobStepModel).filter_by(job_run_id=r.id).order_by(JobStepModel.step_number).all()

        history_entries.append({
            "run_id": r.id,
            "job_name": r.job_name,
            "run_count": r.run_count,
            "status": r.status,
            "return_code": r.return_code,
            "failed_step_number": r.failed_step_number,
            "retry_count": r.retry_count,
            "parent_run_id": r.parent_run_id,
            "start_time": r.start_time.strftime("%H:%M:%S") if r.start_time else "",
            "failure_category": analysis.failure_category if analysis else None,
            "root_cause_summary": analysis.root_cause_summary if analysis else None,
            "ai_confidence": analysis.confidence if analysis else None,
            "restart_strategy": rem.restart_strategy if rem else (analysis.restart_strategy if analysis else None),
            "policy_decision": rem.policy_decision if rem else None,
            "policy_reason": rem.policy_reason if rem else None,
            "remediation_id": rem.execution_id if rem else None,
            "remediation_status": rem.status if rem else None,
            "remediation_events": rem.events_log if rem else [],
            "sap_logs": [
                {
                    "timestamp": l.timestamp.strftime("%H:%M:%S") if hasattr(l.timestamp, 'strftime') else str(l.timestamp),
                    "severity": l.severity,
                    "step_number": l.step_number,
                    "message": l.message,
                    "is_error_highlight": l.is_error_highlight
                } for l in logs
            ],
            "steps": [
                {
                    "step_number": s.step_number,
                    "step_name": s.step_name,
                    "program_name": s.program_name,
                    "status": s.status,
                    "return_code": s.return_code
                } for s in steps
            ]
        })

    return {
        "job_name": job_name,
        "current_run_count": run_count,
        "history": history_entries
    }

async def _run_remediation_background(job_name: str, run_count: int, execution_id: str):
    db = SessionLocal()
    try:
        from app.sap import get_sap_job_service
        run = db.query(JobRunModel).filter_by(job_name=job_name, run_count=run_count).first()
        platform_val = getattr(run, "platform", "MOCK_SAP") if run else "MOCK_SAP"
        sap_service = get_sap_job_service(platform=platform_val)
        service = RemediationService(db, sap_service=sap_service)
        await service.execute_remediation(job_name, run_count, execution_id=execution_id)
    except Exception as e:
        print(f"Background remediation error for {job_name} #{run_count}: {e}")
    finally:
        db.close()

@router.post("/jobs/{job_name}/{run_count}/remediation")
async def trigger_job_remediation(
    job_name: str,
    run_count: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Starts Phase 2 Autonomous Remediation on a specific failed job run.
    Idempotent: prevents starting multiple concurrent remediations on the same run.
    """
    run = db.query(JobRunModel).filter_by(job_name=job_name, run_count=run_count).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"Job run {job_name} #{run_count} not found")

    # Check if job run is already resolved
    existing_success_child = db.query(JobRunModel).filter_by(parent_run_id=run.id, status="SUCCESS").first()
    has_resolved_rem = db.query(RemediationExecutionModel).filter(
        RemediationExecutionModel.job_run_id == run.id,
        RemediationExecutionModel.status.in_(["AUTO_RESOLVED", "MANUALLY_RESOLVED"])
    ).first()

    if run.status == "SUCCESS" or existing_success_child or has_resolved_rem:
        raise HTTPException(
            status_code=400,
            detail=f"Job run {job_name} #{run_count} has already been successfully resolved via agent."
        )

    in_progress_rem = db.query(RemediationExecutionModel).filter_by(job_run_id=run.id, status="IN_PROGRESS").order_by(RemediationExecutionModel.id.desc()).first()
    if in_progress_rem:
        return {
            "execution_id": in_progress_rem.execution_id,
            "status": in_progress_rem.status,
            "message": "Remediation already running for this job execution.",
            "job_name": job_name,
            "run_count": run_count
        }

    execution_id = f"REM-{int(datetime.utcnow().timestamp()*1000)}"

    rem_record = RemediationExecutionModel(
        execution_id=execution_id,
        job_run_id=run.id,
        job_name=job_name,
        original_run_id=run.id,
        original_run_count=run_count,
        status="IN_PROGRESS",
        action="JOB_RESTART",
        restart_strategy="EVALUATING",
        events_log_json=json.dumps([])
    )
    db.add(rem_record)
    db.commit()

    # Launch background remediation
    background_tasks.add_task(_run_remediation_background, job_name, run_count, execution_id)

    return {
        "execution_id": execution_id,
        "status": "IN_PROGRESS",
        "message": f"Phase 2 autonomous remediation initiated for {job_name} #{run_count}",
        "job_name": job_name,
        "run_count": run_count
    }

@router.get("/remediations/{execution_id}")
def get_remediation_status(execution_id: str, db: Session = Depends(get_db)):
    rem = db.query(RemediationExecutionModel).filter_by(execution_id=execution_id).first()
    if not rem:
        raise HTTPException(status_code=404, detail="Remediation execution not found")
    
    return {
        "id": rem.id,
        "execution_id": rem.execution_id,
        "job_name": rem.job_name,
        "original_run_count": rem.original_run_count,
        "new_run_count": rem.new_run_count,
        "failure_category": rem.failure_category,
        "ai_confidence": rem.ai_confidence,
        "ai_recommendation": rem.ai_recommendation,
        "action": rem.action,
        "restart_strategy": rem.restart_strategy,
        "restart_mode": rem.restart_mode,
        "policy_decision": rem.policy_decision,
        "policy_reason": rem.policy_reason,
        "status": rem.status,
        "events_log": rem.events_log,
        "created_at": rem.created_at.strftime("%H:%M:%S") if rem.created_at else ""
    }

@router.get("/remediations/{execution_id}/stream")
async def stream_remediation_events(execution_id: str, db: Session = Depends(get_db)):
    """
    Server-Sent Events (SSE) streaming endpoint for live execution logs and progress updates.
    """
    rem = db.query(RemediationExecutionModel).filter_by(execution_id=execution_id).first()
    if not rem:
        raise HTTPException(status_code=404, detail="Remediation execution not found")

    async def event_generator():
        q = register_event_queue(execution_id)
        try:
            # Replay historical events already in DB
            db_session = SessionLocal()
            curr_rem = db_session.query(RemediationExecutionModel).filter_by(execution_id=execution_id).first()
            if curr_rem and curr_rem.events_log:
                for evt in curr_rem.events_log:
                    yield f"data: {json.dumps(evt)}\n\n"
            db_session.close()

            # If already resolved/escalated, send completed status and close
            if curr_rem and curr_rem.status in ["AUTO_RESOLVED", "ESCALATED", "RESOLUTION_FAILED"]:
                done_evt = {"event_type": "STREAM_FINISHED", "status": curr_rem.status}
                yield f"data: {json.dumps(done_evt)}\n\n"
                return

            # Listen for live broadcasted events
            while True:
                try:
                    evt = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield f"data: {json.dumps(evt)}\n\n"
                    if evt.get("event_type") in ["AUTO_RESOLVED", "ESCALATED", "RESOLUTION_FAILED", "STREAM_FINISHED"]:
                        break
                except asyncio.TimeoutError:
                    # Keepalive ping
                    yield f": keepalive\n\n"
                    # Check DB status
                    chk_session = SessionLocal()
                    chk_rem = chk_session.query(RemediationExecutionModel).filter_by(execution_id=execution_id).first()
                    status = chk_rem.status if chk_rem else "UNKNOWN"
                    chk_session.close()
                    if status in ["AUTO_RESOLVED", "ESCALATED", "RESOLUTION_FAILED"]:
                        done_evt = {"event_type": "STREAM_FINISHED", "status": status}
                        yield f"data: {json.dumps(done_evt)}\n\n"
                        break
        finally:
            unregister_event_queue(execution_id, q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.get("/activity")
def get_recent_activity(platform: str = Query("MOCK_SAP"), db: Session = Depends(get_db)):
    query = db.query(JobEventModel).order_by(JobEventModel.id.desc())
    query = _apply_platform_filter(query, JobEventModel, platform)
    events = query.limit(20).all()
    result = []
    for e in events:
        result.append({
            "id": e.id,
            "event_id": e.event_id,
            "event_type": e.event_type,
            "job_name": e.job_name,
            "run_count": e.run_count,
            "received_at": e.received_at.strftime("%H:%M:%S") if e.received_at else "",
            "processed": e.processed
        })
    return result

@router.get("/remediations")
def list_remediations(
    status: Optional[str] = Query(None),
    platform: str = Query("MOCK_SAP"),
    db: Session = Depends(get_db)
):
    query = db.query(RemediationExecutionModel).order_by(RemediationExecutionModel.id.desc())
    query = _apply_platform_filter(query, RemediationExecutionModel, platform)
    if status:
        query = query.filter(RemediationExecutionModel.status == status)
    
    remediations = query.all()
    result = []
    for rem in remediations:
        run = db.query(JobRunModel).filter_by(id=rem.job_run_id).first()
        analysis = db.query(FailureAnalysisModel).filter_by(job_run_id=rem.job_run_id).first()
        result.append({
            "id": rem.id,
            "execution_id": rem.execution_id,
            "job_name": rem.job_name or (run.job_name if run else "UNKNOWN"),
            "run_count": rem.original_run_count or (run.run_count if run else 0),
            "new_run_count": rem.new_run_count,
            "failure_category": rem.failure_category or (analysis.failure_category if analysis else "UNKNOWN"),
            "action": rem.action,
            "restart_strategy": rem.restart_strategy or "RESTART_FROM_FAILED_STEP",
            "restart_mode": rem.restart_mode,
            "policy_decision": rem.policy_decision,
            "policy_reason": rem.policy_reason,
            "status": rem.status,
            "created_at": rem.created_at.strftime("%H:%M:%S") if rem.created_at else ""
        })
    return result

@router.get("/remediations/{execution_id}/timeline")
def get_remediation_timeline(execution_id: str, db: Session = Depends(get_db)):
    rem = db.query(RemediationExecutionModel).filter_by(execution_id=execution_id).first()
    if not rem:
        rem = db.query(RemediationExecutionModel).filter_by(id=int(execution_id) if execution_id.isdigit() else 0).first()
    if not rem:
        raise HTTPException(status_code=404, detail="Remediation execution not found")
        
    run = db.query(JobRunModel).filter_by(id=rem.job_run_id).first()
    analysis = db.query(FailureAnalysisModel).filter_by(job_run_id=rem.job_run_id).first()
    
    timeline = []
    if rem.events_log:
        for evt in rem.events_log:
            timeline.append({
                "timestamp": evt.get("timestamp", ""),
                "title": evt.get("event_type", "").replace("_", " ").title(),
                "detail": evt.get("message", ""),
                "status": "COMPLETED" if "ERROR" not in evt.get("event_type", "") and "BLOCKED" not in evt.get("event_type", "") else "BLOCKED"
            })
    else:
        timeline = [
            {"timestamp": rem.created_at.strftime("%H:%M:%S") if rem.created_at else "", "title": "Job Failure Event Received", "detail": f"Event ingested for {rem.job_name} #{rem.original_run_count}", "status": "COMPLETED"},
            {"timestamp": rem.created_at.strftime("%H:%M:%S") if rem.created_at else "", "title": "Mock SAP Investigation Completed", "detail": "Retrieved steps, logs, and parameters via SAP_COM_0326", "status": "COMPLETED"},
            {"timestamp": rem.created_at.strftime("%H:%M:%S") if rem.created_at else "", "title": "AI Failure Analysis Completed", "detail": f"Category: {rem.failure_category or 'N/A'}", "status": "COMPLETED"},
            {"timestamp": rem.created_at.strftime("%H:%M:%S") if rem.created_at else "", "title": f"Deterministic Policy Check: {rem.policy_decision}", "detail": rem.policy_reason, "status": "COMPLETED" if rem.policy_decision == "APPROVED" else "BLOCKED"},
        ]

    return {
        "execution_id": rem.execution_id,
        "job_name": rem.job_name or (run.job_name if run else "UNKNOWN"),
        "run_count": rem.original_run_count or (run.run_count if run else 0),
        "status": rem.status,
        "timeline": timeline
    }

@router.get("/escalations")
def list_escalations(platform: str = Query("MOCK_SAP"), db: Session = Depends(get_db)):
    query = db.query(RemediationExecutionModel).filter_by(status="ESCALATED").order_by(RemediationExecutionModel.id.desc())
    query = _apply_platform_filter(query, RemediationExecutionModel, platform)
    remediations = query.all()
    result = []
    for rem in remediations:
        run = db.query(JobRunModel).filter_by(id=rem.job_run_id).first()
        analysis = db.query(FailureAnalysisModel).filter_by(job_run_id=rem.job_run_id).first()
        
        severity = "HIGH" if (rem.failure_category and "AUTHORIZATION" in rem.failure_category) else "CRITICAL" if (run and run.retry_count >= 2) else "MEDIUM"
        
        result.append({
            "id": rem.id,
            "execution_id": rem.execution_id,
            "job_name": rem.job_name or (run.job_name if run else "UNKNOWN"),
            "run_count": rem.original_run_count or (run.run_count if run else 0),
            "failure_category": rem.failure_category or (analysis.failure_category if analysis else "UNKNOWN"),
            "severity": severity,
            "reason": rem.policy_reason,
            "root_cause_summary": analysis.root_cause_summary if analysis else "",
            "suggested_action": analysis.reason if analysis else "Manual inspection required",
            "created_at": rem.created_at.strftime("%H:%M:%S") if rem.created_at else ""
        })
    return result

@router.post("/escalations/{id}/resolve")
def resolve_escalation(id: int, db: Session = Depends(get_db)):
    rem = db.query(RemediationExecutionModel).filter_by(id=id).first()
    if not rem:
        raise HTTPException(status_code=404, detail="Escalation record not found")
    rem.status = "MANUALLY_RESOLVED"
    db.commit()
    return {"message": f"Escalation {rem.execution_id} marked as resolved manually."}
