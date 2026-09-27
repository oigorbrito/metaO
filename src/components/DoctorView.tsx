import React from 'react';
import { Activity, CheckCircle2, XCircle, RefreshCw, AlertTriangle, Terminal } from 'lucide-react';
import { DoctorReport } from '../types/metao';

interface Props {
  doctor: DoctorReport | null;
  onRefresh: () => void;
  loading: boolean;
}

export const DoctorView: React.FC<Props> = ({ doctor, onRefresh, loading }) => {
  return (
    <div className="space-y-6">
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-6 border-b border-slate-800">
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-bold text-white">metaO Doctor</h2>
              <span
                className={`px-2.5 py-0.5 text-xs font-mono font-bold rounded-full uppercase tracking-wider ${
                  doctor?.overall_status === 'PASS'
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                    : 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                }`}
              >
                {doctor?.overall_status === 'PASS' ? 'Ready & Healthy (PASS)' : 'Degraded (FAIL)'}
              </span>
            </div>
            <p className="text-sm text-slate-400 mt-1">
              Verifies operator bootstrap environment, declarative runtime catalog, and state stores.
            </p>
          </div>
          <button
            onClick={onRefresh}
            disabled={loading}
            className="flex items-center gap-2 px-3.5 py-1.5 text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg border border-slate-700 transition cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Re-run Diagnostics</span>
          </button>
        </div>

        {/* Diagnostic Command Explanation */}
        <div className="mt-4 p-3 bg-slate-950/80 border border-slate-800/80 rounded-lg flex items-center gap-3 font-mono text-xs text-slate-300">
          <Terminal className="w-4 h-4 text-cyan-400 shrink-0" />
          <span>Equivalent CLI execution: <code className="text-cyan-300">metao doctor --db=.metao/metao.db</code></span>
        </div>

        {/* Checks List */}
        <div className="mt-6 space-y-3">
          {doctor?.checks.map((chk, idx) => {
            const isPass = chk.status === 'PASS';
            return (
              <div
                key={idx}
                className="p-4 rounded-xl bg-slate-950/50 border border-slate-800/80 hover:border-slate-700 transition"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5">
                      {isPass ? (
                        <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                      ) : (
                        <XCircle className="w-5 h-5 text-rose-400" />
                      )}
                    </div>
                    <div>
                      <h4 className="text-sm font-semibold text-slate-200 font-mono">{chk.name}</h4>
                      <p className="text-xs text-slate-400 mt-0.5">{chk.details}</p>
                    </div>
                  </div>
                  <span
                    className={`px-2 py-0.5 text-[11px] font-mono font-bold rounded ${
                      isPass ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'
                    }`}
                  >
                    {chk.status}
                  </span>
                </div>

                {chk.metrics && (
                  <div className="mt-3 pt-3 border-t border-slate-900 grid grid-cols-2 sm:grid-cols-4 gap-2">
                    {Object.entries(chk.metrics).map(([key, val]) => (
                      <div key={key} className="bg-slate-900/60 rounded px-2.5 py-1.5">
                        <span className="text-[10px] text-slate-500 uppercase block font-mono">{key}</span>
                        <span className="text-xs font-mono font-semibold text-slate-300">{String(val)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Architecture Authority Reference */}
      <div className="p-4 bg-slate-900/40 border border-slate-800/60 rounded-xl flex items-start gap-3 text-xs text-slate-400">
        <Activity className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold text-slate-300">Document Authority: </span>
          Runtime admission gates adhere to <code className="text-cyan-400">docs/DOCUMENT-AUTHORITY-MAP.md</code> and <code className="text-cyan-400">docs/POST-MVP-OPERATIONAL-BASELINE-V1.md</code>.
          Non-negotiable invariants: <code className="text-slate-300">DOCUMENTED != IMPLEMENTED != EXECUTED != ACCEPTED</code>.
        </div>
      </div>
    </div>
  );
};
