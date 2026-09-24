import { useState } from 'react';

const QUESTIONS = [
  { id: 'at_risk', label: 'Which clients are at risk and why?' },
  { id: 'farm_gaps', label: 'Which farm/segment gaps matter most today?' },
  { id: 'local_market', label: 'Why are apples going local, and what is their value?' },
];

// Deterministic, server-data-only fallback. Used whenever no LLM key/endpoint
// is configured, or the call fails — never fabricates a number or an ID.
function deterministicAnswer(questionId, plan) {
  const { client_statuses = {}, allocations = [], local_residual = [] } = plan;

  if (questionId === 'at_risk') {
    const atRisk = Object.entries(client_statuses).filter(([, s]) => s.status !== 'COMPLETE');
    if (atRisk.length === 0) return { text: 'No clients are at risk today — every order is COMPLETE.', ids: [] };
    const lines = atRisk.map(([cid, s]) =>
      `${cid}: ${s.status}, ${s.allocated_t}/${s.demand_t} t allocated (${s.reason || 'no reason recorded'})`
    );
    return { text: lines.join('\n'), ids: atRisk.map(([cid]) => cid) };
  }

  if (questionId === 'farm_gaps') {
    const bySeg = {};
    local_residual.forEach(r => { bySeg[r.segment] = (bySeg[r.segment] || 0) + Number(r.remaining_tonnes); });
    const worstFarms = [...local_residual].sort((a, b) => b.remaining_tonnes - a.remaining_tonnes).slice(0, 3);
    const text = worstFarms.length
      ? `Largest unexported balances: ${worstFarms.map(f => `${f.farm_id} (${f.segment}, ${f.remaining_tonnes} t)`).join(', ')}.`
      : 'No farm currently has unexported balance.';
    return { text, ids: worstFarms.map(f => f.farm_id) };
  }

  if (questionId === 'local_market') {
    const totalVol = local_residual.reduce((s, r) => s + Number(r.remaining_tonnes), 0);
    const totalVal = local_residual.reduce((s, r) => s + Number(r.local_value_eur), 0);
    const farmIds = local_residual.map(r => r.farm_id);
    return {
      text: `${totalVol} t are going to the local market at 10% of reference price, worth €${totalVal.toLocaleString()}. Source farms: ${farmIds.join(', ') || 'none'}.`,
      ids: farmIds,
    };
  }

  return { text: 'Unavailable — this question is not covered by the computed plan.', ids: [] };
}

export default function AssistantPanel({ plan }) {
  const [answer, setAnswer] = useState(null);
  const [activeQ, setActiveQ] = useState(null);
  const [mode, setMode] = useState(null); // 'llm' | 'deterministic' | 'error'

  async function ask(q) {
    setActiveQ(q.id);
    setAnswer(null);

    // Try a real backend assistant endpoint first (wire this to your LLM route).
    // Sends only the minimal structured context, never raw sheets.
    try {
      const res = await fetch('/api/assistant', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: q.id,
          client_statuses: plan.client_statuses,
          local_residual: plan.local_residual,
          kpis: plan.kpis,
        }),
      });
      if (res.status === 501 || res.status === 424) {
        // convention: backend returns this when no key/model is configured
        throw new Error('NO_KEY');
      }
      if (!res.ok) throw new Error('REQUEST_FAILED');
      const data = await res.json();
      setMode('llm');
      setAnswer({ text: data.answer, ids: data.evidence_ids || [] });
    } catch (e) {
      // Honest fallback — never show a fake AI answer.
      const fallback = deterministicAnswer(q.id, plan);
      setMode('deterministic');
      setAnswer(fallback);
    }
  }

  return (
    <div className="card">
      <div className="card-header">
        <h2>Ask about this plan</h2>
        <p>Explains the plan already computed above. It cannot recalculate or change allocations.</p>
      </div>
      <div className="card-body" style={{ paddingBottom: 18 }}>
        <div className="assistant-q">
          {QUESTIONS.map(q => (
            <button key={q.id} onClick={() => ask(q)} disabled={activeQ === q.id && !answer}>
              {q.label}
            </button>
          ))}
        </div>

        {activeQ && !answer && <p>Thinking…</p>}

        {answer && (
          <div className={`assistant-answer ${mode === 'deterministic' ? 'no-key' : ''}`}>
            {mode === 'deterministic' && (
              <p style={{ margin: '0 0 8px', fontWeight: 600 }}>
                No AI model configured — showing a deterministic summary from the computed plan.
              </p>
            )}
            <p style={{ whiteSpace: 'pre-line', margin: 0 }}>{answer.text}</p>
            {answer.ids.length > 0 && (
              <p style={{ marginTop: 10 }}>
                Evidence: {answer.ids.map(id => <span key={id} className="evidence-id" style={{ marginRight: 6 }}>{id}</span>)}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}