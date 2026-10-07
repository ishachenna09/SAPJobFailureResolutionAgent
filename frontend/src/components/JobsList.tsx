import React, { useState } from 'react';
import { JobRunSummary } from '../types/job';
import { Search, Filter, ArrowUpRight } from 'lucide-react';

interface JobsListProps {
  jobs: JobRunSummary[];
  filterStatus?: string;
  onSelectJob: (jobName: string, runCount: number) => void;
}

export const JobsList: React.FC<JobsListProps> = ({ jobs, filterStatus, onSelectJob }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState(filterStatus || 'ALL');

  const filteredJobs = jobs.filter((job) => {
    const matchesSearch = job.job_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          job.run_count.toString().includes(searchTerm) ||
                          (job.failure_category && job.failure_category.toLowerCase().includes(searchTerm.toLowerCase()));
    
    if (!matchesSearch) return false;

    const isResolvedFailed = job.status === 'FAILED' && (job.is_resolved || job.remediation_status === 'AUTO_RESOLVED' || job.remediation_status === 'MANUALLY_RESOLVED');

    if (statusFilter === 'ALL') return true;
    if (statusFilter === 'FAILED') return job.status === 'FAILED' && !isResolvedFailed;
    if (statusFilter === 'SUCCESS') return job.status === 'SUCCESS';
    return job.status === statusFilter;
  });

  return (
    <div className="space-y-4">
      {/* Search & Filter Header */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 glass-panel p-4 rounded-2xl border border-slate-800">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search job name or category..."
            className="w-full bg-[#0f172a] border border-slate-700/80 rounded-xl pl-9 pr-4 py-2 text-sm text-slate-200 focus:outline-none focus:border-sky-500"
          />
        </div>

        <div className="flex items-center space-x-2 w-full sm:w-auto">
          <Filter className="w-4 h-4 text-slate-400" />
          <span className="text-xs text-slate-400">Filter Status:</span>
          {['ALL', 'FAILED', 'SUCCESS'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
                statusFilter === st
                  ? 'bg-sky-600 text-white'
                  : 'bg-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Jobs Table */}
      <div className="glass-panel rounded-2xl overflow-hidden border border-slate-800">
        <table className="w-full text-left text-sm text-slate-300">
          <thead className="bg-slate-900/90 text-slate-400 text-xs uppercase font-semibold border-b border-slate-800">
            <tr>
              <th className="py-3.5 px-5">Job Name</th>
              <th className="py-3.5 px-5">Run Count</th>
              <th className="py-3.5 px-5">Status</th>
              <th className="py-3.5 px-5">Failed Step</th>
              <th className="py-3.5 px-5">Return Code</th>
              <th className="py-3.5 px-5">AI Classification</th>
              <th className="py-3.5 px-5 text-right">Inspect</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {filteredJobs.length === 0 ? (
              <tr>
                <td colSpan={7} className="text-center py-12 text-slate-500">
                  No job executions matching current filters.
                </td>
              </tr>
            ) : (
              filteredJobs.map((job) => (
                <tr
                  key={`${job.job_name}-${job.run_count}`}
                  onClick={() => onSelectJob(job.job_name, job.run_count)}
                  className="hover:bg-slate-800/50 cursor-pointer transition"
                >
                  <td className="py-3.5 px-5 font-bold text-white">
                    {job.job_name}
                    {job.job_text && (
                      <div className="text-xs font-normal text-slate-400">{job.job_text}</div>
                    )}
                  </td>
                  <td className="py-3.5 px-5 font-mono text-slate-300">#{job.run_count}</td>
                  <td className="py-3.5 px-5">
                    {(() => {
                      const isAgentResolved = job.status === 'SUCCESS' && (!!job.parent_run_id || job.retry_count > 0 || !!job.remediation_execution_id || job.remediation_status === 'AUTO_RESOLVED');
                      if (job.status === 'FAILED') {
                        return (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border bg-red-500/10 text-red-400 border-red-500/30">
                            FAILED
                          </span>
                        );
                      }
                      if (isAgentResolved) {
                        return (
                          <span className="inline-flex items-center space-x-1 px-3 py-0.5 rounded-full text-xs font-bold border bg-gradient-to-r from-emerald-500/20 to-sky-500/20 text-emerald-300 border-emerald-500/40 shadow-sm">
                            <span>⚡</span>
                            <span>RESOLVED VIA AGENT (AUTORUN)</span>
                          </span>
                        );
                      }
                      return (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border bg-emerald-500/10 text-emerald-400 border-emerald-500/30">
                          SUCCESS
                        </span>
                      );
                    })()}
                  </td>
                  <td className="py-3.5 px-5 font-mono text-slate-400">
                    {job.failed_step_number ? `Step ${job.failed_step_number}` : '—'}
                  </td>
                  <td className="py-3.5 px-5 font-mono text-slate-400">{job.return_code}</td>
                  <td className="py-3.5 px-5">
                    {job.failure_category ? (
                      <span className="bg-slate-800 text-sky-300 font-mono text-xs px-2.5 py-1 rounded border border-slate-700">
                        {job.failure_category}
                      </span>
                    ) : (
                      <span className="text-slate-500 text-xs">—</span>
                    )}
                  </td>
                  <td className="py-3.5 px-5 text-right">
                    <button className="text-sky-400 hover:text-sky-300 font-medium text-xs inline-flex items-center space-x-1">
                      <span>View</span>
                      <ArrowUpRight className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
