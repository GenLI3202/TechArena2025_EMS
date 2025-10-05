#!/usr/bin/env python3
"""
Quick test to verify CSV output format
"""
from py_script.model import ImprovedBESSOptimizer
import pandas as pd
from pathlib import Path
import json

def test_csv_generation():
    print('🧪 Testing 1-week optimization and CSV generation...')
    
    # Initialize and run optimization
    optimizer = ImprovedBESSOptimizer()
    data = optimizer.load_and_preprocess_data('data/TechArena2025_data_tidy.jsonl')
    
    # Test with DE_LU for 1 week
    country_data = optimizer.extract_country_data(data, 'DE_LU')
    week_data = country_data[:672]  # 1 week = 672 intervals
    
    # Configure and optimize
    optimizer.max_cycles_per_day = 1.5
    optimizer.c_rate = 0.5
    result = optimizer.optimize(week_data)
    
    print(f'Revenue: €{result["total_revenue"]:,.0f}')
    print(f'Status: {result["solver_status"]}')
    print(f'Detailed results keys: {list(result["detailed_results"].keys())}')
    
    # Check what data is available for CSV generation
    detailed = result["detailed_results"]
    
    print('\n📊 Available optimization variables:')
    for key, value in detailed.items():
        if isinstance(value, dict):
            print(f'  {key}: {len(value)} time points')
        else:
            print(f'  {key}: {value}')
    
    # Check timestamps
    if 'p_ch' in detailed and detailed['p_ch']:
        sample_times = list(detailed['p_ch'].keys())[:5]
        print(f'\n⏰ Sample time indices: {sample_times}')
    
    # Check if we have the data needed for submission
    required_vars = ['p_ch', 'p_dis', 'e_soc', 'c_fcr', 'c_afrr_pos', 'c_afrr_neg']
    missing_vars = [var for var in required_vars if var not in detailed or not detailed[var]]
    
    if missing_vars:
        print(f'\n❌ Missing variables for CSV: {missing_vars}')
    else:
        print('\n✅ All required variables available for CSV generation')
    
    return result

if __name__ == "__main__":
    result = test_csv_generation()