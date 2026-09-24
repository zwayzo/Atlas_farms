export default function KpiBand({ plan }) {
  const { kpis } = plan;
  const exportRate = kpis.export_rate_pct ?? (kpis.exported_t / kpis.actual_received_t) * 100;
  const atRisk = plan.client_statuses
    ? Object.values(plan.client_statuses).filter(c => c.status !== 'COMPLETE').length
    : 0;

  const fmtT = (v) => `${Number(v).toLocaleString()} t`;
  const fmtEur = (v) => `€${Number(v).toLocaleString()}`;

  return (
    <div className="kpi-band">
      <div className="kpi">
        <div className="kpi-label">Actual received</div>
        <div className="kpi-value num">{fmtT(kpis.actual_received_t ?? kpis.actual_t)}</div>
        <div className="kpi-sub">of {fmtT(kpis.expected_plan_t ?? kpis.expected_t)} planned</div>
      </div>
      <div className="kpi">
        <div className="kpi-label">Exported</div>
        <div className="kpi-value num">{fmtT(kpis.exported_t ?? kpis.station_capacity_t - kpis.station_capacity_remaining_t)}</div>
        <div className="kpi-sub">station cap {fmtT(kpis.station_capacity_t)}</div>
      </div>
      <div className="kpi">
        <div className="kpi-label">Export rate</div>
        <div className="kpi-value num">{exportRate.toFixed(1)}%</div>
      </div>
      <div className="kpi">
        <div className="kpi-label">Export revenue</div>
        <div className="kpi-value num">{fmtEur(kpis.export_revenue_eur)}</div>
      </div>
      <div className="kpi alert">
        <div className="kpi-label">Local market ({fmtT(kpis.local_residual_volume_t)})</div>
        <div className="kpi-value num">{fmtEur(kpis.local_residual_value_eur ?? kpis.local_value_eur)}</div>
        <div className="kpi-sub">{fmtT(kpis.local_residual_volume_t ?? kpis.local_volume_t)} at {((kpis.local_market_ratio ?? 0.1) * 100).toLocaleString()}% of reference price</div>
      </div>
      <div className="kpi">
        <div className="kpi-label">Total value</div>
        <div className="kpi-value num">{fmtEur(kpis.total_value_eur)}</div>
      </div>
      <div className="kpi">
        <div className="kpi-label">At-risk clients</div>
        <div className="kpi-value num">{atRisk}</div>
        <div className="kpi-sub">partial or unserved</div>
      </div>
    </div>
  );
}
