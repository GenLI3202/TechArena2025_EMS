"""
Quick MPC Rolling Horizon Validation Test
Duration: ~5-10 minutes
Tests: SOC continuity + solve performance
"""

from py_script.rolling_horizon import MPCSimulator
from py_script.core.optimizer import BESSOptimizerModelIII
import json
import time
from datetime import datetime

def main():
    print("=" * 60)
    print("MPC ROLLING HORIZON - QUICK VALIDATION TEST")
    print("=" * 60)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Configuration
    config = {
        'country': 'CH',
        'num_days': 5,  # Use first 5 days of data
        'horizon_hours': 32,
        'execution_hours': 24,
        'alpha': 1.0,
        'c_rate': 0.5,
        'initial_soc_fraction': 0.5
    }

    print("Configuration:")
    for key, value in config.items():
        print(f"  {key}: {value}")
    print()

    # Initialize optimizer
    print("[1/4] Initializing optimizer...")
    optimizer = BESSOptimizerModelIII(alpha=config['alpha'])

    # Load data
    print("[2/4] Loading market data...")
    full_data = optimizer.load_and_preprocess_data('data/archive/phase_1_data_TechArena2025_data_tidy.jsonl')
    data = optimizer.extract_country_data(full_data, config['country'])

    # Use first N days of data (96 timesteps per day = 15-min intervals)
    num_steps = config['num_days'] * 96
    data = data.iloc[:num_steps].copy()
    data.reset_index(drop=True, inplace=True)

    print(f"  Data loaded: {len(data)} timesteps ({len(data)/96:.1f} days)")
    print()

    # Run MPC simulation
    print("[3/4] Running MPC simulation...")
    simulator = MPCSimulator(
        optimizer_model=optimizer,
        full_data=data,
        horizon_hours=config['horizon_hours'],
        execution_hours=config['execution_hours'],
        c_rate=config['c_rate'],
        validate_constraints=True  # Enable validation
    )

    start_time = time.time()
    results = simulator.run_full_simulation(
        initial_soc_fraction=config['initial_soc_fraction']
    )
    total_time = time.time() - start_time

    print(f"  Simulation completed in {total_time:.2f} seconds ({total_time/60:.2f} minutes)")
    print()

    # Validate results
    print("[4/4] Validating results...")
    print("-" * 60)

    validation_results = {
        'test_id': 'MPC_QUICK_VALIDATION',
        'timestamp': datetime.now().isoformat(),
        'config': config,
        'performance': {},
        'correctness': {},
        'overall_status': 'PENDING'
    }

    # --- Performance Validation ---
    print("\nPERFORMANCE VALIDATION:")

    iterations_completed = len(results['iteration_results'])
    solve_times = [iter_result.get('solve_time_sec', 0)
                   for iter_result in results['iteration_results']]

    mean_solve_time = sum(solve_times) / len(solve_times)
    max_solve_time = max(solve_times)

    validation_results['performance'] = {
        'total_simulation_time_sec': total_time,
        'iterations_completed': iterations_completed,
        'iterations_expected': 5,
        'mean_solve_time_sec': mean_solve_time,
        'max_solve_time_sec': max_solve_time,
        'solve_times_per_iteration': solve_times
    }

    perf_pass = (
        total_time < 300 and  # < 5 minutes total
        iterations_completed == 5 and
        mean_solve_time < 60  # < 60 sec average
    )

    print(f"  [OK] Iterations completed: {iterations_completed}/5")
    print(f"  [OK] Total time: {total_time:.2f}s ({total_time/60:.2f} min)")
    print(f"  [OK] Mean solve time: {mean_solve_time:.2f}s")
    print(f"  [OK] Max solve time: {max_solve_time:.2f}s")
    print(f"  => Performance: {'PASS' if perf_pass else 'FAIL'}")

    # --- SOC Continuity Validation ---
    print("\nSOC CONTINUITY VALIDATION:")

    soc_trajectory = results['soc_trajectory']
    soc_changes = []
    for i in range(len(soc_trajectory) - 1):
        change = abs(soc_trajectory[i+1] - soc_trajectory[i])
        soc_changes.append(change)

    max_soc_change = max(soc_changes) if soc_changes else 0

    validation_results['correctness']['soc_continuity'] = {
        'soc_trajectory': soc_trajectory,
        'soc_changes_at_boundaries': soc_changes,
        'max_soc_change_kwh': max_soc_change,
        'initial_soc': soc_trajectory[0],
        'final_soc': results['final_soc']
    }

    soc_pass = max_soc_change < 0.1  # < 0.1 kWh tolerance

    print(f"  [OK] Initial SOC: {soc_trajectory[0]:.2f} kWh")
    print(f"  [OK] Final SOC: {results['final_soc']:.2f} kWh")
    print(f"  [OK] Max SOC change at boundaries: {max_soc_change:.4f} kWh")
    print(f"  [OK] SOC trajectory: {[f'{s:.1f}' for s in soc_trajectory]}")
    print(f"  => SOC Continuity: {'PASS' if soc_pass else 'FAIL'}")

    # --- Constraint Validation ---
    print("\nCONSTRAINT VALIDATION:")

    all_violations = []
    for iter_result in results['iteration_results']:
        if 'validation_report' in iter_result:
            violations = iter_result['validation_report'].get('violations', [])
            all_violations.extend(violations)

    validation_results['correctness']['constraints'] = {
        'total_violations': len(all_violations),
        'violations': all_violations
    }

    constraint_pass = len(all_violations) == 0

    print(f"  [OK] Total violations: {len(all_violations)}")
    if all_violations:
        print("  [WARNING] Violations found:")
        for v in all_violations[:5]:  # Show first 5
            print(f"    - {v}")
    print(f"  => Constraints: {'PASS' if constraint_pass else 'FAIL'}")

    # --- Economic Metrics ---
    print("\nECONOMIC METRICS (Informational):")
    print(f"  • Total revenue: {results['total_revenue']:.2f} EUR")
    print(f"  • Total degradation cost: {results['total_degradation_cost']:.2f} EUR")
    print(f"  • Net profit: {results['net_profit']:.2f} EUR")
    print(f"  • Daily average profit: {results['net_profit']/5:.2f} EUR/day")

    validation_results['economic'] = {
        'total_revenue': results['total_revenue'],
        'degradation_cost': results['total_degradation_cost'],
        'net_profit': results['net_profit'],
        'daily_avg_profit': results['net_profit'] / 5
    }

    # --- Overall Status ---
    overall_pass = perf_pass and soc_pass and constraint_pass
    validation_results['overall_status'] = 'PASS' if overall_pass else 'FAIL'

    print("\n" + "=" * 60)
    print(f"OVERALL VALIDATION: {validation_results['overall_status']}")
    if overall_pass:
        print("[PASS] All tests passed - MPC implementation validated!")
    else:
        print("[FAIL] Some tests failed - review results above")
    print("=" * 60)

    # Export results
    import os
    os.makedirs('results/mpc_validation_quick', exist_ok=True)
    output_file = 'results/mpc_validation_quick/validation_results.json'
    with open(output_file, 'w') as f:
        json.dump(validation_results, f, indent=2)

    print(f"\nResults saved to: {output_file}")
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return validation_results


if __name__ == '__main__':
    results = main()

    # Exit code for CI/CD integration
    exit(0 if results['overall_status'] == 'PASS' else 1)
