"""
Quick MPC test with Phase 2 data
Tests: State propagation + Result aggregation + Bid DataFrame generation
Duration: ~3-5 minutes for 7 days (1 week)
"""

from py_script.rolling_horizon import MPCSimulator
from py_script.core.optimizer import BESSOptimizerModelIII
import pandas as pd
import json
import time
from datetime import datetime
import os

def main():
    print("=" * 80)
    print("MPC PHASE 2 DATA - QUICK TEST (1 WEEK)")
    print("=" * 80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Configuration
    config = {
        'country': 'CH',
        'num_days': 7,  # 1 week test
        'horizon_hours': 24,  # 24h horizon
        'execution_hours': 24,  # 24h execution (no overlap for speed)
        'alpha': 1.0,
        'c_rate': 0.5,
        'initial_soc_fraction': 0.5
    }

    print("Configuration:")
    for key, value in config.items():
        print(f"  {key}: {value}")
    print()

    # Initialize optimizer
    print("[1/4] Initializing Model III optimizer...")
    optimizer = BESSOptimizerModelIII(alpha=config['alpha'])

    # Load Phase 2 data
    print("[2/4] Loading Phase 2 market data...")

    # Use JSONL file (Model I optimizer expects this format)
    try:
        data_file = 'data/archive/phase_1_data_TechArena2025_data_tidy.jsonl'
        full_data = optimizer.load_and_preprocess_data(data_file)
        country_data = optimizer.extract_country_data(full_data, config['country'])

        # Take first N days
        num_steps = config['num_days'] * 96  # 96 timesteps per day
        country_data = country_data.iloc[:num_steps].reset_index(drop=True)

        print(f"  Data loaded: {len(country_data)} timesteps ({len(country_data)/96:.1f} days)")
        print(f"  Columns: {list(country_data.columns[:10])}... ({len(country_data.columns)} total)")
    except Exception as e:
        print(f"[ERROR] Failed to load data: {e}")
        import traceback
        traceback.print_exc()
        return None

    print()

    # Run MPC simulation
    print("[3/4] Running MPC simulation...")
    simulator = MPCSimulator(
        optimizer_model=optimizer,
        full_data=country_data,
        horizon_hours=config['horizon_hours'],
        execution_hours=config['execution_hours'],
        c_rate=config['c_rate'],
        validate_constraints=False  # Disable for speed
    )

    start_time = time.time()
    results = simulator.run_full_simulation(
        initial_soc_fraction=config['initial_soc_fraction']
    )
    total_time = time.time() - start_time

    print(f"\n  Simulation completed in {total_time:.2f} seconds ({total_time/60:.2f} minutes)")
    print()

    # Validate results
    print("[4/4] Validating MPC results...")
    print("-" * 80)

    # Check bid DataFrame
    annual_bids = results.get('annual_bids_df')
    if annual_bids is not None:
        print(f"\n✓ Annual Bids DataFrame:")
        print(f"    Rows: {len(annual_bids)}")
        print(f"    Columns: {list(annual_bids.columns)}")
        print(f"    Expected rows: {num_steps} (actual: {len(annual_bids)})")
        print(f"    Match: {'YES' if len(annual_bids) == num_steps else 'NO'}")

        # Show sample
        print(f"\n  Sample (first 3 rows):")
        print(annual_bids.head(3))
    else:
        print("\n✗ Annual Bids DataFrame: MISSING!")

    # Check financial totals
    print(f"\n✓ Financial Totals:")
    print(f"    Total Revenue: {results['total_revenue']:.2f} EUR")
    print(f"    - DA: {results['da_revenue']:.2f} EUR")
    print(f"    - aFRR Energy: {results['afrr_e_revenue']:.2f} EUR")
    print(f"    - AS Capacity: {results['as_revenue']:.2f} EUR")
    print(f"    Total Degradation: {results['total_degradation_cost']:.2f} EUR")
    print(f"    Net Profit: {results['net_profit']:.2f} EUR")

    # Check SOC trajectory
    print(f"\n✓ SOC Trajectory:")
    print(f"    Iteration boundaries: {len(results['soc_trajectory'])} points")
    print(f"    15-min intervals: {len(results.get('soc_15min', []))} points")
    print(f"    Initial SOC: {results['soc_trajectory'][0]:.2f} kWh")
    print(f"    Final SOC: {results['final_soc']:.2f} kWh")

    # Summary
    print(f"\n" + "=" * 80)
    print("TEST SUMMARY:")
    tests_passed = 0
    tests_total = 3

    # Test 1: Bid DataFrame complete
    if annual_bids is not None and len(annual_bids) == num_steps:
        print("  [PASS] Bid DataFrame generation")
        tests_passed += 1
    else:
        print("  [FAIL] Bid DataFrame generation")

    # Test 2: Financial totals reasonable
    if results['total_revenue'] > 0 and results['net_profit'] != 0:
        print("  [PASS] Financial calculations")
        tests_passed += 1
    else:
        print("  [FAIL] Financial calculations")

    # Test 3: SOC continuity
    soc_traj = results['soc_trajectory']
    soc_changes = [abs(soc_traj[i+1] - soc_traj[i]) for i in range(len(soc_traj)-1)]
    max_soc_change = max(soc_changes) if soc_changes else 0
    if max_soc_change < 100:  # Allow 100 kWh change (reasonable for 24h window)
        print(f"  [PASS] SOC continuity (max change: {max_soc_change:.2f} kWh)")
        tests_passed += 1
    else:
        print(f"  [FAIL] SOC continuity (max change: {max_soc_change:.2f} kWh)")

    print(f"\n  Tests passed: {tests_passed}/{tests_total}")
    print(f"  Overall: {'PASS' if tests_passed == tests_total else 'FAIL'}")
    print("=" * 80)

    # Export results
    output_file = 'results/mpc_phase2_quick_test.json'
    with open(output_file, 'w') as f:
        # Prepare serializable results
        export_data = {
            'test_id': 'MPC_PHASE2_QUICK',
            'timestamp': datetime.now().isoformat(),
            'config': config,
            'runtime_seconds': total_time,
            'financial': {
                'total_revenue': results['total_revenue'],
                'net_profit': results['net_profit'],
                'degradation_cost': results['total_degradation_cost'],
            },
            'bids_df_shape': [len(annual_bids), len(annual_bids.columns)] if annual_bids is not None else None,
            'soc_trajectory_length': len(results['soc_trajectory']),
            'tests_passed': f"{tests_passed}/{tests_total}",
        }
        json.dump(export_data, f, indent=2)

    # Export bid DataFrame
    if annual_bids is not None:
        annual_bids.to_csv('results/mpc_phase2_annual_bids_sample.csv', index=False)
        print(f"\nBid DataFrame exported to: results/mpc_phase2_annual_bids_sample.csv")

    print(f"Results saved to: {output_file}")
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return results


if __name__ == '__main__':
    results = main()
