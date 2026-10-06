import React, { useState, useEffect } from 'react';
import { X, Play, ShieldAlert, Loader2 } from 'lucide-react';

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

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await onSubmit({
        mission: {
          objective,
          required_capabilities: caps.split(',').map(x => x.trim()).filter(Boolean),
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
    } finally {
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
        <div className="p-5 border-b border-slate-800 flex justify-between items-center">
          <div>
            <h3 id="new-mission-title" className="font-bold text-white">Custom Mission Intent</h3>
            <p className="text-xs text-slate-400">Intent only; governance remains backend-owned.</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close dialog"
            className="text-slate-400 hover:text-slate-200 transition p-1 rounded cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={submit} className="p-5 space-y-4 text-xs">
          <div className="p-3 bg-amber-500/5 border border-amber-500/20 rounded flex gap-2 text-amber-200 items-start">
            <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5" />
            <span>This form cannot declare policy approval, trusted verifiers, authorized authorities or acceptance decisions.</span>
          </div>

          {error && (
            <div className="p-3 bg-rose-950/40 border border-rose-900 rounded text-rose-300">
              {error}
            </div>
          )}

          <div>
            <label htmlFor="mission-objective" className="block text-slate-300 font-medium mb-1">
              Objective <span className="text-rose-400">*</span>
            </label>
            <input
              id="mission-objective"
              required
              value={objective}
              onChange={e => setObjective(e.target.value)}
              placeholder="e.g. Execute standard workflow check"
              className="w-full p-2 bg-slate-950 border border-slate-800 rounded text-slate-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
            />
          </div>

          <div>
            <label htmlFor="mission-capabilities" className="block text-slate-300 font-medium mb-1">
              Capabilities (comma separated)
            </label>
            <input
              id="mission-capabilities"
              value={caps}
              onChange={e => setCaps(e.target.value)}
              className="w-full p-2 bg-slate-950 border border-slate-800 rounded text-slate-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
            />
          </div>

          <div>
            <label htmlFor="mission-task-family" className="block text-slate-300 font-medium mb-1">
              Task family
            </label>
            <input
              id="mission-task-family"
              value={family}
              onChange={e => setFamily(e.target.value)}
              className="w-full p-2 bg-slate-950 border border-slate-800 rounded text-slate-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
            />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label htmlFor="mission-money-limit" className="block text-slate-300 font-medium mb-1">
                Money Limit
              </label>
              <input
                id="mission-money-limit"
                type="number"
                value={money}
                onChange={e => setMoney(Number(e.target.value))}
                className="w-full p-2 bg-slate-950 border border-slate-800 rounded text-slate-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
              />
            </div>
            <div>
              <label htmlFor="mission-token-limit" className="block text-slate-300 font-medium mb-1">
                Token Limit
              </label>
              <input
                id="mission-token-limit"
                type="number"
                value={tokens}
                onChange={e => setTokens(Number(e.target.value))}
                className="w-full p-2 bg-slate-950 border border-slate-800 rounded text-slate-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
              />
            </div>
            <div>
              <label htmlFor="mission-wall-time" className="block text-slate-300 font-medium mb-1">
                Wall Time (s)
              </label>
              <input
                id="mission-wall-time"
                type="number"
                value={wall}
                onChange={e => setWall(Number(e.target.value))}
                className="w-full p-2 bg-slate-950 border border-slate-800 rounded text-slate-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full p-2 bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/30 rounded text-indigo-300 font-semibold flex items-center justify-center gap-2 cursor-pointer transition disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
          >
            {submitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Submitting intent...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-indigo-300" />
                <span>Submit intent</span>
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
};
