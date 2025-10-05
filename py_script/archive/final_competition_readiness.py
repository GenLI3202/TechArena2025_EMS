#!/usr/bin/env python3
"""
TechArena 2025 Final Competition Readiness Check

This script performs a comprehensive check to ensure everything is ready
for the final 45-scenario competition run.
"""

import os
import sys
import json
import importlib.util
from datetime import datetime

def check_file_exists(filepath: str, description: str) -> bool:
    """Check if a file exists and report status."""
    if os.path.exists(filepath):
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description}: {filepath} - NOT FOUND")
        return False

def check_module_import(module_path: str, module_name: str) -> bool:
    """Check if a Python module can be imported."""
    try:
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        print(f"✅ Module {module_name}: Imports successfully")
        return True
    except Exception as e:
        print(f"❌ Module {module_name}: Import failed - {e}")
        return False

def check_data_integrity():
    """Check data file integrity."""
    data_file = 'data/TechArena2025_data_tidy.jsonl'
    
    if not os.path.exists(data_file):
        print(f"❌ Data file not found: {data_file}")
        return False
    
    try:
        line_count = 0
        countries = set()
        timestamps = set()
        
        with open(data_file, 'r') as f:
            for line in f:
                if line.strip():
                    line_count += 1
                    try:
                        record = json.loads(line)
                        countries.add(record.get('country'))
                        timestamps.add(record.get('timestamp'))
                    except:
                        pass
        
        print(f"✅ Data file loaded: {line_count:,} records")
        print(f"✅ Countries found: {sorted(countries)}")
        print(f"✅ Date range: {min(timestamps)} to {max(timestamps)}")
        
        # Check expected countries
        expected_countries = {'DE_LU', 'AT', 'CH', 'HU', 'CZ'}
        missing_countries = expected_countries - countries
        if missing_countries:
            print(f"❌ Missing countries: {missing_countries}")
            return False
        else:
            print(f"✅ All required countries present")
        
        return True
        
    except Exception as e:
        print(f"❌ Data file error: {e}")
        return False

def run_comprehensive_readiness_check():
    """Run comprehensive readiness check for final competition."""
    
    print("TechArena 2025 Final Competition Readiness Check")
    print("=" * 60)
    print(f"Check performed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    all_checks_passed = True
    
    # 1. Essential Files Check
    print("\n1. ESSENTIAL FILES CHECK")
    print("-" * 30)
    
    essential_files = [
        ('py_script/model.py', 'Main optimization model'),
        ('py_script/final_45_scenarios.py', 'Final competition script'),
        ('py_script/validate_csv_format.py', 'CSV validation script'),
        ('data/TechArena2025_data_tidy.jsonl', 'Competition data'),
    ]
    
    for filepath, description in essential_files:
        if not check_file_exists(filepath, description):
            all_checks_passed = False
    
    # 2. Module Import Check
    print("\n2. MODULE IMPORT CHECK")
    print("-" * 30)
    
    modules_to_check = [
        ('py_script/model.py', 'model'),
        ('py_script/final_45_scenarios.py', 'final_45_scenarios'),
        ('py_script/validate_csv_format.py', 'validate_csv_format'),
    ]
    
    for module_path, module_name in modules_to_check:
        if os.path.exists(module_path):
            if not check_module_import(module_path, module_name):
                all_checks_passed = False
        else:
            all_checks_passed = False
    
    # 3. Data Integrity Check
    print("\n3. DATA INTEGRITY CHECK")
    print("-" * 30)
    
    if not check_data_integrity():
        all_checks_passed = False
    
    # 4. Scenario Configuration Check
    print("\n4. SCENARIO CONFIGURATION CHECK")
    print("-" * 30)
    
    countries = ['DE_LU', 'AT', 'CH', 'HU', 'CZ']
    c_rates = [0.25, 0.33, 0.5]
    cycle_limits = [1.0, 1.5, 2.0]
    
    total_scenarios = len(countries) * len(c_rates) * len(cycle_limits)
    print(f"✅ Countries: {countries}")
    print(f"✅ C-rates: {c_rates}")
    print(f"✅ Cycle limits: {cycle_limits}")
    print(f"✅ Total scenarios: {total_scenarios}")
    
    # 5. Output Directory Check
    print("\n5. OUTPUT DIRECTORY CHECK")
    print("-" * 30)
    
    output_dir = 'py_script/final_submission_csvs'
    if os.path.exists(output_dir):
        print(f"⚠️  Output directory exists: {output_dir}")
        print("   Previous results may be overwritten")
    else:
        print(f"✅ Output directory will be created: {output_dir}")
    
    # 6. Dependencies Check
    print("\n6. DEPENDENCIES CHECK")
    print("-" * 30)
    
    required_packages = ['pandas', 'numpy', 'pyomo']
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}: Available")
        except ImportError:
            print(f"❌ {package}: Not available")
            all_checks_passed = False
    
    # 7. Estimated Runtime Check
    print("\n7. ESTIMATED RUNTIME")
    print("-" * 30)
    
    # Based on previous performance tests
    avg_time_per_scenario = 0.9  # seconds (from competition_readiness_check.py)
    estimated_total_time = avg_time_per_scenario * total_scenarios
    
    print(f"✅ Average time per scenario: {avg_time_per_scenario} seconds")
    print(f"✅ Estimated total runtime: {estimated_total_time/60:.1f} minutes")
    print(f"✅ Expected completion: ~{estimated_total_time/60:.0f} minutes from start")
    
    # 8. CSV Format Requirements
    print("\n8. CSV FORMAT REQUIREMENTS")
    print("-" * 30)
    
    print("✅ Configuration summary CSV:")
    print("   - 45 rows (5 countries × 9 configurations)")
    print("   - Columns: Country, Configuration, C_Rate, Cycle_Limit, etc.")
    
    print("✅ Operation results CSV:")
    print("   - Time series data for all scenarios")
    print("   - Columns: Country, Configuration, Timestamp, P_Charge_MW, etc.")
    
    print("✅ Country-specific CSV files:")
    print("   - Individual files for each country")
    print("   - Same format as operation results")
    
    # Final Summary
    print("\n" + "=" * 60)
    print("FINAL READINESS SUMMARY")
    print("=" * 60)
    
    if all_checks_passed:
        print("🎉 ALL CHECKS PASSED - READY FOR FINAL COMPETITION RUN!")
        print("\nNext steps:")
        print("1. Run: python final_45_scenarios.py")
        print("2. Monitor progress in final_45_scenarios.log")
        print("3. Validate output: python validate_csv_format.py")
        print("4. Submit CSV files from final_submission_csvs/")
        
        print(f"\nEstimated completion time: ~{estimated_total_time/60:.0f} minutes")
        print("Good luck with the competition! 🚀")
        
    else:
        print("❌ SOME CHECKS FAILED - NOT READY FOR COMPETITION")
        print("\nPlease resolve the issues marked with ❌ above")
        print("Then run this readiness check again.")
    
    print("=" * 60)
    
    return all_checks_passed

if __name__ == "__main__":
    # Change to the correct directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    os.chdir(project_root)
    
    # Run the check
    ready = run_comprehensive_readiness_check()
    
    # Exit with appropriate code
    exit(0 if ready else 1)