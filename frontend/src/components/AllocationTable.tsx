export default function AllocationTable({ allocations, localResidual = [] }) {
  return (
    <>
      <div className="card">
        <div className="card-header">
          <h2>Allocation detail</h2>
          <p>Every exported tonne traced to one farm, segment and client.</p>
        </div>
        <div className="card-body">
          <table>
            <thead>
              <tr>
                <th>Farm</th>
                <th>Segment</th>
                <th>Client</th>
                <th>Tonnes</th>
                <th>Quality upgrade</th>
                <th>Revenue</th>
              </tr>
            </thead>
            <tbody>
              {allocations.map((a, i) => (
                <tr key={i}>
                  <td>{a.farm_id}</td>
                  <td><span className={`seg-dot seg-${a.segment}`} />{a.segment}</td>
                  <td>{a.client_id}</td>
                  <td className="num">{a.tonnes} t</td>
                  <td className="num">{a.quality_upgrade === 0 ? 'exact match' : `+${a.quality_upgrade}`}</td>
                  <td className="num">€{Number(a.revenue_eur ?? a.revenue).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h2>Local market residual</h2>
          <p>Every tonne not exported, at 10% of its segment's reference price.</p>
        </div>
        <div className="card-body">
          <table>
            <thead>
              <tr><th>Farm</th><th>Segment</th><th>Tonnes</th><th>Local value</th></tr>
            </thead>
            <tbody>
              {localResidual.map((r, i) => (
                <tr key={i}>
                  <td>{r.farm_id}</td>
                  <td><span className={`seg-dot seg-${r.segment}`} />{r.segment}</td>
                  <td className="num">{r.remaining_tonnes} t</td>
                  <td className="num">€{Number(r.local_value_eur).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}