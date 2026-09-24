import pandas as pd
import numpy as np

def validate_data(file_path: str):
    # --- Helper Functions ---
    def is_multiple_of_5(val):
        if pd.isna(val):
            return False
        try:
            val_float = float(val)
            if val_float < 0:
                return False
            return np.isclose(val_float % 5, 0) or np.isclose(val_float % 5, 5)
        except (ValueError, TypeError):
            return False

    def is_valid_capacity(val):
        if pd.isna(val):
            return False
        try:
            val_float = float(val)
            if val_float < 0:
                return False
            return np.isclose(val_float, round(val_float, 1))
        except (ValueError, TypeError):
            return False

    def find_header_and_read(sheet_name, id_keyword):
        raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None, engine='openpyxl')
        header_row_idx = None
        for i, row in raw.iterrows():
            if id_keyword in " ".join([str(x) for x in row.dropna().values]):
                header_row_idx = i
                break
        if header_row_idx is None:
            raise ValueError(f"Sheet '{sheet_name}': Could not locate header row containing '{id_keyword}'.")
        return pd.read_excel(file_path, sheet_name=sheet_name, header=header_row_idx, engine='openpyxl'), header_row_idx

    # 1. FARMS
    farms_raw, farms_hdr_idx = find_header_and_read('Farms', 'farm_id')
    farms = farms_raw[farms_raw['farm_id'].notna() & farms_raw['farm_id'].astype(str).str.startswith('F')].copy()

    if farms['farm_id'].isna().any():
        raise ValueError("[Farms Sheet]: Missing farm_id detected.")
    if farms['farm_id'].duplicated().any():
        dups = farms[farms['farm_id'].duplicated()]['farm_id'].tolist()
        raise ValueError(f"[Farms Sheet]: Duplicate farm_id found: {dups}")

    for idx, row in farms.iterrows():
        fid = str(row['farm_id']).strip()
        excel_row = idx + farms_hdr_idx + 2

        if not is_valid_capacity(row['expected_daily_capacity_t']):
            raise ValueError(f"[Farms Sheet - Row {excel_row}, ID: {fid}]: Invalid expected capacity.")

        mix_sum = sum([float(row[c]) for c in ['expected_A_pct', 'expected_B_pct', 'expected_C_pct', 'expected_D_pct']])
        if not np.isclose(mix_sum, 1.0):
            raise ValueError(f"[Farms Sheet - Row {excel_row}, ID: {fid}]: Mix percentages sum to {mix_sum:.4f}, must be 1.0.")

        for col in ['actual_A_t', 'actual_B_t', 'actual_C_t', 'actual_D_t']:
            if not is_multiple_of_5(row[col]):
                raise ValueError(f"[Farms Sheet - Row {excel_row}, ID: {fid}]: '{col}' is not a non-negative multiple of 5t.")

    # 2. CLIENTS
    clients_raw, clients_hdr_idx = find_header_and_read('Clients', 'client_id')
    clients = clients_raw[clients_raw['client_id'].notna() & clients_raw['client_id'].astype(str).str.startswith('C')].copy()

    if clients['client_id'].isna().any():
        raise ValueError("[Clients Sheet]: Missing client_id detected.")
    if clients['client_id'].duplicated().any():
        dups = clients[clients['client_id'].duplicated()]['client_id'].tolist()
        raise ValueError(f"[Clients Sheet]: Duplicate client_id found: {dups}")

    for idx, row in clients.iterrows():
        cid = str(row['client_id']).strip()
        excel_row = idx + clients_hdr_idx + 2

        if str(row['acceptance_mode']).strip() not in {'EXACT', 'MINIMUM'}:
            raise ValueError(f"[Clients Sheet - Row {excel_row}, ID: {cid}]: Invalid acceptance_mode.")
        if str(row['requested_segment']).strip() not in {'A', 'B', 'C', 'D'}:
            raise ValueError(f"[Clients Sheet - Row {excel_row}, ID: {cid}]: Invalid requested_segment.")
        if not is_multiple_of_5(row['demand_t']):
            raise ValueError(f"[Clients Sheet - Row {excel_row}, ID: {cid}]: demand_t is not a non-negative multiple of 5t.")

    # 3. STATION
    station_raw, station_hdr_idx = find_header_and_read('Station', 'station_id')
    station = station_raw[station_raw['station_id'].notna() & station_raw['station_id'].astype(str).str.startswith('STATION')].copy()

    for idx, row in station.iterrows():
        sid = str(row['station_id']).strip()
        excel_row = idx + station_hdr_idx + 2
        if not is_multiple_of_5(row['export_conditioning_capacity_t']):
            raise ValueError(f"[Station Sheet - Row {excel_row}, ID: {sid}]: Capacity is not a non-negative multiple of 5t.")

    return farms, clients, station



def read_and_validate_reference_prices(file_path):
    """Reads the 'Local-market reference prices by quality segment' table
    from the Station sheet and validates it has all 4 segments with
    positive prices. Returns {'A': float, 'B': float, 'C': float, 'D': float}.
    """
    import pandas as pd
    raw = pd.read_excel(file_path, sheet_name='Station', header=None, engine='openpyxl')

    header_row_idx = None
    for i, row in raw.iterrows():
        row_str = " ".join([str(x) for x in row.dropna().values])
        if 'segment' in row_str and 'reference_export_price_per_t_eur' in row_str:
            header_row_idx = i
            break
    if header_row_idx is None:
        raise ValueError("[Validation Error] Sheet 'Station': Could not locate the segment reference-price table.")

    prices = {}
    r = header_row_idx + 1
    while r < len(raw):
        seg = raw.iloc[r, 0]
        price = raw.iloc[r, 1]
        if pd.isna(seg):
            break
        seg = str(seg).strip()
        if seg not in {'A', 'B', 'C', 'D'}:
            break
        try:
            price_f = float(price)
        except (ValueError, TypeError):
            raise ValueError(f"[Validation Error] Sheet 'Station': reference price for segment '{seg}' is not numeric.")
        if price_f <= 0:
            raise ValueError(f"[Validation Error] Sheet 'Station': reference price for segment '{seg}' must be positive, got {price_f}.")
        prices[seg] = price_f
        r += 1

    missing = {'A', 'B', 'C', 'D'} - prices.keys()
    if missing:
        raise ValueError(f"[Validation Error] Sheet 'Station': missing reference price(s) for segment(s): {sorted(missing)}.")

    return prices