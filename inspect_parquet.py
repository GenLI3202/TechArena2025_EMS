#!/usr/bin/env python3
"""Inspect Phase 2 parquet files directly."""

import pandas as pd
from pathlib import Path

data_dir = Path("data/phase2_processed/parquet")

print("="*80)
print("Inspecting Phase 2 Parquet Files")
print("="*80)

# Check FCR
print("\n1. FCR Data:")
fcr_df = pd.read_parquet(data_dir / 'fcr.parquet')
print(f"Shape: {fcr_df.shape}")
print(f"Columns: {list(fcr_df.columns)}")
print(f"First 10 rows:")
print(fcr_df.head(10))
print(f"\nAfter resampling to 15min:")
fcr_df['timestamp'] = pd.to_datetime(fcr_df['timestamp'])
fcr_df = fcr_df.set_index('timestamp')
fcr_resampled = fcr_df.resample('15min').ffill()
print(f"Shape after resample: {fcr_resampled.shape}")
print(f"First 20 rows of resampled:")
print(fcr_resampled.head(20))

# Check timestamps
print("\n2. Day-Ahead Timestamps (first 10):")
da_df = pd.read_parquet(data_dir / 'day_ahead.parquet')
print(da_df['timestamp'].head(10))

print("\n3. aFRR Energy Timestamps (first 10):")
afrr_energy_df = pd.read_parquet(data_dir / 'afrr_energy.parquet')
print(afrr_energy_df['timestamp'].head(10))
