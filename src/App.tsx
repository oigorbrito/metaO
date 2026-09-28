import React, { useCallback, useEffect, useState } from 'react';
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
  BenchmarkEvidence,
  DoctorReport,
  MissionEvent,
  MissionRecord,
  RuntimeCatalogEntry,
  RuntimeCertification,
} from './types/metao';
import { AlertCircle, CheckCircle2, Info, X } from 'lucide-react';

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || `Request failed: ${response.status}`);
  }
  return data as T;
}

export default function App() {
  const [activeTab, setActiveTab] = useState<TabType>('missions');
  const [doctor, setDoctor] = useState<DoctorReport | null>(null);
  const [runtimes, setRuntimes] = useState<RuntimeCatalogEntry[]>([]);
  const [missions, setMissions] = useState<MissionRecord[]>([]);
  const [certifications, setCertifications] = useState<RuntimeCertification[]>([]);
  const [benchmarks, setBenchmarks] = useState<BenchmarkEvidence[]>([]);
  const [events, setEvents] = useState<MissionEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedMission, setSelectedMission] = useState<MissionRecord | null>(
    null,
  );
  const [isNewMissionOpen, setIsNewMissionOpen] = useState(false);
  const [toast, setToast] = useState<{
    text: string;
    type: 'success' | 'error' | 'info';
  } | null>(null);

  const showToast = (
    text: string,
    type: 'success' | 'error' | 'info' = 'info',
  ) => {
    setToast({ text, type });
    setTimeout(() => setToast(null), 4000);
  };

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [doc, run, mis, cert, bench, evt] = await Promise.all([
        requestJson<DoctorReport>('/api/doctor'),
        requestJson<RuntimeCatalogEntry[]>('/api/runtimes'),
        requestJson<MissionRecord[]>('/api/missions'),
        requestJson<RuntimeCertification[]>('/api/certificates'),
        requestJson<BenchmarkEvidence[]>('/api/benchmarks'),
        requestJson<MissionEvent[]>('/api/events'),
      ]);

      setDoctor(doc);
      setRuntimes(run);
      setMissions(mis);
      setCertifications(cert);
      setBenchmarks(bench);
      setEvents(evt);
    } catch (error: any) {
      console.error('Failed to load canonical control-plane data:', error);
      showToast(
        'Canonical backend state could not be loaded: ' + error.message,
        'error',
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const postJson = <T,>(url: string, body: unknown = {}): Promise<T> =>
    requestJson<T>(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

  const handleQuarantine = async (id: string, reason: string) => {
    try {
      await postJson(`/api/runtimes/${id}/quarantine`, { reason });
      showToast(`Runtime ${id} quarantined by canonical backend`, 'success');
      await loadData();
    } catch (error: any) {
      showToast(error.message, 'error');
    }
  };

  const handleRestore = async (id: string, reason: string) => {
    try {
      await postJson(`/api/runtimes/${id}/restore`, { reason });
      showToast(`Runtime ${id} restore recorded by canonical backend`, 'success');
      await loadData();
    } catch (error: any) {
      showToast(error.message, 'error');
    }
  };

  const handleRevokeCertificate = async (certId: string, reason: string) => {
    try {
      await postJson(`/api/certificates/${certId}/revoke`, { reason });
      showToast(`Certificate ${certId} revocation recorded`, 'success');
      await loadData();
    } catch (error: any) {
      showToast(error.message, 'error');
    }
  };

  const handleRunMission = async (intent: unknown) => {
    try {
      await postJson('/api/missions/run', intent);
    } catch (error: any) {
      showToast(error.message, 'info');
      throw error;
    }
  };

  const handleApprove = async (
    id: string,
    _approver: string,
    approved: boolean,
    reason?: string,
  ) => {
    try {
      const data = await postJson<MissionRecord>(
        `/api/missions/${id}/approve`,
        { approved, reason },
      );
      showToast(`Mission ${id}: canonical approval record updated`, 'success');
      await loadData();
      if (selectedMission?.mission_id === id) setSelectedMission(data);
    } catch (error: any) {
      showToast(error.message, 'error');
    }
  };

  const handleCancel = async (id: string, reason?: string) => {
    try {
      await postJson(`/api/missions/${id}/cancel`, { reason });
      showToast(`Mission ${id}: cancellation delegated to backend`, 'info');
      await loadData();
    } catch (error: any) {
      showToast(error.message, 'error');
    }
  };

  const runExample = async (endpoint: string) => {
    try {
      const data = await postJson<MissionRecord>(endpoint);
      showToast(
        `Canonical example result: ${data.status}`,
        data.status === 'ACCEPTED' ? 'success' : 'info',
      );
      await loadData();
      setSelectedMission(data);
    } catch (error: any) {
      showToast(error.message, 'error');
    }
  };

  const pendingApprovalsCount = missions.filter(
    (mission) => mission.status === 'WAITING_APPROVAL',
  ).length;

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
            onRunQuickstartAccepted={() =>
              runExample('/api/examples/quickstart-accepted')
            }
            onRunPolicyDeny={() => runExample('/api/examples/policy-deny')}
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

        {activeTab === 'benchmarks' && (
          <BenchmarksView benchmarks={benchmarks} />
        )}

        {activeTab === 'doctor' && (
          <DoctorView doctor={doctor} onRefresh={loadData} loading={loading} />
        )}

        {activeTab === 'events' && <EventLedgerView events={events} />}
      </main>

      <footer className="border-t border-slate-900 bg-slate-950/60 py-4 text-center text-xs text-slate-500 font-mono">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>
            metaO Operator Console • presentation over canonical backend authority
          </span>
          <span className="text-slate-600">
            DOCUMENTED != IMPLEMENTED != EXECUTED != ACCEPTED
          </span>
        </div>
      </footer>

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

      {toast && (
        <div className="fixed bottom-5 right-5 z-50 flex items-center gap-2.5 px-4 py-3 rounded-xl bg-slate-900 border border-slate-700 shadow-2xl text-xs font-medium text-white">
          {toast.type === 'success' && (
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          )}
          {toast.type === 'error' && (
            <AlertCircle className="w-4 h-4 text-rose-400" />
          )}
          {toast.type === 'info' && (
            <Info className="w-4 h-4 text-cyan-400" />
          )}
          <span>{toast.text}</span>
          <button
            onClick={() => setToast(null)}
            className="ml-2 text-slate-400 hover:text-white"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}
