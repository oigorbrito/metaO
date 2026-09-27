import React from 'react';
import { Hexagon, Activity, Cpu, ShieldCheck, BarChart3, ListFilter, Play, Stethoscope } from 'lucide-react';

export type TabType = 'missions' | 'runtimes' | 'certificates' | 'benchmarks' | 'doctor' | 'events';

interface Props {
  activeTab: TabType;
  setActiveTab: (tab: TabType) => void;
  onOpenNewMission: () => void;
  pendingApprovalsCount: number;
}

export const Navbar: React.FC<Props> = ({
  activeTab,
  setActiveTab,
  onOpenNewMission,
  pendingApprovalsCount,
}) => {
  const tabs: { id: TabType; label: string; icon: any; badge?: number }[] = [
    { id: 'missions', label: 'Missions', icon: Activity, badge: pendingApprovalsCount },
    { id: 'runtimes', label: 'Runtime Catalog', icon: Cpu },
    { id: 'certificates', label: 'Certifications', icon: ShieldCheck },
    { id: 'benchmarks', label: 'Benchmarks & Evidence', icon: BarChart3 },
    { id: 'doctor', label: 'Doctor Diagnostics', icon: Stethoscope },
    { id: 'events', label: 'Event Ledger', icon: ListFilter },
  ];

  return (
    <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-600 via-indigo-600 to-violet-500 p-0.5 shadow-lg shadow-cyan-500/20">
              <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center text-cyan-400">
                <Hexagon className="w-5 h-5 fill-cyan-400/20" />
              </div>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="font-bold text-lg tracking-tight text-white font-mono">metaO</h1>
                <span className="px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 rounded">
                  Control Plane
                </span>
              </div>
              <p className="text-xs text-slate-400 hidden sm:block">
                Pluggable Orchestrator Governance & Acceptance Engine
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 sm:gap-4">
            <button
              onClick={onOpenNewMission}
              className="inline-flex items-center gap-2 px-3.5 py-2 text-xs sm:text-sm font-semibold text-slate-950 bg-gradient-to-r from-cyan-400 to-teal-400 hover:from-cyan-300 hover:to-teal-300 rounded-lg shadow-sm transition-all shadow-cyan-500/25 active:scale-95 cursor-pointer"
            >
              <Play className="w-4 h-4 fill-slate-950" />
              <span>Launch Mission</span>
            </button>
          </div>
        </div>

        {/* Tab navigation */}
        <nav className="flex space-x-1 sm:space-x-4 overflow-x-auto py-2 no-scrollbar border-t border-slate-800/60">
          {tabs.map(tab => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as TabType)}
                className={`flex items-center gap-2 px-3 py-2 text-xs sm:text-sm font-medium rounded-lg whitespace-nowrap transition-colors cursor-pointer ${
                  isActive
                    ? 'bg-slate-800 text-cyan-400 shadow-sm border border-slate-700/60'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-cyan-400' : 'text-slate-400'}`} />
                <span>{tab.label}</span>
                {Boolean(tab.badge && tab.badge > 0) && (
                  <span className="px-1.5 py-0.2 bg-amber-500/20 text-amber-300 border border-amber-500/40 text-[10px] font-bold rounded-full animate-pulse">
                    {tab.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>
    </header>
  );
};
