import React, { useState, useMemo } from 'react';
import { ListFilter, Terminal, Clock, ShieldCheck, Activity } from 'lucide-react';
import { MissionEvent } from '../types/metao';

interface Props {
  events: MissionEvent[];
}

export const EventLedgerView: React.FC<Props> = ({ events }) => {
  const [filter, setFilter] = useState('');

  // Performance optimization: Memoize filtering and normalize filter query string once per search update
  // to avoid O(N) string lowercasing operations on every render when parent components re-render.
  const filtered = useMemo(() => {
    if (!filter.trim()) return events;
    const lowerFilter = filter.toLowerCase();
    return events.filter(
      e =>
        e.mission_id.toLowerCase().includes(lowerFilter) ||
        e.kind.toLowerCase().includes(lowerFilter)
    );
  }, [events, filter]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white">Event Ledger & Observability</h2>
          <p className="text-sm text-slate-400">
            Immutable SQLite event audit trail tracking mission creation, policy gates, dispatch, and acceptance proofs.
          </p>
        </div>
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <input
            type="text"
            placeholder="Filter events..."
            value={filter}
            onChange={e => setFilter(e.target.value)}
            className="w-full sm:w-64 bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
          />
        </div>
      </div>

      <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden">
        <div className="p-3 bg-slate-950/60 border-b border-slate-800 flex items-center justify-between text-xs font-mono text-slate-400">
          <div className="flex items-center gap-2">
            <Terminal className="w-3.5 h-3.5 text-cyan-400" />
            <span>metao events &lt;mission_id&gt;</span>
          </div>
          <span>{filtered.length} events</span>
        </div>

        <div className="divide-y divide-slate-800/60 max-h-[600px] overflow-y-auto">
          {filtered.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-500">
              No matching events recorded in ledger.
            </div>
          ) : (
            filtered.map(e => (
              <div key={e.event_id} className="p-4 hover:bg-slate-800/30 transition text-xs font-mono">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 mb-1.5">
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-2 py-0.5 text-[10px] font-bold rounded ${
                        e.kind.includes('ACCEPTED') || e.kind.includes('PASSED')
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          : e.kind.includes('BLOCKED') || e.kind.includes('DENIED') || e.kind.includes('FAILED')
                          ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                          : e.kind.includes('APPROVAL')
                          ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                          : 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'
                      }`}
                    >
                      {e.kind}
                    </span>
                    <span className="text-slate-300 font-semibold">{e.mission_id}</span>
                  </div>
                  <span className="text-slate-500 text-[11px]">
                    {new Date(e.timestamp).toLocaleTimeString()}
                  </span>
                </div>

                <div className="p-2 rounded bg-slate-950/80 border border-slate-800/60 text-slate-400 overflow-x-auto text-[11px]">
                  <pre>{JSON.stringify(e.data, null, 2)}</pre>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
