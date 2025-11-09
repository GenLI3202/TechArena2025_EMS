#!/usr/bin/env python3
"""Check column names in combined_df."""
import pandas as pd
from py_script.core.optimizer import BESSOptimizerModelIII

# Initialize and load data
opt = BESSOptimizerModelIII()

# Manually load to check combined_df columns
import json
data_file = 'data/phase_1_data_TechArena2025_data_tidy.jsonl'

data_list = []
with open(data_file, 'r') as f:
    for line in f:
        data_list.append(json.loads(line.strip()))

df = pd.DataFrame(data_list)
df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed')
df['timestamp'] = df['timestamp'].dt.round('15min')

# Process day-ahead data
da_data = df[df['source'] == 'day_ahead'].copy()
da_data = da_data.pivot_table(
    values='price',
    index='timestamp',
    columns=['country', 'source', 'direction'],
    aggfunc='first'
)

print("Sample of column names in da_data:")
print(da_data.columns[:10].tolist())
print(f"\nTotal columns: {len(da_data.columns)}")

# Check if there are aFRR energy columns
afrr_energy_cols = [col for col in da_data.columns if 'afrr_energy' in str(col)]
print(f"\naFRR energy columns: {len(afrr_energy_cols)}")
if afrr_energy_cols:
    print("Sample aFRR energy columns:")
    print(afrr_energy_cols[:5])
