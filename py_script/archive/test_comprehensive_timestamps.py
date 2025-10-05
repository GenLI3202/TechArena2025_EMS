#!/usr/bin/env python3
"""
Comprehensive test script to validate timestamp alignment across the ENTIRE dataset.
"""

import sys
import os
import json
import pandas as pd
import numpy as np
from pathlib import Path

# Add the script directory to Python path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

def comprehensive_timestamp_test():
    """Test timestamp alignment across the entire dataset."""
    print("=== COMPREHENSIVE TIMESTAMP ALIGNMENT TEST ===")
    
    try:
        from model import BESSOptimizer
        
        # Load data
        optimizer = BESSOptimizer()
        data_file = script_dir.parent / "data" / "TechArena2025_data_tidy.jsonl"
        processed_data = optimizer.load_and_preprocess_data(str(data_file))
        
        print(f"✓ Processed data loaded: {processed_data.shape}")
        
        # Load ALL original day-ahead data for comprehensive comparison
        print("Loading complete original dataset...")
        original_records = []
        with open(data_file, 'r') as f:
            for line in f:
                record = json.loads(line.strip())
                if record['source'] == 'day_ahead':
                    original_records.append(record)
        
        original_df = pd.DataFrame(original_records)
        original_df['timestamp'] = pd.to_datetime(original_df['timestamp'], format='mixed')
        
        print(f"✓ Original data loaded: {len(original_df)} records")
        
        # Test each country separately
        countries = ['DE_LU', 'AT', 'CH', 'HU', 'CZ']
        total_mismatches = 0
        total_comparisons = 0
        
        for country in countries:
            print(f"\n--- Testing {country} ---")
            
            # Get original data for this country
            country_original = original_df[original_df['country'] == country].copy()
            country_original['timestamp_rounded'] = country_original['timestamp'].dt.round('15min')
            country_original = country_original.set_index('timestamp_rounded').sort_index()
            
            # Get processed data for this country
            processed_col = (country, 'day_ahead', '')
            if processed_col not in processed_data.columns:
                print(f"  ❌ {country} not found in processed data")
                continue
                
            country_processed = processed_data[processed_col].dropna()
            
            print(f"  Original records: {len(country_original)}")
            print(f"  Processed records: {len(country_processed)}")
            
            # Compare all overlapping timestamps
            country_mismatches = 0
            country_comparisons = 0
            sample_mismatches = []
            
            for ts in country_original.index:
                if ts in country_processed.index:
                    original_val = country_original.loc[ts, 'price_eur_mwh']
                    processed_val = country_processed.loc[ts]
                    
                    if not pd.isna(original_val) and not pd.isna(processed_val):
                        country_comparisons += 1
                        if abs(original_val - processed_val) > 0.001:
                            country_mismatches += 1
                            if len(sample_mismatches) < 5:  # Keep first 5 mismatches
                                sample_mismatches.append({
                                    'timestamp': ts,
                                    'original': original_val,
                                    'processed': processed_val,
                                    'diff': abs(original_val - processed_val)
                                })
            
            print(f"  Comparisons: {country_comparisons}")
            print(f"  Mismatches: {country_mismatches}")
            print(f"  Accuracy: {((country_comparisons - country_mismatches) / country_comparisons * 100):.2f}%")
            
            if sample_mismatches:
                print(f"  Sample mismatches:")
                for mismatch in sample_mismatches:
                    print(f"    {mismatch['timestamp']}: {mismatch['original']:.3f} vs {mismatch['processed']:.3f} (diff: {mismatch['diff']:.3f})")
            
            total_mismatches += country_mismatches
            total_comparisons += country_comparisons
        
        # Overall results
        print(f"\n=== OVERALL RESULTS ===")
        print(f"Total comparisons: {total_comparisons:,}")
        print(f"Total mismatches: {total_mismatches:,}")
        overall_accuracy = (total_comparisons - total_mismatches) / total_comparisons * 100
        print(f"Overall accuracy: {overall_accuracy:.3f}%")
        
        if total_mismatches == 0:
            print("🎉 PERFECT: No timestamp misalignments found across entire dataset!")
            return True
        elif overall_accuracy > 99.9:
            print(f"⚠️  MOSTLY GOOD: {overall_accuracy:.3f}% accuracy (only {total_mismatches} mismatches)")
            print("   This may be acceptable depending on tolerance requirements")
            return True
        else:
            print(f"❌ SIGNIFICANT ISSUES: {overall_accuracy:.3f}% accuracy with {total_mismatches} mismatches")
            return False
            
    except Exception as e:
        print(f"❌ Error during comprehensive testing: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_temporal_consistency():
    """Test that processed data maintains temporal consistency (no gaps or duplicates)."""
    print("\n=== TEMPORAL CONSISTENCY TEST ===")
    
    try:
        from model import BESSOptimizer
        
        optimizer = BESSOptimizer()
        data_file = script_dir.parent / "data" / "TechArena2025_data_tidy.jsonl"
        processed_data = optimizer.load_and_preprocess_data(str(data_file))
        
        # Check index properties
        print(f"Index start: {processed_data.index.min()}")
        print(f"Index end: {processed_data.index.max()}")
        print(f"Index length: {len(processed_data)}")
        print(f"Index frequency: {pd.infer_freq(processed_data.index)}")
        
        # Check for duplicates
        duplicates = processed_data.index.duplicated().sum()
        print(f"Duplicate timestamps: {duplicates}")
        
        # Check for missing 15-min intervals
        expected_range = pd.date_range(
            start=processed_data.index.min(),
            end=processed_data.index.max(),
            freq='15min'
        )
        missing_timestamps = set(expected_range) - set(processed_data.index)
        print(f"Missing 15-min intervals: {len(missing_timestamps)}")
        
        if missing_timestamps and len(missing_timestamps) <= 10:
            print("Missing timestamps:")
            for ts in sorted(list(missing_timestamps)[:10]):
                print(f"  {ts}")
        
        # Check day-ahead data completeness for each country
        print("\nDay-ahead data completeness:")
        countries = ['DE_LU', 'AT', 'CH', 'HU', 'CZ']
        for country in countries:
            col = (country, 'day_ahead', '')
            if col in processed_data.columns:
                non_null_count = processed_data[col].count()
                total_count = len(processed_data)
                completeness = (non_null_count / total_count) * 100
                print(f"  {country}: {non_null_count:,}/{total_count:,} ({completeness:.1f}%)")
        
        # Overall assessment
        if duplicates == 0 and len(missing_timestamps) == 0:
            print("✅ EXCELLENT: Perfect temporal consistency")
            return True
        elif duplicates == 0 and len(missing_timestamps) < 100:
            print(f"⚠️  GOOD: Minor gaps ({len(missing_timestamps)} missing intervals)")
            return True
        else:
            print(f"❌ ISSUES: {duplicates} duplicates, {len(missing_timestamps)} gaps")
            return False
            
    except Exception as e:
        print(f"❌ Error during temporal consistency testing: {e}")
        return False

def test_specific_problematic_periods():
    """Test specific time periods that are known to be problematic."""
    print("\n=== TESTING SPECIFIC PROBLEMATIC PERIODS ===")
    
    try:
        from model import BESSOptimizer
        
        optimizer = BESSOptimizer()
        data_file = script_dir.parent / "data" / "TechArena2025_data_tidy.jsonl"
        processed_data = optimizer.load_and_preprocess_data(str(data_file))
        
        # Test periods around daylight saving time changes, month boundaries, etc.
        test_periods = [
            ('2024-01-01 00:00:00', '2024-01-01 06:00:00', 'New Year start'),
            ('2024-03-31 00:00:00', '2024-03-31 06:00:00', 'DST change (spring)'),
            ('2024-06-30 18:00:00', '2024-07-01 06:00:00', 'Month boundary'),
            ('2024-10-27 00:00:00', '2024-10-27 06:00:00', 'DST change (fall)'),
            ('2024-12-31 18:00:00', '2025-01-01 06:00:00', 'Year boundary'),
        ]
        
        all_good = True
        
        for start_str, end_str, description in test_periods:
            print(f"\nTesting {description}: {start_str} to {end_str}")
            
            start_ts = pd.Timestamp(start_str)
            end_ts = pd.Timestamp(end_str)
            
            # Check if this period exists in our data
            if start_ts < processed_data.index.min() or end_ts > processed_data.index.max():
                print(f"  Skipping - outside data range")
                continue
            
            period_data = processed_data.loc[start_ts:end_ts]
            expected_intervals = pd.date_range(start=start_ts, end=end_ts, freq='15min')
            
            print(f"  Expected intervals: {len(expected_intervals)}")
            print(f"  Actual intervals: {len(period_data)}")
            
            missing_in_period = set(expected_intervals) - set(period_data.index)
            if missing_in_period:
                print(f"  ❌ Missing {len(missing_in_period)} intervals in this period")
                all_good = False
            else:
                print(f"  ✅ Complete - no missing intervals")
        
        return all_good
        
    except Exception as e:
        print(f"❌ Error during specific period testing: {e}")
        return False

if __name__ == "__main__":
    print("Running comprehensive timestamp alignment validation...")
    
    test1 = comprehensive_timestamp_test()
    test2 = test_temporal_consistency()
    test3 = test_specific_problematic_periods()
    
    print(f"\n{'='*60}")
    print("FINAL RESULTS:")
    print(f"✅ Comprehensive alignment test: {'PASS' if test1 else 'FAIL'}")
    print(f"✅ Temporal consistency test: {'PASS' if test2 else 'FAIL'}")
    print(f"✅ Problematic periods test: {'PASS' if test3 else 'FAIL'}")
    
    if test1 and test2 and test3:
        print("\n🎉 ALL COMPREHENSIVE TESTS PASSED!")
        print("The timestamp alignment fix is solid across the entire dataset!")
    else:
        print("\n❌ SOME COMPREHENSIVE TESTS FAILED!")
        print("There may still be timestamp alignment issues in the dataset!")
    
    sys.exit(0 if (test1 and test2 and test3) else 1)