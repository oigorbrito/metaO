import React from 'react';
import { BarChart3, Database, CheckCircle, ExternalLink, Terminal } from 'lucide-react';
import { BenchmarkEvidence } from '../types/metao';

interface Props {
  benchmarks: BenchmarkEvidence[];
}

export const BenchmarksView: React.FC<Props> = ({ benchmarks }) => {
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white">Empirical Benchmark Evidence</h2>
          <p className="text-sm text-slate-400">
            Authoritative performance evidence informing runtime strategy scoring and capability bounds.
          </p>
        </div>
        <div className="text-xs font-mono px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-slate-400 flex items-center gap-2">
          <Terminal className="w-3.5 h-3.5 text-cyan-400" />
          <span>metao runtime-benchmarks &lt;id&gt;</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {benchmarks.map(b => (
          <div
            key={b.evidence_id}
            className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition"
          >
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 text-[10px] font-mono font-bold bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 rounded">
                    {b.benchmark_id}
                  </span>
                  <span className="text-xs text-slate-400 font-mono">v{b.benchmark_version}</span>
                </div>
                <h3 className="font-mono font-bold text-base text-white mt-1.5">{b.executor_id}</h3>
                <p className="text-xs text-slate-400">Model: {b.model_id} ({b.provider_id})</p>
              </div>

              <span className="text-[11px] font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded">
                {b.source}
              </span>
            </div>

            {/* Metrics Grid */}
            <div className="mt-4 grid grid-cols-2 gap-2">
              {b.metrics.map((m, idx) => (
                <div key={idx} className="p-2.5 bg-slate-950/70 border border-slate-800/80 rounded-lg">
                  <span className="text-[10px] text-slate-500 uppercase font-mono block">
                    {m.name.replace(/_/g, ' ')}
                  </span>
                  <div className="flex items-baseline gap-1 mt-0.5">
                    <span className="text-base font-bold font-mono text-cyan-300">
                      {m.unit === 'ratio'
                        ? `${(m.value * 100).toFixed(1)}%`
                        : m.unit === 'usd'
                        ? `$${m.value.toFixed(2)}`
                        : m.value}
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono">{m.unit}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* Evidence Metadata */}
            <div className="mt-4 pt-3 border-t border-slate-800/80 space-y-1.5 text-xs text-slate-400 font-mono">
              <div className="flex justify-between">
                <span className="text-slate-500">Harness:</span>
                <span className="text-slate-300">{b.harness_id} (v{b.harness_version})</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Task Set:</span>
                <span className="text-slate-300">{b.task_set}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Raw Ref:</span>
                <span className="text-cyan-400 truncate max-w-[180px]">{b.raw_result_ref}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="p-4 bg-slate-900/40 border border-slate-800/60 rounded-xl text-xs text-slate-400 flex items-start gap-3">
        <Database className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold text-slate-300">Empirical Selection Rule: </span>
          Per <code className="text-cyan-400">docs/EMPIRICAL-EVIDENCE-AND-REPRODUCIBILITY.md</code>, benchmark evidence may inform runtime strategy scoring only. It never bypasses capability eligibility, health/quarantine, or independent acceptance verifications.
        </div>
      </div>
    </div>
  );
};
