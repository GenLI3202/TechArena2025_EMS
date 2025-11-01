"""
Main script for BESS optimization - Huawei TechArena 2025
=========================================================

This script provides an easy entry point for running the BESS optimization
with different modes: test, single scenario, or full optimization.

Usage:
    python main.py test              # Run quick test with sample data
    python main.py quick            # Run with real data subset
    python main.py single DE 0.5 1.0 # Run single scenario
    python main.py full             # Run all scenarios (takes time!)
"""

import sys
import os
import argparse
import json
from datetime import datetime

# Add parent directory to path for package imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core import BESSOptimizerV2

def main():
    parser = argparse.ArgumentParser(description='BESS Optimization for TechArena 2025')
    parser.add_argument('mode', choices=['test', 'quick', 'single', 'full'],
                       help='Execution mode')
    parser.add_argument('country', nargs='?', choices=['DE', 'AT', 'CH', 'HU', 'CZ'],
                       help='Country (for single mode)')
    parser.add_argument('c_rate', nargs='?', type=float, choices=[0.25, 0.33, 0.5],
                       help='C-rate (for single mode)')
    parser.add_argument('n_cycles', nargs='?', type=float, choices=[1.0, 1.5, 2.0],
                       help='Daily cycles (for single mode)')
    
    args = parser.parse_args()
    
    # Initialize optimizer
    optimizer = BESSOptimizerV2()
    
    if args.mode == 'test':
        print("Running test mode with synthetic data...")
        run_test_mode()
        
    elif args.mode == 'quick':
        print("Running quick test with real data subset...")
        run_quick_mode(optimizer)
        
    elif args.mode == 'single':
        if not all([args.country, args.c_rate, args.n_cycles]):
            print("Error: single mode requires country, c_rate, and n_cycles")
            print("Example: python main.py single DE 0.5 1.0")
            sys.exit(1)
        run_single_mode(optimizer, args.country, args.c_rate, args.n_cycles)
        
    elif args.mode == 'full':
        print("Running full optimization for all scenarios...")
        print("This may take several hours depending on solver and hardware!")
        run_full_mode(optimizer)

def run_test_mode():
    """Run with synthetic test data."""
    try:
        from test_model import create_test_data
        
        # Create test data
        test_file = create_test_data()
        
        # Initialize optimizer
        optimizer = BESSOptimizerV2()
        
        # Run single test scenario
        result = optimizer.run_optimization(test_file, "DE", 0.5, 1.0)
        
        if result["status"] in ["optimal", "feasible"]:
            print(f"✓ Test successful! Profit: {result['objective_value']:.2f} EUR")
        else:
            print(f"✗ Test failed: {result['status']}")
            
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)
            
    except Exception as e:
        print(f"Test mode failed: {e}")

def run_quick_mode(optimizer):
    """Run with real data subset."""
    try:
        from quick_test import test_with_real_data
        test_with_real_data()
    except Exception as e:
        print(f"Quick mode failed: {e}")

def run_single_mode(optimizer, country, c_rate, n_cycles):
    """Run optimization for a single scenario."""
    data_file = "../data/TechArena2025_data_tidy.jsonl"
    
    if not os.path.exists(data_file):
        print(f"Error: Data file not found: {data_file}")
        print("Please ensure the data file is in the correct location.")
        sys.exit(1)
    
    print(f"Running optimization for {country}, C-rate={c_rate}, cycles={n_cycles}")
    print("This may take 5-30 minutes depending on solver and data size...")
    
    start_time = datetime.now()
    result = optimizer.run_optimization(data_file, country, c_rate, n_cycles)
    end_time = datetime.now()
    
    print(f"\nOptimization completed in {end_time - start_time}")
    
    if result["status"] in ["optimal", "feasible"]:
        print(f"✓ Success! Status: {result['status']}")
        print(f"  Annual Profit: {result['objective_value']:,.2f} EUR")
        print(f"  Energy Charged: {result['summary']['total_energy_charged_kwh']:,.1f} kWh")
        print(f"  Energy Discharged: {result['summary']['total_energy_discharged_kwh']:,.1f} kWh")
        print(f"  Average FCR Bid: {result['summary']['avg_fcr_bid_mw']:.2f} MW")
        print(f"  Average aFRR+ Bid: {result['summary']['avg_afrr_pos_bid_mw']:.2f} MW")
        print(f"  Average aFRR- Bid: {result['summary']['avg_afrr_neg_bid_mw']:.2f} MW")
        
        # Save result
        output_file = f"result_{country}_C{c_rate}_Cyc{n_cycles}.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\nDetailed results saved to: {output_file}")
        
    else:
        print(f"✗ Optimization failed: {result['status']}")
        if 'error' in result:
            print(f"  Error: {result['error']}")

def run_full_mode(optimizer):
    """Run optimization for all scenarios."""
    data_file = "../data/TechArena2025_data_tidy.jsonl"
    
    if not os.path.exists(data_file):
        print(f"Error: Data file not found: {data_file}")
        sys.exit(1)
    
    # Confirm with user
    response = input("This will run 45 optimization scenarios and may take several hours. Continue? (y/N): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return
    
    print("Starting full optimization...")
    start_time = datetime.now()
    
    # Run all scenarios
    all_results = optimizer.run_all_scenarios(data_file)
    
    end_time = datetime.now()
    print(f"\nFull optimization completed in {end_time - start_time}")
    
    # Analyze results
    successful_results = [r for r in all_results if r["status"] in ["optimal", "feasible"]]
    failed_results = [r for r in all_results if r["status"] not in ["optimal", "feasible"]]
    
    print(f"\nResults Summary:")
    print(f"  Successful scenarios: {len(successful_results)}/{len(all_results)}")
    print(f"  Failed scenarios: {len(failed_results)}")
    
    if successful_results:
        # Find best scenario
        best_result = max(successful_results, key=lambda x: x["objective_value"])
        best_scenario = best_result["scenario"]
        
        print(f"\nBest Scenario:")
        print(f"  Country: {best_scenario['country']}")
        print(f"  C-rate: {best_scenario['c_rate']}")
        print(f"  Daily cycles: {best_scenario['n_cycles']}")
        print(f"  Annual profit: {best_result['objective_value']:,.2f} EUR")
        
        # Save all results
        output_file = f"all_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(all_results, f, indent=2, default=str)
        print(f"\nAll results saved to: {output_file}")
        
        # Create summary CSV
        summary_data = []
        for result in successful_results:
            scenario = result["scenario"]
            summary = result["summary"]
            summary_data.append({
                'Country': scenario['country'],
                'C_rate': scenario['c_rate'],
                'Daily_cycles': scenario['n_cycles'],
                'Annual_profit_EUR': result['objective_value'],
                'Energy_charged_kWh': summary['total_energy_charged_kwh'],
                'Energy_discharged_kWh': summary['total_energy_discharged_kwh'],
                'Avg_FCR_bid_MW': summary['avg_fcr_bid_mw'],
                'Avg_aFRR_pos_bid_MW': summary['avg_afrr_pos_bid_mw'],
                'Avg_aFRR_neg_bid_MW': summary['avg_afrr_neg_bid_mw']
            })
        
        import pandas as pd
        summary_df = pd.DataFrame(summary_data)
        csv_file = f"optimization_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        summary_df.to_csv(csv_file, index=False)
        print(f"Summary CSV saved to: {csv_file}")
        
    else:
        print("No successful scenarios found!")

if __name__ == "__main__":
    main()