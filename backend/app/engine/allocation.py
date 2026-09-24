import pandas as pd
import numpy as np

def run_allocation_engine(farms_df: pd.DataFrame, clients_df: pd.DataFrame, station_df: pd.DataFrame, ref_prices: dict):
    # 1. Capacité de la station
    station_capacity = float(station_df['export_conditioning_capacity_t'].iloc[0])
    station_capacity_remaining = station_capacity

    # 2. Construction du pool de stock initial
    supply = {}
    for _, row in farms_df.iterrows():
        fid = str(row['farm_id']).strip()
        for seg in ['A', 'B', 'C', 'D']:
            supply[(fid, seg)] = float(row[f'actual_{seg}_t'])

    # 3. Tri des clients par prix décroissant (puis client_id)
    clients_sorted = clients_df.copy()
    clients_sorted['export_price_per_t_eur'] = clients_sorted['export_price_per_t_eur'].astype(float)
    clients_sorted = clients_sorted.sort_values(
        by=['export_price_per_t_eur', 'client_id'],
        ascending=[False, True]
    )

    seg_ranks = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
    allocations = []
    client_statuses = {}

    # 4. Boucle d'allocation commerciale
    for _, client in clients_sorted.iterrows():
        cid = str(client['client_id']).strip()
        mode = str(client['acceptance_mode']).strip()
        req_seg = str(client['requested_segment']).strip()
        demand = float(client['demand_t'])
        price = float(client['export_price_per_t_eur'])

        remaining_demand = demand
        req_rank = seg_ranks[req_seg]

        candidates = []
        for (fid, seg), tonnes in supply.items():
            if tonnes <= 0:
                continue

            seg_rank = seg_ranks[seg]

            if mode == 'EXACT' and seg != req_seg:
                continue
            elif mode == 'MINIMUM' and seg_rank > req_rank:
                continue

            upgrade = req_rank - seg_rank
            candidates.append({
                'farm_id': fid,
                'segment': seg,
                'upgrade': int(upgrade)  # Conversion explicite en int
            })

        candidates.sort(key=lambda x: (x['upgrade'], x['farm_id']))

        for cand in candidates:
            if remaining_demand <= 0 or station_capacity_remaining <= 0:
                break

            fid = cand['farm_id']
            seg = cand['segment']
            avail = supply[(fid, seg)]

            alloc_tonnes = min(remaining_demand, avail, station_capacity_remaining)
            alloc_tonnes = float((alloc_tonnes // 5) * 5)  # Conversion float natif

            if alloc_tonnes > 0:
                allocations.append({
                    'farm_id': str(fid),
                    'segment': str(seg),
                    'client_id': str(cid),
                    'tonnes': float(alloc_tonnes),
                    'quality_upgrade': int(cand['upgrade']),
                    'revenue_eur': float(alloc_tonnes * price)
                })

                supply[(fid, seg)] -= alloc_tonnes
                remaining_demand -= alloc_tonnes
                station_capacity_remaining -= alloc_tonnes

        # Statut du client
        allocated_qty = float(demand - remaining_demand)
        if remaining_demand == 0:
            status = 'COMPLETE'
            reason = None
        elif allocated_qty > 0:
            status = 'PARTIAL'
            reason = 'STATION_CAPACITY_REACHED' if station_capacity_remaining == 0 else 'INSUFFICIENT_COMPATIBLE_SEGMENT'
        else:
            status = 'UNSERVED'
            reason = 'STATION_CAPACITY_REACHED' if station_capacity_remaining == 0 else 'INSUFFICIENT_COMPATIBLE_SEGMENT'

        client_statuses[cid] = {
            'status': str(status),
            'demand_t': float(demand),
            'allocated_t': float(allocated_qty),
            'remaining_demand_t': float(remaining_demand),
            'reason': reason
        }

    # 5. Marché local pour le reliquat non exporté
    # ref_prices = {'A': 150.0, 'B': 100.0, 'C': 75.0, 'D': 50.0}
    local_ratio = float(station_df['local_market_ratio'].iloc[0])
    local_residual = []
    total_local_vol = 0.0
    total_local_val = 0.0

    for (fid, seg), tonnes_left in supply.items():
        if tonnes_left > 0:
            valeur = float(tonnes_left * local_ratio * ref_prices[seg])
            local_residual.append({
                'farm_id': str(fid),
                'segment': str(seg),
                'remaining_tonnes': float(tonnes_left),
                'local_value_eur': valeur
            })
            total_local_vol += float(tonnes_left)
            total_local_val += valeur
        # Expected vs actual totals (needed for the "plan vs actual" KPIs)
    expected_plan_t = float(farms_df['expected_daily_capacity_t'].sum())
    actual_received_t = float(sum(
        float(row[f'actual_{seg}_t'])
        for _, row in farms_df.iterrows()
        for seg in ['A', 'B', 'C', 'D']
    ))
    export_revenue_eur = float(sum(a['revenue_eur'] for a in allocations))
    exported_t = station_capacity - station_capacity_remaining
    export_rate_pct = (exported_t / actual_received_t * 100) if actual_received_t > 0 else 0.0
    return {
        "kpis": {
            "expected_plan_t": expected_plan_t,
            "actual_received_t": actual_received_t,
            "station_capacity_t": float(station_capacity),
            "station_capacity_remaining_t": float(station_capacity_remaining),
            "exported_t": float(exported_t),
            "export_rate_pct": export_rate_pct,
            "export_revenue_eur": export_revenue_eur,
            "local_residual_volume_t": float(total_local_vol),
            "local_residual_value_eur": float(total_local_val),
        },
        "allocations": allocations,
        "client_statuses": client_statuses,
        "local_residual": local_residual
    }