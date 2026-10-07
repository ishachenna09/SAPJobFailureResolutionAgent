import {
  DashboardStats,
  JobRunSummary,
  JobRunDetail,
  ActivityItem,
  RemediationItem,
  EscalationItem,
  TimelineEvent,
  JobHistoryEntry,
  RemediationEvent,
} from '../types/job';

const API_BASE = '';

export async function switchEnvironment(platform: string): Promise<{ status: string; platform: string; runs_fetched?: number; message?: string }> {
  const res = await fetch(`${API_BASE}/api/environment/switch?platform=${encodeURIComponent(platform)}`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to switch environment');
  return res.json();
}

export async function fetchDashboardStats(platform: string = 'MOCK_SAP'): Promise<DashboardStats> {
  const res = await fetch(`${API_BASE}/api/stats?platform=${encodeURIComponent(platform)}`);
  if (!res.ok) throw new Error('Failed to fetch stats');
  return res.json();
}

export async function fetchJobs(
  status?: string,
  jobName?: string,
  activeFailedOnly: boolean = false,
  platform: string = 'MOCK_SAP'
): Promise<JobRunSummary[]> {
  const params = new URLSearchParams();
  if (status) params.append('status', status);
  if (jobName) params.append('job_name', jobName);
  if (activeFailedOnly) params.append('active_failed_only', 'true');
  params.append('platform', platform);

  const res = await fetch(`${API_BASE}/api/jobs?${params.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch jobs');
  return res.json();
}

export async function fetchJobDetail(jobName: string, runCount: number): Promise<JobRunDetail> {
  const res = await fetch(`${API_BASE}/api/jobs/${encodeURIComponent(jobName)}/${runCount}`);
  if (!res.ok) throw new Error('Failed to fetch job detail');
  return res.json();
}

export async function fetchJobHistory(
  jobName: string,
  runCount: number
): Promise<{ job_name: string; current_run_count: number; history: JobHistoryEntry[] }> {
  const res = await fetch(`${API_BASE}/api/jobs/${encodeURIComponent(jobName)}/${runCount}/history`);
  if (!res.ok) throw new Error('Failed to fetch job history');
  return res.json();
}

export async function triggerJobRemediation(
  jobName: string,
  runCount: number
): Promise<{ execution_id: string; status: string; message: string; job_name: string; run_count: number }> {
  const res = await fetch(`${API_BASE}/api/jobs/${encodeURIComponent(jobName)}/${runCount}/remediation`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to trigger job remediation');
  }
  return res.json();
}

export async function fetchRemediationDetail(executionId: string): Promise<{
  id: number;
  execution_id: string;
  job_name: string;
  original_run_count: number;
  new_run_count?: number;
  failure_category: string;
  ai_confidence: number;
  ai_recommendation: string;
  action: string;
  restart_strategy: string;
  restart_mode: string;
  policy_decision: string;
  policy_reason: string;
  status: string;
  events_log: RemediationEvent[];
  created_at: string;
}> {
  const res = await fetch(`${API_BASE}/api/remediations/${encodeURIComponent(executionId)}`);
  if (!res.ok) throw new Error('Failed to fetch remediation detail');
  return res.json();
}

export async function fetchActivityFeed(platform: string = 'MOCK_SAP'): Promise<ActivityItem[]> {
  const res = await fetch(`${API_BASE}/api/activity?platform=${encodeURIComponent(platform)}`);
  if (!res.ok) throw new Error('Failed to fetch activity feed');
  return res.json();
}

export async function fetchRemediations(status?: string, platform: string = 'MOCK_SAP'): Promise<RemediationItem[]> {
  const params = new URLSearchParams();
  if (status) params.append('status', status);
  params.append('platform', platform);
  const res = await fetch(`${API_BASE}/api/remediations?${params.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch remediations');
  return res.json();
}

export async function fetchRemediationTimeline(executionId: string): Promise<{
  execution_id: string;
  job_name: string;
  run_count: number;
  status: string;
  timeline: TimelineEvent[];
}> {
  const res = await fetch(`${API_BASE}/api/remediations/${encodeURIComponent(executionId)}/timeline`);
  if (!res.ok) throw new Error('Failed to fetch remediation timeline');
  return res.json();
}

export async function fetchEscalations(platform: string = 'MOCK_SAP'): Promise<EscalationItem[]> {
  const res = await fetch(`${API_BASE}/api/escalations?platform=${encodeURIComponent(platform)}`);
  if (!res.ok) throw new Error('Failed to fetch escalations');
  return res.json();
}

export async function resolveEscalation(id: number) {
  const res = await fetch(`${API_BASE}/api/escalations/${id}/resolve`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to resolve escalation');
  return res.json();
}

export async function generateMockFailure(scenario: string, jobName?: string, runCount?: number) {
  const res = await fetch(`${API_BASE}/api/mock-sap/generate-failure`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario, job_name: jobName, run_count: runCount }),
  });
  if (!res.ok) throw new Error('Failed to generate mock failure');
  return res.json();
}

export function subscribeRemediationStream(
  executionId: string,
  onEvent: (event: RemediationEvent) => void,
  onFinished: (finalStatus: string) => void,
  onError: (err: any) => void
): () => void {
  const eventSource = new EventSource(`${API_BASE}/api/remediations/${encodeURIComponent(executionId)}/stream`);

  eventSource.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      if (data.event_type === 'STREAM_FINISHED') {
        onFinished(data.status);
        eventSource.close();
      } else {
        onEvent(data);
        if (['AUTO_RESOLVED', 'ESCALATED', 'RESOLUTION_FAILED'].includes(data.event_type)) {
          onFinished(data.event_type);
          eventSource.close();
        }
      }
    } catch (err) {
      console.error('Error parsing SSE data:', err);
    }
  };

  eventSource.onerror = (err) => {
    onError(err);
    eventSource.close();
  };

  return () => {
    eventSource.close();
  };
}
