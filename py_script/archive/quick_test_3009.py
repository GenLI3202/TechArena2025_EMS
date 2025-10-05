"""
Quick test script to verify the model works with actual data
===========================================================

This script tests the optimization model with a small subset of the real data
to verify everything works before running the full optimization.
"""

import sys
import os
import pandas as pd
import json
from datetime import datetime, timedelta

# Add current directory to path
sys.path.append(os.path.dirname(__file__))
from model import BESSOptimizer

def test_with_real_data():
    """Test the model with a subset of real data."""
    print("Testing BESS Optimization Model with Real Data")
    print("=" * 50)
    
    # Initialize optimizer
    optimizer = BESSOptimizer()
    
    # Create a subset of real data (first few days)
    data_file = "../data/TechArena2025_data_tidy.jsonl"
    subset_file = "real_data_subset.jsonl"
    
    print("Creating data subset...")
    
    # Read and filter data for first 3 days of January 2024
    target_start = datetime(2024, 1, 1)
    target_end = datetime(2024, 1, 4)  # 3 days
    
    subset_data = []
    with open(data_file, 'r') as f:
        for line in f:
            record = json.loads(line.strip())
            ts = datetime.strptime(record['timestamp'][:19], "%Y-%m-%d %H:%M:%S")
            
            if target_start <= ts < target_end:
                subset_data.append(record)
    
    # Save subset
    with open(subset_file, 'w') as f:
        for record in subset_data:
            f.write(json.dumps(record) + '\n')
    
    print(f"Created subset with {len(subset_data)} records")
    
    # Test different countries and configurations
    test_scenarios = [
        ("DE", 0.5, 1.0),  # Germany, 0.5 C-rate, 1.0 cycles/day
        ("AT", 0.25, 1.5), # Austria, 0.25 C-rate, 1.5 cycles/day
    ]
    
    for country, c_rate, n_cycles in test_scenarios:
        print(f"\nTesting scenario: {country}, C-rate={c_rate}, cycles={n_cycles}")
        
        try:
            # Run optimization
            result = optimizer.run_optimization(subset_file, country, c_rate, n_cycles)
            
            if result["status"] in ["optimal", "feasible"]:
                print(f"  ✓ Success! Profit: {result['objective_value']:.2f} EUR")
                print(f"    Energy charged: {result['summary']['total_energy_charged_kwh']:.1f} kWh")
                print(f"    Energy discharged: {result['summary']['total_energy_discharged_kwh']:.1f} kWh")
                print(f"    Avg FCR bid: {result['summary']['avg_fcr_bid_mw']:.2f} MW")
            else:
                print(f"  ✗ Failed: {result['status']}")
                if 'error' in result:
                    print(f"    Error: {result['error']}")
                    
        except Exception as e:
            print(f"  ✗ Exception: {e}")
    
    # Clean up
    if os.path.exists(subset_file):
        os.remove(subset_file)
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_with_real_data()