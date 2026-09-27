import React from 'react';
import { Play, CheckCircle2, XCircle, AlertTriangle, Clock, Eye, Ban, ShieldCheck, Check } from 'lucide-react';
import { MissionRecord } from '../types/metao';

interface Props {
  missions: MissionRecord[];
  onInspect: (mission: MissionRecord) => void;
  onApprove: (id: string, approver: string, approved: boolean, reason?: string) => Promise<void>;
  onCancel: (id: string, reason?: string) => Promise<void>;
  onRunQuickstartAccepted: () => void;
  onRunPolicyDeny: () => void;
  onOpenNewMission: () => void;
  loading: boolean;
}

export const MissionsView: React.FC<Props> = ({
  missions,
  onInspect,
  onApprove,
  onCancel,
  onRunQuickstartAccepted,
  onRunPolicyDeny,
  onOpenNewMission,
  loading,
}) => {
  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'ACCEPTED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="w-3.5 h-3.5" />
            ACCEPTED
          </span>
        );
      case 'BLOCKED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-rose-500/10 text-rose-400 border border-rose-500/30">
            <Ban className="w-3.5 h-3.5" />
            BLOCKED
          </span>
        );
      case 'WAITING_APPROVAL':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-amber-500/10 text-amber-300 border border-amber-500/30 animate-pulse">
            <AlertTriangle className="w-3.5 h-3.5" />
            WAITING APPROVAL
          </span>
        );
      case 'RUNNING':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
            <Clock className="w-3.5 h-3.5 animate-spin" />
            RUNNING
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-slate-500/10 text-slate-400 border border-slate-500/30">
            <XCircle className="w-3.5 h-3.5" />
            {status}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Quickstart Action Banners */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-mono text-cyan-400 font-semibold uppercase">Committed Example</span>
              <span className="px-1.5 py-0.5 text-[10px] font-mono bg-emerald-500/10 text-emerald-400 rounded">
                Expected: ACCEPTED
              </span>
            </div>
            <h4 className="text-sm font-bold text-white mb-1">Quickstart Accepted Mission</h4>
            <p className="text-xs text-slate-400">
              Deterministic local run with quickstart-local provider, policy compliance, and independent verification proof.
            </p>
          </div>
          <button
            onClick={onRunQuickstartAccepted}
            className="mt-4 w-full flex items-center justify-center gap-2 px-3 py-2 text-xs font-semibold rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 transition cursor-pointer"
          >
            <Play className="w-3.5 h-3.5 fill-cyan-300" />
            <span>Execute Quickstart Mission</span>
          </button>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-mono text-rose-400 font-semibold uppercase">Committed Negative Path</span>
              <span className="px-1.5 py-0.5 text-[10px] font-mono bg-rose-500/10 text-rose-400 rounded">
                Expected: BLOCKED
              </span>
            </div>
            <h4 className="text-sm font-bold text-white mb-1">Policy Deny Mission</h4>
            <p className="text-xs text-slate-400">
              Proves metaO governance authority rejects unauthorized root capabilities before dispatching any orchestrator.
            </p>
          </div>
          <button
            onClick={onRunPolicyDeny}
            className="mt-4 w-full flex items-center justify-center gap-2 px-3 py-2 text-xs font-semibold rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 transition cursor-pointer"
          >
            <Ban className="w-3.5 h-3.5" />
            <span>Test Policy Gate Deny</span>
          </button>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-mono text-indigo-400 font-semibold uppercase">Custom Workload</span>
              <span className="px-1.5 py-0.5 text-[10px] font-mono bg-indigo-500/10 text-indigo-400 rounded">
                Intent only
              </span>
            </div>
            <h4 className="text-sm font-bold text-white mb-1">Custom Mission Spec</h4>
            <p className="text-xs text-slate-400">
              Describe a custom mission intent and budget. Policy, verifier and acceptance authority remain backend-owned.
            </p>
          </div>
          <button
            onClick={onOpenNewMission}
            className="mt-4 w-full flex items-center justify-center gap-2 px-3 py-2 text-xs font-semibold rounded-lg bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 transition cursor-pointer"
          >
            <Play className="w-3.5 h-3.5 fill-indigo-300" />
            <span>Configure New Mission</span>
          </button>
        </div>
      </div>

      {/* Missions Table */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden">
        <div className="p-4 sm:p-5 border-b border-slate-800 flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-white">Mission Execution Ledger</h3>
            <p className="text-xs text-slate-400">
              All persisted mission records, status decisions, and independent acceptance proofs.
            </p>
          </div>
          <span className="text-xs font-mono text-slate-500">{missions.length} recorded</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800/80 bg-slate-950/40 text-[11px] uppercase font-mono text-slate-400 tracking-wider">
                <th className="py-3 px-4">Mission ID</th>
                <th className="py-3 px-4">Objective</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Orchestrator</th>
                <th className="py-3 px-4">Acceptance</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-xs">
              {missions.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500">
                    No missions launched yet. Click "Launch Mission" to start.
                  </td>
                </tr>
              ) : (
                missions.map(m => {
                  const isWaitingApproval = m.status === 'WAITING_APPROVAL';

                  return (
                    <tr key={m.mission_id} className="hover:bg-slate-800/40 transition">
                      <td className="py-3.5 px-4 font-mono font-medium text-slate-200">
                        {m.mission_id}
                      </td>
                      <td className="py-3.5 px-4 text-slate-300 max-w-xs truncate">
                        {m.mission.objective}
                      </td>
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        {getStatusBadge(m.status)}
                      </td>
                      <td className="py-3.5 px-4 font-mono text-slate-300">
                        {m.orchestrator_id ? (
                          <span className="px-2 py-0.5 bg-slate-800 rounded border border-slate-700">
                            {m.orchestrator_id}
                          </span>
                        ) : (
                          <span className="text-slate-600">—</span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 font-mono">
                        <span
                          className={`font-semibold ${
                            m.acceptance_decision === 'ACCEPT'
                              ? 'text-emerald-400'
                              : m.acceptance_decision === 'DENY'
                              ? 'text-rose-400'
                              : 'text-amber-400'
                          }`}
                        >
                          {m.acceptance_decision}
                        </span>
                        {m.acceptance?.proof && (
                          <span className="ml-1 text-[10px] text-slate-500 block">
                            Acceptance Proof
                          </span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 text-right whitespace-nowrap space-x-2">
                        {isWaitingApproval && (
                          <button
                            onClick={() => onApprove(m.mission_id, 'operator-human-gate', true)}
                            className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30 border border-emerald-500/40 cursor-pointer"
                          >
                            <Check className="w-3.5 h-3.5" />
                            Approve
                          </button>
                        )}
                        <button
                          onClick={() => onInspect(m)}
                          className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded border border-slate-700 cursor-pointer transition"
                        >
                          <Eye className="w-3.5 h-3.5 text-cyan-400" />
                          Inspect
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
