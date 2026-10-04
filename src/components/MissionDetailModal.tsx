import React, { useState } from 'react';
import { X, ShieldCheck, Terminal, Copy, Check } from 'lucide-react';
import { MissionRecord } from '../types/metao';

export const MissionDetailModal: React.FC<{
  mission: MissionRecord;
  onClose: () => void;
}> = ({ mission, onClose }) => {
  const [tab, setTab] = useState<'overview' | 'proof' | 'attempts' | 'raw'>('overview');
  const [copied, setCopied] = useState(false);
  const proof = mission.acceptance?.proof;

  const copy = () => {
    navigator.clipboard.writeText(JSON.stringify(mission, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="mission-detail-title"
        className="bg-slate-900 border border-slate-800 rounded-xl max-w-3xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden"
      >
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <div>
            <h3 id="mission-detail-title" className="font-mono font-bold text-white text-base">
              {mission.mission_id}
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">{mission.mission.objective}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close modal"
            className="p-1.5 text-slate-400 hover:text-white rounded-lg transition focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500 cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div role="tablist" aria-label="Mission detail tabs" className="flex border-b border-slate-800 px-5 gap-4 text-xs">
          {(['overview', 'proof', 'attempts', 'raw'] as const).map(x => (
            <button
              key={x}
              id={`tab-${x}`}
              role="tab"
              aria-selected={tab === x}
              aria-controls={`tabpanel-${x}`}
              onClick={() => setTab(x)}
              className={`py-2.5 px-1 border-b-2 font-medium capitalize transition cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500 rounded-t ${
                tab === x
                  ? 'border-cyan-400 text-cyan-400 font-semibold'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              {x}
            </button>
          ))}
        </div>

        <div
          id={`tabpanel-${tab}`}
          role="tabpanel"
          aria-labelledby={`tab-${tab}`}
          className="p-5 overflow-y-auto flex-1 text-xs"
        >
          {tab === 'overview' && (
            <div className="space-y-4">
              <section className="bg-slate-950/60 border border-slate-800 rounded-lg p-4">
                <div className="text-[10px] uppercase font-mono text-slate-500 mb-2">
                  Canonical mission state
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    Status: <span className="font-mono text-cyan-300">{mission.status}</span>
                  </div>
                  <div>
                    Acceptance: <span className="font-mono">{mission.acceptance_decision}</span>
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap gap-1">
                  {mission.mission.required_capabilities.map(c => (
                    <span
                      key={c}
                      className="px-2 py-0.5 bg-slate-800 rounded font-mono text-cyan-300"
                    >
                      {c}
                    </span>
                  ))}
                </div>
              </section>
              <section className="bg-slate-950/60 border border-slate-800 rounded-lg p-4">
                <div className="text-[10px] uppercase font-mono text-slate-500 mb-2">
                  Canonical budget
                </div>
                <pre className="text-slate-300 overflow-x-auto">
                  {JSON.stringify(mission.budget, null, 2)}
                </pre>
              </section>
              {mission.approval_request && (
                <section className="bg-slate-950/60 border border-amber-500/20 rounded-lg p-4">
                  <div className="text-amber-300 font-semibold">Human approval requested</div>
                  <pre className="mt-2 text-slate-300">
                    {JSON.stringify(mission.approval_request, null, 2)}
                  </pre>
                </section>
              )}
            </div>
          )}

          {tab === 'proof' &&
            (proof ? (
              <div className="bg-slate-950/60 border border-emerald-500/20 rounded-lg p-4 space-y-3">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-emerald-400 shrink-0" />
                  <div>
                    <div className="font-semibold text-emerald-300">
                      Canonical acceptance decision proof
                    </div>
                    <div className="font-mono text-[10px] text-slate-400">{proof.digest}</div>
                  </div>
                </div>
                <div>Decision: {proof.decision}</div>
                <div>
                  Evidence IDs:
                  <pre className="text-slate-300 mt-1">{JSON.stringify(proof.evidence_ids, null, 2)}</pre>
                </div>
                <div>
                  Reasons:
                  <pre className="whitespace-pre-wrap text-slate-300 mt-1">
                    {JSON.stringify(proof.reasons, null, 2)}
                  </pre>
                </div>
              </div>
            ) : (
              <div className="p-8 text-center text-slate-500">
                No canonical acceptance proof is present.
              </div>
            ))}

          {tab === 'attempts' && (
            <div className="space-y-3">
              {mission.attempts.map(a => (
                <div
                  key={a.attempt_number}
                  className="bg-slate-950/60 border border-slate-800 rounded-lg p-4"
                >
                  <div className="font-mono text-cyan-300">
                    Attempt #{a.attempt_number} • {a.orchestrator_id}
                  </div>
                  <div className="mt-2 grid grid-cols-2 gap-2">
                    <div>Status: {a.execution_status || 'N/A'}</div>
                    <div>Acceptance: {a.acceptance_decision}</div>
                    <div>Cost: {a.cost}</div>
                    <div>Failure: {a.failure_class || 'N/A'}</div>
                  </div>
                  <pre className="mt-2 text-slate-400 whitespace-pre-wrap">
                    {JSON.stringify(a.reasons, null, 2)}
                  </pre>
                </div>
              ))}
            </div>
          )}

          {tab === 'raw' && (
            <div>
              <div className="flex justify-end mb-2">
                <button
                  type="button"
                  onClick={copy}
                  className="flex items-center gap-1.5 px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs font-medium transition cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? 'Copied' : 'Copy JSON'}</span>
                </button>
              </div>
              <pre className="p-3 bg-slate-950 border border-slate-800 rounded-lg overflow-x-auto text-slate-300">
                {JSON.stringify(mission, null, 2)}
              </pre>
            </div>
          )}
        </div>

        <div className="p-4 border-t border-slate-800 bg-slate-950/60 flex items-center gap-2 text-xs font-mono text-slate-400">
          <Terminal className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
          <span>metao inspect {mission.mission_id}</span>
        </div>
      </div>
    </div>
  );
};
