#!/usr/bin/env python3
"""Quick script to check Phase 2 data availability for Switzerland."""

import sys
from pathlib import Path
import pandas as pd

sys.path.append(str(Path(__file__).parent / 'py_script'))
from validate_mpc_soc_continuity import load_phase2_data
from py_script.core.optimizer import BESSOptimizerModelIII

# Load data
data_dir = Path("data/phase2_processed/parquet")
full_data = load_phase2_data(data_dir)

# Extract CH data
optimizer = BESSOptimizerModelIII(alpha=0.5, use_afrr_ev_weighting=True)
country_data = optimizer.extract_country_data(full_data, 'CH')

print(f"\nCH Data shape: {country_data.shape}")
print(f"Date range: {country_data.index.min()} to {country_data.index.max()}")
print(f"\nFirst 5 rows:")
print(country_data.head())

# Check for null values around January 13
start_day = 12  # 0-indexed (Jan 13)
start_step = start_day * 96
end_step = start_step + (5 * 96)

print(f"\nData for Jan 13-17 (steps {start_step} to {end_step}):")
data_5day = country_data.iloc[start_step:end_step].copy()

print(f"\nNull value counts in 5-day period:")
null_counts = data_5day.isnull().sum()
print(null_counts[null_counts > 0])

print(f"\nFirst 10 rows of 5-day period:")
print(data_5day.head(10))

print(f"\nSample of data (first 128 timesteps for MPC horizon):")
horizon_data = data_5day.iloc[:128]
null_in_horizon = horizon_data.isnull().sum()
print(f"Null counts in first horizon (128 steps):")
print(null_in_horizon[null_in_horizon > 0])
