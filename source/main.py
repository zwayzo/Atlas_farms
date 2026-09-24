import sys
from parcing import validate_data, read_and_validate_reference_prices  # or parsing import
from tools import build_supply_pool, sort_clients, allocate_clients, calculate_local_market  # or tools import
import pandas as pd


def main():
    try:
        farms_df, clients_df, station_df = validate_data("../Atlas_Fresh_Production_Commercial_Data.xlsx")
        ref_prices = read_and_validate_reference_prices("../Atlas_Fresh_Production_Commercial_Data.xlsx")

        print("Data loaded and validated successfully.")
        supply = build_supply_pool(farms_df)
        print("Supply pool built successfully.")
        # print("Supply Pool:", supply)
        sorted_clients = sort_clients(clients_df)
        print("Clients sorted successfully.")
        # print("Sorted Clients:\n", sorted_clients)
        allocations, client_statuse, remaining_capacity = allocate_clients(sorted_clients, supply)
        print("Client allocations completed successfully.")
        alloc_df = pd.DataFrame(allocations)

        # Reorder and format columns
        alloc_df['revenue'] = alloc_df['revenue'].apply(lambda x: f"€{x:,.2f}")
        alloc_df['tonnes'] = alloc_df['tonnes'].apply(lambda x: f"{x:.1f} t")

        print("\n" + "="*60)
        print("              EXPORT ALLOCATION SCHEDULE")
        print("="*60)
        print(alloc_df[['client_id', 'farm_id', 'segment', 'tonnes', 'revenue']].to_string(index=False))
        print("="*60)


        local_residual, total_local_vol, total_local_val = calculate_local_market(supply, ref_prices=ref_prices)

        local_df = pd.DataFrame(local_residual)
        local_df['local_value_eur'] = local_df['local_value_eur'].apply(lambda x: f"€{x:,.2f}")
        local_df['remaining_tonnes'] = local_df['remaining_tonnes'].apply(lambda x: f"{x:.1f} t")

        print("\n" + "="*60)
        print("             LOCAL MARKET RESIDUAL SUMMARY")
        print("="*60)
        print(local_df.to_string(index=False))
        print("="*60)
        print(f"Total Residual Volume : {total_local_vol:.1f} t")
        print(f"Total Local Market Val: €{total_local_val:,.2f}")
        print("="*60)

        
        # Proceed with the rest of your application logic here...

    except ValueError as err:
        # Print only the validation message without triggering a traceback
        print(err, file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()