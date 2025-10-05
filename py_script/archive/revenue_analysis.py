#!/usr/bin/env python3
"""
Revenue Analysis for BESS Optimization
======================================

This script analyzes the revenue potential of the BESS optimization model
with different configurations and provides detailed breakdown.
"""

import sys
import json
import os
from model import BESSOptimizer

def main():
    print("BESS Revenue Analysis")
    print("=" * 50)
    
    # Load test data
    print("Loading test data...")
    with open('../data/TechArena2025_data_tidy.jsonl', 'r') as f:
        all_data = [json.loads(line) for line in f]
    
    # Create 2-day test subset for Austria
    austria_2days = [d for d in all_data if d['country'] == 'AT'][:192]
    
    # Save subset
    test_file = 'test_revenue.jsonl'
    with open(test_file, 'w') as f:
        for record in austria_2days:
            f.write(json.dumps(record) + '\n')
    
    print(f"Created 2-day test dataset: {len(austria_2days)} records")
    print()
    
    # Initialize optimizer
    optimizer = BESSOptimizer()
    
    # Test configurations
    configs = [
        {'c_rate': 0.5, 'cycle_limit': 1.0, 'name': 'Conservative'},
        {'c_rate': 1.0, 'cycle_limit': 1.0, 'name': 'Standard'}, 
        {'c_rate': 2.0, 'cycle_limit': 1.0, 'name': 'Aggressive'}
    ]
    
    print("Revenue Results (Austria, 2-day scenarios):")
    print("=" * 70)
    print(f"{'Config':<12} {'C-rate':<8} {'2-day Revenue':<15} {'Daily Avg':<12} {'Annual Projection'}")
    print("-" * 70)
    
    results = []
    
    for config in configs:
        try:
            result = optimizer.optimize_bess(test_file, 
                                           c_rate=config['c_rate'], 
                                           cycle_limit=config['cycle_limit'])
            
            if result['success']:
                revenue_2d = result['objective_value']
                daily_avg = revenue_2d / 2
                annual_projection = daily_avg * 365
                
                print(f"{config['name']:<12} {config['c_rate']:<8.1f} "
                      f"{revenue_2d:<15.2f} {daily_avg:<12.2f} {annual_projection:>15,.0f}")
                
                results.append({
                    'config': config['name'],
                    'c_rate': config['c_rate'],
                    'revenue_2d': revenue_2d,
                    'daily_avg': daily_avg,
                    'annual_projection': annual_projection,
                    'success': True
                })
            else:
                print(f"{config['name']:<12} {config['c_rate']:<8.1f} FAILED: {result.get('error', 'Unknown')}")
                results.append({
                    'config': config['name'],
                    'c_rate': config['c_rate'],
                    'success': False,
                    'error': result.get('error', 'Unknown')
                })
                
        except Exception as e:
            print(f"{config['name']:<12} {config['c_rate']:<8.1f} ERROR: {str(e)}")
            results.append({
                'config': config['name'],
                'c_rate': config['c_rate'],
                'success': False,
                'error': str(e)
            })
    
    print()
    
    # Analyze successful results
    successful = [r for r in results if r['success']]
    if successful:
        print("Analysis Summary:")
        print("=" * 50)
        
        best = max(successful, key=lambda x: x['annual_projection'])
        worst = min(successful, key=lambda x: x['annual_projection'])
        
        print(f"Best configuration: {best['config']} (C-rate {best['c_rate']})")
        print(f"  Annual projection: {best['annual_projection']:,.0f} EUR")
        print()
        print(f"Worst configuration: {worst['config']} (C-rate {worst['c_rate']})")
        print(f"  Annual projection: {worst['annual_projection']:,.0f} EUR")
        print()
        
        improvement = (best['annual_projection'] / worst['annual_projection'] - 1) * 100
        print(f"Performance improvement: {improvement:.1f}%")
        
        print()
        print("Revenue Breakdown Analysis:")
        print("-" * 30)
        print("Note: This is based on 2-day Austria data scaled to annual.")
        print("Actual annual optimization may yield different results due to:")
        print("- Seasonal price variations")
        print("- Long-term cycling constraints")
        print("- Market coupling effects")
        print("- Calendar-based pricing patterns")
    
    else:
        print("No successful optimizations found!")
    
    # Save results
    results_file = 'revenue_analysis_results.json'
    with open(results_file, 'w') as f:
        json.dump({
            'test_period': '2024-01-01 to 2024-01-02',
            'country': 'Austria',
            'results': results,
            'summary': {
                'best_config': best['config'] if successful else None,
                'best_annual_projection': best['annual_projection'] if successful else None,
                'test_type': '2-day scaled projection'
            }
        }, f, indent=2)
    
    print(f"\nResults saved to: {results_file}")
    
    # Clean up
    if os.path.exists(test_file):
        os.remove(test_file)

if __name__ == "__main__":
    main()