def build_supply_pool(farms_df):
    supply = {}
    for _, row in farms_df.iterrows():
        fid = str(row['farm_id']).strip()
        for seg in ['A', 'B', 'C', 'D']:
            supply[(fid, seg)] = float(row[f'actual_{seg}_t'])
    return supply


def sort_clients(clients):
    # Ensure export_price_per_t_eur is numeric for proper sorting
    clients_sorted = clients.copy()
    clients_sorted['export_price_per_t_eur'] = clients_sorted['export_price_per_t_eur'].astype(float)
    
    # Sort by price descending, then client_id ascending
    clients_sorted = clients_sorted.sort_values(
        by=['export_price_per_t_eur', 'client_id'],
        ascending=[False, True]
    )
    return clients_sorted

def allocate_clients(sorted_clients, supply, station_capacity=500.0):
    seg_ranks = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
    station_capacity_remaining = float(station_capacity)
    
    allocations = []
    client_statuses = {}

    for _, client in sorted_clients.iterrows():
        cid = str(client['client_id']).strip()
        mode = str(client['acceptance_mode']).strip()
        req_seg = str(client['requested_segment']).strip()
        demand = float(client['demand_t'])
        price = float(client['export_price_per_t_eur'])
        
        remaining_demand = demand
        req_rank = seg_ranks[req_seg]

        # 1. Find compatible candidates
        candidates = []
        for (fid, seg), tonnes in supply.items():
            if tonnes <= 0:
                continue
            
            seg_rank = seg_ranks[seg]
            
            # Compatibility check
            if mode == 'EXACT' and seg != req_seg:
                continue
            elif mode == 'MINIMUM' and seg_rank > req_rank:  # Worse quality rejected
                continue

            # Quality upgrade distance (0 = exact match)
            upgrade = req_rank - seg_rank
            candidates.append({
                'farm_id': fid,
                'segment': seg,
                'upgrade': upgrade
            })

        # 2. Sort candidates: lowest upgrade first, then farm_id
        candidates.sort(key=lambda x: (x['upgrade'], x['farm_id']))

        # 3. Walk list and allocate
        for cand in candidates:
            if remaining_demand <= 0 or station_capacity_remaining <= 0:
                break

            fid = cand['farm_id']
            seg = cand['segment']
            avail = supply[(fid, seg)]

            # Take as much as possible up to demand, stock availability, or station cap
            alloc_tonnes = min(remaining_demand, avail, station_capacity_remaining)
            
            if alloc_tonnes > 0:
                allocations.append({
                    'farm_id': fid,
                    'segment': seg,
                    'client_id': cid,
                    'tonnes': alloc_tonnes,
                    'quality_upgrade': cand['upgrade'],
                    'revenue': alloc_tonnes * price
                })

                # Deduct from supply and counters
                supply[(fid, seg)] -= alloc_tonnes
                remaining_demand -= alloc_tonnes
                station_capacity_remaining -= alloc_tonnes

        # 4. Set final status and reason
        if remaining_demand == 0:
            status = 'COMPLETE'
            reason = None
        elif remaining_demand < demand and remaining_demand > 0:
            status = 'PARTIAL'
            reason = 'STATION_CAPACITY_REACHED' if station_capacity_remaining == 0 else 'INSUFFICIENT_COMPATIBLE_SEGMENT'
        else:
            status = 'UNSERVED'
            reason = 'STATION_CAPACITY_REACHED' if station_capacity_remaining == 0 else 'INSUFFICIENT_COMPATIBLE_SEGMENT'

        client_statuses[cid] = {
            'status': status,
            'demand_t': demand,
            'allocated_t': demand - remaining_demand,
            'remaining_demand_t': remaining_demand,
            'reason': reason
        }

    return allocations, client_statuses, station_capacity_remaining


import pandas as pd

def calculate_local_market(supply, ref_prices, local_ratio=0.10):
    local_residual = []
    total_local_volume = 0.0
    total_local_value = 0.0

    for (fid, seg), tonnes_left in supply.items():
        if tonnes_left > 0:
            value = tonnes_left * local_ratio * ref_prices[seg]
            local_residual.append({
                'farm_id': fid,
                'segment': seg,
                'remaining_tonnes': tonnes_left,
                'local_value_eur': value
            })
            total_local_volume += tonnes_left
            total_local_value += value

    return local_residual, total_local_volume, total_local_value