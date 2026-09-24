from pathlib import Path
from collections import defaultdict
from io import BytesIO

import openpyxl
from fastapi.testclient import TestClient
from app.main import app

from app.engine.allocation import run_allocation_engine
from app.engine.validators import validate_data, read_and_validate_reference_prices

SEED = Path(__file__).resolve().parents[1] / 'app' / 'data' / 'seed.xlsx'


def test_baseline_and_all_allocation_invariants():
    farms, clients, station = validate_data(SEED)
    result = run_allocation_engine(farms, clients, station, read_and_validate_reference_prices(SEED))
    kpis = result['kpis']
    assert (kpis['expected_plan_t'], kpis['actual_received_t'], kpis['exported_t'],
            kpis['local_residual_volume_t']) == (600, 560, 500, 60)
    assert round(kpis['export_rate_pct'], 1) == 89.3
    assert (kpis['export_revenue_eur'], kpis['local_residual_value_eur']) == (549500, 4500)
    assert sum(v['status'] != 'COMPLETE' for v in result['client_statuses'].values()) == 3
    for cid, reason in [('C02', 'INSUFFICIENT_COMPATIBLE_SEGMENT'),
                        ('C09', 'INSUFFICIENT_COMPATIBLE_SEGMENT'),
                        ('C08', 'STATION_CAPACITY_REACHED')]:
        assert result['client_statuses'][cid]['status'] == 'PARTIAL'
        assert result['client_statuses'][cid]['reason'] == reason

    by_farm = defaultdict(float)
    by_client = defaultdict(float)
    client_rows = {r['client_id']: r for _, r in clients.iterrows()}
    for row in result['allocations']:
        by_farm[(row['farm_id'], row['segment'])] += row['tonnes']
        by_client[row['client_id']] += row['tonnes']
        order = 'ABCD'
        client = client_rows[row['client_id']]
        assert row['tonnes'] > 0 and row['tonnes'] % 5 == 0
        assert (row['segment'] == client['requested_segment'] if client['acceptance_mode'] == 'EXACT'
                else order.index(row['segment']) <= order.index(client['requested_segment']))
    for _, farm in farms.iterrows():
        for segment in 'ABCD':
            assert by_farm[(farm['farm_id'], segment)] <= farm[f'actual_{segment}_t']
    for _, client in clients.iterrows():
        assert by_client[client['client_id']] <= client['demand_t']
    assert kpis['exported_t'] <= kpis['station_capacity_t']
    assert kpis['exported_t'] + kpis['local_residual_volume_t'] == kpis['actual_received_t']


def test_valid_input_change_recomputes_values():
    farms, clients, station = validate_data(SEED)
    prices = read_and_validate_reference_prices(SEED)
    farms = farms.copy()
    farms.loc[farms['farm_id'] == 'F01', 'actual_D_t'] += 5
    changed = run_allocation_engine(farms, clients, station, prices)['kpis']
    assert (changed['actual_received_t'], changed['local_residual_volume_t']) == (565, 65)


def test_uploaded_modified_workbook_is_recomputed():
    workbook = openpyxl.load_workbook(SEED)
    workbook['Farms']['K5'] = 5  # F01 Segment D receives 5 additional tonnes.
    data = BytesIO()
    workbook.save(data)
    result = TestClient(app).post('/api/plan', files={
        'file': ('changed.xlsx', data.getvalue(),
                 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    })
    assert result.status_code == 200, result.text
    assert result.json()['kpis']['actual_received_t'] == 565
