import React from 'react';
import { LayoutDashboard, ListFilter, CheckCircle2, AlertTriangle, Activity, ShieldCheck, ShieldAlert } from 'lucide-react';

interface SidebarProps {
  currentTab: string;
  onTabChange: (tab: string) => void;
  failedCount: number;
  escalationsCount: number;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, onTabChange, failedCount, escalationsCount }) => {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'all', label: 'All Job Executions', icon: ListFilter },
    { id: 'failed', label: 'Failed Jobs', icon: AlertTriangle, badge: failedCount > 0 ? failedCount : undefined, badgeColor: 'bg-red-500/20 text-red-400 border border-red-500/30' },
    { id: 'remediations', label: 'Remediations Console', icon: ShieldCheck },
    { id: 'escalations', label: 'Escalations Queue', icon: ShieldAlert, badge: escalationsCount > 0 ? escalationsCount : undefined, badgeColor: 'bg-amber-500/20 text-amber-400 border border-amber-500/30' },
    { id: 'success', label: 'Successful Jobs', icon: CheckCircle2 },
    { id: 'activity', label: 'Agent Activity Feed', icon: Activity },
  ];

  return (
    <aside className="w-64 bg-[#0f172a] border-r border-slate-800 flex flex-col justify-between select-none">
      <div className="p-4 space-y-1">
        <div className="px-3 py-2 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
          Operations Console
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition ${
                isActive
                  ? 'bg-sky-600/15 text-sky-400 border border-sky-500/30 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <div className="flex items-center space-x-3">
                <Icon className={`w-4 h-4 ${isActive ? 'text-sky-400' : 'text-slate-400'}`} />
                <span>{item.label}</span>
              </div>
              {item.badge !== undefined && (
                <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${item.badgeColor}`}>
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      <div className="p-4 border-t border-slate-800/80">
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3">
          <div className="flex items-center space-x-2 text-xs font-semibold text-slate-300">
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
            <span>Target Contract: S/4HANA</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-1">
            Communication Scenario <code className="text-slate-400 font-mono">SAP_COM_0326</code> active.
          </p>
        </div>
      </div>
    </aside>
  );
};
