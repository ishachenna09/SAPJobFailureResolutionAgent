from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import json
from app.db.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class JobModel(Base):
    __tablename__ = "jobs"
    
    job_name = Column(String(100), primary_key=True, index=True)
    description = Column(String(255), nullable=True)
    environment = Column(String(50), default="MOCK")
    platform = Column(String(50), default="MOCK_SAP", index=True) # MOCK_SAP or SAP_BTP
    restart_allowed = Column(Boolean, default=True)
    max_retries = Column(Integer, default=2)

    runs = relationship("JobRunModel", back_populates="job_info", cascade="all, delete-orphan")


class JobRunModel(Base):
    __tablename__ = "job_runs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_name = Column(String(100), ForeignKey("jobs.job_name"), index=True)
    run_count = Column(Integer, index=True)
    platform = Column(String(50), default="MOCK_SAP", index=True) # MOCK_SAP or SAP_BTP
    status = Column(String(50), index=True) # FAILED, SUCCESS, RUNNING, SCHEDULED, READY, CANCELLED, ABORTED
    start_time = Column(DateTime, default=utc_now)
    end_time = Column(DateTime, nullable=True)
    return_code = Column(Integer, default=0)
    failed_step_number = Column(Integer, nullable=True)
    job_user = Column(String(100), default="SAP_JOB_USER")
    job_text = Column(String(255), nullable=True)
    retry_count = Column(Integer, default=0)
    parent_run_id = Column(Integer, ForeignKey("job_runs.id"), nullable=True)
    remediation_execution_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    
    job_info = relationship("JobModel", back_populates="runs")
    steps = relationship("JobStepModel", back_populates="job_run", cascade="all, delete-orphan")
    logs = relationship("JobLogModel", back_populates="job_run", cascade="all, delete-orphan")
    parameters = relationship("JobParameterModel", back_populates="job_run", cascade="all, delete-orphan")
    analysis = relationship("FailureAnalysisModel", back_populates="job_run", uselist=False, cascade="all, delete-orphan")
    remediations = relationship("RemediationExecutionModel", back_populates="job_run", cascade="all, delete-orphan", foreign_keys="RemediationExecutionModel.job_run_id")

class JobStepModel(Base):
    __tablename__ = "job_steps"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_run_id = Column(Integer, ForeignKey("job_runs.id"), index=True)
    step_number = Column(Integer)
    step_name = Column(String(100))
    program_name = Column(String(100), nullable=True)
    status = Column(String(50)) # SUCCESS, FAILED, RUNNING, SKIPPED, NOT_EXECUTED
    return_code = Column(Integer, default=0)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    
    job_run = relationship("JobRunModel", back_populates="steps")


class JobLogModel(Base):
    __tablename__ = "job_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_run_id = Column(Integer, ForeignKey("job_runs.id"), index=True)
    timestamp = Column(DateTime, default=utc_now)
    severity = Column(String(20), default="INFO") # ERROR, WARN, INFO, DEBUG
    step_number = Column(Integer, nullable=True)
    message = Column(Text)
    is_error_highlight = Column(Boolean, default=False)
    
    job_run = relationship("JobRunModel", back_populates="logs")


class JobParameterModel(Base):
    __tablename__ = "job_parameters"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_run_id = Column(Integer, ForeignKey("job_runs.id"), index=True)
    param_name = Column(String(100))
    param_value = Column(String(255))
    
    job_run = relationship("JobRunModel", back_populates="parameters")


class JobEventModel(Base):
    __tablename__ = "job_events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(100), unique=True, index=True)
    event_type = Column(String(100))
    job_name = Column(String(100))
    run_count = Column(Integer)
    platform = Column(String(50), default="MOCK_SAP", index=True)
    idempotency_key = Column(String(255), unique=True, index=True)
    payload_json = Column(Text)
    received_at = Column(DateTime, default=utc_now)
    processed = Column(Boolean, default=False)


class FailureAnalysisModel(Base):
    __tablename__ = "failure_analyses"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_run_id = Column(Integer, ForeignKey("job_runs.id"), unique=True, index=True)
    platform = Column(String(50), default="MOCK_SAP", index=True)
    failure_category = Column(String(100))
    confidence = Column(Float)
    root_cause_summary = Column(Text)
    evidence_json = Column(Text) # JSON list of strings
    recommended_action = Column(String(100))
    restart_mode = Column(String(10)) # E or A
    restart_strategy = Column(String(50), nullable=True) # RESTART_FROM_FAILED_STEP, RESTART_FROM_START, DO_NOT_RESTART
    reason = Column(Text)
    created_at = Column(DateTime, default=utc_now)
    
    job_run = relationship("JobRunModel", back_populates="analysis")

    @property
    def evidence(self):
        try:
            return json.loads(self.evidence_json) if self.evidence_json else []
        except Exception:
            return []


class RemediationExecutionModel(Base):
    __tablename__ = "remediation_executions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(String(100), unique=True, index=True)
    job_run_id = Column(Integer, ForeignKey("job_runs.id"), index=True)
    job_name = Column(String(100), nullable=True)
    platform = Column(String(50), default="MOCK_SAP", index=True)
    original_run_id = Column(Integer, nullable=True)
    original_run_count = Column(Integer, nullable=True)
    new_run_id = Column(Integer, nullable=True)
    new_run_count = Column(Integer, nullable=True)
    failure_category = Column(String(100), nullable=True)
    ai_confidence = Column(Float, nullable=True)
    ai_recommendation = Column(String(100), nullable=True)
    action = Column(String(50)) # JOB_RESTART, ESCALATE
    restart_strategy = Column(String(50), nullable=True) # RESTART_FROM_FAILED_STEP, RESTART_FROM_START, DO_NOT_RESTART
    restart_mode = Column(String(10), nullable=True) # E, A, or NONE
    policy_decision = Column(String(50)) # APPROVED, REJECTED
    policy_reason = Column(Text)
    status = Column(String(50)) # AUTO_RESOLVED, ESCALATED, IN_PROGRESS, RESOLUTION_FAILED
    events_log_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    
    job_run = relationship("JobRunModel", back_populates="remediations", foreign_keys=[job_run_id])

    @property
    def events_log(self):
        try:
            return json.loads(self.events_log_json) if self.events_log_json else []
        except Exception:
            return []
