import { useState } from 'react';
import KpiBand from './components/KpiBand';
import ProductionView from './components/ProductionView';
import CommercialView from './components/CommercialView';
import AllocationTable from './components/AllocationTable';
import AssistantPanel from './components/AssistantPanel';

const API_URL = '/api/plan/seed';
const TABS = ['Overview', 'Production', 'Commercial', 'Allocations', 'Assistant'];

export default function App() {
  const [status, setStatus] = useState('empty'); // empty | loading | ready | error
  const [plan, setPlan] = useState(null);
  const [farms, setFarms] = useState([]);
  const [clients, setClients] = useState([]);
  const [errorMsg, setErrorMsg] = useState('');
  const [tab, setTab] = useState('Overview');

  async function loadSeed() {
    setStatus('loading');
    setErrorMsg('');
    try {
      // Assumes a preloaded seed file on the server. If you require an
      // upload instead, swap this for a <input type="file"> + FormData post.
      const res = await fetch(API_URL, { method: 'POST' });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Server error (${res.status})`);
      }
      const data = await res.json();
      setPlan(data);
      setFarms(data.farms || []);
      setClients(data.clients || []);
      setStatus('ready');
    } catch (e) {
      setErrorMsg(e.message || 'Something went wrong loading the plan.');
      setStatus('error');
    }
  }

  return (
    <div>
      <div className="topbar">
        <div className="app-shell" style={{ padding: 0 }}>
          <h1>Atlas Fresh — Daily Export Planner</h1>
          <p>Production × Commercial decision support. Fictional data.</p>
        </div>
      </div>

      <div className="app-shell">
        {status === 'empty' && (
          <div className="state-box">
            <p>No plan loaded yet.</p>
            <button onClick={loadSeed}>Load today's snapshot</button>
          </div>
        )}

        {status === 'loading' && (
          <div className="state-box"><p>Loading and validating today's data…</p></div>
        )}

        {status === 'error' && (
          <div className="state-box error">
            <p><strong>Could not build the plan.</strong></p>
            <p>{errorMsg}</p>
            <button onClick={loadSeed}>Retry</button>
          </div>
        )}

        {status === 'ready' && plan && (
          <>
            <KpiBand plan={plan} />

            <div className="tabs">
              {TABS.map(t => (
                <button key={t} className={`tab ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>
                  {t}
                </button>
              ))}
            </div>

            {tab === 'Overview' && (
              <div className="card">
                <div className="card-header">
                  <h2>Today in one minute</h2>
                  <p>Production planned {plan.kpis.expected_plan_t} t and received {plan.kpis.actual_received_t} t. The station exported {plan.kpis.exported_t} t out of {plan.kpis.station_capacity_t} t capacity.</p>
                </div>
                <div className="card-body" style={{ paddingBottom: 16 }}>
                  <p>
                    Overall variance against the farm plan is {plan.kpis.actual_received_t - plan.kpis.expected_plan_t} t. The export station processed {plan.kpis.exported_t} t,
                    and every partial or unserved client has a stated reason in the
                    Commercial tab. What could not be exported is shown, farm by farm, on the
                    Allocations tab — that fruit sells for only {((plan.kpis.local_market_ratio ?? 0.1) * 100).toLocaleString()}% of its reference price.
                  </p>
                </div>
              </div>
            )}

            {tab === 'Production' && (
              <ProductionView farms={farms} localResidual={plan.local_residual} />
            )}

            {tab === 'Commercial' && (
              <CommercialView clients={clients} statuses={plan.client_statuses} />
            )}

            {tab === 'Allocations' && (
              <AllocationTable allocations={plan.allocations} localResidual={plan.local_residual} />
            )}

            {tab === 'Assistant' && (
              <AssistantPanel plan={plan} />
            )}
          </>
        )}
      </div>
    </div>
  );
}
