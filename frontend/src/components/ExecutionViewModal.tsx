import React, { useState, useEffect, useRef } from 'react';
import {
  X,
  Cpu,
  Terminal,
  CheckCircle2,
  AlertOctagon,
  ShieldCheck,
  ShieldAlert,
  RotateCcw,
  Activity,
  ArrowRight,
  Sparkles,
} from 'lucide-react';
import { RemediationEvent, RestartStrategy } from '../types/job';
import { fetchRemediationDetail, subscribeRemediationStream } from '../services/api';

interface ExecutionViewModalProps {
  isOpen: boolean;
  jobName: string;
  runCount: number;
  executionId?: string;
  onClose: () => void;
  onRefresh: () => void;
}

export const ExecutionViewModal: React.FC<ExecutionViewModalProps> = ({
  isOpen,
  jobName,
  runCount,
  executionId,
  onClose,
  onRefresh,
}) => {
  const [status, setStatus] = useState<string>('IN_PROGRESS');
  const [events, setEvents] = useState<RemediationEvent[]>([]);
  const [remediationDetail, setRemediationDetail] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen || !executionId) return;

    let isMounted = true;
    setLoading(true);

    // Initial fetch of current state
    fetchRemediationDetail(executionId)
      .then((detail) => {
        if (!isMounted) return;
        setRemediationDetail(detail);
        setStatus(detail.status);
        if (detail.events_log && detail.events_log.length > 0) {
          setEvents(detail.events_log);
        }
        setLoading(false);
      })
      .catch((err) => {
        console.error('Error fetching remediation detail:', err);
        setLoading(false);
      });

    // Subscribe to real-time SSE stream
    const unsubscribe = subscribeRemediationStream(
      executionId,
      (newEvent) => {
        if (!isMounted) return;
        setEvents((prev) => {
          // Avoid duplicate events
          if (prev.some((e) => e.timestamp === newEvent.timestamp && e.event_type === newEvent.event_type)) {
            return prev;
          }
          return [...prev, newEvent];
        });

        if (['AUTO_RESOLVED', 'ESCALATED', 'RESOLUTION_FAILED'].includes(newEvent.event_type)) {
          setStatus(newEvent.event_type);
          onRefresh();
        }
      },
      (finalStatus) => {
        if (!isMounted) return;
        setStatus(finalStatus);
        onRefresh();
        // Fetch final details
        fetchRemediationDetail(executionId).then((d) => isMounted && setRemediationDetail(d));
      },
      (err) => {
        console.error('SSE Stream error, falling back to polling:', err);
      }
    );

    return () => {
      isMounted = false;
      unsubscribe();
    };
  }, [isOpen, executionId]);

  // Auto-scroll logs to bottom
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [events]);

  if (!isOpen) return null;

  // Determine stage progression from events
  const hasInvestigation = events.some((e) => e.event_type.includes('INVESTIGATION'));
  const hasAI = events.some((e) => e.event_type.includes('AI_ANALYSIS'));
  const hasPolicy = events.some((e) => e.event_type.includes('POLICY'));
  const hasStrategy = events.some((e) => e.event_type.includes('STRATEGY'));
  const hasRestart = events.some((e) => e.event_type.includes('RESTART'));
  const hasMonitoring = events.some((e) => e.event_type.includes('MONITORING') || e.event_type.includes('STEP_EXECUTED'));
  const hasValidation = events.some((e) => e.event_type.includes('VALIDATION'));
  const isResolved = status === 'AUTO_RESOLVED';
  const isEscalated = status === 'ESCALATED';
  const isFailed = status === 'RESOLUTION_FAILED';
  const isRunning = status === 'IN_PROGRESS';

  const stages = [
    { label: 'Investigation', completed: hasInvestigation, active: isRunning && !hasAI },
    { label: 'AI Diagnosis', completed: hasAI, active: isRunning && hasAI && !hasPolicy },
    { label: 'Policy Evaluation', completed: hasPolicy, active: isRunning && hasPolicy && !hasStrategy },
    { label: 'Restart Strategy', completed: hasStrategy, active: isRunning && hasStrategy && !hasRestart },
    { label: 'Job Restart', completed: hasRestart, active: isRunning && hasRestart && !hasMonitoring },
    { label: 'Monitoring', completed: hasMonitoring, active: isRunning && hasMonitoring && !hasValidation },
    { label: 'Validation', completed: hasValidation, active: isRunning && hasValidation && !isResolved && !isEscalated },
    { label: isEscalated ? 'Escalated' : 'Resolved', completed: isResolved || isEscalated, active: false },
  ];

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
      <div className="bg-[#0f172a] border border-slate-700/80 rounded-2xl w-full max-w-3xl shadow-2xl flex flex-col max-h-[85vh] overflow-hidden">
        {/* Fixed Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/90 shrink-0">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-sky-500/20 text-sky-400 border border-sky-500/30 flex items-center justify-center">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-base font-bold text-white tracking-tight">{jobName}</h3>
                <span className="text-xs font-mono bg-slate-800 text-slate-300 px-2 py-0.5 rounded border border-slate-700">
                  Run #{runCount} {remediationDetail?.new_run_count ? `→ #${remediationDetail.new_run_count}` : ''}
                </span>
                {executionId && (
                  <span className="text-[11px] font-mono text-sky-400 bg-sky-950/60 px-2 py-0.5 rounded border border-sky-800">
                    {executionId}
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400">Autonomous Agent Phase 2 Remediation & Policy Engine</p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <span
              className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider flex items-center space-x-1.5 border ${
                isResolved
                  ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
                  : isEscalated
                  ? 'bg-red-500/20 text-red-400 border-red-500/40'
                  : isFailed
                  ? 'bg-red-900/30 text-red-400 border-red-800'
                  : 'bg-amber-500/20 text-amber-400 border-amber-500/40'
              }`}
            >
              {isResolved ? (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>AUTO RESOLVED</span>
                </>
              ) : isEscalated ? (
                <>
                  <AlertOctagon className="w-3.5 h-3.5" />
                  <span>ESCALATED TO HUMAN</span>
                </>
              ) : isFailed ? (
                <>
                  <AlertOctagon className="w-3.5 h-3.5" />
                  <span>RESOLUTION FAILED</span>
                </>
              ) : (
                <>
                  <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
                  <span>REMEDIATION IN PROGRESS</span>
                </>
              )}
            </span>

            <button
              onClick={onClose}
              className="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-800 transition"
              title="Close modal (remediation continues in background)"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Scrollable Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {/* Progress Tracker Stages */}
          <div className="bg-slate-900/80 p-4 rounded-xl border border-slate-800">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-400 mb-3">
              <span>Agent Execution Pipeline</span>
              <span className="font-mono text-[11px] text-sky-400">
                {stages.filter((s) => s.completed).length} / {stages.length} Completed
              </span>
            </div>

            <div className="grid grid-cols-4 sm:grid-cols-8 gap-2">
              {stages.map((st, idx) => (
                <div
                  key={idx}
                  className={`p-2 rounded-lg border text-center flex flex-col items-center justify-center transition ${
                    st.completed
                      ? 'bg-emerald-950/30 border-emerald-600/40 text-emerald-300'
                      : st.active
                      ? 'bg-sky-950/40 border-sky-500 text-sky-300 animate-pulse'
                      : 'bg-slate-950/40 border-slate-800/80 text-slate-500'
                  }`}
                >
                  <div className="w-4 h-4 mb-1 flex items-center justify-center text-xs font-bold">
                    {st.completed ? '✓' : idx + 1}
                  </div>
                  <span className="text-[10px] font-medium leading-tight truncate w-full">{st.label}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Strategy & Policy Decision Cards */}
          {(remediationDetail?.restart_strategy || remediationDetail?.policy_decision) && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-slate-900/70 p-4 rounded-xl border border-slate-800 space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400 font-medium">Policy Decision</span>
                  <span
                    className={`font-bold px-2 py-0.5 rounded text-[11px] font-mono border ${
                      remediationDetail.policy_decision === 'APPROVED'
                        ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
                        : 'bg-red-500/20 text-red-400 border-red-500/40'
                    }`}
                  >
                    {remediationDetail.policy_decision}
                  </span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed font-sans">{remediationDetail.policy_reason}</p>
              </div>

              <div className="bg-slate-900/70 p-4 rounded-xl border border-slate-800 space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400 font-medium">Restart Strategy</span>
                  <span className="bg-sky-950 text-sky-300 font-mono text-[11px] px-2 py-0.5 rounded border border-sky-700 font-bold">
                    {remediationDetail.restart_strategy || 'RESTART_FROM_FAILED_STEP'}
                  </span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">
                  SAP Action: <code className="text-sky-300 font-mono">JobRestart({remediationDetail.restart_mode || 'E'})</code>
                  {remediationDetail.new_run_count && (
                    <span className="text-emerald-400 block mt-0.5">
                      Restarted run spawned: <span className="font-mono font-bold">#{remediationDetail.new_run_count}</span>
                    </span>
                  )}
                </p>
              </div>
            </div>
          )}

          {/* Real-time Streaming Logs Box */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs font-mono text-slate-400">
              <span className="flex items-center space-x-1.5">
                <Terminal className="w-3.5 h-3.5 text-sky-400" />
                <span className="text-white font-semibold">Live Agent Execution & SAP Activity Stream</span>
              </span>
              {isRunning && <span className="text-sky-400 animate-pulse font-semibold">Agent Active...</span>}
            </div>

            <div className="bg-[#090d16] border border-slate-800 rounded-xl p-4 font-mono text-xs space-y-2 h-64 overflow-y-auto shadow-inner">
              {events.length === 0 ? (
                <div className="text-slate-500 py-8 text-center">Connecting to live agent event stream...</div>
              ) : (
                events.map((evt, idx) => {
                  const isErr = evt.event_type.includes('ERROR') || evt.event_type.includes('REJECTED') || evt.event_type.includes('ESCALATED');
                  const isSucc = evt.event_type.includes('SUCCESS') || evt.event_type.includes('AUTO_RESOLVED');
                  const isPol = evt.event_type.includes('POLICY') || evt.event_type.includes('STRATEGY');
                  const isAi = evt.event_type.includes('AI');

                  return (
                    <div
                      key={idx}
                      className={`flex items-start space-x-2.5 leading-relaxed ${
                        isErr
                          ? 'text-red-400 font-semibold'
                          : isSucc
                          ? 'text-emerald-400 font-medium'
                          : isPol
                          ? 'text-sky-300'
                          : isAi
                          ? 'text-purple-300'
                          : 'text-slate-300'
                      }`}
                    >
                      <span className="text-slate-500 text-[11px] select-none shrink-0">{evt.timestamp}</span>
                      <span className="text-slate-400 text-[10px] uppercase font-bold bg-slate-800/80 px-1 rounded select-none shrink-0">
                        {evt.event_type.replace('_', ' ')}
                      </span>
                      <span className="flex-1 break-words">{evt.message}</span>
                    </div>
                  );
                })
              )}
              <div ref={logsEndRef} />
            </div>
          </div>
        </div>

        {/* Fixed Footer */}
        <div className="px-6 py-3.5 border-t border-slate-800 flex items-center justify-between bg-slate-900/90 shrink-0">
          <p className="text-[11px] text-slate-400">
            {isRunning
              ? 'Closing this modal will NOT cancel execution. The agent continues in the background.'
              : 'Remediation completed. Execution lineage and technical logs are preserved in Job History.'}
          </p>
          <button
            onClick={onClose}
            className="bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs px-4 py-2 rounded-lg transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
