#!/usr/bin/env python3
"""
CSV Format Validation Script for TechArena 2025 Submission

This script validates that our generated CSV files meet the submission requirements.
"""

import os
import pandas as pd
import numpy as np
from typing import Dict, List, Optional

def validate_csv_format():
    """Validate the CSV format requirements for TechArena 2025."""
    
    print("TechArena 2025 CSV Format Validation")
    print("="*50)
    
    # Expected CSV structure based on typical competition requirements
    expected_columns = {
        'configuration_summary.csv': [
            'Country', 'Configuration', 'C_Rate', 'Cycle_Limit', 
            'Total_Revenue_EUR', 'Optimization_Time_s', 'Data_Points'
        ],
        'operation_results.csv': [
            'Country', 'Configuration', 'Timestamp', 
            'P_Charge_MW', 'P_Discharge_MW', 'E_SOC_MWh',
            'C_FCR_MW', 'C_AFRR_Pos_MW', 'C_AFRR_Neg_MW'
        ]
    }
    
    # Validation rules
    validation_rules = {
        'configuration_summary.csv': {
            'Country': ['DE_LU', 'AT', 'CH', 'HU', 'CZ'],
            'C_Rate': [0.5, 1.0, 2.0],
            'Cycle_Limit': [0.5, 1.0, 2.0],
            'Total_Revenue_EUR': 'numeric_positive',
            'Optimization_Time_s': 'numeric_positive',
            'Data_Points': 'integer_positive'
        },
        'operation_results.csv': {
            'Country': ['DE_LU', 'AT', 'CH', 'HU', 'CZ'],
            'P_Charge_MW': 'numeric_non_negative',
            'P_Discharge_MW': 'numeric_non_negative', 
            'E_SOC_MWh': 'numeric_non_negative',
            'C_FCR_MW': 'numeric_non_negative',
            'C_AFRR_Pos_MW': 'numeric_non_negative',
            'C_AFRR_Neg_MW': 'numeric_non_negative'
        }
    }
    
    # Check if files exist
    output_dir = 'final_submission_csvs'
    if not os.path.exists(output_dir):
        print(f"❌ Output directory '{output_dir}' does not exist")
        print("   Run final_45_scenarios.py first to generate CSV files")
        return False
    
    validation_passed = True
    
    for filename, expected_cols in expected_columns.items():
        filepath = os.path.join(output_dir, filename)
        
        print(f"\nValidating {filename}:")
        print("-" * 30)
        
        if not os.path.exists(filepath):
            print(f"❌ File not found: {filepath}")
            validation_passed = False
            continue
        
        try:
            # Load CSV
            df = pd.read_csv(filepath)
            print(f"✅ File loaded successfully")
            print(f"   Shape: {df.shape}")
            
            # Check columns
            missing_cols = set(expected_cols) - set(df.columns)
            extra_cols = set(df.columns) - set(expected_cols)
            
            if missing_cols:
                print(f"❌ Missing columns: {missing_cols}")
                validation_passed = False
            else:
                print(f"✅ All required columns present")
            
            if extra_cols:
                print(f"⚠️  Extra columns: {extra_cols}")
            
            # Validate data types and values
            if filename in validation_rules:
                rules = validation_rules[filename]
                for col, rule in rules.items():
                    if col not in df.columns:
                        continue
                    
                    if isinstance(rule, list):
                        # Check categorical values
                        invalid_values = set(df[col].unique()) - set(rule)
                        if invalid_values:
                            print(f"❌ Invalid values in {col}: {invalid_values}")
                            validation_passed = False
                        else:
                            print(f"✅ {col}: all values valid")
                    
                    elif rule == 'numeric_positive':
                        if not pd.api.types.is_numeric_dtype(df[col]):
                            print(f"❌ {col}: not numeric")
                            validation_passed = False
                        elif (df[col] <= 0).any():
                            print(f"❌ {col}: contains non-positive values")
                            validation_passed = False
                        else:
                            print(f"✅ {col}: positive numeric values")
                    
                    elif rule == 'numeric_non_negative':
                        if not pd.api.types.is_numeric_dtype(df[col]):
                            print(f"❌ {col}: not numeric")
                            validation_passed = False
                        elif (df[col] < 0).any():
                            print(f"❌ {col}: contains negative values")
                            validation_passed = False
                        else:
                            print(f"✅ {col}: non-negative numeric values")
                    
                    elif rule == 'integer_positive':
                        if not pd.api.types.is_integer_dtype(df[col]):
                            print(f"❌ {col}: not integer")
                            validation_passed = False
                        elif (df[col] <= 0).any():
                            print(f"❌ {col}: contains non-positive values")
                            validation_passed = False
                        else:
                            print(f"✅ {col}: positive integer values")
            
            # Additional checks for specific files
            if filename == 'configuration_summary.csv':
                # Should have exactly 45 rows (5 countries × 9 configurations)
                expected_rows = 5 * 9  # 45 scenarios
                if len(df) != expected_rows:
                    print(f"❌ Expected {expected_rows} rows, got {len(df)}")
                    validation_passed = False
                else:
                    print(f"✅ Correct number of scenarios: {len(df)}")
                
                # Check all country-configuration combinations exist
                countries = ['DE_LU', 'AT', 'CH', 'HU', 'CZ']
                c_rates = [0.25, 0.33, 0.5]
                cycle_limits = [1.0, 1.5, 2.0]
                
                expected_combinations = set()
                for country in countries:
                    for c_rate in c_rates:
                        for cycle_limit in cycle_limits:
                            expected_combinations.add((country, c_rate, cycle_limit))
                
                actual_combinations = set(zip(df['Country'], df['C_Rate'], df['Cycle_Limit']))
                missing_combinations = expected_combinations - actual_combinations
                
                if missing_combinations:
                    print(f"❌ Missing scenario combinations: {missing_combinations}")
                    validation_passed = False
                else:
                    print(f"✅ All 45 scenario combinations present")
            
            elif filename == 'operation_results.csv':
                # Check timestamp format
                if 'Timestamp' in df.columns:
                    try:
                        pd.to_datetime(df['Timestamp'].iloc[0])
                        print(f"✅ Timestamp format appears valid")
                    except:
                        print(f"❌ Invalid timestamp format")
                        validation_passed = False
                
                # Check that we have data for all countries and configurations
                if 'Country' in df.columns and 'Configuration' in df.columns:
                    unique_scenarios = df[['Country', 'Configuration']].drop_duplicates()
                    if len(unique_scenarios) < 45:
                        print(f"❌ Missing data for some scenarios: only {len(unique_scenarios)}/45")
                        validation_passed = False
                    else:
                        print(f"✅ Data present for all 45 scenarios")
        
        except Exception as e:
            print(f"❌ Error reading file: {e}")
            validation_passed = False
    
    # Summary
    print(f"\n{'='*50}")
    if validation_passed:
        print("🎉 CSV FORMAT VALIDATION PASSED!")
        print("   All files meet the expected submission requirements")
    else:
        print("❌ CSV FORMAT VALIDATION FAILED!")
        print("   Some files do not meet the submission requirements")
        print("   Please review the errors above and regenerate the files")
    print(f"{'='*50}")
    
    return validation_passed

def show_csv_samples():
    """Show sample data from generated CSV files."""
    print("\nSample CSV Data:")
    print("="*50)
    
    output_dir = 'final_submission_csvs'
    csv_files = ['configuration_summary.csv', 'operation_results.csv']
    
    for filename in csv_files:
        filepath = os.path.join(output_dir, filename)
        if os.path.exists(filepath):
            print(f"\n{filename} (first 5 rows):")
            print("-" * 40)
            df = pd.read_csv(filepath)
            print(df.head().to_string(index=False))
            print(f"Total rows: {len(df)}")
        else:
            print(f"\n{filename}: File not found")

if __name__ == "__main__":
    # Run validation
    validation_passed = validate_csv_format()
    
    # Show samples if validation passed
    if validation_passed:
        show_csv_samples()
    
    # Exit with appropriate code
    exit(0 if validation_passed else 1)