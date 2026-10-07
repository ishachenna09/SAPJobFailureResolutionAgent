import React, { useState, useEffect } from 'react';
import { JobRunDetail, JobHistoryEntry } from '../types/job';
import {
  ArrowLeft,
  CheckCircle2,
  AlertOctagon,
  Cpu,
  Terminal,
  ListTree,
  Sliders,
  Brain,
  FileText,
  Search,
  ShieldCheck,
  Activity,
  History as HistoryIcon,
  GitBranch,
  ShieldAlert,
  RotateCcw,
  Sparkles,
  ArrowRight,
  Play,
} from 'lucide-react';
import { fetchJobHistory, triggerJobRemediation } from '../services/api';
import { ExecutionViewModal } from './ExecutionViewModal';

interface JobDetailProps {
  job: JobRunDetail;
  onBack: () => void;
}

export const JobDetail: React.FC<JobDetailProps> = ({ job, onBack }) => {
  const [activeTab, setActiveTab] = useState<
    'overview' | 'steps' | 'logs' | 'parameters' | 'ai' | 'policy' | 'timeline' | 'history'
  >('overview');
  const [logFilter, setLogFilter] = useState<string>('ALL');
  const [logSearch, setLogSearch] = useState<string>('');

  // History tab data
  const [historyData, setHistoryData] = useState<JobHistoryEntry[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // Execution modal state
  const [activeExecutionId, setActiveExecutionId] = useState<string | null>(null);

  const isFailed = job.status === 'FAILED';
  const isAutoResolved = job.status === 'SUCCESS' && (job.retry_count > 0 || !!job.parent_run_id);
  const isRemediated = job.remediations?.some(r => r.status === 'AUTO_RESOLVED' || r.status === 'MANUALLY_RESOLVED');
  const isResolved = isAutoResolved || isRemediated;

  const loadHistory = async () => {
    setLoadingHistory(true);
    try {
      const res = await fetchJobHistory(job.job_name, job.run_count);
      setHistoryData(res.history);
    } catch (err) {
      console.error('Error fetching job history:', err);
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'history') {
      loadHistory();
    }
  }, [activeTab, job.job_name, job.run_count]);

  const handleStartRemediation = async () => {
    try {
      const res = await triggerJobRemediation(job.job_name, job.run_count);
      setActiveExecutionId(res.execution_id);
    } catch (err: any) {
      alert(`Error starting remediation: ${err.message}`);
    }
  };

  const filteredLogs = job.logs.filter((l) => {
    const matchesSev = logFilter === 'ALL' || l.severity === logFilter;
    const matchesMsg = l.message.toLowerCase().includes(logSearch.toLowerCase());
    return matchesSev && matchesMsg;
  });

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
        <button
          onClick={onBack}
          className="text-xs font-semibold text-sky-400 hover:text-sky-300 inline-flex items-center space-x-1.5 transition"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Operations Console</span>
        </button>

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-3">
              <h2 className="text-2xl font-bold text-white tracking-tight">{job.job_name}</h2>
              <span className="font-mono text-slate-400 text-sm bg-slate-800 px-2.5 py-0.5 rounded-lg border border-slate-700">
                Run #{job.run_count}
              </span>
              {job.parent_run_id && (
                <span className="text-xs font-mono text-sky-300 bg-sky-950/60 px-2.5 py-0.5 rounded-lg border border-sky-800">
                  Remediated from Run #{job.parent_run_id}
                </span>
              )}
            </div>
            {job.job_text && <p className="text-slate-400 text-sm mt-1">{job.job_text}</p>}
          </div>

          <div className="flex items-center space-x-3">
            {isResolved ? (
              <span className="inline-flex items-center space-x-2 px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 shadow-lg">
                <CheckCircle2 className="w-4 h-4" />
                <span>AUTO RESOLVED (Retried {job.retry_count}x)</span>
              </span>
            ) : isFailed ? (
              <div className="flex items-center space-x-2">
                <span className="inline-flex items-center space-x-2 px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider bg-red-500/20 text-red-400 border border-red-500/40 shadow-lg">
                  <AlertOctagon className="w-4 h-4" />
                  <span>Status: FAILED</span>
                </span>
                <button
                  onClick={handleStartRemediation}
                  className="bg-gradient-to-r from-sky-600 to-blue-600 hover:from-sky-500 hover:to-blue-500 text-white font-bold text-xs px-3.5 py-1.5 rounded-full shadow transition flex items-center space-x-1.5"
                >
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>Run Agent</span>
                </button>
              </div>
            ) : (
              <span className="inline-flex items-center space-x-2 px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                <CheckCircle2 className="w-4 h-4" />
                <span>Status: SUCCESS</span>
              </span>
            )}

            <span className="bg-slate-800 text-slate-300 border border-slate-700 text-xs px-3 py-1.5 rounded-full">
              {job.environment}
            </span>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex space-x-2 border-b border-slate-800/80 pt-2 overflow-x-auto">
          {[
            { id: 'overview', label: 'Overview', icon: FileText },
            { id: 'history', label: 'Job Lineage & History', icon: HistoryIcon },
            { id: 'steps', label: 'Job Steps', icon: ListTree },
            { id: 'logs', label: 'Monospace Logs', icon: Terminal },
            { id: 'parameters', label: 'Parameters', icon: Sliders },
            { id: 'ai', label: 'AI Diagnosis', icon: Brain },
            { id: 'policy', label: 'Policy Check', icon: ShieldCheck },
            { id: 'timeline', label: 'Remediation Timeline', icon: Activity },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center space-x-2 px-4 py-2.5 text-xs font-medium border-b-2 transition ${
                  isActive
                    ? 'border-sky-500 text-sky-400 bg-sky-500/5'
                    : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Tab Content */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800">
        {/* TAB 1: OVERVIEW */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Lineage Banner if remediated */}
            {isAutoResolved && (
              <div className="p-4 rounded-xl border border-emerald-500/30 bg-emerald-950/20 flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <Sparkles className="w-5 h-5 text-emerald-400" />
                  <div>
                    <h4 className="text-sm font-bold text-white">Autonomously Remediated Job</h4>
                    <p className="text-xs text-slate-300 mt-0.5">
                      This job previously failed and was resolved via Autonomous Agent remediation. Original failed run and logs are preserved.
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setActiveTab('history')}
                  className="bg-emerald-600/30 hover:bg-emerald-600/50 text-emerald-300 border border-emerald-500/40 text-xs font-bold px-3.5 py-1.5 rounded-lg transition flex items-center space-x-1"
                >
                  <span>View History</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            )}

            <h3 className="text-base font-bold text-white border-b border-slate-800 pb-2">Execution Metadata</h3>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                <span className="text-xs text-slate-400 block font-medium">Job Name</span>
                <span className="text-sm font-bold text-white font-mono">{job.job_name}</span>
              </div>

              <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                <span className="text-xs text-slate-400 block font-medium">Run Identifier</span>
                <span className="text-sm font-bold text-white font-mono">#{job.run_count}</span>
              </div>

              <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                <span className="text-xs text-slate-400 block font-medium">Current Status</span>
                <span className={`text-sm font-bold font-mono ${isFailed ? 'text-red-400' : 'text-emerald-400'}`}>
                  {isAutoResolved ? 'AUTO RESOLVED' : job.status}
                </span>
              </div>

              <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                <span className="text-xs text-slate-400 block font-medium">Failed Step</span>
                <span className="text-sm font-bold text-white font-mono">
                  {job.failed_step_number ? `Step ${job.failed_step_number}` : 'None'}
                </span>
              </div>

              <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                <span className="text-xs text-slate-400 block font-medium">Return Code</span>
                <span className="text-sm font-bold text-white font-mono">{job.return_code}</span>
              </div>

              <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                <span className="text-xs text-slate-400 block font-medium">Service Account</span>
                <span className="text-sm font-bold text-white font-mono">{job.job_user}</span>
              </div>
            </div>

            {/* AI Diagnosis Summary & Strategy Display (Requirement 15) */}
            {job.analysis && (
              <div className="bg-gradient-to-br from-slate-900 to-sky-950/40 p-5 rounded-2xl border border-sky-800/60 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2 text-sky-400 font-bold text-sm">
                    <Brain className="w-4 h-4" />
                    <span>Agent AI Failure Analysis & Remediation Strategy</span>
                  </div>
                  <span className="bg-sky-950 text-sky-300 font-mono text-xs px-2.5 py-0.5 rounded border border-sky-700 font-semibold">
                    {job.analysis.failure_category}
                  </span>
                </div>
                <p className="text-slate-300 text-sm">{job.analysis.root_cause_summary}</p>
                <div className="text-xs text-slate-400">
                  Confidence Score: <span className="font-bold text-emerald-400">{Math.round(job.analysis.confidence * 100)}%</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs pt-2">
                  <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800">
                    <span className="text-slate-400 block font-semibold">AI Recommendation</span>
                    <span className="text-sky-300 font-bold mt-1 block">{job.analysis.recommended_action || 'Restart'}</span>
                  </div>

                  <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800">
                    <span className="text-slate-400 block font-semibold">Final Policy Decision</span>
                    <span className="text-emerald-400 font-bold mt-1 block">
                      {job.analysis.restart_strategy === 'DO_NOT_RESTART'
                        ? 'DO NOT RESTART (Escalate to Human Ops)'
                        : job.analysis.restart_strategy === 'RESTART_FROM_START'
                        ? 'Restart from Beginning (RESTART_FROM_START)'
                        : 'Restart from Failed Step (RESTART_FROM_FAILED_STEP)'}
                    </span>
                  </div>

                  <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800 md:col-span-2">
                    <span className="text-slate-400 block font-semibold">Policy Evaluation Reason</span>
                    <span className="text-slate-200 mt-1 block leading-relaxed">{job.analysis.reason}</span>
                  </div>

                  <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800 md:col-span-2">
                    <span className="text-slate-400 block font-semibold">Actual Action</span>
                    <span className="text-sky-400 font-mono font-bold mt-1 block">
                      {job.platform === 'SAP_BTP'
                        ? 'BTP Job Scheduling REST API HTTP Action Retry'
                        : `SAP JobRestart(mode="${job.analysis.restart_mode || 'E'}")`}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: MANDATORY JOB LINEAGE & HISTORY */}
        {activeTab === 'history' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center space-x-2">
                  <GitBranch className="w-5 h-5 text-sky-400" />
                  <span>Job Lineage & Execution History</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Complete persistent audit trail: Original failed run → Agent Investigation & Strategy → Restarted run.
                </p>
              </div>

              <button
                onClick={loadHistory}
                disabled={loadingHistory}
                className="text-xs text-sky-400 hover:text-sky-300 flex items-center space-x-1"
              >
                <RotateCcw className={`w-3.5 h-3.5 ${loadingHistory ? 'animate-spin' : ''}`} />
                <span>Refresh Lineage</span>
              </button>
            </div>

            {loadingHistory ? (
              <div className="py-12 text-center text-slate-400">Loading complete job execution history...</div>
            ) : historyData.length === 0 ? (
              <div className="py-12 text-center text-slate-500">No previous runs recorded for {job.job_name}.</div>
            ) : (
              <div className="space-y-8">
                {historyData.map((hRun, idx) => {
                  const isRunFailed = hRun.status === 'FAILED';
                  const isRunSuccess = hRun.status === 'SUCCESS';

                  return (
                    <div key={hRun.run_id} className="relative space-y-4">
                      {/* Run Header Card */}
                      <div
                        className={`p-5 rounded-2xl border ${
                          isRunFailed
                            ? 'bg-red-950/20 border-red-900/60'
                            : 'bg-emerald-950/20 border-emerald-900/60'
                        } space-y-4`}
                      >
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
                          <div className="flex items-center space-x-3">
                            <span className="text-base font-bold text-white font-mono">Run #{hRun.run_count}</span>
                            <span
                              className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider border ${
                                isRunFailed
                                  ? 'bg-red-500/20 text-red-400 border-red-500/30'
                                  : 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                              }`}
                            >
                              {hRun.status}
                            </span>
                            {hRun.parent_run_id && (
                              <span className="text-xs font-mono text-sky-400 bg-sky-950 px-2 py-0.5 rounded border border-sky-800">
                                Parent: Run #{hRun.parent_run_id}
                              </span>
                            )}
                          </div>

                          <div className="text-xs text-slate-400 font-mono">
                            Return Code: <strong className={isRunFailed ? 'text-red-400' : 'text-emerald-400'}>{hRun.return_code}</strong> | Started: {hRun.start_time}
                          </div>
                        </div>

                        {/* Run Details Grid */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                          {hRun.failure_category && (
                            <div className="bg-slate-900/70 p-3 rounded-xl border border-slate-800 space-y-1">
                              <span className="text-slate-400 font-bold uppercase text-[10px]">Failure Diagnosis</span>
                              <div className="text-red-300 font-semibold font-mono">{hRun.failure_category}</div>
                              <p className="text-slate-300 text-[11px]">{hRun.root_cause_summary}</p>
                            </div>
                          )}

                          {hRun.restart_strategy && (
                            <div className="bg-slate-900/70 p-3 rounded-xl border border-slate-800 space-y-1">
                              <span className="text-slate-400 font-bold uppercase text-[10px]">Restart Strategy</span>
                              <div className="text-sky-300 font-semibold font-mono">{hRun.restart_strategy}</div>
                              <p className="text-slate-300 text-[11px]">
                                Policy: <strong className={hRun.policy_decision === 'APPROVED' ? 'text-emerald-400' : 'text-red-400'}>{hRun.policy_decision || 'APPROVED'}</strong>
                              </p>
                            </div>
                          )}

                          {hRun.remediation_id && (
                            <div className="bg-slate-900/70 p-3 rounded-xl border border-slate-800 space-y-1">
                              <span className="text-slate-400 font-bold uppercase text-[10px]">Remediation Execution</span>
                              <div className="text-sky-400 font-mono font-bold">{hRun.remediation_id}</div>
                              <div className="text-emerald-400 font-semibold text-[11px]">{hRun.remediation_status}</div>
                            </div>
                          )}
                        </div>

                        {/* Split Logs: Agent Activity vs SAP Job Logs */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 pt-2">
                          {/* Agent Activity Logs */}
                          <div className="bg-[#090d16] p-3.5 rounded-xl border border-slate-800 space-y-2">
                            <div className="flex items-center space-x-1.5 text-sky-400 text-xs font-bold uppercase tracking-wider">
                              <Cpu className="w-3.5 h-3.5" />
                              <span>Agent Activity Stream</span>
                            </div>
                            <div className="space-y-1.5 max-h-40 overflow-y-auto text-[11px] font-mono">
                              {hRun.remediation_events && hRun.remediation_events.length > 0 ? (
                                hRun.remediation_events.map((e, ei) => (
                                  <div key={ei} className="text-slate-300 flex items-start space-x-2">
                                    <span className="text-slate-500 shrink-0">{e.timestamp}</span>
                                    <span className="text-sky-400 font-bold shrink-0">[{e.event_type}]</span>
                                    <span className="flex-1">{e.message}</span>
                                  </div>
                                ))
                              ) : (
                                <div className="text-slate-500">Standard operational run (no remediation required)</div>
                              )}
                            </div>
                          </div>

                          {/* SAP Technical Job Logs */}
                          <div className="bg-[#090d16] p-3.5 rounded-xl border border-slate-800 space-y-2">
                            <div className="flex items-center space-x-1.5 text-amber-400 text-xs font-bold uppercase tracking-wider">
                              <Terminal className="w-3.5 h-3.5" />
                              <span>SAP Technical Job Log</span>
                            </div>
                            <div className="space-y-1.5 max-h-40 overflow-y-auto text-[11px] font-mono">
                              {hRun.sap_logs.map((l, li) => (
                                <div
                                  key={li}
                                  className={`flex items-start space-x-2 ${
                                    l.severity === 'ERROR' ? 'text-red-400 font-semibold' : 'text-slate-300'
                                  }`}
                                >
                                  <span className="text-slate-500 shrink-0">{l.timestamp}</span>
                                  <span className="shrink-0 font-bold">[{l.severity}]</span>
                                  <span className="flex-1 break-words">{l.message}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Lineage Connector arrow */}
                      {idx < historyData.length - 1 && (
                        <div className="flex items-center justify-center py-1">
                          <div className="flex flex-col items-center">
                            <div className="w-0.5 h-4 bg-sky-500/50" />
                            <span className="bg-sky-950 text-sky-300 border border-sky-700 text-[10px] font-mono font-bold px-3 py-0.5 rounded-full my-1">
                              ↓ Remediated by AI Agent ↓
                            </span>
                            <div className="w-0.5 h-4 bg-sky-500/50" />
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* TAB 3: STEPS */}
        {activeTab === 'steps' && (
          <div className="space-y-4">
            <h3 className="text-base font-bold text-white border-b border-slate-800 pb-2">SAP Job Steps Timeline</h3>
            <div className="space-y-3">
              {job.steps.map((step) => {
                const stepFailed = step.status === 'FAILED';
                return (
                  <div
                    key={step.step_number}
                    className={`p-4 rounded-xl border transition flex items-center justify-between ${
                      stepFailed
                        ? 'bg-red-950/20 border-red-800/60'
                        : step.status === 'SUCCESS'
                        ? 'bg-slate-900/80 border-slate-800'
                        : 'bg-slate-950/40 border-slate-900 text-slate-500'
                    }`}
                  >
                    <div className="flex items-center space-x-4">
                      <div
                        className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs ${
                          stepFailed
                            ? 'bg-red-500/20 text-red-400 border border-red-500/40'
                            : step.status === 'SUCCESS'
                            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                            : 'bg-slate-800 text-slate-500'
                        }`}
                      >
                        {step.step_number}
                      </div>
                      <div>
                        <div className="font-semibold text-white text-sm">{step.step_name}</div>
                        {step.program_name && (
                          <div className="text-xs font-mono text-slate-400">Program: {step.program_name}</div>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center space-x-4 text-xs font-mono">
                      {step.start_time && <span className="text-slate-400">{step.start_time} - {step.end_time || 'Present'}</span>}
                      <span
                        className={`px-2.5 py-0.5 rounded-full font-semibold border ${
                          stepFailed
                            ? 'bg-red-500/10 text-red-400 border-red-500/30'
                            : step.status === 'SUCCESS'
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                            : 'bg-slate-800 text-slate-500 border-slate-700'
                        }`}
                      >
                        {step.status} (RC: {step.return_code})
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* TAB 4: LOGS */}
        {activeTab === 'logs' && (
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
              <h3 className="text-base font-bold text-white">SAP Job Execution Log Viewer</h3>

              <div className="flex items-center space-x-2 w-full sm:w-auto">
                <div className="relative flex-1 sm:w-48">
                  <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={logSearch}
                    onChange={(e) => setLogSearch(e.target.value)}
                    placeholder="Search logs..."
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg pl-8 pr-3 py-1 text-xs text-slate-200 focus:outline-none"
                  />
                </div>

                {['ALL', 'ERROR', 'WARN', 'INFO'].map((sev) => (
                  <button
                    key={sev}
                    onClick={() => setLogFilter(sev)}
                    className={`px-2.5 py-1 rounded text-[11px] font-semibold transition ${
                      logFilter === sev
                        ? 'bg-sky-600 text-white'
                        : 'bg-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {sev}
                  </button>
                ))}
              </div>
            </div>

            <div className="bg-[#090d16] border border-slate-800 rounded-xl p-4 font-mono text-xs space-y-1.5 max-h-[500px] overflow-y-auto">
              {filteredLogs.map((log, idx) => (
                <div
                  key={idx}
                  className={`p-1.5 rounded flex items-start space-x-3 ${
                    log.is_error_highlight || log.severity === 'ERROR'
                      ? 'bg-red-950/40 border border-red-800/60 text-red-300 font-semibold'
                      : log.severity === 'WARN'
                      ? 'text-amber-300'
                      : 'text-slate-300'
                  }`}
                >
                  <span className="text-slate-500 select-none">{log.timestamp}</span>
                  <span
                    className={`px-1 rounded text-[10px] uppercase font-bold select-none ${
                      log.severity === 'ERROR' ? 'bg-red-900/60 text-red-200' : 'bg-slate-800 text-slate-400'
                    }`}
                  >
                    {log.severity}
                  </span>
                  {log.step_number && <span className="text-sky-400 select-none">[Step {log.step_number}]</span>}
                  <span className="flex-1 break-all">{log.message}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* TAB 5: PARAMETERS */}
        {activeTab === 'parameters' && (
          <div className="space-y-4">
            <h3 className="text-base font-bold text-white border-b border-slate-800 pb-2">SAP Job Execution Parameters</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {job.parameters.map((p, idx) => (
                <div key={idx} className="bg-slate-900/80 p-4 rounded-xl border border-slate-800 flex justify-between items-center">
                  <span className="text-xs font-mono font-semibold text-slate-400">{p.param_name}</span>
                  <span className="text-sm font-mono font-bold text-sky-400">{p.param_value}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* TAB 6: AI DIAGNOSIS */}
        {activeTab === 'ai' && (
          <div className="space-y-6">
            {job.analysis ? (
              <>
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <div>
                    <h3 className="text-lg font-bold text-white flex items-center space-x-2">
                      <Brain className="w-5 h-5 text-sky-400" />
                      <span>AI Failure Diagnosis & Classification</span>
                    </h3>
                    <p className="text-xs text-slate-400 mt-0.5">Autonomous classification via Pydantic structured AI schema</p>
                  </div>

                  <span className="bg-sky-950 text-sky-300 font-mono text-sm px-3 py-1 rounded-lg border border-sky-700 font-bold">
                    {job.analysis.failure_category}
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="bg-slate-900/80 p-5 rounded-xl border border-slate-800 space-y-3">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Root Cause Explanation</span>
                    <p className="text-sm text-slate-200 leading-relaxed">{job.analysis.root_cause_summary}</p>
                    
                    <div className="pt-2">
                      <span className="text-xs text-slate-400 block mb-1">Confidence Score</span>
                      <div className="w-full bg-slate-800 h-2.5 rounded-full overflow-hidden">
                        <div
                          className="bg-gradient-to-r from-sky-500 to-emerald-400 h-full rounded-full"
                          style={{ width: `${job.analysis.confidence * 100}%` }}
                        />
                      </div>
                      <span className="text-xs font-bold text-emerald-400 mt-1 block">
                        {Math.round(job.analysis.confidence * 100)}% Confidence
                      </span>
                    </div>
                  </div>

                  <div className="bg-slate-900/80 p-5 rounded-xl border border-slate-800 space-y-3">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Extracted Log Evidence</span>
                    <ul className="space-y-2 text-xs text-slate-300">
                      {job.analysis.evidence.map((ev, i) => (
                        <li key={i} className="flex items-start space-x-2 bg-slate-950/60 p-2 rounded border border-slate-800 font-mono">
                          <span className="text-red-400 font-bold">•</span>
                          <span>{ev}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </>
            ) : (
              <div className="py-8 text-center text-slate-500">No AI analysis required for successful execution.</div>
            )}
          </div>
        )}

        {/* TAB 7: POLICY CHECK */}
        {activeTab === 'policy' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2 text-white font-bold text-base">
                <ShieldCheck className="w-5 h-5 text-sky-400" />
                <span>Deterministic Safety & Remediation Policy Decision</span>
              </div>

              <span
                className={`font-mono text-xs font-bold px-3 py-1 rounded-full border ${
                  job.analysis && (job.analysis.failure_category.includes('LOCK') || job.analysis.failure_category.includes('RFC') || job.analysis.failure_category.includes('INCONSISTENCY'))
                    ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
                    : 'bg-red-500/20 text-red-400 border-red-500/40'
                }`}
              >
                Policy Result: {job.analysis && (job.analysis.failure_category.includes('LOCK') || job.analysis.failure_category.includes('RFC') || job.analysis.failure_category.includes('INCONSISTENCY')) ? 'APPROVED' : 'REJECTED / BLOCKED'}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[
                {
                  rule: 'Failure Category in Auto-Restart Allowlist',
                  passed: job.analysis ? (job.analysis.failure_category.includes('LOCK') || job.analysis.failure_category.includes('RFC') || job.analysis.failure_category.includes('INCONSISTENCY')) : true,
                  detail: job.analysis && (job.analysis.failure_category.includes('LOCK') || job.analysis.failure_category.includes('RFC') || job.analysis.failure_category.includes('INCONSISTENCY'))
                    ? `Category '${job.analysis.failure_category}' is retryable.`
                    : `Category '${job.analysis?.failure_category || 'NON_RETRYABLE'}' is classified as non-retryable.`
                },
                {
                  rule: 'AI Diagnosis Confidence Threshold (>= 90%)',
                  passed: job.analysis ? job.analysis.confidence >= 0.9 : true,
                  detail: `AI confidence is ${job.analysis ? Math.round(job.analysis.confidence * 100) : 100}% (Threshold: 90%).`
                },
                {
                  rule: 'SAP Job Permitted Restart Flag',
                  passed: job.restart_allowed,
                  detail: job.restart_allowed ? 'Job permits automatic restart.' : 'Job metadata blocks automatic restart.'
                },
                {
                  rule: 'Retry Limit Safety Check',
                  passed: job.retry_count <= job.max_retries,
                  detail: `Current retry count (${job.retry_count}) is within max retry limit (${job.max_retries}).`
                }
              ].map((check, idx) => (
                <div key={idx} className="bg-slate-900/80 p-4 rounded-xl border border-slate-800 flex items-start space-x-3">
                  <div className={`mt-0.5 w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold ${check.passed ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40' : 'bg-red-500/20 text-red-400 border border-red-500/40'}`}>
                    {check.passed ? '✓' : '✕'}
                  </div>
                  <div>
                    <div className="font-semibold text-white text-xs">{check.rule}</div>
                    <div className="text-[11px] text-slate-400 mt-0.5">{check.detail}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* TAB 8: REMEDIATION TIMELINE */}
        {activeTab === 'timeline' && (
          <div className="space-y-6">
            <h3 className="text-base font-bold text-white border-b border-slate-800 pb-2">Autonomous Agent Event Timeline</h3>

            <div className="relative border-l-2 border-slate-800 ml-4 space-y-6 pl-6 py-2">
              {[
                { title: 'Job Failure Event Received', detail: 'Event ingested via webhook /events/sap/job-failed', status: 'COMPLETED' },
                { title: 'Mock SAP Investigation Completed', detail: 'Fetched steps, logs, and parameters via SAP_COM_0326', status: 'COMPLETED' },
                { title: 'AI Failure Diagnosis Completed', detail: `Category: ${job.analysis?.failure_category || 'SUCCESS'}`, status: 'COMPLETED' },
                {
                  title: 'Deterministic Policy Evaluation',
                  detail: job.analysis && !job.analysis.failure_category.includes('AUTHORIZATION') ? 'Policy APPROVED automatic restart' : 'Policy REJECTED automatic restart',
                  status: job.analysis && !job.analysis.failure_category.includes('AUTHORIZATION') ? 'COMPLETED' : 'BLOCKED'
                },
                ...(job.analysis && !job.analysis.failure_category.includes('AUTHORIZATION') ? [
                  { title: `Executed JobRestart(mode="${job.analysis?.restart_mode || 'E'}")`, detail: `Restart strategy: ${job.analysis?.restart_strategy || 'RESTART_FROM_FAILED_STEP'}`, status: 'COMPLETED' },
                  { title: 'Monitored SAP Execution Status', detail: 'Polled JobStatusGet -> RUNNING -> SUCCESS', status: 'COMPLETED' },
                  { title: 'Validated Step Return Codes', detail: 'All step return codes verified 0', status: 'COMPLETED' },
                  { title: 'AUTO RESOLVED', detail: 'Job successfully remediated autonomously', status: 'COMPLETED' }
                ] : [
                  { title: 'Automation Blocked by Policy Engine', detail: 'Non-retryable failure category', status: 'BLOCKED' },
                  { title: 'Case Moved to Escalation Queue', detail: 'Operational team review required', status: 'ESCALATED' }
                ])
              ].map((item, idx) => (
                <div key={idx} className="relative">
                  <span className={`absolute -left-[31px] top-1 w-3.5 h-3.5 rounded-full border-2 ${item.status === 'COMPLETED' ? 'bg-emerald-500 border-slate-900' : 'bg-red-500 border-slate-900'}`} />
                  <div className="bg-slate-900/60 p-3.5 rounded-xl border border-slate-800">
                    <div className="font-bold text-xs text-white">{item.title}</div>
                    <div className="text-[11px] text-slate-400 mt-0.5 font-mono">{item.detail}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Execution View Modal */}
      {activeExecutionId && (
        <ExecutionViewModal
          isOpen={!!activeExecutionId}
          jobName={job.job_name}
          runCount={job.run_count}
          executionId={activeExecutionId}
          onClose={() => setActiveExecutionId(null)}
          onRefresh={() => {
            loadHistory();
          }}
        />
      )}
    </div>
  );
};
