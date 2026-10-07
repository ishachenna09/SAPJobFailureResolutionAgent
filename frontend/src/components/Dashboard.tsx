import React from 'react';
import { DashboardStats, JobRunSummary, ActivityItem } from '../types/job';
import { AlertOctagon, CheckCircle, Activity, Layers, ArrowUpRight, Cpu } from 'lucide-react';

interface DashboardProps {
  stats: DashboardStats;
  recentJobs: JobRunSummary[];
  activity: ActivityItem[];
  onSelectJob: (jobName: string, runCount: number) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ stats, recentJobs, activity, onSelectJob }) => {
  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-sky-950/40 to-slate-900 border border-slate-800 rounded-2xl p-6 relative overflow-hidden">
        <div className="absolute right-0 top-0 bottom-0 w-1/3 bg-gradient-to-l from-sky-500/10 to-transparent pointer-events-none" />
        <div className="flex items-center justify-between relative z-10">
          <div>
            <div className="flex items-center space-x-2 text-sky-400 font-semibold text-xs uppercase tracking-wider mb-1">
              <Cpu className="w-4 h-4" />
              <span>Active — Autonomous Remediation & Execution Engine</span>
            </div>
            <h2 className="text-2xl font-bold text-white tracking-tight">Autonomous SAP Operations Center</h2>
            <p className="text-slate-400 text-sm mt-1 max-w-2xl">
              The agent continuously ingests SAP job events, diagnoses root cause with AI, evaluates deterministic safety policies, executes <code className="text-sky-300 font-mono">JobRestart(E/A)</code>, monitors recovery, and maintains persistent run lineage.
            </p>
          </div>
        </div>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="glass-card rounded-2xl p-5 relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Total Job Runs</span>
            <Layers className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-3xl font-extrabold text-white">{stats.total_jobs}</div>
          <p className="text-xs text-slate-400 mt-2">
            Monitored via {stats.platform === 'SAP_BTP' ? 'SAP BTP REST Service' : 'Mock SAP Service'}
          </p>
        </div>

        <div className="glass-card rounded-2xl p-5 relative overflow-hidden border-l-4 border-l-red-500">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Recognized Failures</span>
            <AlertOctagon className="w-4 h-4 text-red-400" />
          </div>
          <div className="text-3xl font-extrabold text-red-400">{stats.failed_jobs}</div>
          <div className="flex items-center space-x-1 text-xs text-red-300/80 mt-2">
            <span>{stats.failure_rate}% failure rate</span>
          </div>
        </div>

        <div className="glass-card rounded-2xl p-5 relative overflow-hidden border-l-4 border-l-emerald-500">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Recognized Successes</span>
            <CheckCircle className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-3xl font-extrabold text-emerald-400">{stats.successful_jobs}</div>
          <div className="flex items-center space-x-1 text-xs text-emerald-300/80 mt-2">
            <span>{stats.success_rate}% success rate</span>
          </div>
        </div>

        <div className="glass-card rounded-2xl p-5 relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Agent Engine</span>
            <Activity className="w-4 h-4 text-sky-400" />
          </div>
          <div className="flex items-center space-x-2">
            <span className="w-3 h-3 rounded-full bg-emerald-400 pulse-dot"></span>
            <span className="text-2xl font-bold text-white">{stats.agent_status}</span>
          </div>
          <p className="text-xs text-slate-400 mt-2">Real-time status analysis ready</p>
        </div>
      </div>

      {/* Main Grid: Jobs Table & Activity Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Jobs Table */}
        <div className="lg:col-span-2 glass-panel rounded-2xl p-5 border border-slate-800">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-bold text-white">Recent Job Executions</h3>
              <p className="text-xs text-slate-400">Click any row to inspect steps, logs, and AI diagnosis</p>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-900/80 text-slate-400 text-xs uppercase font-semibold border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">Job Name</th>
                  <th className="py-3 px-4">Run #</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Failed Step</th>
                  <th className="py-3 px-4">AI Failure Category</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {recentJobs.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-center py-8 text-slate-500">
                      No jobs recorded yet. Trigger a job simulation above!
                    </td>
                  </tr>
                ) : (
                  recentJobs.map((job) => {
                    const isFailed = job.status === 'FAILED';
                    return (
                      <tr
                        key={`${job.job_name}-${job.run_count}`}
                        onClick={() => onSelectJob(job.job_name, job.run_count)}
                        className="hover:bg-slate-800/50 cursor-pointer transition"
                      >
                        <td className="py-3 px-4 font-semibold text-white">
                          {job.job_name}
                          {job.job_text && (
                            <div className="text-[11px] font-normal text-slate-400 truncate max-w-xs">{job.job_text}</div>
                          )}
                        </td>
                        <td className="py-3 px-4 font-mono text-slate-300">#{job.run_count}</td>
                        <td className="py-3 px-4">
                          <span
                            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
                              isFailed
                                ? 'bg-red-500/10 text-red-400 border-red-500/30'
                                : job.status === 'SUCCESS'
                                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                                : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                            }`}
                          >
                            {isFailed ? 'FAILED' : job.status}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-mono text-slate-400">
                          {job.failed_step_number ? `Step ${job.failed_step_number}` : '—'}
                        </td>
                        <td className="py-3 px-4">
                          {job.failure_category ? (
                            <span className="bg-slate-800 text-sky-300 font-mono text-xs px-2 py-0.5 rounded border border-slate-700">
                              {job.failure_category}
                            </span>
                          ) : (
                            <span className="text-slate-500 text-xs">None</span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <button className="text-sky-400 hover:text-sky-300 text-xs font-medium inline-flex items-center space-x-1">
                            <span>Inspect</span>
                            <ArrowUpRight className="w-3.5 h-3.5" />
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Live Activity Feed */}
        <div className="glass-panel rounded-2xl p-5 border border-slate-800 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-bold text-white">Agent Operational Log</h3>
              <span className="text-xs text-emerald-400 font-mono flex items-center space-x-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                <span>LIVE</span>
              </span>
            </div>

            <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
              {activity.length === 0 ? (
                <div className="text-xs text-slate-500 py-4 text-center">No recent events</div>
              ) : (
                activity.map((act) => (
                  <div
                    key={act.id}
                    onClick={() => onSelectJob(act.job_name, act.run_count)}
                    className="p-3 bg-slate-900/70 border border-slate-800/80 rounded-xl hover:border-slate-700 cursor-pointer transition"
                  >
                    <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                      <span className="font-mono">{act.received_at}</span>
                      <span className="text-[10px] bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded">
                        {act.event_type}
                      </span>
                    </div>
                    <div className="text-xs font-medium text-slate-200">
                      Recognized event for <span className="text-sky-400 font-semibold">{act.job_name}</span> #{act.run_count}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-800 text-center text-xs text-slate-500">
            Automated status updates processed seamlessly
          </div>
        </div>
      </div>
    </div>
  );
};
