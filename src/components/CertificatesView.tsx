import React, { useState } from 'react';
import { ShieldCheck, ShieldAlert, Award, FileCode, CheckCircle2, XCircle, Terminal } from 'lucide-react';
import { RuntimeCertification } from '../types/metao';

interface Props {
  certifications: RuntimeCertification[];
  onRevoke: (certId: string, reason: string) => Promise<void>;
  loading: boolean;
}

export const CertificatesView: React.FC<Props> = ({ certifications, onRevoke, loading }) => {
  const [selectedCert, setSelectedCert] = useState<RuntimeCertification | null>(null);
  const [revokeReason, setRevokeReason] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleRevoke = async () => {
    if (!selectedCert) return;
    setSubmitting(true);
    try {
      await onRevoke(selectedCert.certificate_id, revokeReason || 'Administrative governance revocation');
      setSelectedCert(null);
      setRevokeReason('');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white">Runtime Certification & Conformance</h2>
          <p className="text-sm text-slate-400">
            Durable conformance certificates verifying orchestrators adhere to deterministic contracts without state leaks.
          </p>
        </div>
        <div className="text-xs font-mono px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-slate-400 flex items-center gap-2">
          <Terminal className="w-3.5 h-3.5 text-cyan-400" />
          <span>metao runtime-certificates &lt;id&gt;</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {certifications.map(cert => {
          const isValid = cert.passed && !cert.revoked;

          return (
            <div
              key={cert.certificate_id}
              className={`p-5 rounded-xl border flex flex-col justify-between ${
                cert.revoked
                  ? 'bg-rose-950/20 border-rose-900/50'
                  : isValid
                  ? 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
                  : 'bg-amber-950/20 border-amber-900/50'
              }`}
            >
              <div>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2.5">
                    <div
                      className={`w-9 h-9 rounded-lg flex items-center justify-center font-mono ${
                        isValid
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                      }`}
                    >
                      {isValid ? <ShieldCheck className="w-5 h-5" /> : <ShieldAlert className="w-5 h-5" />}
                    </div>
                    <div>
                      <h3 className="font-mono font-bold text-sm text-white">{cert.certificate_id}</h3>
                      <p className="text-xs text-slate-400 font-mono">
                        Runtime: <span className="text-cyan-400">{cert.orchestrator_id}</span> (v{cert.runtime_version})
                      </p>
                    </div>
                  </div>

                  <span
                    className={`px-2.5 py-0.5 text-xs font-mono font-bold rounded ${
                      cert.revoked
                        ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                        : cert.passed
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                        : 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                    }`}
                  >
                    {cert.revoked ? 'REVOKED' : cert.passed ? 'PASSED' : 'FAILED'}
                  </span>
                </div>

                {cert.revoked && cert.revocation_reason && (
                  <div className="mt-3 p-2 bg-rose-950/50 border border-rose-900/60 rounded text-xs text-rose-300">
                    <span className="font-semibold">Revocation reason: </span>
                    {cert.revocation_reason}
                  </div>
                )}

                <div className="mt-4 space-y-2 text-xs">
                  <div className="flex justify-between py-1 border-b border-slate-800/80">
                    <span className="text-slate-400">Probe Execution:</span>
                    <span className="font-mono text-slate-200">{cert.probe_execution_id}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-800/80">
                    <span className="text-slate-400">Total Checks:</span>
                    <span className="font-mono text-slate-200">{cert.total_checks} automated assertions</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-800/80">
                    <span className="text-slate-400">Checks Digest:</span>
                    <span className="font-mono text-slate-400 truncate max-w-[200px]" title={cert.checks_digest}>
                      {cert.checks_digest}
                    </span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-800/80">
                    <span className="text-slate-400">Certified Date:</span>
                    <span className="font-mono text-slate-300">
                      {new Date(cert.certified_at_epoch * 1000).toLocaleString()}
                    </span>
                  </div>
                </div>

                {cert.failed_checks.length > 0 && (
                  <div className="mt-3">
                    <span className="text-[11px] font-semibold text-rose-400 block mb-1">Failed Assertions:</span>
                    <div className="space-y-1">
                      {cert.failed_checks.map((fc, i) => (
                        <div key={i} className="flex items-center gap-1.5 text-xs text-rose-300 font-mono">
                          <XCircle className="w-3.5 h-3.5 text-rose-400" />
                          <span>{fc}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <div className="mt-5 pt-3 border-t border-slate-800 flex items-center justify-between">
                <span className="text-xs text-slate-500 font-mono">
                  {cert.passed && !cert.revoked ? 'Reusable Certificate' : 'Non-reusable'}
                </span>

                {!cert.revoked && (
                  <button
                    onClick={() => {
                      setSelectedCert(cert);
                      setRevokeReason('');
                    }}
                    className="px-2.5 py-1 text-xs font-medium text-rose-400 hover:text-rose-300 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 rounded cursor-pointer transition"
                  >
                    Revoke Certificate
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Revocation Modal */}
      {selectedCert && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 shadow-2xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400">
                <ShieldAlert className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">Revoke Runtime Certificate</h3>
                <p className="text-xs text-slate-400 font-mono">{selectedCert.certificate_id}</p>
              </div>
            </div>

            <p className="text-xs text-slate-300 mb-3">
              Revoking a certificate immutably invalidates this generation in the SQLite certification revocation store. The runtime will fail admission gates until a new passing probe is certified.
            </p>

            <div className="mb-4">
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                Revocation Justification / Audit Reason
              </label>
              <textarea
                value={revokeReason}
                onChange={e => setRevokeReason(e.target.value)}
                placeholder="e.g. Discovered security regression or failing audit probe in newer version"
                rows={3}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div className="flex items-center justify-end gap-2">
              <button
                onClick={() => setSelectedCert(null)}
                disabled={submitting}
                className="px-3 py-1.5 text-xs font-medium text-slate-400 hover:text-white transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleRevoke}
                disabled={submitting}
                className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-rose-500 hover:bg-rose-400 text-white transition cursor-pointer"
              >
                {submitting ? 'Revoking...' : 'Confirm Revocation'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
