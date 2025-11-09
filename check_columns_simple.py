#!/usr/bin/env python3
"""Check column names in combined_df after load_and_preprocess_data."""
import pandas as pd
import numpy as np
from py_script.core.optimizer import BESSOptimizerModelIII

# Initialize and load data
opt = BESSOptimizerModelIII()
combined_df = opt.load_and_preprocess_data('data/phase_1_data_TechArena2025_data_tidy.jsonl')

print('='*80)
print('Column Structure in combined_df')
print('='*80)

print(f"\nTotal columns: {len(combined_df.columns)}")
print(f"\nColumn index type: {type(combined_df.columns)}")
print(f"\nColumn levels: {combined_df.columns.nlevels if hasattr(combined_df.columns, 'nlevels') else 'N/A'}")

print("\nFirst 20 columns:")
for i, col in enumerate(combined_df.columns[:20]):
    print(f"  {i}: {col}")

# Check for aFRR energy columns
print("\n" + '='*80)
print('Searching for aFRR energy columns...')
print('='*80)

afrr_energy_cols = []
for col in combined_df.columns:
    col_str = str(col)
    if 'afrr_energy' in col_str.lower():
        afrr_energy_cols.append(col)

print(f"\nFound {len(afrr_energy_cols)} aFRR energy columns:")
for col in afrr_energy_cols[:10]:
    print(f"  {col}")
    # Check if any values are NaN
    if len(afrr_energy_cols) > 0:
        sample_col = combined_df[col]
        zeros = (sample_col == 0).sum()
        nans = sample_col.isna().sum()
        non_zero = ((sample_col != 0) & (~sample_col.isna())).sum()
        print(f"    Zeros: {zeros}, NaNs: {nans}, Non-zero: {non_zero}")
        break

print('\n' + '='*80)
