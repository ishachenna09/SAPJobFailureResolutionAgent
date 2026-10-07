export type RestartStrategy = 'RESTART_FROM_FAILED_STEP' | 'RESTART_FROM_START' | 'DO_NOT_RESTART';

export interface JobStep {
  step_number: number;
  step_name: string;
  program_name?: string;
  status: 'SUCCESS' | 'FAILED' | 'RUNNING' | 'SKIPPED' | 'NOT_EXECUTED';
  return_code: number;
  start_time?: string;
  end_time?: string;
}

export interface JobLog {
  timestamp: string;
  severity: 'ERROR' | 'WARN' | 'INFO' | 'DEBUG';
  step_number?: number;
  message: string;
  is_error_highlight: boolean;
}

export interface JobParameter {
  param_name: string;
  param_value: string;
}

export interface FailureAnalysis {
  failure_category: string;
  confidence: number;
  root_cause_summary: string;
  evidence: string[];
  recommended_action: string;
  restart_mode: string;
  restart_strategy?: RestartStrategy | string;
  reason: string;
}

export interface RemediationEvent {
  timestamp: string;
  event_type: string;
  message: string;
  payload?: any;
}

export interface JobRunDetail {
  id: number;
  job_name: string;
  run_count: number;
  platform?: 'MOCK_SAP' | 'SAP_BTP';
  status: 'FAILED' | 'SUCCESS' | 'RUNNING' | 'SCHEDULED' | 'CANCELLED';
  start_time: string;
  end_time?: string;
  return_code: number;
  failed_step_number?: number;
  job_user: string;
  job_text?: string;
  retry_count: number;
  parent_run_id?: number;
  remediation_execution_id?: string;
  environment: string;
  restart_allowed: boolean;
  max_retries: number;
  steps: JobStep[];
  logs: JobLog[];
  parameters: JobParameter[];
  analysis?: FailureAnalysis;
  remediations?: {
    execution_id: string;
    action: string;
    restart_strategy?: string;
    restart_mode?: string;
    policy_decision: string;
    policy_reason: string;
    status: string;
    new_run_count?: number;
    created_at: string;
  }[];
}

export interface JobRunSummary {
  id: number;
  job_name: string;
  run_count: number;
  platform?: 'MOCK_SAP' | 'SAP_BTP';
  status: 'FAILED' | 'SUCCESS' | 'RUNNING' | 'SCHEDULED';
  start_time: string;
  failed_step_number?: number;
  return_code: number;
  job_text?: string;
  job_user?: string;
  failure_category?: string;
  retry_count: number;
  parent_run_id?: number;
  remediation_execution_id?: string;
  remediation_status?: string;
  is_resolved?: boolean;
}

export interface DashboardStats {
  total_jobs: number;
  failed_jobs: number;
  successful_jobs: number;
  running_jobs: number;
  failure_rate: number;
  success_rate: number;
  agent_status: string;
  platform?: 'MOCK_SAP' | 'SAP_BTP';
}

export interface ActivityItem {
  id: number;
  event_id: string;
  event_type: string;
  job_name: string;
  run_count: number;
  received_at: string;
  processed: boolean;
}

export interface RemediationItem {
  id: number;
  execution_id: string;
  job_name: string;
  run_count: number;
  new_run_count?: number;
  failure_category: string;
  action: string;
  restart_strategy?: RestartStrategy | string;
  restart_mode: string;
  policy_decision: 'APPROVED' | 'REJECTED';
  policy_reason: string;
  status: 'AUTO_RESOLVED' | 'ESCALATED' | 'IN_PROGRESS' | 'RESOLUTION_FAILED' | 'MANUALLY_RESOLVED';
  created_at: string;
}

export interface EscalationItem {
  id: number;
  execution_id: string;
  job_name: string;
  run_count: number;
  failure_category: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  reason: string;
  root_cause_summary: string;
  suggested_action: string;
  created_at: string;
}

export interface TimelineEvent {
  timestamp: string;
  title: string;
  detail: string;
  status: 'COMPLETED' | 'BLOCKED' | 'ESCALATED' | 'IN_PROGRESS';
}

export interface JobHistoryEntry {
  run_id: number;
  job_name: string;
  run_count: number;
  status: string;
  return_code: number;
  failed_step_number?: number;
  retry_count: number;
  parent_run_id?: number;
  start_time: string;
  failure_category?: string;
  root_cause_summary?: string;
  ai_confidence?: number;
  restart_strategy?: string;
  policy_decision?: string;
  policy_reason?: string;
  remediation_id?: string;
  remediation_status?: string;
  remediation_events: RemediationEvent[];
  sap_logs: JobLog[];
  steps: JobStep[];
}
