import pandas as pd
from pathlib import Path
from py_script.data.load_process_market_data import load_phase2_market_tables

# Load data
tables = load_phase2_market_tables(Path('data/TechArena2025_Phase2_data.xlsx'))

# Replicate the extraction logic
TIMESTAMP_COL = 'timestamp'
timestamps = pd.to_datetime(tables['day_ahead'][TIMESTAMP_COL]).dt.floor('s')
fcr_df = tables['fcr'].copy()
fcr_df[TIMESTAMP_COL] = pd.to_datetime(fcr_df[TIMESTAMP_COL]).dt.floor('s')
fcr_df = fcr_df.set_index(TIMESTAMP_COL)

print(f"FCR DataFrame shape before reindex: {fcr_df.shape}")
print(f"Timestamps to reindex to: {len(timestamps)}")

# Reindex
fcr_reindexed = fcr_df.reindex(timestamps).ffill()

print(f"FCR DataFrame shape after reindex: {fcr_reindexed.shape}")

# Check Feb 6
feb6_start = 36 * 96
feb6_end = 37 * 96
feb6_data = fcr_reindexed.iloc[feb6_start:feb6_end]

print(f'\nFeb 6 FCR prices (DE) after reindex+ffill:')
print(f'Unique values: {feb6_data["DE"].unique()}')
print(f'Unique count: {feb6_data["DE"].nunique()}')

print(f'\nFirst few values:')
print(feb6_data['DE'].head(24))
