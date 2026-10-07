import React, { useState } from 'react';
import { RemediationItem } from '../types/job';
import { CheckCircle2, AlertOctagon, RefreshCw, ShieldCheck, ArrowUpRight, Search } from 'lucide-react';

interface RemediationsListProps {
  remediations: RemediationItem[];
  onSelectJob: (jobName: string, runCount: number) => void;
}

export const RemediationsList: React.FC<RemediationsListProps> = ({ remediations, onSelectJob }) => {
  const [filter, setFilter] = useState('ALL');
  const [searchTerm, setSearchTerm] = useState('');

  const filtered = remediations.filter((rem) => {
    const matchesSearch = rem.job_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          rem.execution_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          rem.failure_category.toLowerCase().includes(searchTerm.toLowerCase());
    
    if (filter === 'ALL') return matchesSearch;
    return matchesSearch && rem.status === filter;
  });

  return (
    <div className="space-y-4">
      {/* Header & Filters */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 glass-panel p-4 rounded-2xl border border-slate-800">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search execution ID, job or category..."
            className="w-full bg-[#0f172a] border border-slate-700/80 rounded-xl pl-9 pr-4 py-2 text-sm text-slate-200 focus:outline-none focus:border-sky-500"
          />
        </div>

        <div className="flex items-center space-x-2 w-full sm:w-auto">
          {['ALL', 'AUTO_RESOLVED', 'ESCALATED'].map((st) => (
            <button
              key={st}
              onClick={() => setFilter(st)}
              className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
                filter === st
                  ? 'bg-sky-600 text-white'
                  : 'bg-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              {st === 'AUTO_RESOLVED' ? 'AUTO RESOLVED' : st}
            </button>
          ))}
        </div>
      </div>

      {/* Remediations Table */}
      <div className="glass-panel rounded-2xl overflow-hidden border border-slate-800">
        <table className="w-full text-left text-sm text-slate-300">
          <thead className="bg-slate-900/90 text-slate-400 text-xs uppercase font-semibold border-b border-slate-800">
            <tr>
              <th className="py-3.5 px-5">Execution ID</th>
              <th className="py-3.5 px-5">Job & Run</th>
              <th className="py-3.5 px-5">Failure Category</th>
              <th className="py-3.5 px-5">Policy Check</th>
              <th className="py-3.5 px-5">Autonomous Action</th>
              <th className="py-3.5 px-5">Outcome</th>
              <th className="py-3.5 px-5 text-right">Timeline</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={7} className="text-center py-12 text-slate-500">
                  No remediation executions recorded yet. Trigger a failure scenario in the simulator!
                </td>
              </tr>
            ) : (
              filtered.map((rem) => {
                const isResolved = rem.status === 'AUTO_RESOLVED';
                return (
                  <tr
                    key={rem.id}
                    onClick={() => onSelectJob(rem.job_name, rem.run_count)}
                    className="hover:bg-slate-800/50 cursor-pointer transition"
                  >
                    <td className="py-3.5 px-5 font-mono text-xs text-sky-400 font-semibold">{rem.execution_id}</td>
                    <td className="py-3.5 px-5 font-bold text-white">
                      {rem.job_name}
                      <div className="text-xs font-normal font-mono text-slate-400">#{rem.run_count}</div>
                    </td>
                    <td className="py-3.5 px-5">
                      <span className="bg-slate-800 text-sky-300 font-mono text-xs px-2.5 py-0.5 rounded border border-slate-700">
                        {rem.failure_category}
                      </span>
                    </td>
                    <td className="py-3.5 px-5">
                      <span
                        className={`inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
                          rem.policy_decision === 'APPROVED'
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                            : 'bg-red-500/10 text-red-400 border-red-500/30'
                        }`}
                      >
                        <ShieldCheck className="w-3 h-3" />
                        <span>{rem.policy_decision}</span>
                      </span>
                    </td>
                    <td className="py-3.5 px-5 font-mono text-xs text-slate-300">
                      {rem.action} {rem.restart_mode !== 'NONE' && `(mode=${rem.restart_mode})`}
                    </td>
                    <td className="py-3.5 px-5">
                      <span
                        className={`inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-bold border ${
                          isResolved
                            ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                            : 'bg-red-500/15 text-red-400 border-red-500/30'
                        }`}
                      >
                        {isResolved ? <CheckCircle2 className="w-3.5 h-3.5" /> : <AlertOctagon className="w-3.5 h-3.5" />}
                        <span>{rem.status === 'AUTO_RESOLVED' ? 'AUTO RESOLVED' : rem.status}</span>
                      </span>
                    </td>
                    <td className="py-3.5 px-5 text-right">
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
  );
};
