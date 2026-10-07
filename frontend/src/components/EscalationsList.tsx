import React from 'react';
import { EscalationItem } from '../types/job';
import { AlertOctagon, CheckCircle2, UserCheck, ShieldAlert, ArrowUpRight } from 'lucide-react';
import { resolveEscalation } from '../services/api';

interface EscalationsListProps {
  escalations: EscalationItem[];
  onRefresh: () => void;
  onSelectJob: (jobName: string, runCount: number) => void;
}

export const EscalationsList: React.FC<EscalationsListProps> = ({ escalations, onRefresh, onSelectJob }) => {
  const handleMarkResolved = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await resolveEscalation(id);
      onRefresh();
    } catch (err) {
      console.error('Error marking escalation resolved:', err);
    }
  };

  return (
    <div className="space-y-4">
      {/* Banner */}
      <div className="bg-gradient-to-r from-red-950/40 via-slate-900 to-slate-900 border border-red-900/50 rounded-2xl p-5 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-red-500/20 text-red-400 border border-red-500/30 flex items-center justify-center">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white tracking-tight">Operations Escalation Queue</h2>
            <p className="text-xs text-slate-400">
              The Agent Safety Policy blocked automatic remediation for non-retryable failures or exceeded retry limits. Human intervention required.
            </p>
          </div>
        </div>
        <span className="bg-red-500/20 text-red-400 font-bold text-xs px-3 py-1 rounded-full border border-red-500/30">
          {escalations.length} Active Escalations
        </span>
      </div>

      {/* Escalations List */}
      <div className="space-y-3">
        {escalations.length === 0 ? (
          <div className="glass-panel p-12 rounded-2xl text-center border border-slate-800 text-slate-500">
            <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto mb-2 opacity-80" />
            <p className="text-sm font-semibold text-slate-300">No Active Escalations Queue</p>
            <p className="text-xs text-slate-500">All failed jobs have been either auto-resolved or cleared.</p>
          </div>
        ) : (
          escalations.map((esc) => {
            const isHigh = esc.severity === 'HIGH' || esc.severity === 'CRITICAL';
            return (
              <div
                key={esc.id}
                onClick={() => onSelectJob(esc.job_name, esc.run_count)}
                className="glass-panel p-5 rounded-2xl border border-slate-800 hover:border-slate-700 cursor-pointer transition space-y-3"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
                  <div className="flex items-center space-x-3">
                    <span className="font-bold text-base text-white">{esc.job_name}</span>
                    <span className="font-mono text-xs text-slate-400 bg-slate-800 px-2 py-0.5 rounded">
                      #{esc.run_count}
                    </span>
                    <span className="bg-slate-800 text-sky-300 font-mono text-xs px-2.5 py-0.5 rounded border border-slate-700">
                      {esc.failure_category}
                    </span>
                  </div>

                  <div className="flex items-center space-x-3">
                    <span
                      className={`text-xs font-bold px-2.5 py-0.5 rounded-full border uppercase tracking-wider ${
                        isHigh ? 'bg-red-500/20 text-red-400 border-red-500/40' : 'bg-amber-500/20 text-amber-400 border-amber-500/40'
                      }`}
                    >
                      Severity: {esc.severity}
                    </span>
                    <span className="text-xs text-slate-400 font-mono">{esc.created_at}</span>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                  <div className="bg-slate-900/60 p-3 rounded-xl border border-slate-800/80 space-y-1">
                    <span className="font-bold text-slate-400 uppercase tracking-wider block text-[10px]">Why Automation Was Blocked</span>
                    <p className="text-red-300 font-medium">{esc.reason}</p>
                  </div>

                  <div className="bg-slate-900/60 p-3 rounded-xl border border-slate-800/80 space-y-1">
                    <span className="font-bold text-slate-400 uppercase tracking-wider block text-[10px]">Suggested Human Action</span>
                    <p className="text-slate-200">{esc.suggested_action}</p>
                  </div>
                </div>

                <div className="flex justify-between items-center pt-1">
                  <span className="text-[11px] font-mono text-slate-500">{esc.execution_id}</span>
                  <div className="flex items-center space-x-3">
                    <button
                      onClick={(e) => handleMarkResolved(esc.id, e)}
                      className="bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 border border-emerald-500/40 text-xs font-semibold px-3 py-1.5 rounded-lg transition"
                    >
                      Mark Manually Resolved
                    </button>
                    <button className="text-sky-400 hover:text-sky-300 text-xs font-medium inline-flex items-center space-x-1">
                      <span>Inspect Logs</span>
                      <ArrowUpRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
