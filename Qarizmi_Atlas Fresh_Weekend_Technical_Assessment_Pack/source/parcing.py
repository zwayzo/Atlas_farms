import pandas as pd
import numpy as np
from pathlib import Path

def validate_data(file_path: str):
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Excel file not found at path: {path.resolve()}")

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
            row_str = " ".join([str(x) for x in row.dropna().values])
            if id_keyword in row_str:
                header_row_idx = i
                break
                
        if header_row_idx is None:
            raise ValueError(f"[Validation Error] Sheet '{sheet_name}': Could not locate header row containing '{id_keyword}'.")
        
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row_idx, engine='openpyxl')
        return df, header_row_idx

    def check_missing_ids(df_raw, id_col, sheet_name, header_idx):
        """
        Detects non-empty data rows that are missing a primary ID key
        BEFORE any filtering/dropping occurs.
        """
        for idx, row in df_raw.iterrows():
            excel_row = idx + header_idx + 2
            # Skip completely empty rows or generic legend blocks below the table
            non_id_cols = row.drop(labels=[id_col], errors='ignore')
            if non_id_cols.dropna().empty:
                continue
                
            # If id cell is missing/blank, but other data exists in the row
            val = row[id_col]
            if pd.isna(val) or str(val).strip() == "" or str(val).lower() == "nan":
                # Check if this row actually contains data and isn't just footnote/text documentation
                numeric_data_exists = any(isinstance(x, (int, float)) and not pd.isna(x) for x in non_id_cols.values)
                if numeric_data_exists:
                    raise ValueError(f"[Validation Error] Sheet '{sheet_name}', Row {excel_row}: Data present but missing '{id_col}'.")

    # ==========================================
    # 1. FARMS SHEET VALIDATION
    # ==========================================
    farms_raw, farms_hdr_idx = find_header_and_read('Farms', 'farm_id')

    # STEP A: Check missing IDs on raw sheet first
    check_missing_ids(farms_raw, 'farm_id', 'Farms', farms_hdr_idx)

    # STEP B: Isolate valid data rows
    farms = farms_raw[farms_raw['farm_id'].notna() & farms_raw['farm_id'].astype(str).str.startswith('F')].copy()

    # STEP C: Check duplicates
    if farms['farm_id'].duplicated().any():
        dups = farms[farms['farm_id'].duplicated()]['farm_id'].tolist()
        raise ValueError(f"[Validation Error] Sheet 'Farms': Duplicate farm_id found: {dups}")

    # STEP D: Row-by-row checks
    for idx, row in farms.iterrows():
        fid = str(row['farm_id']).strip()
        excel_row = idx + farms_hdr_idx + 2

        cap = row['expected_daily_capacity_t']
        if not is_valid_capacity(cap):
            raise ValueError(f"[Validation Error] Sheet 'Farms', Row {excel_row} (ID: {fid}): Invalid 'expected_daily_capacity_t' value '{cap}'. Must be non-negative with at most 1 decimal place.")

        mix_sum = sum([float(row[c]) for c in ['expected_A_pct', 'expected_B_pct', 'expected_C_pct', 'expected_D_pct']])
        if not np.isclose(mix_sum, 1.0):
            raise ValueError(f"[Validation Error] Sheet 'Farms', Row {excel_row} (ID: {fid}): Mix percentages sum to {mix_sum:.4f}, expected 1.0.")

        for col in ['actual_A_t', 'actual_B_t', 'actual_C_t', 'actual_D_t']:
            val = row[col]
            if not is_multiple_of_5(val):
                raise ValueError(f"[Validation Error] Sheet 'Farms', Row {excel_row} (ID: {fid}): '{col}' value '{val}' is not a non-negative multiple of 5t.")

    # ==========================================
    # 2. CLIENTS SHEET VALIDATION
    # ==========================================
    clients_raw, clients_hdr_idx = find_header_and_read('Clients', 'client_id')

    # STEP A: Check missing IDs on raw sheet first
    check_missing_ids(clients_raw, 'client_id', 'Clients', clients_hdr_idx)

    # STEP B: Isolate valid data rows
    clients = clients_raw[clients_raw['client_id'].notna() & clients_raw['client_id'].astype(str).str.startswith('C')].copy()

    # STEP C: Check duplicates
    if clients['client_id'].duplicated().any():
        dups = clients[clients['client_id'].duplicated()]['client_id'].tolist()
        raise ValueError(f"[Validation Error] Sheet 'Clients': Duplicate client_id found: {dups}")

    valid_modes = {'EXACT', 'MINIMUM'}
    valid_segments = {'A', 'B', 'C', 'D'}

    # STEP D: Row-by-row checks
    for idx, row in clients.iterrows():
        cid = str(row['client_id']).strip()
        excel_row = idx + clients_hdr_idx + 2

        mode = str(row['acceptance_mode']).strip()
        if mode not in valid_modes:
            raise ValueError(f"[Validation Error] Sheet 'Clients', Row {excel_row} (ID: {cid}): Invalid 'acceptance_mode' '{mode}'. Must be 'EXACT' or 'MINIMUM'.")

        seg = str(row['requested_segment']).strip()
        if seg not in valid_segments:
            raise ValueError(f"[Validation Error] Sheet 'Clients', Row {excel_row} (ID: {cid}): Invalid 'requested_segment' '{seg}'. Must be A, B, C, or D.")

        dem = row['demand_t']
        if not is_multiple_of_5(dem):
            raise ValueError(f"[Validation Error] Sheet 'Clients', Row {excel_row} (ID: {cid}): 'demand_t' value '{dem}' is not a non-negative multiple of 5t.")

    # ==========================================
    # 3. STATION SHEET VALIDATION
    # ==========================================
    station_raw, station_hdr_idx = find_header_and_read('Station', 'station_id')

    # STEP A: Check missing IDs on raw sheet first
    check_missing_ids(station_raw, 'station_id', 'Station', station_hdr_idx)

    # STEP B: Isolate valid data rows
    station = station_raw[station_raw['station_id'].notna() & station_raw['station_id'].astype(str).str.startswith('STATION')].copy()

    # STEP C: Check duplicates
    if station['station_id'].duplicated().any():
        dups = station[station['station_id'].duplicated()]['station_id'].tolist()
        raise ValueError(f"[Validation Error] Sheet 'Station': Duplicate station_id found: {dups}")

    # STEP D: Row-by-row checks
    for idx, row in station.iterrows():
        sid = str(row['station_id']).strip()
        excel_row = idx + station_hdr_idx + 2

        cap = row['export_conditioning_capacity_t']
        if not is_multiple_of_5(cap):
            raise ValueError(f"[Validation Error] Sheet 'Station', Row {excel_row} (ID: {sid}): 'export_conditioning_capacity_t' value '{cap}' is not a non-negative multiple of 5t.")

    print("✅ All sheets loaded and validated successfully.")
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