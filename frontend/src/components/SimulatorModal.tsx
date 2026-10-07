import React, { useState, useEffect } from 'react';
import {
  X,
  Zap,
  Play,
  AlertOctagon,
  RefreshCw,
  Cpu,
  WifiOff,
  CheckCircle2,
  Sliders,
  ShieldAlert,
  Loader2,
  ArrowRight,
} from 'lucide-react';
import { JobRunSummary } from '../types/job';
import { fetchJobs, generateMockFailure, triggerJobRemediation } from '../services/api';
import { ExecutionViewModal } from './ExecutionViewModal';

interface SimulatorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRefresh: () => void;
  platform?: 'MOCK_SAP' | 'SAP_BTP';
}

export const SimulatorModal: React.FC<SimulatorModalProps> = ({
  isOpen,
  onClose,
  onRefresh,
  platform = 'MOCK_SAP',
}) => {
  const [failedJobs, setFailedJobs] = useState<JobRunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [backendConnected, setBackendConnected] = useState(true);
  const [triggeringDemo, setTriggeringDemo] = useState(false);
  const [runningJobKey, setRunningJobKey] = useState<string | null>(null);

  // Active execution modal state
  const [activeExecution, setActiveExecution] = useState<{
    jobName: string;
    runCount: number;
    executionId: string;
  } | null>(null);

  const loadFailedJobs = async () => {
    setLoading(true);
    try {
      // activeFailedOnly=true fetches only failed jobs that have not been superseded by a successful rerun
      const data = await fetchJobs('FAILED', undefined, true, platform);
      setFailedJobs(data);
      setBackendConnected(true);
    } catch (err) {
      console.error('Failed to load simulator jobs:', err);
      setBackendConnected(false);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadFailedJobs();
    }
  }, [isOpen, platform]);

  if (!isOpen) return null;

  const handleCreateDemoFailure = async (scenario: string, jobName?: string) => {
    setTriggeringDemo(true);
    try {
      await generateMockFailure(scenario, jobName);
      await loadFailedJobs();
      onRefresh();
    } catch (err: any) {
      alert(`Failed to trigger demo event: ${err.message}`);
    } finally {
      setTriggeringDemo(false);
    }
  };

  const handleRunAgent = async (job: JobRunSummary) => {
    const jobKey = `${job.job_name}:${job.run_count}`;
    setRunningJobKey(jobKey);

    try {
      const res = await triggerJobRemediation(job.job_name, job.run_count);
      // Open the dedicated running-job execution view
      setActiveExecution({
        jobName: job.job_name,
        runCount: job.run_count,
        executionId: res.execution_id,
      });
      // Refresh failed jobs list in background
      await loadFailedJobs();
      onRefresh();
    } catch (err: any) {
      alert(`Error starting remediation: ${err.message}`);
    } finally {
      setRunningJobKey(null);
    }
  };

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
        <div className="bg-[#0f172a] border border-slate-700/80 rounded-2xl w-full max-w-2xl shadow-2xl flex flex-col max-h-[85vh] overflow-hidden">
          {/* Fixed Header */}
          <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/90 shrink-0">
            <div className="flex items-center space-x-2.5">
              <div className="w-8 h-8 rounded-lg bg-sky-500/20 text-sky-400 border border-sky-500/30 flex items-center justify-center">
                <Zap className="w-4 h-4 fill-current" />
              </div>
              <div>
                <h2 className="text-base font-bold text-white tracking-tight">SAP Event Simulator</h2>
                <p className="text-xs text-slate-400">Autonomous Failure Ingestion & Remediation Trigger</p>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <div className="flex items-center space-x-1.5 text-xs">
                <span
                  className={`w-2 h-2 rounded-full ${backendConnected ? 'bg-emerald-400' : 'bg-red-400 animate-ping'}`}
                />
                <span className={backendConnected ? 'text-slate-300' : 'text-red-400 font-semibold'}>
                  {backendConnected ? 'Backend Connected' : 'Disconnected'}
                </span>
              </div>

              <button
                onClick={onClose}
                className="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-800 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Scrollable Body */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Section 1: Active Failed Jobs List */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center space-x-2">
                  <span>Currently Failed Jobs in SAP</span>
                  <span className="bg-red-500/20 text-red-400 font-mono text-[10px] px-2 py-0.5 rounded-full border border-red-500/30">
                    {failedJobs.length} Failed
                  </span>
                </h3>

                <button
                  onClick={loadFailedJobs}
                  disabled={loading}
                  className="text-xs text-sky-400 hover:text-sky-300 flex items-center space-x-1 transition disabled:opacity-50"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                  <span>Refresh Jobs</span>
                </button>
              </div>

              {/* State A: Backend Down */}
              {!backendConnected ? (
                <div className="p-8 rounded-xl border border-red-900/60 bg-red-950/20 text-center space-y-3">
                  <WifiOff className="w-8 h-8 text-red-400 mx-auto" />
                  <div>
                    <h4 className="text-sm font-bold text-white">Backend is not connected</h4>
                    <p className="text-xs text-slate-400 mt-1">
                      Start the FastAPI backend server to retrieve SAP jobs and evaluate remediation policies.
                    </p>
                  </div>
                  <button
                    onClick={loadFailedJobs}
                    className="bg-red-600/30 hover:bg-red-600/50 text-red-300 border border-red-500/40 text-xs font-semibold px-4 py-2 rounded-lg transition"
                  >
                    Retry Connection
                  </button>
                </div>
              ) : loading ? (
                /* State B: Loading */
                <div className="p-12 text-center text-slate-400 space-y-2">
                  <Loader2 className="w-6 h-6 text-sky-400 animate-spin mx-auto" />
                  <p className="text-xs">Loading failed SAP jobs from backend...</p>
                </div>
              ) : failedJobs.length === 0 ? (
                /* State C: Connected but 0 failed jobs */
                <div className="p-8 rounded-xl border border-slate-800 bg-slate-900/40 text-center space-y-2">
                  <CheckCircle2 className="w-7 h-7 text-emerald-400 mx-auto" />
                  <h4 className="text-sm font-semibold text-slate-300">No failed jobs currently available</h4>
                  <p className="text-xs text-slate-500 max-w-sm mx-auto">
                    All SAP application jobs are operating normally or have been automatically resolved. Use the Developer Controls below to simulate a failure event.
                  </p>
                </div>
              ) : (
                /* State D: Failed jobs rendered */
                <div className="space-y-3">
                  {failedJobs.map((job) => {
                    const jobKey = `${job.job_name}:${job.run_count}`;
                    const isJobRunning = runningJobKey === jobKey;

                    return (
                      <div
                        key={jobKey}
                        className="p-4 rounded-xl border border-red-900/50 bg-red-950/20 hover:border-red-800/80 transition flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                      >
                        <div className="space-y-1">
                          <div className="flex items-center space-x-2">
                            <span className="font-bold text-white text-sm">{job.job_name}</span>
                            <span className="font-mono text-xs text-slate-400 bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
                              Run #{job.run_count}
                            </span>
                            <span className="bg-red-500/20 text-red-400 font-mono text-[11px] px-2 py-0.5 rounded-full border border-red-500/30 font-bold">
                              FAILED
                            </span>
                          </div>

                          <div className="text-xs text-slate-300 flex items-center space-x-3">
                            <span>
                              Failed Step:{' '}
                              <strong className="text-slate-200">
                                {job.failed_step_number ? `Step ${job.failed_step_number}` : 'Step 1'}
                              </strong>
                            </span>
                            <span>•</span>
                            <span>
                              Error:{' '}
                              <code className="text-red-300 font-mono">
                                {job.failure_category || 'DATABASE_LOCK_TIMEOUT'}
                              </code>
                            </span>
                          </div>

                          {job.job_text && <p className="text-[11px] text-slate-400">{job.job_text}</p>}
                        </div>

                        <div className="shrink-0 flex items-center space-x-2">
                          <button
                            disabled={isJobRunning}
                            onClick={() => handleRunAgent(job)}
                            className="w-full sm:w-auto bg-gradient-to-r from-sky-600 to-blue-600 hover:from-sky-500 hover:to-blue-500 text-white font-bold text-xs px-4 py-2.5 rounded-xl shadow-lg transition flex items-center justify-center space-x-2 disabled:opacity-60 active:scale-95"
                          >
                            {isJobRunning ? (
                              <>
                                <Loader2 className="w-4 h-4 animate-spin text-white" />
                                <span>Agent Running...</span>
                              </>
                            ) : (
                              <>
                                <Play className="w-3.5 h-3.5 fill-current" />
                                <span>Run Agent</span>
                              </>
                            )}
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Section 2: Developer / Demo Controls */}
            <div className="border-t border-slate-800 pt-5 space-y-3">
              <div className="flex items-center space-x-2 text-slate-400">
                <Sliders className="w-4 h-4 text-sky-400" />
                <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
                  Developer / Demo Controls
                </span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Click a button below to generate a real Mock SAP failure event in the backend. The job will appear in the Failed Jobs list above without auto-resolving.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                <button
                  disabled={triggeringDemo}
                  onClick={() => handleCreateDemoFailure('TRANSIENT_DB_LOCK', 'Z_CUSTOMER_LOAD')}
                  className="text-left p-3 rounded-xl border border-slate-800 bg-slate-900/60 hover:bg-slate-800/80 hover:border-slate-700 transition group flex items-center justify-between disabled:opacity-50"
                >
                  <div>
                    <div className="text-xs font-bold text-sky-300 flex items-center space-x-1.5">
                      <span>Create DB Lock Failure</span>
                    </div>
                    <span className="text-[11px] text-slate-400 block font-mono">
                      Z_CUSTOMER_LOAD (Retry from failed step)
                    </span>
                  </div>
                  <Play className="w-3.5 h-3.5 text-sky-400 group-hover:translate-x-1 transition" />
                </button>

                <button
                  disabled={triggeringDemo}
                  onClick={() => handleCreateDemoFailure('AUTHORIZATION_FAILURE', 'Z_FIN_POSTING')}
                  className="text-left p-3 rounded-xl border border-slate-800 bg-slate-900/60 hover:bg-slate-800/80 hover:border-slate-700 transition group flex items-center justify-between disabled:opacity-50"
                >
                  <div>
                    <div className="text-xs font-bold text-amber-300 flex items-center space-x-1.5">
                      <span>Create Authorization Failure</span>
                    </div>
                    <span className="text-[11px] text-slate-400 block font-mono">
                      Z_FIN_POSTING (Blocked & Escalate)
                    </span>
                  </div>
                  <ShieldAlert className="w-3.5 h-3.5 text-amber-400 group-hover:translate-x-1 transition" />
                </button>

                <button
                  disabled={triggeringDemo}
                  onClick={() => handleCreateDemoFailure('RESTART_FROM_START', 'Z_SETTLEMENT_RUN')}
                  className="text-left p-3 rounded-xl border border-slate-800 bg-slate-900/60 hover:bg-slate-800/80 hover:border-slate-700 transition group flex items-center justify-between disabled:opacity-50"
                >
                  <div>
                    <div className="text-xs font-bold text-purple-300 flex items-center space-x-1.5">
                      <span>Create Restart-from-Start Failure</span>
                    </div>
                    <span className="text-[11px] text-slate-400 block font-mono">
                      Z_SETTLEMENT_RUN (Rerun all steps)
                    </span>
                  </div>
                  <Play className="w-3.5 h-3.5 text-purple-400 group-hover:translate-x-1 transition" />
                </button>

                <button
                  disabled={triggeringDemo}
                  onClick={() => handleCreateDemoFailure('RFC_TIMEOUT', 'Z_VENDOR_SYNC')}
                  className="text-left p-3 rounded-xl border border-slate-800 bg-slate-900/60 hover:bg-slate-800/80 hover:border-slate-700 transition group flex items-center justify-between disabled:opacity-50"
                >
                  <div>
                    <div className="text-xs font-bold text-emerald-300 flex items-center space-x-1.5">
                      <span>Create RFC Timeout Failure</span>
                    </div>
                    <span className="text-[11px] text-slate-400 block font-mono">
                      Z_VENDOR_SYNC (Transient network retry)
                    </span>
                  </div>
                  <Play className="w-3.5 h-3.5 text-emerald-400 group-hover:translate-x-1 transition" />
                </button>
              </div>
            </div>
          </div>

          {/* Fixed Footer */}
          <div className="px-6 py-3.5 border-t border-slate-800 flex items-center justify-between bg-slate-900/90 shrink-0">
            <div className="text-[11px] text-slate-400 flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-sky-400"></span>
              <span>Communication scenario SAP_COM_0326 active</span>
            </div>
            <button
              onClick={onClose}
              className="bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs px-4 py-2 rounded-lg transition"
            >
              Close
            </button>
          </div>
        </div>
      </div>

      {/* Execution View Modal */}
      {activeExecution && (
        <ExecutionViewModal
          isOpen={!!activeExecution}
          jobName={activeExecution.jobName}
          runCount={activeExecution.runCount}
          executionId={activeExecution.executionId}
          onClose={() => {
            setActiveExecution(null);
            loadFailedJobs();
          }}
          onRefresh={onRefresh}
        />
      )}
    </>
  );
};
