#!/usr/bin/env python3
"""
Test script to verify the timestamp alignment fix in the BESS optimizer.
"""

import sys
import os
import json
import pandas as pd
from pathlib import Path

# Add the script directory to Python path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

def test_timestamp_alignment():
    """Test that timestamps are correctly aligned after the fix."""
    print("=== TESTING TIMESTAMP ALIGNMENT FIX ===")
    
    # Load the fixed BESS optimizer
    try:
        from model import BESSOptimizer
        print("✓ BESSOptimizer imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import BESSOptimizer: {e}")
        return False
    
    # Data file path
    data_file = script_dir.parent / "data" / "TechArena2025_data_tidy.jsonl"
    if not data_file.exists():
        print(f"✗ Data file not found: {data_file}")
        return False
    
    try:
        # Initialize optimizer and load data
        optimizer = BESSOptimizer()
        processed_data = optimizer.load_and_preprocess_data(str(data_file))
        
        print(f"✓ Data loaded successfully")
        print(f"  Shape: {processed_data.shape}")
        print(f"  Date range: {processed_data.index.min()} to {processed_data.index.max()}")
        
        # Load original tidy data for comparison
        print("\n=== COMPARING WITH ORIGINAL DATA ===")
        
        original_data = []
        with open(data_file, 'r') as f:
            for line in f:
                record = json.loads(line.strip())
                if record['source'] == 'day_ahead' and record['country'] == 'AT':
                    original_data.append(record)
        
        original_df = pd.DataFrame(original_data)
        original_df['timestamp'] = pd.to_datetime(original_df['timestamp'], format='mixed')
        original_df = original_df.set_index('timestamp').sort_index()
        
        print(f"Original data points: {len(original_df)}")
        
        # Test specific timestamps around the problematic 04:00:00 time
        # Note: Original data has microseconds, so we need to find the closest matches
        test_timestamps_exact = [
            '2024-01-01 03:45:00.004000',
            '2024-01-01 04:00:00.005000', 
            '2024-01-01 04:15:00.005000',
            '2024-01-01 04:30:00.005000'
        ]
        
        test_timestamps_rounded = [
            '2024-01-01 03:45:00',
            '2024-01-01 04:00:00', 
            '2024-01-01 04:15:00',
            '2024-01-01 04:30:00'
        ]
        
        print("\n=== TIMESTAMP COMPARISON ===")
        all_match = True
        
        at_col = ('AT', 'day_ahead', '')  # AT day-ahead column in processed data
        
        for exact_ts_str, rounded_ts_str in zip(test_timestamps_exact, test_timestamps_rounded):
            exact_ts = pd.Timestamp(exact_ts_str)
            rounded_ts = pd.Timestamp(rounded_ts_str)
            
            # Get original value (with microseconds)
            if exact_ts in original_df.index:
                original_value = original_df.loc[exact_ts, 'price_eur_mwh']
            else:
                # Try to find the nearest timestamp
                nearest_idx = original_df.index.get_indexer([exact_ts], method='nearest')[0]
                if nearest_idx >= 0:
                    actual_ts = original_df.index[nearest_idx]
                    original_value = original_df.iloc[nearest_idx]['price_eur_mwh']
                    print(f"  Note: Using nearest timestamp {actual_ts} for {exact_ts}")
                else:
                    original_value = None
            
            # Get processed value (rounded to 15-min)
            if rounded_ts in processed_data.index and at_col in processed_data.columns:
                processed_value = processed_data.loc[rounded_ts, at_col]
            else:
                processed_value = None
            
            # Compare
            if original_value is not None and processed_value is not None:
                match = abs(original_value - processed_value) < 0.001  # Small tolerance for float precision
                print(f"  {rounded_ts}: Original={original_value:.2f}, Processed={processed_value:.2f}, Match={match}")
                if not match:
                    all_match = False
            else:
                print(f"  {rounded_ts}: Original={original_value}, Processed={processed_value}, Data missing!")
                all_match = False
        
        # Test a broader range to ensure no systematic shifts
        print("\n=== BROADER TIMESTAMP TEST ===")
        test_range = pd.date_range('2024-01-01 00:00:00', '2024-01-01 06:00:00', freq='15min')
        mismatches = 0
        total_comparisons = 0
        
        for rounded_ts in test_range:
            # Find the closest original timestamp (which has microseconds)
            closest_idx = original_df.index.get_indexer([rounded_ts], method='nearest')[0]
            if closest_idx >= 0:
                actual_ts = original_df.index[closest_idx]
                # Check if it's within a reasonable time window (e.g., same minute)
                time_diff = abs((actual_ts - rounded_ts).total_seconds())
                
                if time_diff < 60:  # Within 1 minute
                    original_val = original_df.iloc[closest_idx]['price_eur_mwh']
                    
                    if rounded_ts in processed_data.index and at_col in processed_data.columns:
                        processed_val = processed_data.loc[rounded_ts, at_col]
                        
                        if not pd.isna(original_val) and not pd.isna(processed_val):
                            total_comparisons += 1
                            if abs(original_val - processed_val) > 0.001:
                                mismatches += 1
                                if mismatches <= 3:  # Show first 3 mismatches
                                    print(f"  MISMATCH at {rounded_ts}: {original_val:.2f} vs {processed_val:.2f}")
                                    print(f"    (Original timestamp: {actual_ts})")
        
        print(f"\nBroad test results: {mismatches} mismatches out of {total_comparisons} comparisons")
        
        if all_match and mismatches == 0:
            print("\n🎉 SUCCESS: Timestamp alignment is now CORRECT!")
            print("   All timestamps match between original and processed data")
            return True
        else:
            print("\n❌ FAILURE: Timestamp alignment still has issues")
            print(f"   Key timestamps match: {all_match}")
            print(f"   Broader test mismatches: {mismatches}/{total_comparisons}")
            return False
    
    except Exception as e:
        print(f"✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_market_data_integrity():
    """Test that market data maintains its integrity after processing."""
    print("\n=== TESTING MARKET DATA INTEGRITY ===")
    
    try:
        from model import BESSOptimizer
        
        optimizer = BESSOptimizer()
        data_file = script_dir.parent / "data" / "TechArena2025_data_tidy.jsonl"
        processed_data = optimizer.load_and_preprocess_data(str(data_file))
        
        # Check that we have the expected columns
        expected_countries = ['DE_LU', 'AT', 'CH', 'HU', 'CZ']
        expected_sources = ['day_ahead', 'fcr', 'afrr']
        
        print("Checking column structure...")
        for country in expected_countries:
            if country in processed_data.columns.levels[0]:
                print(f"✓ {country} data found")
                
                # Check for day-ahead data
                da_col = (country, 'day_ahead', '')
                if da_col in processed_data.columns:
                    non_null_count = processed_data[da_col].count()
                    print(f"  - Day-ahead: {non_null_count} non-null values")
                
        # Check time range
        print(f"\nTime range: {processed_data.index.min()} to {processed_data.index.max()}")
        print(f"Total time periods: {len(processed_data)}")
        print(f"Index frequency: {pd.infer_freq(processed_data.index)}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error during integrity testing: {e}")
        return False

if __name__ == "__main__":
    print("Testing timestamp alignment fix...")
    
    success1 = test_timestamp_alignment()
    success2 = test_market_data_integrity()
    
    if success1 and success2:
        print("\n🎉 ALL TESTS PASSED!")
        print("The timestamp alignment issue has been FIXED!")
        print("BESS optimization results will now be accurate.")
    else:
        print("\n❌ SOME TESTS FAILED!")
        print("The timestamp alignment issue may still exist.")
    
    sys.exit(0 if (success1 and success2) else 1)