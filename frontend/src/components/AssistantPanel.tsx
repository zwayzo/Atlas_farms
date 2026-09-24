import { useState } from 'react';

const QUESTIONS = [
  { id: 'at_risk', label: 'Which clients are at risk and why?' },
  { id: 'farm_gaps', label: 'Which farm/segment gaps matter most today?' },
  { id: 'local_market', label: 'Why are apples going local, and what is their value?' },
];

// Deterministic, server-data-only fallback. Used whenever no LLM key/endpoint
// is configured, or the call fails — never fabricates a number or an ID.
function deterministicAnswer(questionId, plan) {
  const { client_statuses = {}, local_residual = [], farms = [] } = plan;

  if (questionId === 'at_risk') {
    const atRisk = Object.entries(client_statuses).filter(([, s]) => s.status !== 'COMPLETE');
    if (atRisk.length === 0) return { text: 'No clients are at risk today — every order is COMPLETE.', ids: [] };
    const lines = atRisk.map(([cid, s]) =>
      `${cid}: ${s.status}, ${s.allocated_t}/${s.demand_t} t allocated (${s.reason || 'no reason recorded'})`
    );
    return { text: lines.join('\n'), ids: atRisk.map(([cid]) => cid) };
  }

  if (questionId === 'farm_gaps') {
    const gaps = farms.flatMap(f => 'ABCD'.split('').map(segment => ({
      farm_id: f.farm_id, segment,
      gap: Number(f[`actual_${segment}_t`]) - Number(f.expected_daily_capacity_t) * Number(f[`expected_${segment}_pct`]),
    }))).filter(row => row.gap < 0).sort((a, b) => a.gap - b.gap).slice(0, 3);
    return gaps.length
      ? { text: `Largest farm/segment shortfalls against plan: ${gaps.map(g => `${g.farm_id} Segment ${g.segment} (${g.gap.toFixed(1)} t)`).join(', ')}.`, ids: [...new Set(gaps.map(g => g.farm_id))] }
      : { text: 'No farm/segment shortfalls against plan are recorded.', ids: [] };
  }

  if (questionId === 'local_market') {
    const totalVol = local_residual.reduce((s, r) => s + Number(r.remaining_tonnes), 0);
    const totalVal = local_residual.reduce((s, r) => s + Number(r.local_value_eur), 0);
    const farmIds = local_residual.map(r => r.farm_id);
    return {
      text: `${totalVol} t are going to the local market at ${((plan.kpis.local_market_ratio ?? 0.1) * 100).toLocaleString()}% of reference price, worth €${totalVal.toLocaleString()}. Source farms: ${farmIds.join(', ') || 'none'}.`,
      ids: farmIds,
    };
  }

  return { text: 'Unavailable — this question is not covered by the computed plan.', ids: [] };
}

export default function AssistantPanel({ plan }) {
  const [answer, setAnswer] = useState(null);
  const [activeQ, setActiveQ] = useState(null);
  const [mode, setMode] = useState(null); // 'llm' | 'deterministic' | 'error'
  const [fallbackReason, setFallbackReason] = useState('');

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
          farms: q.id === 'farm_gaps' ? plan.farms : undefined,
          local_residual: plan.local_residual,
          kpis: plan.kpis,
        }),
      });
      if (res.status === 501 || res.status === 424) {
        // convention: backend returns this when no key/model is configured
        throw new Error('NO_KEY');
      }
      if (!res.ok) {
        const errorBody = await res.json().catch(() => ({}));
        if (res.status === 502 && String(errorBody.detail || '').startsWith('MODEL_UNAVAILABLE')) {
          throw new Error('MODEL_UNAVAILABLE');
        }
        throw new Error(res.status === 502 ? 'PROVIDER_FAILURE' : 'REQUEST_FAILED');
      }
      const data = await res.json();
      setMode('llm');
      setAnswer({ text: data.answer, ids: data.evidence_ids || [] });
    } catch (e) {
      // Honest fallback — never show a fake AI answer.
      const fallback = deterministicAnswer(q.id, plan);
      setMode('deterministic');
      setFallbackReason(e.message === 'NO_KEY' ? 'No AI model configured' :
        e.message === 'MODEL_UNAVAILABLE' ? 'Configured Groq model unavailable; check GROQ_MODEL in backend/.env' :
        e.message === 'PROVIDER_FAILURE' ? 'AI provider unavailable or returned invalid output' :
        'Assistant request failed');
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
                {fallbackReason} — showing a deterministic summary from the computed plan.
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
