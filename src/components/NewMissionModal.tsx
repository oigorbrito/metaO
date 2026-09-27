import React, { useState } from 'react';
import { X, Play, Code, Sliders, CheckCircle2, ShieldAlert } from 'lucide-react';
import { Mission, Policy, AcceptanceBudget, AcceptanceContext } from '../types/metao';

interface Props {
  onClose: () => void;
  onSubmit: (spec: {
    mission: Mission;
    policy: Policy;
    budget: AcceptanceBudget;
    acceptance_context: AcceptanceContext;
  }) => Promise<void>;
}

export const NewMissionModal: React.FC<Props> = ({ onClose, onSubmit }) => {
  const [mode, setMode] = useState<'form' | 'json'>('form');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form states
  const [missionId, setMissionId] = useState(`mission-${Date.now().toString(36)}`);
  const [objective, setObjective] = useState('Build deterministic patch with verification');
  const [capabilities, setCapabilities] = useState('workflow, code_generation');
  const [taskFamily, setTaskFamily] = useState('standard_workflow');
  const [policyAllowed, setPolicyAllowed] = useState(true);
  const [requireHuman, setRequireHuman] = useState(false);
  const [policyReason, setPolicyReason] = useState('Approved by standard control-plane rule');
  const [moneyLimit, setMoneyLimit] = useState(1.0);
  const [tokenLimit, setTokenLimit] = useState(2000);
  const [wallTimeLimit, setWallTimeLimit] = useState(60.0);

  // JSON state
  const defaultJson = {
    mission: {
      mission_id: `mission-${Date.now().toString(36)}`,
      objective: 'Run agentic workflow with independent acceptance verification',
      required_capabilities: ['workflow'],
      task_family: 'standard_workflow',
    },
    policy: {
      policy_bundle_id: 'quickstart-policy',
      allowed: true,
      require_human: false,
      reason: 'Standard execution policy',
    },
    budget: {
      money_limit: 1.0,
      token_limit: 1500,
      wall_time_limit_s: 60.0,
      verifier_attempt_limit: 3,
    },
    acceptance_context: {
      subject_id: 'workload-subject',
      subject_state_id: 'state-01',
      verification_context_id: 'verification-ctx-01',
      policy_bundle_id: 'quickstart-policy',
      required_obligations: ['execution_result'],
      trusted_verifiers: ['adapter-observer'],
      trusted_provenance_roots: [],
      authorized_authorities: ['metao-runtime'],
    },
    now_epoch: Date.now() / 1000,
    max_attempts: 2,
  };

  const [rawJson, setRawJson] = useState(JSON.stringify(defaultJson, null, 2));

  const handleApplyPreset = (type: 'quickstart' | 'deny' | 'human' | 'code') => {
    if (type === 'quickstart') {
      setMissionId(`quickstart-run-${Math.floor(Math.random() * 1000)}`);
      setObjective('quickstart mission');
      setCapabilities('workflow');
      setPolicyAllowed(true);
      setRequireHuman(false);
      setPolicyReason('Policy check passed - allowed by quickstart rule');
    } else if (type === 'deny') {
      setMissionId(`deny-run-${Math.floor(Math.random() * 1000)}`);
      setObjective('unauthorized privileged system operation');
      setCapabilities('system_access');
      setPolicyAllowed(false);
      setRequireHuman(false);
      setPolicyReason('Deny policy triggered: root system privilege prohibited');
    } else if (type === 'human') {
      setMissionId(`human-gate-${Math.floor(Math.random() * 1000)}`);
      setObjective('deploy to staging environment with operator confirmation');
      setCapabilities('workflow');
      setPolicyAllowed(true);
      setRequireHuman(true);
      setPolicyReason('Policy requires human gatekeeper approval before dispatch');
    } else if (type === 'code') {
      setMissionId(`codegen-${Math.floor(Math.random() * 1000)}`);
      setObjective('synthesize patch for issue #42 and run test harness');
      setCapabilities('workflow, code_generation, tool_calling');
      setPolicyAllowed(true);
      setRequireHuman(false);
      setPolicyReason('Sandbox code generation approved');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      if (mode === 'json') {
        const parsed = JSON.parse(rawJson);
        await onSubmit(parsed);
      } else {
        const spec = {
          mission: {
            mission_id: missionId,
            objective,
            required_capabilities: capabilities.split(',').map(s => s.trim()).filter(Boolean),
            task_family: taskFamily || undefined,
          },
          policy: {
            policy_bundle_id: 'active-governance-v1',
            allowed: policyAllowed,
            require_human: requireHuman,
            reason: policyReason,
          },
          budget: {
            money_limit: Number(moneyLimit),
            token_limit: Number(tokenLimit),
            wall_time_limit_s: Number(wallTimeLimit),
            verifier_attempt_limit: 3,
          },
          acceptance_context: {
            subject_id: `${missionId}-subject`,
            subject_state_id: `${missionId}-state`,
            verification_context_id: `${missionId}-verif`,
            policy_bundle_id: 'active-governance-v1',
            required_obligations: ['execution_result'],
            trusted_verifiers: ['adapter-observer'],
            trusted_provenance_roots: [],
            authorized_authorities: ['metao-runtime'],
          },
        };
        await onSubmit(spec);
      }
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to submit mission');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-2xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
              <Play className="w-5 h-5 fill-cyan-400" />
            </div>
            <div>
              <h3 className="font-bold text-base text-white">Launch Mission</h3>
              <p className="text-xs text-slate-400">Dispatch governed workload with independent acceptance verification.</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Presets Bar */}
        <div className="p-3 bg-slate-950/60 border-b border-slate-800 flex flex-wrap items-center gap-2">
          <span className="text-[10px] uppercase font-mono font-bold text-slate-500 mr-1">Presets:</span>
          <button
            type="button"
            onClick={() => handleApplyPreset('quickstart')}
            className="px-2.5 py-1 text-xs rounded bg-slate-800 hover:bg-slate-700 text-cyan-300 font-mono border border-slate-700 cursor-pointer"
          >
            Quickstart Accepted
          </button>
          <button
            type="button"
            onClick={() => handleApplyPreset('deny')}
            className="px-2.5 py-1 text-xs rounded bg-slate-800 hover:bg-slate-700 text-rose-300 font-mono border border-slate-700 cursor-pointer"
          >
            Policy Deny
          </button>
          <button
            type="button"
            onClick={() => handleApplyPreset('human')}
            className="px-2.5 py-1 text-xs rounded bg-slate-800 hover:bg-slate-700 text-amber-300 font-mono border border-slate-700 cursor-pointer"
          >
            Human Gate
          </button>
          <button
            type="button"
            onClick={() => handleApplyPreset('code')}
            className="px-2.5 py-1 text-xs rounded bg-slate-800 hover:bg-slate-700 text-indigo-300 font-mono border border-slate-700 cursor-pointer"
          >
            Code Generation
          </button>

          <div className="ml-auto flex items-center border border-slate-800 rounded-lg p-0.5 bg-slate-900">
            <button
              type="button"
              onClick={() => setMode('form')}
              className={`px-2 py-0.5 text-xs font-medium rounded ${
                mode === 'form' ? 'bg-cyan-500/20 text-cyan-300' : 'text-slate-400'
              }`}
            >
              Form
            </button>
            <button
              type="button"
              onClick={() => setMode('json')}
              className={`px-2 py-0.5 text-xs font-medium rounded ${
                mode === 'json' ? 'bg-cyan-500/20 text-cyan-300' : 'text-slate-400'
              }`}
            >
              JSON
            </button>
          </div>
        </div>

        {/* Content */}
        <form onSubmit={handleSubmit} className="p-5 overflow-y-auto flex-1 space-y-4 text-xs">
          {error && (
            <div className="p-3 bg-rose-950/40 border border-rose-900/60 rounded-lg text-rose-300">
              {error}
            </div>
          )}

          {mode === 'form' ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                    Mission ID
                  </label>
                  <input
                    type="text"
                    value={missionId}
                    onChange={e => setMissionId(e.target.value)}
                    required
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                    Task Family
                  </label>
                  <input
                    type="text"
                    value={taskFamily}
                    onChange={e => setTaskFamily(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Objective
                </label>
                <input
                  type="text"
                  value={objective}
                  onChange={e => setObjective(e.target.value)}
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Required Capabilities (comma separated)
                </label>
                <input
                  type="text"
                  value={capabilities}
                  onChange={e => setCapabilities(e.target.value)}
                  placeholder="workflow, code_generation, tool_calling"
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>

              {/* Policy Section */}
              <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg space-y-3">
                <span className="text-[10px] uppercase font-mono font-bold text-slate-400 block">
                  Policy Gate Configuration
                </span>
                <div className="flex items-center gap-6">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={policyAllowed}
                      onChange={e => setPolicyAllowed(e.target.checked)}
                      className="rounded bg-slate-900 border-slate-700 text-cyan-500 focus:ring-0"
                    />
                    <span className="text-slate-300 font-medium">Policy Allows Execution</span>
                  </label>

                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={requireHuman}
                      onChange={e => setRequireHuman(e.target.checked)}
                      className="rounded bg-slate-900 border-slate-700 text-amber-500 focus:ring-0"
                    />
                    <span className="text-slate-300 font-medium">Require Human Gatekeeper</span>
                  </label>
                </div>
                <div>
                  <label className="block text-[10px] text-slate-500 mb-1">Policy Justification / Reason</label>
                  <input
                    type="text"
                    value={policyReason}
                    onChange={e => setPolicyReason(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded p-1.5 text-xs text-slate-300 focus:outline-none"
                  />
                </div>
              </div>

              {/* Budget Section */}
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                    Money Limit ($)
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    value={moneyLimit}
                    onChange={e => setMoneyLimit(parseFloat(e.target.value) || 0)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 font-mono text-slate-200 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                    Token Limit
                  </label>
                  <input
                    type="number"
                    value={tokenLimit}
                    onChange={e => setTokenLimit(parseInt(e.target.value) || 0)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 font-mono text-slate-200 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                    Wall Time (s)
                  </label>
                  <input
                    type="number"
                    value={wallTimeLimit}
                    onChange={e => setWallTimeLimit(parseFloat(e.target.value) || 0)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 font-mono text-slate-200 focus:outline-none"
                  />
                </div>
              </div>
            </div>
          ) : (
            <div>
              <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                Mission Specification JSON
              </label>
              <textarea
                value={rawJson}
                onChange={e => setRawJson(e.target.value)}
                rows={14}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 font-mono text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>
          )}

          <div className="pt-4 border-t border-slate-800 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-2 text-xs font-medium text-slate-400 hover:text-white transition cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 text-xs font-semibold rounded-lg bg-cyan-400 hover:bg-cyan-300 text-slate-950 transition cursor-pointer shadow-sm shadow-cyan-500/20"
            >
              {submitting ? 'Executing...' : 'Execute Mission'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
