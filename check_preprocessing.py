#!/usr/bin/env python3
"""Check if preprocessing is working correctly."""
import pandas as pd
import numpy as np
from py_script.core.optimizer import BESSOptimizerModelIII

# Initialize and load data
opt = BESSOptimizerModelIII()
data = opt.load_and_preprocess_data('data/phase_1_data_TechArena2025_data_tidy.jsonl')
country_data = opt.extract_country_data(data, 'HU')
data_slice = country_data.iloc[0:144].copy()

print('='*80)
print('Checking aFRR Energy Price Preprocessing')
print('='*80)

print(f'\nTotal rows: {len(data_slice)}')
print(f'\naFRR Energy Negative Prices:')
print(f'  Zero prices:        {(data_slice["price_afrr_energy_neg"] == 0).sum()}')
print(f'  NaN prices:         {data_slice["price_afrr_energy_neg"].isna().sum()}')
non_zero_non_nan = ((data_slice["price_afrr_energy_neg"] != 0) &
                    (~data_slice["price_afrr_energy_neg"].isna())).sum()
print(f'  Non-zero, non-NaN:  {non_zero_non_nan}')

print(f'\naFRR Energy Positive Prices:')
print(f'  Zero prices:        {(data_slice["price_afrr_energy_pos"] == 0).sum()}')
print(f'  NaN prices:         {data_slice["price_afrr_energy_pos"].isna().sum()}')
non_zero_non_nan_pos = ((data_slice["price_afrr_energy_pos"] != 0) &
                        (~data_slice["price_afrr_energy_pos"].isna())).sum()
print(f'  Non-zero, non-NaN:  {non_zero_non_nan_pos}')

print('\nSample of prices (timesteps 48-56):')
print(data_slice.iloc[48:56][['price_afrr_energy_pos', 'price_afrr_energy_neg']])

print('\n' + '='*80)
