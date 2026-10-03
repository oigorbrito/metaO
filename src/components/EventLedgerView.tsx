import React, { useState, useMemo } from 'react';
import { Terminal } from 'lucide-react';
import { MissionEvent } from '../types/metao';

interface Props {
  events: MissionEvent[];
}

/**
 * Memoized subcomponent for rendering individual event log entries.
 * Prevents redundant JSON serialization and DOM updates when filtering or parent re-rendering.
 */
const EventItem = React.memo<{ event: MissionEvent }>(({ event }) => {
  // Memoize formatted JSON payload to avoid expensive stringification on every render.
  const formattedPayload = useMemo(
    () => JSON.stringify(event.data, null, 2),
    [event.data]
  );

  return (
    <div className="p-4 hover:bg-slate-800/30 transition text-xs font-mono">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 mb-1.5">
        <div className="flex items-center gap-2">
          <span
            className={`px-2 py-0.5 text-[10px] font-bold rounded ${
              event.kind.includes('ACCEPTED') || event.kind.includes('PASSED')
                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                : event.kind.includes('BLOCKED') || event.kind.includes('DENIED') || event.kind.includes('FAILED')
                ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                : event.kind.includes('APPROVAL')
                ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                : 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'
            }`}
          >
            {event.kind}
          </span>
          <span className="text-slate-300 font-semibold">{event.mission_id}</span>
        </div>
        <span className="text-slate-500 text-[11px]">
          {new Date(event.timestamp).toLocaleTimeString()}
        </span>
      </div>

      <div className="p-2 rounded bg-slate-950/80 border border-slate-800/60 text-slate-400 overflow-x-auto text-[11px]">
        <pre>{formattedPayload}</pre>
      </div>
    </div>
  );
});

EventItem.displayName = 'EventItem';

export const EventLedgerView: React.FC<Props> = ({ events }) => {
  const [filter, setFilter] = useState('');

  // Performance optimization:
  // 1. Memoize filtered results to prevent re-filtering on unrelated parent/component re-renders.
  // 2. Compute search term lowercasing once outside the loop instead of twice per item inside the filter.
  const filtered = useMemo(() => {
    const trimmed = filter.trim();
    if (!trimmed) return events;

    const term = trimmed.toLowerCase();
    return events.filter(
      e =>
        e.mission_id.toLowerCase().includes(term) ||
        e.kind.toLowerCase().includes(term)
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
            filtered.map(e => <EventItem key={e.event_id} event={e} />)
          )}
        </div>
      </div>
    </div>
  );
};
