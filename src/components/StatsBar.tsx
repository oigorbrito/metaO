import React, { useMemo } from 'react';
import { ShieldCheck, Cpu, CheckCircle2, Activity } from 'lucide-react';
import { DoctorReport, MissionRecord, RuntimeCatalogEntry, RuntimeCertification } from '../types/metao';

interface Props {
  doctor: DoctorReport | null;
  runtimes: RuntimeCatalogEntry[];
  missions: MissionRecord[];
  certifications: RuntimeCertification[];
}

export const StatsBar: React.FC<Props> = React.memo(({ doctor, runtimes, missions, certifications }) => {
  const activeRuntimes = useMemo(() => runtimes.filter(r => r.disposition === 'ACTIVE'), [runtimes]);
  const validCerts = useMemo(() => certifications.filter(c => c.passed && !c.revoked), [certifications]);
  const acceptedMissions = useMemo(() => missions.filter(m => m.status === 'ACCEPTED'), [missions]);

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
        <div>
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Doctor Health</p>
          <div className="flex items-center gap-2 mt-1">
            <span className={`inline-block w-2.5 h-2.5 rounded-full ${doctor?.overall_status === 'PASS' ? 'bg-emerald-400 shadow-[0_0_8px_#34d399]' : 'bg-rose-400'}`} />
            <h3 className="text-xl font-bold font-mono text-white">{doctor?.overall_status || 'CHECKING...'}</h3>
          </div>
        </div>
        <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
          <Activity className="w-5 h-5" />
        </div>
      </div>

      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
        <div>
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Admitted Runtimes</p>
          <div className="flex items-baseline gap-1 mt-1">
            <h3 className="text-xl font-bold font-mono text-white">{activeRuntimes.length}</h3>
            <span className="text-xs text-slate-400">/ {runtimes.length} active</span>
          </div>
        </div>
        <div className="w-10 h-10 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
          <Cpu className="w-5 h-5" />
        </div>
      </div>

      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
        <div>
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Valid Certificates</p>
          <div className="flex items-baseline gap-1 mt-1">
            <h3 className="text-xl font-bold font-mono text-white">{validCerts.length}</h3>
            <span className="text-xs text-slate-400">/ {certifications.length} passed</span>
          </div>
        </div>
        <div className="w-10 h-10 rounded-lg bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-violet-400">
          <ShieldCheck className="w-5 h-5" />
        </div>
      </div>

      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
        <div>
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Accepted Missions</p>
          <div className="flex items-baseline gap-1 mt-1">
            <h3 className="text-xl font-bold font-mono text-white">{acceptedMissions.length}</h3>
            <span className="text-xs text-slate-400">/ {missions.length} total</span>
          </div>
        </div>
        <div className="w-10 h-10 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
          <CheckCircle2 className="w-5 h-5" />
        </div>
      </div>
    </div>
  );
});
