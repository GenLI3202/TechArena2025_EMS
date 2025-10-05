#!/usr/bin/env python3
"""
Quick Validation Script for TechArena 2025 Submission
=====================================================

This script performs a quick test of the submission pipeline by:
1. Testing imports
2. Running a single scenario
3. Validating file structure
4. Checking data extraction

Use this before running the full main.py to catch any issues early.

Usage:
    python validate_submission.py
"""

import os
import sys
from datetime import datetime

def test_imports():
    """Test that all required modules can be imported."""
    print("=" * 70)
    print("TEST 1: Import Validation")
    print("=" * 70)
    
    try:
        import pandas
        print("✅ pandas")
    except ImportError as e:
        print(f"❌ pandas: {e}")
        return False
    
    try:
        import numpy
        print("✅ numpy")
    except ImportError as e:
        print(f"❌ numpy: {e}")
        return False
    
    try:
        import pyomo.environ
        print("✅ pyomo")
    except ImportError as e:
        print(f"❌ pyomo: {e}")
        return False
    
    try:
        import openpyxl
        print("✅ openpyxl")
    except ImportError as e:
        print(f"❌ openpyxl: {e}")
        return False
    
    try:
        from model import ImprovedBESSOptimizer
        print("✅ model.ImprovedBESSOptimizer")
    except ImportError as e:
        print(f"❌ model.ImprovedBESSOptimizer: {e}")
        return False
    
    try:
        from investment_analysis import InvestmentAnalyzer
        print("✅ investment_analysis.InvestmentAnalyzer")
    except ImportError as e:
        print(f"❌ investment_analysis.InvestmentAnalyzer: {e}")
        return False
    
    try:
        from excel_generator import (
            generate_configuration_xlsx,
            generate_investment_xlsx,
            generate_operation_xlsx
        )
        print("✅ excel_generator functions")
    except ImportError as e:
        print(f"❌ excel_generator: {e}")
        return False
    
    print("\n✅ All imports successful!\n")
    return True


def test_file_structure():
    """Test that all required files and folders exist."""
    print("=" * 70)
    print("TEST 2: File Structure Validation")
    print("=" * 70)
    
    required_files = [
        'main.py',
        'model.py',
        'investment_analysis.py',
        'excel_generator.py',
        'requirements.txt',
        'README.md'
    ]
    
    required_folders = [
        'input',
        'output'
    ]
    
    input_file = os.path.join('input', 'TechArena2025_data_tidy.jsonl')
    
    all_ok = True
    
    # Check required files
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"❌ {file} - NOT FOUND")
            all_ok = False
    
    # Check required folders
    for folder in required_folders:
        if os.path.isdir(folder):
            print(f"✅ {folder}/ directory")
        else:
            print(f"❌ {folder}/ directory - NOT FOUND")
            all_ok = False
    
    # Check input file
    if os.path.exists(input_file):
        size_mb = os.path.getsize(input_file) / (1024 * 1024)
        print(f"✅ {input_file} ({size_mb:.2f} MB)")
    else:
        print(f"❌ {input_file} - NOT FOUND")
        all_ok = False
    
    if all_ok:
        print("\n✅ File structure is correct!\n")
    else:
        print("\n❌ File structure has issues!\n")
    
    return all_ok


def test_single_scenario():
    """Run a single optimization scenario as a smoke test."""
    print("=" * 70)
    print("TEST 3: Single Scenario Smoke Test")
    print("=" * 70)
    
    try:
        from model import ImprovedBESSOptimizer
        
        # Initialize optimizer
        print("Initializing optimizer...")
        optimizer = ImprovedBESSOptimizer()
        
        # Load data
        input_file = os.path.join('input', 'TechArena2025_data_tidy.jsonl')
        print(f"Loading data from {input_file}...")
        market_data = optimizer.load_and_preprocess_data(input_file)
        print(f"✅ Loaded {market_data.shape[0]} time steps")
        
        # Extract data for one country
        country = 'AT'  # Use Austria as test case
        print(f"\nExtracting data for {country}...")
        country_data = optimizer.extract_country_data(market_data, country)
        print(f"✅ Extracted {len(country_data)} time steps for {country}")
        
        # Build model for one configuration
        c_rate = 0.25
        cycles = 1.0
        print(f"\nBuilding model: C-rate={c_rate}, Cycles={cycles}...")
        model = optimizer.build_optimization_model(country_data, c_rate, cycles)
        print(f"✅ Model built successfully")
        
        # Solve model (auto-detect best available solver)
        print(f"\nSolving model (this may take 30-60 seconds)...")
        print("Auto-detecting solver (CPLEX/Gurobi if available, else HiGHS)...")
        solution = optimizer.solve_model(model, solver_name=None)
        
        if solution['status'] in ['optimal', 'feasible']:
            revenue = solution['objective_value']
            solve_time = solution['solve_time']
            print(f"✅ Solution found!")
            print(f"   Status: {solution['status']}")
            print(f"   Revenue: €{revenue:,.0f}")
            print(f"   Solve time: {solve_time:.2f}s")
            
            # Test string key conversion
            print(f"\nTesting solution extraction...")
            if 'p_ch' in solution:
                first_charge = solution['p_ch'].get('0', None)
                if first_charge is not None:
                    print(f"✅ String key extraction works (p_ch[0] = {first_charge:.2f} kW)")
                else:
                    print(f"⚠️  Warning: String key extraction may have issues")
            
            print("\n✅ Single scenario test PASSED!\n")
            return True
        else:
            print(f"❌ Solver failed with status: {solution['status']}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_investment_analyzer():
    """Test the investment analyzer with sample data."""
    print("=" * 70)
    print("TEST 4: Investment Analyzer Test")
    print("=" * 70)
    
    try:
        from investment_analysis import InvestmentAnalyzer
        
        analyzer = InvestmentAnalyzer()
        print("✅ InvestmentAnalyzer initialized")
        
        # Test with sample data
        country = 'DE'
        c_rate = 0.33
        annual_revenue = 500000  # 500k EUR
        
        print(f"\nRunning DCF analysis for {country}...")
        result = analyzer.analyze_investment(
            country=country,
            c_rate=c_rate,
            annual_revenue_2024=annual_revenue
        )
        
        print(f"✅ DCF analysis complete")
        print(f"   NPV: €{result['npv']:,.0f}")
        print(f"   IRR: {result['irr']:.2f}%")
        print(f"   Levelized ROI: {result['levelized_roi']:.2f}%")
        
        # Test Excel formatting
        print(f"\nTesting Excel formatting...")
        df = analyzer.format_for_excel(result)
        print(f"✅ Excel formatting successful ({len(df)} rows)")
        
        print("\n✅ Investment analyzer test PASSED!\n")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all validation tests."""
    print("\n" + "=" * 70)
    print("  TechArena 2025 - Submission Validation Script")
    print("=" * 70)
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70 + "\n")
    
    results = []
    
    # Test 1: Imports
    results.append(("Imports", test_imports()))
    
    # Test 2: File structure
    results.append(("File Structure", test_file_structure()))
    
    # Only continue with computational tests if basic tests pass
    if all([r[1] for r in results]):
        # Test 3: Single scenario
        results.append(("Single Scenario", test_single_scenario()))
        
        # Test 4: Investment analyzer
        results.append(("Investment Analyzer", test_investment_analyzer()))
    else:
        print("⚠️  Skipping computational tests due to basic test failures\n")
    
    # Summary
    print("=" * 70)
    print("  VALIDATION SUMMARY")
    print("=" * 70)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {test_name:.<50} {status}")
    
    print("=" * 70)
    
    all_passed = all([r[1] for r in results])
    
    if all_passed:
        print("\n🎉 All validation tests PASSED!")
        print("   You can now run the full pipeline with: python main.py")
    else:
        print("\n❌ Some validation tests FAILED!")
        print("   Please fix the issues before running the full pipeline")
    
    print("=" * 70)
    print(f"  Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
