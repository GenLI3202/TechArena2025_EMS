#!/usr/bin/env python3
"""
TechArena 2025 Competition Readiness Check
=========================================

Quick validation script to verify system readiness for the final 45-scenario run.
This is a streamlined version of the comprehensive preliminary tests.

Usage:
    python competition_readiness_check.py

Output:
    - Pass/Fail status
    - Performance projections  
    - Go/No-Go decision for final run
"""

import sys
import time
import json
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Add project root to path
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))

def quick_environment_check():
    """Quick environment validation"""
    print("🔧 Environment Check...")
    
    issues = []
    
    # Python version
    if sys.version_info < (3, 8):
        issues.append(f"Python version {sys.version} < 3.8")
    
    # Critical packages
    for package in ['pandas', 'numpy', 'pyomo', 'openpyxl']:
        try:
            __import__(package)
        except ImportError:
            issues.append(f"Missing: {package}")
    
    # Solver availability
    try:
        import pyomo.environ as pyo
        solver_found = False
        for solver_name in ['cplex', 'gurobi', 'appsi_highs', 'highs']:
            try:
                solver = pyo.SolverFactory(solver_name)
                if solver.available():
                    solver_found = True
                    print(f"   ✅ Solver: {solver_name}")
                    break
            except:
                continue
        
        if not solver_found:
            issues.append("No optimization solver available")
            
    except Exception as e:
        issues.append(f"Solver test error: {str(e)}")
    
    return issues

def quick_data_check():
    """Quick data validation"""
    print("📊 Data Check...")
    
    issues = []
    
    # Check data files
    data_files = [
        'data/TechArena2025_data.xlsx',
        'data/TechArena2025_data_tidy.jsonl'
    ]
    
    for file_path in data_files:
        full_path = repo_root / file_path
        if not full_path.exists():
            issues.append(f"Missing: {file_path}")
        else:
            size_mb = full_path.stat().st_size / (1024 * 1024)
            print(f"   ✅ {file_path}: {size_mb:.1f} MB")
    
    # Quick data load test
    try:
        from py_script.model import ImprovedBESSOptimizer
        optimizer = ImprovedBESSOptimizer()
        data = optimizer.load_and_preprocess_data(str(repo_root / 'data/TechArena2025_data_tidy.jsonl'))
        print(f"   ✅ Data loaded: {len(data)} records")
    except Exception as e:
        issues.append(f"Data loading failed: {str(e)}")
    
    return issues

def quick_performance_test():
    """Quick performance test"""
    print("⚡ Performance Test...")
    
    issues = []
    performance_data = {}
    
    try:
        from py_script.model import ImprovedBESSOptimizer
        
        # Initialize
        optimizer = ImprovedBESSOptimizer()
        data = optimizer.load_and_preprocess_data(str(repo_root / 'data/TechArena2025_data_tidy.jsonl'))
        
        # Quick test: 2-day optimization
        print("   🧪 2-day test (DE_LU)...")
        country_data = optimizer.extract_country_data(data, 'DE_LU')
        subset_data = country_data[:192]  # 2 days
        
        optimizer.max_cycles_per_day = 1.5
        optimizer.c_rate = 0.5
        
        start_time = time.time()
        result = optimizer.optimize(subset_data)
        solve_time = time.time() - start_time
        
        revenue = result.get('total_revenue', 0)
        time_per_interval = solve_time / 192 * 1000  # ms per interval
        
        print(f"   ✅ Revenue: €{revenue:,.0f}")
        print(f"   ✅ Speed: {time_per_interval:.2f}ms/interval")
        
        # Project full-year performance
        full_year_time = time_per_interval / 1000 * 35040 / 60  # minutes
        all_scenarios_time = full_year_time * 45 / 60  # hours
        
        print(f"   📊 Full-year projection: {full_year_time:.1f}min")
        print(f"   📊 45 scenarios: {all_scenarios_time:.1f}h")
        
        performance_data = {
            'revenue_2day': revenue,
            'solve_time': solve_time,
            'time_per_interval_ms': time_per_interval,
            'full_year_minutes': full_year_time,
            'all_scenarios_hours': all_scenarios_time
        }
        
        # Performance checks
        if time_per_interval > 100:  # > 100ms per interval
            issues.append("Performance may be too slow")
        
        if all_scenarios_time > 12:  # > 12 hours total
            issues.append("Total runtime may be excessive")
            
    except Exception as e:
        issues.append(f"Performance test failed: {str(e)}")
    
    return issues, performance_data

def quick_model_validation():
    """Quick model validation across countries"""
    print("🌍 Model Validation...")
    
    issues = []
    
    try:
        from py_script.model import ImprovedBESSOptimizer
        
        optimizer = ImprovedBESSOptimizer()
        data = optimizer.load_and_preprocess_data(str(repo_root / 'data/TechArena2025_data_tidy.jsonl'))
        
        # Test 3 representative countries quickly
        test_countries = ['DE_LU', 'AT', 'CH']
        
        for country in test_countries:
            try:
                country_data = optimizer.extract_country_data(data, country)
                subset_data = country_data[:96]  # 1 day
                
                optimizer.max_cycles_per_day = 1.0
                optimizer.c_rate = 0.33
                
                result = optimizer.optimize(subset_data)
                revenue = result.get('total_revenue', 0)
                
                if revenue > 0:
                    print(f"   ✅ {country}: €{revenue:,.0f}")
                else:
                    issues.append(f"{country}: No revenue generated")
                    
            except Exception as e:
                issues.append(f"{country}: {str(e)}")
    
    except Exception as e:
        issues.append(f"Model validation failed: {str(e)}")
    
    return issues

def generate_readiness_report(all_issues, performance_data):
    """Generate final readiness report"""
    print("\n" + "🏆" + "=" * 50)
    print("   COMPETITION READINESS REPORT")
    print("=" * 52)
    
    # Overall status
    ready = len(all_issues) == 0
    status = "✅ READY FOR COMPETITION" if ready else "❌ ISSUES FOUND"
    
    print(f"\n🎯 STATUS: {status}")
    
    # Issues
    if all_issues:
        print(f"\n⚠️  ISSUES TO RESOLVE ({len(all_issues)}):")
        for i, issue in enumerate(all_issues, 1):
            print(f"   {i}. {issue}")
    
    # Performance summary
    if performance_data:
        print(f"\n⚡ PERFORMANCE PROJECTIONS:")
        print(f"   Single scenario: ~{performance_data['full_year_minutes']:.1f} minutes")
        print(f"   All 45 scenarios: ~{performance_data['all_scenarios_hours']:.1f} hours")
        print(f"   Speed: {performance_data['time_per_interval_ms']:.1f}ms per interval")
    
    # Final decision
    print(f"\n🚀 DECISION:")
    if ready:
        print("   ✅ GO - System ready for final run")
        print("   🎯 Execute: python final_45_scenarios.py")
        print("   ⏱️  Estimated completion: 2-8 hours")
    else:
        print("   ❌ NO-GO - Resolve issues first")
        print("   🔧 Run full preliminary tests for details")
        print("   🎯 Execute: python preliminary_tests.py")
    
    print("=" * 52)
    
    return ready

def main():
    """Run competition readiness check"""
    print("🏁 TechArena 2025 Competition Readiness Check")
    print("=" * 50)
    print("⚡ Quick validation before final run...")
    print("=" * 50)
    
    start_time = time.time()
    all_issues = []
    performance_data = {}
    
    # Run quick checks
    try:
        # Environment
        issues = quick_environment_check()
        all_issues.extend(issues)
        
        # Data
        issues = quick_data_check()
        all_issues.extend(issues)
        
        # Performance
        issues, perf_data = quick_performance_test()
        all_issues.extend(issues)
        performance_data = perf_data
        
        # Model validation
        issues = quick_model_validation()
        all_issues.extend(issues)
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {str(e)}")
        all_issues.append(f"Critical error: {str(e)}")
    
    # Generate report
    total_time = time.time() - start_time
    ready = generate_readiness_report(all_issues, performance_data)
    
    print(f"\n⏱️  Check completed in {total_time:.1f} seconds")
    
    return 0 if ready else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)