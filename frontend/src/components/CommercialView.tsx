// Expects clients: [{ client_id, name, acceptance_mode, requested_segment,
//                      demand_t, export_price_per_t_eur }]
// statuses: { [client_id]: { status, demand_t, allocated_t, remaining_demand_t, reason } }
const REASON_LABEL = {
  STATION_CAPACITY_REACHED: 'Station capacity reached',
  INSUFFICIENT_COMPATIBLE_SEGMENT: 'Not enough compatible fruit left',
};

const BADGE_CLASS = {
  COMPLETE: 'badge-complete',
  PARTIAL: 'badge-partial',
  UNSERVED: 'badge-unserved',
};

export default function CommercialView({ clients, statuses }) {
  return (
    <div className="card">
      <div className="card-header">
        <h2>Clients — orders and service status</h2>
        <p>Processed by export price, highest first. Every partial or unserved order has a stated reason.</p>
      </div>
      <div className="card-body">
        <table>
          <thead>
            <tr>
              <th>Client</th>
              <th>Rule</th>
              <th>Demand</th>
              <th>Allocated</th>
              <th>Remaining</th>
              <th>Price/t</th>
              <th>Revenue</th>
              <th>Status</th>
              <th>Reason</th>
            </tr>
          </thead>
          <tbody>
            {clients.map(c => {
              const st = statuses[c.client_id] || {};
              return (
                <tr key={c.client_id}>
                  <td><strong>{c.client_id}</strong>{c.name ? ` — ${c.name}` : ''}</td>
                  <td><span className={`seg-dot seg-${c.requested_segment}`} />{c.acceptance_mode} {c.requested_segment}</td>
                  <td className="num">{Number(st.demand_t ?? c.demand_t)} t</td>
                  <td className="num">{Number(st.allocated_t ?? 0)} t</td>
                  <td className="num">{Number(st.remaining_demand_t ?? 0)} t</td>
                  <td className="num">€{Number(c.export_price_per_t_eur).toLocaleString()}</td>
                  <td className="num">€{Number(st.revenue_eur || 0).toLocaleString()}</td>
                  <td><span className={`badge ${BADGE_CLASS[st.status] || ''}`}>{st.status}</span></td>
                  <td>{st.reason ? REASON_LABEL[st.reason] || st.reason : '—'}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
