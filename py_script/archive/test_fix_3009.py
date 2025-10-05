#!/usr/bin/env python3
"""Test script to verify the fix works and analyze data."""

from market_da import load_market_tables
from pathlib import Path
import pandas as pd

def test_and_analyze():
    # Load tables
    tables = load_market_tables(Path('../SoloGen_TechArena2025_Phase1/input/TechArena2025_data.xlsx'))
    
    # Fix the numeric conversion issue
    for table_name, df in tables.items():
        print(f"=== Processing {table_name} ===")
        print(f"Shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        
        # Convert all price columns to numeric
        for col in df.columns[1:]:  # Skip timestamp
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        print(f"Data types after conversion:")
        print(df.dtypes)
        print()
    
    # Test analysis functions
    from market_da import summarize_volatility, summarize_fcr, summarize_afrr
    
    print("=== Day-ahead Volatility Summary ===")
    vol_summary = summarize_volatility(tables['day_ahead'])
    print(vol_summary)
    
    print("\n=== FCR Summary ===")
    fcr_summary = summarize_fcr(tables['fcr'])
    print(fcr_summary)
    
    print("\n=== aFRR Summary (first 10 rows) ===")
    afrr_summary = summarize_afrr(tables['afrr'])
    print(afrr_summary.head(10))

if __name__ == "__main__":
    test_and_analyze()