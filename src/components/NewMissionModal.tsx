import React, { useState } from 'react';
import { X, Play, ShieldAlert } from 'lucide-react';

export const NewMissionModal: React.FC<{
  onClose: () => void;
  onSubmit: (intent: any) => Promise<void>;
}> = ({ onClose, onSubmit }) => {
  const [objective, setObjective] = useState('');
  const [caps, setCaps] = useState('workflow');
  const [family, setFamily] = useState('standard_workflow');
  const [money, setMoney] = useState(1);
  const [tokens, setTokens] = useState(2000);
  const [wall, setWall] = useState(60);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await onSubmit({
        mission: {
          objective,
          required_capabilities: caps
            .split(',')
            .map(x => x.trim())
            .filter(Boolean),
          task_family: family || undefined,
        },
        budget: {
          money_limit: Number(money),
          token_limit: Number(tokens),
          wall_time_limit_s: Number(wall),
        },
      });
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to submit mission intent');
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="new-mission-title"
        className="bg-slate-900 border border-slate-800 rounded-xl max-w-xl w-full shadow-2xl overflow-hidden"
      >
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <div>
            <h3 id="new-mission-title" className="font-bold text-slate-100">
              Custom Mission Intent
            </h3>
            <p className="text-xs text-slate-400">
              Intent only; governance remains backend-owned.
            </p>
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

        <form onSubmit={submit} className="p-5 space-y-4 text-xs">
          <div className="p-3 bg-amber-500/5 border border-amber-500/20 rounded-lg flex items-center gap-2 text-amber-200">
            <ShieldAlert className="w-4 h-4 shrink-0" />
            <span>
              This form cannot declare policy approval, trusted verifiers, authorized authorities or acceptance decisions.
            </span>
          </div>

          {error && (
            <div className="p-3 bg-rose-950/40 border border-rose-900 rounded-lg text-rose-300">
              {error}
            </div>
          )}

          <div>
            <label htmlFor="mission-objective" className="block font-semibold text-slate-300 mb-1">
              Objective <span className="text-rose-400">*</span>
            </label>
            <input
              id="mission-objective"
              required
              value={objective}
              onChange={e => setObjective(e.target.value)}
              className="w-full p-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500"
            />
          </div>

          <div>
            <label htmlFor="mission-caps" className="block font-semibold text-slate-300 mb-1">
              Capabilities (comma-separated)
            </label>
            <input
              id="mission-caps"
              value={caps}
              onChange={e => setCaps(e.target.value)}
              className="w-full p-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500"
            />
          </div>

          <div>
            <label htmlFor="mission-family" className="block font-semibold text-slate-300 mb-1">
              Task family
            </label>
            <input
              id="mission-family"
              value={family}
              onChange={e => setFamily(e.target.value)}
              className="w-full p-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500"
            />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label htmlFor="mission-money" className="block font-semibold text-slate-300 mb-1">
                Money limit
              </label>
              <input
                id="mission-money"
                type="number"
                value={money}
                onChange={e => setMoney(Number(e.target.value))}
                className="w-full p-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500"
              />
            </div>
            <div>
              <label htmlFor="mission-tokens" className="block font-semibold text-slate-300 mb-1">
                Token limit
              </label>
              <input
                id="mission-tokens"
                type="number"
                value={tokens}
                onChange={e => setTokens(Number(e.target.value))}
                className="w-full p-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500"
              />
            </div>
            <div>
              <label htmlFor="mission-wall" className="block font-semibold text-slate-300 mb-1">
                Wall time (s)
              </label>
              <input
                id="mission-wall"
                type="number"
                value={wall}
                onChange={e => setWall(Number(e.target.value))}
                className="w-full p-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full p-2.5 bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/30 rounded-lg text-indigo-300 flex justify-center items-center gap-2 font-semibold transition cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Play className={`w-4 h-4 fill-indigo-300 ${submitting ? 'animate-spin' : ''}`} />
            <span>{submitting ? 'Submitting...' : 'Submit intent'}</span>
          </button>
        </form>
      </div>
    </div>
  );
};
