import React, { useState } from 'react';
import { X, CheckCircle2, XCircle, AlertTriangle, ShieldCheck, Terminal, Copy, Check } from 'lucide-react';
import { MissionRecord } from '../types/metao';

interface Props {
  mission: MissionRecord;
  onClose: () => void;
}

export const MissionDetailModal: React.FC<Props> = ({ mission, onClose }) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'proof' | 'attempts' | 'raw'>('overview');
  const [copied, setCopied] = useState(false);

  const handleCopyRaw = () => {
    navigator.clipboard.writeText(JSON.stringify(mission, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-3xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 font-mono text-sm font-bold">
              mO
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-mono font-bold text-base text-white">{mission.mission_id}</h3>
                <span
                  className={`px-2 py-0.5 text-[10px] font-mono font-bold rounded ${
                    mission.status === 'ACCEPTED'
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                      : mission.status === 'BLOCKED'
                      ? 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                      : 'bg-amber-500/10 text-amber-300 border border-amber-500/30'
                  }`}
                >
                  {mission.status}
                </span>
              </div>
              <p className="text-xs text-slate-400 truncate max-w-md">{mission.mission.objective}</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-slate-800 px-4 sm:px-5 space-x-4 bg-slate-950/40 text-xs font-medium">
          <button
            onClick={() => setActiveTab('overview')}
            className={`py-2.5 border-b-2 transition cursor-pointer ${
              activeTab === 'overview'
                ? 'border-cyan-400 text-cyan-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Overview & Policy
          </button>
          <button
            onClick={() => setActiveTab('proof')}
            className={`py-2.5 border-b-2 transition cursor-pointer ${
              activeTab === 'proof'
                ? 'border-cyan-400 text-cyan-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Acceptance Proof
          </button>
          <button
            onClick={() => setActiveTab('attempts')}
            className={`py-2.5 border-b-2 transition cursor-pointer ${
              activeTab === 'attempts'
                ? 'border-cyan-400 text-cyan-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Execution Attempts ({mission.attempts.length})
          </button>
          <button
            onClick={() => setActiveTab('raw')}
            className={`py-2.5 border-b-2 transition cursor-pointer ${
              activeTab === 'raw'
                ? 'border-cyan-400 text-cyan-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Raw JSON Record
          </button>
        </div>

        {/* Body */}
        <div className="p-5 overflow-y-auto flex-1 space-y-4 text-xs">
          {activeTab === 'overview' && (
            <div className="space-y-4">
              {/* Mission Metadata */}
              <div className="bg-slate-950/60 border border-slate-800 rounded-lg p-3.5 space-y-2">
                <span className="text-[10px] font-mono uppercase text-slate-500 font-bold block">
                  Mission Specification
                </span>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <span className="text-slate-400">Objective:</span>
                    <p className="font-semibold text-slate-200">{mission.mission.objective}</p>
                  </div>
                  <div>
                    <span className="text-slate-400">Task Family:</span>
                    <p className="font-mono text-cyan-300">{mission.mission.task_family || 'default'}</p>
                  </div>
                </div>
                <div>
                  <span className="text-slate-400 block mb-1">Required Capabilities:</span>
                  <div className="flex flex-wrap gap-1">
                    {mission.mission.required_capabilities.map(c => (
                      <span key={c} className="px-2 py-0.5 bg-slate-800 text-cyan-300 font-mono rounded text-[10px]">
                        {c}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Policy Evaluation */}
              <div className="bg-slate-950/60 border border-slate-800 rounded-lg p-3.5 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono uppercase text-slate-500 font-bold">
                    Policy Gate Evaluation
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded font-mono font-bold text-[10px] ${
                      mission.policy.allowed
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                    }`}
                  >
                    {mission.policy.allowed ? 'POLICY ALLOWED' : 'POLICY DENIED'}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-slate-300">
                  <div>
                    <span className="text-slate-500 block">Policy Bundle:</span>
                    <span className="font-mono">{mission.policy.policy_bundle_id}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Requires Human Gate:</span>
                    <span className="font-mono">{mission.policy.require_human ? 'Yes' : 'No'}</span>
                  </div>
                </div>
                {mission.policy.reason && (
                  <p className="p-2 bg-slate-900 border border-slate-800 rounded text-slate-300">
                    {mission.policy.reason}
                  </p>
                )}
              </div>

              {/* Budget Limits */}
              <div className="bg-slate-950/60 border border-slate-800 rounded-lg p-3.5">
                <span className="text-[10px] font-mono uppercase text-slate-500 font-bold block mb-2">
                  Acceptance Budget Limits
                </span>
                <div className="grid grid-cols-4 gap-2 text-center font-mono">
                  <div className="p-2 bg-slate-900 rounded border border-slate-800">
                    <span className="text-[10px] text-slate-500 block">Max Cost</span>
                    <span className="font-bold text-slate-200">${mission.budget.money_limit}</span>
                  </div>
                  <div className="p-2 bg-slate-900 rounded border border-slate-800">
                    <span className="text-[10px] text-slate-500 block">Max Tokens</span>
                    <span className="font-bold text-slate-200">{mission.budget.token_limit}</span>
                  </div>
                  <div className="p-2 bg-slate-900 rounded border border-slate-800">
                    <span className="text-[10px] text-slate-500 block">Wall-Time</span>
                    <span className="font-bold text-slate-200">{mission.budget.wall_time_limit_s}s</span>
                  </div>
                  <div className="p-2 bg-slate-900 rounded border border-slate-800">
                    <span className="text-[10px] text-slate-500 block">Verifier Attempts</span>
                    <span className="font-bold text-slate-200">{mission.budget.verifier_attempt_limit}</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'proof' && (
            <div className="space-y-4">
              {mission.proof ? (
                <div className="bg-slate-950/60 border border-emerald-500/20 rounded-lg p-4 space-y-3">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                    <div className="flex items-center gap-2">
                      <ShieldCheck className="w-5 h-5 text-emerald-400" />
                      <div>
                        <h4 className="font-mono font-bold text-sm text-emerald-300">
                          Cryptographic Acceptance Proof
                        </h4>
                        <span className="font-mono text-[10px] text-slate-400">{mission.proof.proof_id}</span>
                      </div>
                    </div>
                    <span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 rounded font-mono text-[10px] font-bold">
                      VERIFIED & ACCEPTED
                    </span>
                  </div>

                  <div>
                    <span className="text-[10px] uppercase font-mono text-slate-500 font-bold block mb-1">
                      Obligation Verification Results
                    </span>
                    <div className="space-y-2">
                      {Object.entries(mission.proof.obligation_results).map(([ob, res]) => (
                        <div key={ob} className="p-2.5 bg-slate-900 rounded border border-slate-800 flex items-start gap-2.5">
                          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                          <div className="flex-1 font-mono">
                            <div className="flex justify-between items-baseline">
                              <span className="font-bold text-slate-200">{ob}</span>
                              <span className="text-[10px] text-slate-400">Verifier: {res.verifier}</span>
                            </div>
                            {res.details && <p className="text-[11px] text-slate-400 mt-1 font-sans">{res.details}</p>}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="pt-2 border-t border-slate-800 space-y-1 font-mono text-[11px] text-slate-400">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Signing Authority:</span>
                      <span className="text-cyan-300">{mission.proof.authority_id}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Signature:</span>
                      <span className="text-slate-300 truncate max-w-[260px]">{mission.proof.signature}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Timestamp:</span>
                      <span className="text-slate-300">{new Date(mission.proof.accepted_at * 1000).toLocaleString()}</span>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="p-8 text-center bg-slate-950/40 border border-slate-800 rounded-lg text-slate-500">
                  No acceptance proof generated (mission status is {mission.status}).
                </div>
              )}
            </div>
          )}

          {activeTab === 'attempts' && (
            <div className="space-y-3">
              {mission.attempts.length === 0 ? (
                <div className="p-8 text-center bg-slate-950/40 border border-slate-800 rounded-lg text-slate-500">
                  No runtime execution attempts were dispatched.
                </div>
              ) : (
                mission.attempts.map(att => (
                  <div key={att.attempt_number} className="bg-slate-950/60 border border-slate-800 rounded-lg p-3.5 space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-slate-200">Attempt #{att.attempt_number}</span>
                        <span className="px-1.5 py-0.2 bg-slate-800 font-mono text-[10px] text-cyan-300 rounded border border-slate-700">
                          {att.orchestrator_id}
                        </span>
                      </div>
                      <span
                        className={`px-2 py-0.5 rounded font-mono text-[10px] font-bold ${
                          att.execution_status === 'SUCCEEDED'
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                        }`}
                      >
                        {att.execution_status}
                      </span>
                    </div>

                    <div className="grid grid-cols-3 gap-2 font-mono text-[11px] text-center bg-slate-900 p-2 rounded">
                      <div>
                        <span className="text-[10px] text-slate-500 block">Cost</span>
                        <span className="text-slate-200">${att.cost}</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-500 block">Tokens</span>
                        <span className="text-slate-200">{att.tokens}</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-500 block">Execution ID</span>
                        <span className="text-slate-400 truncate block text-[10px]">{att.execution_id}</span>
                      </div>
                    </div>

                    {att.reasons.length > 0 && (
                      <div className="space-y-1 text-[11px] text-slate-300">
                        {att.reasons.map((r, i) => (
                          <div key={i} className="flex items-start gap-1.5">
                            <span className="text-cyan-400">•</span>
                            <span>{r}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          )}

          {activeTab === 'raw' && (
            <div>
              <div className="flex justify-end mb-2">
                <button
                  onClick={handleCopyRaw}
                  className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 transition cursor-pointer"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? 'Copied!' : 'Copy JSON'}</span>
                </button>
              </div>
              <pre className="p-3 bg-slate-950 border border-slate-800 rounded-lg text-slate-300 font-mono text-[11px] overflow-x-auto max-h-[400px]">
                {JSON.stringify(mission, null, 2)}
              </pre>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between text-xs font-mono text-slate-400">
          <div className="flex items-center gap-2">
            <Terminal className="w-3.5 h-3.5 text-cyan-400" />
            <span>metao inspect {mission.mission_id}</span>
          </div>
          <button
            onClick={onClose}
            className="px-3 py-1.5 font-sans font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg border border-slate-700 cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
