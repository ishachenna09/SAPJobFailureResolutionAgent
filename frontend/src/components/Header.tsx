import React from 'react';
import { Search, ShieldAlert, Cpu, Activity, Zap } from 'lucide-react';

interface HeaderProps {
  onSearch: (term: string) => void;
  onOpenSimulator: () => void;
  agentStatus: string;
  platform: 'MOCK_SAP' | 'SAP_BTP';
  onPlatformChange: (platform: 'MOCK_SAP' | 'SAP_BTP') => void;
}

export const Header: React.FC<HeaderProps> = ({
  onSearch,
  onOpenSimulator,
  agentStatus,
  platform,
  onPlatformChange,
}) => {
  return (
    <header className="h-16 bg-[#0f172a] border-b border-slate-800 px-6 flex items-center justify-between sticky top-0 z-30 shadow-lg">
      {/* Left Branding */}
      <div className="flex items-center space-x-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-500 to-blue-600 flex items-center justify-center shadow-lg shadow-sky-500/20">
          <Cpu className="w-5 h-5 text-white" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="font-bold text-lg text-white tracking-tight">SAP Job Failure Agent</h1>
            <span className="bg-sky-950 text-sky-400 border border-sky-800 text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wider">
              {platform === 'SAP_BTP' ? 'SAP BTP REST' : 'SAP_COM_0326'}
            </span>
          </div>
          <p className="text-xs text-slate-400">Autonomous Job Failure Recognition, Safety Policy & Remediation</p>
        </div>
      </div>

      {/* Center Search */}
      <div className="w-80 relative hidden md:block">
        <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          placeholder="Search job name, run count, error code..."
          onChange={(e) => onSearch(e.target.value)}
          className="w-full bg-[#1e293b] border border-slate-700/60 rounded-lg pl-9 pr-4 py-1.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500 transition"
        />
      </div>

      {/* Right Controls */}
      <div className="flex items-center space-x-3">
        <button
          onClick={onOpenSimulator}
          className="flex items-center space-x-2 bg-gradient-to-r from-sky-600 to-blue-600 hover:from-sky-500 hover:to-blue-500 text-white font-medium text-xs px-3.5 py-2 rounded-lg shadow-md transition transform active:scale-95"
        >
          <Zap className="w-3.5 h-3.5 fill-current" />
          <span>Simulate SAP Job Event</span>
        </button>

        {/* Environment Switch Segmented Control */}
        <div className="flex items-center bg-slate-900 border border-slate-700/80 rounded-lg p-0.5 text-xs font-semibold">
          <button
            onClick={() => onPlatformChange('MOCK_SAP')}
            className={`px-3 py-1 rounded-md transition ${
              platform === 'MOCK_SAP'
                ? 'bg-sky-600 text-white shadow-sm font-bold'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Mock SAP
          </button>
          <button
            onClick={() => onPlatformChange('SAP_BTP')}
            className={`px-3 py-1 rounded-md transition ${
              platform === 'SAP_BTP'
                ? 'bg-sky-600 text-white shadow-sm font-bold'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            SAP BTP
          </button>
        </div>

        {/* Agent Status Badge */}
        <div className="flex items-center space-x-2 bg-slate-800/80 border border-slate-700/80 rounded-lg px-3 py-1.5 text-xs">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
          </span>
          <span className="text-slate-300 font-medium">Agent {agentStatus}</span>
        </div>
      </div>
    </header>
  );
};
