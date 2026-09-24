import pandas as pd

from app.engine.allocation import run_allocation_engine


def plan(farms, clients, capacity=100):
    return run_allocation_engine(
        pd.DataFrame(farms), pd.DataFrame(clients),
        pd.DataFrame([{'export_conditioning_capacity_t': capacity, 'local_market_ratio': 0.1}]),
        {'A': 1500, 'B': 1250, 'C': 1000, 'D': 750},
    )


def farm(fid, a=0, b=0, c=0, d=0):
    return {'farm_id': fid, 'expected_daily_capacity_t': a+b+c+d,
            'actual_A_t': a, 'actual_B_t': b, 'actual_C_t': c, 'actual_D_t': d}


def client(cid, mode, segment, demand, price):
    return {'client_id': cid, 'acceptance_mode': mode, 'requested_segment': segment,
            'demand_t': demand, 'export_price_per_t_eur': price}


def test_orders_by_price_then_client_id():
    result = plan([farm('F02', b=15), farm('F01', b=15)], [
        client('C03', 'EXACT', 'B', 10, 1100),
        client('C02', 'EXACT', 'B', 10, 1200),
        client('C01', 'EXACT', 'B', 10, 1200),
    ])
    assert [(a['client_id'], a['farm_id'], a['tonnes']) for a in result['allocations']] == [
        ('C01', 'F01', 10), ('C02', 'F01', 5), ('C02', 'F02', 5), ('C03', 'F02', 10)
    ]


def test_exact_and_minimum_prefer_smallest_upgrade():
    result = plan([farm('F02', a=10, b=10), farm('F01', a=10, c=10)], [
        client('C01', 'EXACT', 'B', 10, 1300),
        client('C02', 'MINIMUM', 'C', 25, 1200),
    ])
    assert [(a['client_id'], a['segment'], a['farm_id'], a['quality_upgrade'])
            for a in result['allocations']] == [
        ('C01', 'B', 'F02', 0), ('C02', 'C', 'F01', 0),
        ('C02', 'A', 'F01', 2), ('C02', 'A', 'F02', 2),
    ]
    assert result['client_statuses']['C02']['status'] == 'COMPLETE'


def test_station_limit_causes_partial_and_local_residual():
    result = plan([farm('F01', b=30)], [
        client('C01', 'EXACT', 'B', 30, 1100)
    ], capacity=20)
    assert result['client_statuses']['C01']['status'] == 'PARTIAL'
    assert result['client_statuses']['C01']['reason'] == 'STATION_CAPACITY_REACHED'
    assert result['kpis']['exported_t'] == 20
    assert result['local_residual'] == [{
        'farm_id': 'F01', 'segment': 'B', 'remaining_tonnes': 10, 'local_value_eur': 1250
    }]
