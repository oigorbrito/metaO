import React, { useState, useEffect, useCallback } from 'react';
import { Navbar, TabType } from './components/Navbar';
import { StatsBar } from './components/StatsBar';
import { MissionsView } from './components/MissionsView';
import { RuntimesView } from './components/RuntimesView';
import { CertificatesView } from './components/CertificatesView';
import { BenchmarksView } from './components/BenchmarksView';
import { DoctorView } from './components/DoctorView';
import { EventLedgerView } from './components/EventLedgerView';
import { MissionDetailModal } from './components/MissionDetailModal';
import { NewMissionModal } from './components/NewMissionModal';
import {
  DoctorReport,
  MissionRecord,
  RuntimeCatalogEntry,
  RuntimeCertification,
  BenchmarkEvidence,
  MissionEvent,
} from './types/metao';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState<TabType>('missions');
  const [doctor, setDoctor] = useState<DoctorReport | null>(null);
  const [runtimes, setRuntimes] = useState<RuntimeCatalogEntry[]>([]);
  const [missions, setMissions] = useState<MissionRecord[]>([]);
  const [certifications, setCertifications] = useState<RuntimeCertification[]>([]);
  const [benchmarks, setBenchmarks] = useState<BenchmarkEvidence[]>([]);
  const [events, setEvents] = useState<MissionEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedMission, setSelectedMission] = useState<MissionRecord | null>(null);
  const [isNewMissionOpen, setIsNewMissionOpen] = useState(false);
  const [toast, setToast] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const showToast = (text: string, type: 'success' | 'error' | 'info' = 'info') => {
    setToast({ text, type });
    setTimeout(() => {
      setToast(null);
    }, 4000);
  };

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [docRes, runRes, misRes, certRes, benchRes, evtRes] = await Promise.all([
        fetch('/api/doctor').then(r => r.json()),
        fetch('/api/runtimes').then(r => r.json()),
        fetch('/api/missions').then(r => r.json()),
        fetch('/api/certificates').then(r => r.json()),
        fetch('/api/benchmarks').then(r => r.json()),
        fetch('/api/events').then(r => r.json()),
      ]);

      setDoctor(docRes);
      setRuntimes(runRes);
      setMissions(misRes);
      setCertifications(certRes);
      setBenchmarks(benchRes);
      setEvents(evtRes);
    } catch (err: any) {
      console.error('Failed to load control plane data:', err);
      showToast('Error syncing control plane state: ' + err.message, 'error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Quarantine runtime
  const handleQuarantine = async (id: string, reason: string) => {
    try {
      const res = await fetch(`/api/runtimes/${id}/quarantine`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason, actor: 'operator-ui' }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || 'Failed to quarantine');
      }
      showToast(`Runtime ${id} durably quarantined`, 'success');
      await loadData();
    } catch (err: any) {
      showToast(err.message, 'error');
    }
  };

  // Restore runtime
  const handleRestore = async (id: string, reason: string) => {
    try {
      const res = await fetch(`/api/runtimes/${id}/restore`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason, actor: 'operator-ui' }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || 'Failed to restore');
      }
      showToast(`Runtime ${id} restored to active admission`, 'success');
      await loadData();
    } catch (err: any) {
      showToast(err.message, 'error');
    }
  };

  // Revoke certificate
  const handleRevokeCertificate = async (certId: string, reason: string) => {
    try {
      const res = await fetch(`/api/certificates/${certId}/revoke`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason, actor: 'governance-authority' }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || 'Failed to revoke');
      }
      showToast(`Certificate ${certId} revoked`, 'success');
      await loadData();
    } catch (err: any) {
      showToast(err.message, 'error');
    }
  };

  // Run mission
  const handleRunMission = async (spec: any) => {
    try {
      const res = await fetch('/api/missions/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(spec),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Failed to execute mission');
      }
      showToast(`Mission ${data.mission_id} executed: ${data.status}`, 'success');
      await loadData();
      setSelectedMission(data);
    } catch (err: any) {
      showToast(err.message, 'error');
      throw err;
    }
  };

  // Approve mission
  const handleApprove = async (id: string, approver: string, approved: boolean, reason?: string) => {
    try {
      const res = await fetch(`/api/missions/${id}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approver, approved, reason }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to approve');
      showToast(`Mission ${id} approval decided: ${data.status}`, 'success');
      await loadData();
      if (selectedMission?.mission_id === id) {
        setSelectedMission(data);
      }
    } catch (err: any) {
      showToast(err.message, 'error');
    }
  };

  // Cancel mission
  const handleCancel = async (id: string, reason?: string) => {
    try {
      const res = await fetch(`/api/missions/${id}/cancel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to cancel');
      showToast(`Mission ${id} cancelled`, 'info');
      await loadData();
    } catch (err: any) {
      showToast(err.message, 'error');
    }
  };

  // Run Quickstart Accepted Preset
  const handleRunQuickstartAccepted = async () => {
    const id = `quickstart-run-${Math.floor(1000 + Math.random() * 9000)}`;
    const spec = {
      mission: {
        mission_id: id,
        objective: 'quickstart mission',
        required_capabilities: ['workflow'],
        task_family: 'standard_workflow',
      },
      policy: {
        policy_bundle_id: 'quickstart-policy',
        allowed: true,
        require_human: false,
        reason: 'Policy check passed - allowed by quickstart rule',
      },
      budget: {
        money_limit: 1.0,
        token_limit: 1000,
        wall_time_limit_s: 60.0,
        verifier_attempt_limit: 3,
      },
      acceptance_context: {
        subject_id: 'quickstart-subject',
        subject_state_id: 'quickstart-state',
        verification_context_id: 'quickstart-verification',
        policy_bundle_id: 'quickstart-policy',
        required_obligations: ['execution_result'],
        trusted_verifiers: ['adapter-observer'],
        trusted_provenance_roots: [],
        authorized_authorities: ['metao-runtime'],
      },
      max_attempts: 2,
    };
    await handleRunMission(spec);
  };

  // Run Policy Deny Preset
  const handleRunPolicyDeny = async () => {
    const id = `policy-deny-${Math.floor(1000 + Math.random() * 9000)}`;
    const spec = {
      mission: {
        mission_id: id,
        objective: 'privileged root action outside sandbox',
        required_capabilities: ['system_access'],
        task_family: 'system_admin',
      },
      policy: {
        policy_bundle_id: 'strict-governance-v1',
        allowed: false,
        require_human: false,
        reason: 'Policy violation: Unsanctioned capability system_access requested outside sandbox.',
      },
      budget: {
        money_limit: 0.5,
        token_limit: 500,
        wall_time_limit_s: 30.0,
        verifier_attempt_limit: 1,
      },
      acceptance_context: {
        subject_id: 'deny-subject',
        subject_state_id: 'deny-state',
        verification_context_id: 'deny-context',
        policy_bundle_id: 'strict-governance-v1',
        required_obligations: ['execution_result'],
        trusted_verifiers: ['adapter-observer'],
        trusted_provenance_roots: [],
        authorized_authorities: ['metao-runtime'],
      },
      max_attempts: 1,
    };
    await handleRunMission(spec);
  };

  const pendingApprovalsCount = missions.filter(m => m.status === 'WAITING_APPROVAL').length;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-cyan-500/20 selection:text-cyan-300">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onOpenNewMission={() => setIsNewMissionOpen(true)}
        pendingApprovalsCount={pendingApprovalsCount}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <StatsBar
          doctor={doctor}
          runtimes={runtimes}
          missions={missions}
          certifications={certifications}
        />

        {activeTab === 'missions' && (
          <MissionsView
            missions={missions}
            onInspect={setSelectedMission}
            onApprove={handleApprove}
            onCancel={handleCancel}
            onRunQuickstartAccepted={handleRunQuickstartAccepted}
            onRunPolicyDeny={handleRunPolicyDeny}
            onOpenNewMission={() => setIsNewMissionOpen(true)}
            loading={loading}
          />
        )}

        {activeTab === 'runtimes' && (
          <RuntimesView
            runtimes={runtimes}
            onQuarantine={handleQuarantine}
            onRestore={handleRestore}
            loading={loading}
          />
        )}

        {activeTab === 'certificates' && (
          <CertificatesView
            certifications={certifications}
            onRevoke={handleRevokeCertificate}
            loading={loading}
          />
        )}

        {activeTab === 'benchmarks' && <BenchmarksView benchmarks={benchmarks} />}

        {activeTab === 'doctor' && (
          <DoctorView doctor={doctor} onRefresh={loadData} loading={loading} />
        )}

        {activeTab === 'events' && <EventLedgerView events={events} />}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950/60 py-4 text-center text-xs text-slate-500 font-mono">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>metaO Control Plane • Framework-neutral agent orchestrator governance</span>
          <span className="text-slate-600">DOCUMENTED != IMPLEMENTED != EXECUTED != ACCEPTED</span>
        </div>
      </footer>

      {/* Modals */}
      {selectedMission && (
        <MissionDetailModal
          mission={selectedMission}
          onClose={() => setSelectedMission(null)}
        />
      )}

      {isNewMissionOpen && (
        <NewMissionModal
          onClose={() => setIsNewMissionOpen(false)}
          onSubmit={handleRunMission}
        />
      )}

      {/* Toast Notification */}
      {toast && (
        <div className="fixed bottom-5 right-5 z-50 flex items-center gap-2.5 px-4 py-3 rounded-xl bg-slate-900 border border-slate-700 shadow-2xl text-xs font-medium text-white animate-in slide-in-from-bottom-2">
          {toast.type === 'success' && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
          {toast.type === 'error' && <AlertCircle className="w-4 h-4 text-rose-400" />}
          {toast.type === 'info' && <Info className="w-4 h-4 text-cyan-400" />}
          <span>{toast.text}</span>
          <button onClick={() => setToast(null)} className="ml-2 text-slate-400 hover:text-white cursor-pointer">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}
