import React, { useState } from 'react';
import { Cpu, ShieldAlert, CheckCircle, Clock, DollarSign, Award, Shield, AlertOctagon, Terminal } from 'lucide-react';
import { RuntimeCatalogEntry } from '../types/metao';

interface Props {
  runtimes: RuntimeCatalogEntry[];
  onQuarantine: (id: string, reason: string) => Promise<void>;
  onRestore: (id: string, reason: string) => Promise<void>;
  loading: boolean;
}

export const RuntimesView: React.FC<Props> = ({ runtimes, onQuarantine, onRestore, loading }) => {
  const [selectedRuntime, setSelectedRuntime] = useState<RuntimeCatalogEntry | null>(null);
  const [actionType, setActionType] = useState<'quarantine' | 'restore' | null>(null);
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleAction = async () => {
    if (!selectedRuntime || !actionType) return;
    setSubmitting(true);
    try {
      if (actionType === 'quarantine') {
        await onQuarantine(selectedRuntime.orchestrator_id, reason || 'Operator administrative quarantine');
      } else {
        await onRestore(selectedRuntime.orchestrator_id, reason || 'Operator administrative restore');
      }
      setActionType(null);
      setSelectedRuntime(null);
      setReason('');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white">Declarative Runtime Catalog</h2>
          <p className="text-sm text-slate-400">
            Pluggable agent orchestrators evaluated, certified, and admitted into the metaO control plane.
          </p>
        </div>
        <div className="text-xs font-mono px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-slate-400 flex items-center gap-2">
          <Terminal className="w-3.5 h-3.5 text-cyan-400" />
          <span>metao runtimes</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {runtimes.map(runtime => {
          const isQuarantined = runtime.disposition === 'QUARANTINED';
          const isHealthy = runtime.health === 'HEALTHY';

          return (
            <div
              key={runtime.orchestrator_id}
              className={`rounded-xl border p-5 transition flex flex-col justify-between ${
                isQuarantined
                  ? 'bg-rose-950/20 border-rose-900/50'
                  : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
              }`}
            >
              <div>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2.5">
                    <div
                      className={`w-9 h-9 rounded-lg flex items-center justify-center font-mono ${
                        isQuarantined
                          ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                          : 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'
                      }`}
                    >
                      <Cpu className="w-4 h-4" />
                    </div>
                    <div>
                      <h3 className="font-mono font-bold text-sm text-white">{runtime.orchestrator_id}</h3>
                      <span className="text-[11px] text-slate-500 font-mono">v{runtime.version}</span>
                    </div>
                  </div>

                  <span
                    className={`px-2 py-0.5 text-[10px] font-mono font-bold uppercase rounded ${
                      isQuarantined
                        ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                        : isHealthy
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                        : 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                    }`}
                  >
                    {isQuarantined ? 'QUARANTINED' : runtime.health}
                  </span>
                </div>

                {isQuarantined && runtime.quarantine_reason && (
                  <div className="mt-3 p-2 bg-rose-950/40 border border-rose-900/60 rounded text-[11px] text-rose-300">
                    <span className="font-semibold">Quarantine reason: </span>
                    {runtime.quarantine_reason}
                  </div>
                )}

                {/* Metrics */}
                <div className="grid grid-cols-3 gap-2 mt-4 text-center">
                  <div className="bg-slate-950/60 border border-slate-800/80 rounded p-2">
                    <span className="text-[10px] uppercase text-slate-500 block">Quality</span>
                    <span className="text-xs font-mono font-bold text-slate-200">
                      {(runtime.quality * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="bg-slate-950/60 border border-slate-800/80 rounded p-2">
                    <span className="text-[10px] uppercase text-slate-500 block">Success</span>
                    <span className="text-xs font-mono font-bold text-slate-200">
                      {(runtime.success_rate * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="bg-slate-950/60 border border-slate-800/80 rounded p-2">
                    <span className="text-[10px] uppercase text-slate-500 block">Latency</span>
                    <span className="text-xs font-mono font-bold text-slate-200">
                      {runtime.latency_ms}ms
                    </span>
                  </div>
                </div>

                {/* Capabilities */}
                <div className="mt-4">
                  <span className="text-[10px] uppercase font-semibold text-slate-500 tracking-wider block mb-1.5">
                    Capabilities
                  </span>
                  <div className="flex flex-wrap gap-1">
                    {runtime.capabilities.map(cap => (
                      <span
                        key={cap}
                        className="px-2 py-0.5 text-[10px] font-mono bg-slate-800/80 border border-slate-700/60 rounded text-slate-300"
                      >
                        {cap}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Trust profile */}
                <div className="mt-3 flex items-center gap-1.5 text-xs text-slate-400">
                  <Shield className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Trust Profile: <code className="text-indigo-300 font-mono text-[11px]">{runtime.trust_profile}</code></span>
                </div>
              </div>

              {/* Action buttons */}
              <div className="mt-5 pt-3 border-t border-slate-800 flex items-center justify-between">
                <span className="text-xs font-mono text-slate-500">
                  ${runtime.cost.toFixed(3)}/kTok
                </span>

                {isQuarantined ? (
                  <button
                    onClick={() => {
                      setSelectedRuntime(runtime);
                      setActionType('restore');
                      setReason('');
                    }}
                    className="px-2.5 py-1 text-xs font-medium text-emerald-400 hover:text-emerald-300 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 rounded cursor-pointer transition"
                  >
                    Restore Runtime
                  </button>
                ) : (
                  <button
                    onClick={() => {
                      setSelectedRuntime(runtime);
                      setActionType('quarantine');
                      setReason('');
                    }}
                    className="px-2.5 py-1 text-xs font-medium text-rose-400 hover:text-rose-300 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 rounded cursor-pointer transition"
                  >
                    Quarantine
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Quarantine / Restore Modal */}
      {actionType && selectedRuntime && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 shadow-2xl">
            <div className="flex items-center gap-3 mb-4">
              <div
                className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                  actionType === 'quarantine'
                    ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                    : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                }`}
              >
                {actionType === 'quarantine' ? (
                  <ShieldAlert className="w-5 h-5" />
                ) : (
                  <CheckCircle className="w-5 h-5" />
                )}
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">
                  {actionType === 'quarantine' ? 'Quarantine Runtime' : 'Restore Runtime'}
                </h3>
                <p className="text-xs text-slate-400 font-mono">{selectedRuntime.orchestrator_id}</p>
              </div>
            </div>

            <p className="text-xs text-slate-300 mb-3">
              {actionType === 'quarantine'
                ? 'Quarantined runtimes are excluded from admission and dispatch until explicitly restored by an authorized operator.'
                : 'Restoring will re-admit this runtime into active selection evaluation.'}
            </p>

            <div className="mb-4">
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                Reason / Justification
              </label>
              <textarea
                value={reason}
                onChange={e => setReason(e.target.value)}
                placeholder={
                  actionType === 'quarantine'
                    ? 'e.g. Non-deterministic behavior or upstream API quota degradation'
                    : 'e.g. Upstream incident resolved and conformance re-verified'
                }
                rows={3}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div className="flex items-center justify-end gap-2">
              <button
                onClick={() => {
                  setActionType(null);
                  setSelectedRuntime(null);
                }}
                disabled={submitting}
                className="px-3 py-1.5 text-xs font-medium text-slate-400 hover:text-white transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleAction}
                disabled={submitting}
                className={`px-3 py-1.5 text-xs font-semibold rounded-lg text-slate-950 transition cursor-pointer ${
                  actionType === 'quarantine'
                    ? 'bg-rose-400 hover:bg-rose-300'
                    : 'bg-emerald-400 hover:bg-emerald-300'
                }`}
              >
                {submitting ? 'Applying...' : actionType === 'quarantine' ? 'Confirm Quarantine' : 'Confirm Restore'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
