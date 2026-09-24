// Expects farms: [{ farm_id, expected_daily_capacity_t, expected_A_pct.. D_pct,
//                    actual_A_t.. D_t, residual_A_t.. D_t (optional) }]
export default function ProductionView({ farms, localResidual = [] }) {
  const residualByFarm = {};
  localResidual.forEach(r => {
    residualByFarm[r.farm_id] = residualByFarm[r.farm_id] || {};
    residualByFarm[r.farm_id][r.segment] = r.remaining_tonnes;
  });

  const seg = ['A', 'B', 'C', 'D'];

  return (
    <div className="card">
      <div className="card-header">
        <h2>Farms — plan vs actual</h2>
        <p>Expected daily capacity and A/B/C/D mix against today's real receipts. Red = below plan.</p>
      </div>
      <div className="card-body">
        <table>
          <thead>
            <tr>
              <th>Farm</th>
              <th>Expected</th>
              {seg.map(s => <th key={s}><span className={`seg-dot seg-${s}`} />{s} actual</th>)}
              <th>Total actual</th>
              <th>Variance</th>
              <th>To local market</th>
            </tr>
          </thead>
          <tbody>
            {farms.map(f => {
              const expected = Number(f.expected_daily_capacity_t);
              const actualTotal = seg.reduce((sum, s) => sum + Number(f[`actual_${s}_t`] || 0), 0);
              const variance = actualTotal - expected;
              const localTotal = seg.reduce((sum, s) => sum + Number(residualByFarm[f.farm_id]?.[s] || 0), 0);
              return (
                <tr key={f.farm_id}>
                  <td><strong>{f.farm_id}</strong></td>
                  <td className="num">{expected.toFixed(1)} t</td>
                  {seg.map(s => (
                    <td key={s} className="num">{Number(f[`actual_${s}_t`] || 0)} t</td>
                  ))}
                  <td className="num"><strong>{actualTotal} t</strong></td>
                  <td className={`num ${variance < 0 ? 'variance-neg' : 'variance-pos'}`}>
                    {variance >= 0 ? '+' : ''}{variance.toFixed(1)} t
                  </td>
                  <td className="num">{localTotal > 0 ? `${localTotal} t` : '—'}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}