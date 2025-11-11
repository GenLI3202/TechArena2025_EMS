"""
Demonstration Script: Full Model III Pipeline
==============================================

This script demonstrates the complete three-layer optimization framework
for Phase II Model (iii) with calendar and cyclic aging costs.

Pipeline Stages:
----------------
1. Data loading and preprocessing
2. Single-horizon test (Model III basic functionality)
3. MPC simulation (rolling horizon for full year)
4. Meta-optimization (find optimal alpha)

Usage:
------
    # Quick test (1 week)
    python demo_model_iii_pipeline.py --mode quick

    # Full year with meta-optimization
    python demo_model_iii_pipeline.py --mode full --country CH

    # Custom alpha test
    python demo_model_iii_pipeline.py --mode mpc --alpha 1.5 --weeks 4

Author: Gen's BESS Optimization Team
Date: November 2025
"""

import sys
from pathlib import Path
import argparse
import json
import logging

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from core.optimizer import BESSOptimizerModelIII, BESSOptimizerModelII
from rolling_horizon import MPCSimulator, MetaOptimizer
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_data(data_file: str, country: str, limit_days: int = None, use_ev_weighting: bool = False):
    """Load and preprocess market data."""
    logger.info("=" * 80)
    logger.info("STEP 1: LOADING DATA")
    logger.info("=" * 80)

    # Create a temporary optimizer just for data loading
    temp_optimizer = BESSOptimizerModelIII(alpha=1.0, use_afrr_ev_weighting=use_ev_weighting)

    # Load data
    logger.info("Loading data from: %s", data_file)
    full_data = temp_optimizer.load_and_preprocess_data(data_file)

    # Extract country data
    logger.info("Extracting data for country: %s", country)
    country_data = temp_optimizer.extract_country_data(full_data, country)

    # Limit to specified days (for testing)
    if limit_days is not None:
        intervals_per_day = int(24 / temp_optimizer.market_params['time_step_hours'])
        max_intervals = limit_days * intervals_per_day
        country_data = country_data.iloc[:max_intervals].copy()
        logger.info("Limited to %d days (%d intervals)", limit_days, len(country_data))

    logger.info("Data loaded: %d intervals (%.1f days)",
               len(country_data),
               len(country_data) * temp_optimizer.market_params['time_step_hours'] / 24)

    return country_data


def test_model_iii_basic(country_data: pd.DataFrame, alpha: float = 1.0, use_ev_weighting: bool = False):
    """Test Model III on a single horizon (basic functionality check)."""
    logger.info("")
    logger.info("=" * 80)
    logger.info("STEP 2: BASIC MODEL III TEST (Single Horizon)")
    logger.info("=" * 80)

    # Create optimizer
    optimizer = BESSOptimizerModelIII(alpha=alpha, use_afrr_ev_weighting=use_ev_weighting)

    # Take first 2 days
    test_data = country_data.iloc[:192].copy()  # 192 = 2 days * 96 intervals/day
    test_data = test_data.reset_index(drop=True)

    logger.info("Testing with %d intervals (%.1f days)",
               len(test_data), len(test_data) * 0.25 / 24)

    # Build and solve
    c_rate = 0.5
    model = optimizer.build_optimization_model(test_data, c_rate)
    solution = optimizer.solve_model(model)

    # Display results
    if solution['status'] in ['optimal', 'feasible']:
        logger.info("✓ Model III basic test PASSED")
        logger.info("  Objective value: %.2f EUR", solution['objective_value'])

        if 'degradation_metrics' in solution:
            metrics = solution['degradation_metrics']
            logger.info("  Cyclic cost: %.2f EUR", metrics.get('total_cyclic_cost_eur', 0))
            logger.info("  Calendar cost: %.2f EUR", metrics.get('total_calendar_cost_eur', 0))
    else:
        logger.error("✗ Model III basic test FAILED: %s", solution.get('status'))

    return solution


def test_mpc_simulation(country_data: pd.DataFrame, alpha: float = 1.0, max_iterations: int = None, use_ev_weighting: bool = False):
    """Test MPC simulation (rolling horizon)."""
    logger.info("")
    logger.info("=" * 80)
    logger.info("STEP 3: MPC SIMULATION (Rolling Horizon)")
    logger.info("=" * 80)

    # Create optimizer
    optimizer = BESSOptimizerModelIII(alpha=alpha, use_afrr_ev_weighting=use_ev_weighting)

    # Create MPC simulator
    simulator = MPCSimulator(
        optimizer_model=optimizer,
        full_data=country_data,
        horizon_hours=48,
        execution_hours=24,
        c_rate=0.5,
        validate_constraints=True,  # Enable validation for testing
    )

    # Run simulation
    results = simulator.run_full_simulation(
        initial_soc_fraction=0.5,
        max_iterations=max_iterations
    )

    # Display summary
    logger.info("")
    logger.info("MPC Simulation Results:")
    logger.info("  Total revenue: %.2f EUR", results['total_revenue'])
    logger.info("  Total degradation: %.2f EUR", results['total_degradation_cost'])
    logger.info("  Net profit: %.2f EUR", results['net_profit'])
    logger.info("  Final SOC: %.2f kWh", results['final_soc'])
    logger.info("  Iterations: %d", results['summary']['iterations'])

    # Check for validation violations
    if results['validation_reports']:
        total_violations = sum(
            r['report']['summary']['total_violations']
            for r in results['validation_reports']
        )
        if total_violations > 0:
            logger.warning("  ⚠ Found %d constraint violations across all iterations", total_violations)
        else:
            logger.info("  ✓ All constraints validated successfully")

    return results


def test_meta_optimization(country_data: pd.DataFrame, alpha_values: list = None, use_ev_weighting: bool = False):
    """Test meta-optimization (alpha parameter sweep)."""
    logger.info("")
    logger.info("=" * 80)
    logger.info("STEP 4: META-OPTIMIZATION (Alpha Parameter Sweep)")
    logger.info("=" * 80)

    if alpha_values is None:
        alpha_values = [0.5, 1.0, 1.5]  # Quick test with 3 values

    # Country configuration
    country_config = {
        'wacc': 0.05,
        'inflation': 0.02,
        'investment_eur_per_kwh': 200,
        'capacity_kwh': 4472,
    }

    # Create meta-optimizer
    meta_opt = MetaOptimizer(
        full_data=country_data,
        country_config=country_config,
        alpha_values=alpha_values,
        c_rate=0.5,
        mpc_config={
            'horizon_hours': 48,
            'execution_hours': 24,
            'validate_constraints': False,  # Disable for speed
        },
        use_afrr_ev_weighting=use_ev_weighting,
    )

    # Find optimal alpha
    results = meta_opt.find_optimal_alpha(parallel=False)

    # Display results
    if results['status'] == 'success':
        logger.info("")
        logger.info("Meta-Optimization Results:")
        logger.info("  Best alpha: %.4f", results['best_alpha'])
        logger.info("  Best 10-year ROI: %.2f%%", results['best_roi'] * 100)
        logger.info("  Annual profit: %.2f EUR",
                   results['best_result']['annual_profit_eur'])

        # Show all alpha results
        logger.info("")
        logger.info("All Alpha Results:")
        for result in results['all_results']:
            if result['status'] == 'success':
                logger.info("  α=%.2f → ROI=%.2f%% | Profit=%.0f EUR",
                           result['alpha'],
                           result['roi_10_year'] * 100,
                           result['annual_profit_eur'])

    return results


def extract_date_data(country_data: pd.DataFrame, target_date_str: str, hours: int):
    """Extract data for a specific date and duration.

    Args:
        country_data: Full year data with datetime column
        target_date_str: Target date in 'YYYY-MM-DD' format
        hours: Number of hours to extract (24, 36, or 48)

    Returns:
        DataFrame with requested time window
    """
    target_date = pd.to_datetime(target_date_str)
    intervals_needed = int(hours * 4)  # 4 intervals per hour (15-min resolution)

    # Find the starting index - use datetime column
    if 'datetime' in country_data.columns:
        time_diffs = abs(country_data['datetime'] - target_date)
        start_idx = time_diffs.argmin()
    else:
        # If no datetime column, assume data is sorted chronologically
        logger.warning("No 'datetime' column found, extracting from beginning")
        start_idx = 0

    # Extract data
    extracted_data = country_data.iloc[start_idx:start_idx + intervals_needed].copy()
    extracted_data = extracted_data.reset_index(drop=True)

    if 'datetime' in country_data.columns:
        actual_start = country_data.iloc[start_idx]['datetime']
        logger.info(f"Extracted {len(extracted_data)} intervals ({hours}h) starting from {actual_start}")
    else:
        logger.info(f"Extracted {len(extracted_data)} intervals ({hours}h)")

    return extracted_data


def run_validation_tests(country_data: pd.DataFrame, config_file: str = None):
    """Run comprehensive Model III validation tests.

    Phases:
    1. Single-horizon tests (24h, 36h, 48h) for summer and winter
    2. Model II comparison
    3. Minimal MPC rolling horizon test
    """
    logger.info("")
    logger.info("=" * 80)
    logger.info("MODEL III VALIDATION TEST SUITE")
    logger.info("=" * 80)

    # Load config
    if config_file is None:
        config_file = Path(__file__).parent / 'mpc_config.json'

    with open(config_file, 'r') as f:
        config = json.load(f)

    val_config = config['execution_modes']['model_iii_validation']

    # Extract test parameters
    summer_date = val_config['test_dates']['summer']
    winter_date = val_config['test_dates']['winter']
    test_horizons = val_config['test_horizons']
    alpha = val_config['alpha_test_value']
    solve_threshold = val_config['solve_time_threshold_seconds']

    results = {
        'phase1_single_horizon': [],
        'phase2_mpc': None,
        'recommended_horizon': None
    }

    # ========================================================================
    # PHASE 1: Single-Horizon Tests
    # ========================================================================
    logger.info("")
    logger.info("=" * 80)
    logger.info("PHASE 1: SINGLE-HORIZON VALIDATION")
    logger.info("=" * 80)
    logger.info(f"Testing horizons: {test_horizons} hours")
    logger.info(f"Alpha value: {alpha}")
    logger.info(f"Dates: Summer ({summer_date}), Winter ({winter_date})")

    max_horizon_under_threshold = 24  # Default to 24h

    for season, date_str in [('Summer', summer_date), ('Winter', winter_date)]:
        logger.info("")
        logger.info(f"--- {season} Tests ({date_str}) ---")

        for hours in test_horizons:
            logger.info(f"\n  Testing {hours}h horizon...")

            # Extract data
            test_data = extract_date_data(country_data, date_str, hours)

            # Test Model III
            optimizer_iii = BESSOptimizerModelIII(alpha=alpha, use_afrr_ev_weighting=True)

            start_time = time.time()
            model_iii = optimizer_iii.build_optimization_model(test_data, c_rate=0.5)
            solution_iii = optimizer_iii.solve_model(model_iii)
            solve_time_iii = time.time() - start_time

            # Test Model II for comparison
            optimizer_ii = BESSOptimizerModelII(alpha=alpha, use_afrr_ev_weighting=True)
            model_ii = optimizer_ii.build_optimization_model(test_data, c_rate=0.5)
            solution_ii = optimizer_ii.solve_model(model_ii)

            # Extract metrics
            status_iii = solution_iii.get('status', 'unknown')
            obj_iii = solution_iii.get('objective_value', 0)
            obj_ii = solution_ii.get('objective_value', 0)

            # Degradation metrics
            deg_iii = solution_iii.get('degradation_metrics', {})
            deg_ii = solution_ii.get('degradation_metrics', {})

            cyclic_iii = deg_iii.get('total_cyclic_cost_eur', 0)
            calendar_iii = deg_iii.get('total_calendar_cost_eur', 0)
            cyclic_ii = deg_ii.get('total_cyclic_cost_eur', 0)

            # Profit components
            profit_da_iii = solution_iii.get('profit_da', 0)
            profit_afrr_iii = solution_iii.get('profit_afrr_energy', 0)
            profit_as_iii = solution_iii.get('profit_as_capacity', 0)

            # Calculate average SOC
            soc_values_iii = list(solution_iii.get('e_soc', {}).values())
            avg_soc_iii = np.mean(soc_values_iii) if soc_values_iii else 0
            soc_values_ii = list(solution_ii.get('e_soc', {}).values())
            avg_soc_ii = np.mean(soc_values_ii) if soc_values_ii else 0

            # Display results
            logger.info(f"    Model III: Status={status_iii}, Obj={obj_iii:,.2f} EUR, Time={solve_time_iii:.2f}s")
            logger.info(f"      - DA Profit: {profit_da_iii:,.2f} EUR")
            logger.info(f"      - aFRR-E Profit: {profit_afrr_iii:,.2f} EUR")
            logger.info(f"      - AS Capacity: {profit_as_iii:,.2f} EUR")
            logger.info(f"      - Cyclic Cost: {cyclic_iii:,.2f} EUR")
            logger.info(f"      - Calendar Cost: {calendar_iii:,.2f} EUR")
            logger.info(f"      - Avg SOC: {avg_soc_iii:,.1f} kWh ({avg_soc_iii/4472*100:.1f}%)")

            logger.info(f"    Model II:  Obj={obj_ii:,.2f} EUR, Cyclic={cyclic_ii:,.2f} EUR, Avg SOC={avg_soc_ii:,.1f} kWh")
            logger.info(f"    Comparison: Obj Δ={obj_iii-obj_ii:+,.2f} EUR, SOC Δ={avg_soc_iii-avg_soc_ii:+,.1f} kWh")

            # Check solve time threshold
            if solve_time_iii < solve_threshold:
                max_horizon_under_threshold = max(max_horizon_under_threshold, hours)
                logger.info(f"    ✓ Solve time {solve_time_iii:.2f}s < {solve_threshold}s threshold")
            else:
                logger.warning(f"    ⚠ Solve time {solve_time_iii:.2f}s > {solve_threshold}s threshold")

            # Store results
            results['phase1_single_horizon'].append({
                'season': season,
                'date': date_str,
                'hours': hours,
                'model_iii_obj': obj_iii,
                'model_ii_obj': obj_ii,
                'obj_diff': obj_iii - obj_ii,
                'cyclic_cost_iii': cyclic_iii,
                'calendar_cost_iii': calendar_iii,
                'cyclic_cost_ii': cyclic_ii,
                'avg_soc_iii': avg_soc_iii,
                'avg_soc_ii': avg_soc_ii,
                'soc_reduction': avg_soc_ii - avg_soc_iii,
                'solve_time': solve_time_iii,
                'status': status_iii
            })

    # Determine recommended horizon for MPC
    results['recommended_horizon'] = max_horizon_under_threshold
    logger.info("")
    logger.info("=" * 80)
    logger.info(f"PHASE 1 COMPLETE - Recommended MPC Horizon: {max_horizon_under_threshold}h")
    logger.info("=" * 80)

    # ========================================================================
    # PHASE 2: Minimal MPC Rolling Horizon Test
    # ========================================================================
    logger.info("")
    logger.info("=" * 80)
    logger.info("PHASE 2: MINIMAL MPC ROLLING HORIZON TEST")
    logger.info("=" * 80)

    mpc_horizon = max_horizon_under_threshold
    mpc_execution = val_config['mpc_execution_hours']
    mpc_iterations = val_config['mpc_test_iterations']

    logger.info(f"MPC Configuration:")
    logger.info(f"  Horizon: {mpc_horizon}h")
    logger.info(f"  Execution: {mpc_execution}h")
    logger.info(f"  Iterations: {mpc_iterations}")
    logger.info(f"  Start date: {summer_date} (using summer data)")

    # Extract data for MPC test
    mpc_days = int(np.ceil(mpc_iterations * mpc_execution / 24) + mpc_horizon / 24)
    logger.info(f"  Data needed: {mpc_days} days")

    mpc_data = extract_date_data(country_data, summer_date, mpc_days * 24)

    # Create optimizer and simulator
    optimizer_mpc = BESSOptimizerModelIII(alpha=alpha, use_afrr_ev_weighting=True)

    simulator = MPCSimulator(
        optimizer_model=optimizer_mpc,
        full_data=mpc_data,
        horizon_hours=mpc_horizon,
        execution_hours=mpc_execution,
        c_rate=0.5,
        validate_constraints=True,
    )

    # Run MPC simulation
    logger.info("")
    logger.info("Running MPC simulation...")
    mpc_results = simulator.run_full_simulation(
        initial_soc_fraction=0.5,
        max_iterations=mpc_iterations
    )

    # Display MPC results
    logger.info("")
    logger.info("MPC Simulation Results:")
    logger.info(f"  Iterations completed: {mpc_results['summary']['iterations']}")
    logger.info(f"  Total revenue: {mpc_results['total_revenue']:,.2f} EUR")
    logger.info(f"  Total degradation: {mpc_results['total_degradation_cost']:,.2f} EUR")
    logger.info(f"  Net profit: {mpc_results['net_profit']:,.2f} EUR")
    logger.info(f"  Final SOC: {mpc_results['final_soc']:,.2f} kWh")

    # Check for violations
    if mpc_results['validation_reports']:
        total_violations = sum(
            r['report']['summary']['total_violations']
            for r in mpc_results['validation_reports']
        )
        if total_violations > 0:
            logger.warning(f"  ⚠ Found {total_violations} constraint violations")
        else:
            logger.info(f"  ✓ All constraints validated successfully")

    results['phase2_mpc'] = {
        'iterations': mpc_results['summary']['iterations'],
        'total_revenue': mpc_results['total_revenue'],
        'total_degradation': mpc_results['total_degradation_cost'],
        'net_profit': mpc_results['net_profit'],
        'final_soc': mpc_results['final_soc'],
        'violations': total_violations if mpc_results['validation_reports'] else 0
    }

    # ========================================================================
    # SUMMARY AND EXPORT
    # ========================================================================
    logger.info("")
    logger.info("=" * 80)
    logger.info("VALIDATION TEST SUITE COMPLETE")
    logger.info("=" * 80)

    # Create summary report
    logger.info("")
    logger.info("SUMMARY:")
    logger.info("-" * 80)
    logger.info("Phase 1 Results (Single Horizon):")
    for result in results['phase1_single_horizon']:
        logger.info(f"  {result['season']:6} {result['hours']:2}h: "
                   f"Obj={result['model_iii_obj']:>8,.0f} EUR, "
                   f"Calendar={result['calendar_cost_iii']:>6,.0f} EUR, "
                   f"SOC Reduction={result['soc_reduction']:>+6,.0f} kWh, "
                   f"Time={result['solve_time']:>5,.1f}s")

    logger.info("")
    logger.info(f"Phase 2 Results (MPC):")
    logger.info(f"  Net Profit: {results['phase2_mpc']['net_profit']:,.2f} EUR")
    logger.info(f"  Violations: {results['phase2_mpc']['violations']}")

    # Export results to CSV
    output_dir = Path(__file__).parent.parent.parent / 'results'
    output_dir.mkdir(exist_ok=True, parents=True)

    # Export Phase 1 results
    df_phase1 = pd.DataFrame(results['phase1_single_horizon'])
    output_file = output_dir / 'model_iii_validation_phase1.csv'
    df_phase1.to_csv(output_file, index=False)
    logger.info(f"\nPhase 1 results exported to: {output_file}")

    # Export Phase 2 results
    with open(output_dir / 'model_iii_validation_phase2.json', 'w') as f:
        json.dump(results['phase2_mpc'], f, indent=2)
    logger.info(f"Phase 2 results exported to: {output_dir / 'model_iii_validation_phase2.json'}")

    logger.info("")
    logger.info("=" * 80)

    return results


def main():
    """Main demonstration function."""
    parser = argparse.ArgumentParser(description='Model III Pipeline Demonstration')
    parser.add_argument('--mode', choices=['quick', 'basic', 'mpc', 'meta', 'full', 'validation'],
                       default='quick', help='Execution mode')
    parser.add_argument('--country', default='CH', help='Country code (DE, AT, CH, HU, CZ)')
    parser.add_argument('--alpha', type=float, default=1.0, help='Alpha value (for basic/mpc modes)')
    parser.add_argument('--days', type=int, help='Limit to N days (for testing)')
    parser.add_argument('--weeks', type=int, help='Limit to N weeks (for testing)')
    parser.add_argument('--data-file', default='../../data/TechArena2025_data_tidy.jsonl',
                       help='Path to data file')
    parser.add_argument('--use-ev-weighting', action='store_true',
                       help='Enable Expected Value weighting for aFRR energy bids (default: False)')

    args = parser.parse_args()

    # Calculate day limit
    limit_days = None
    if args.days:
        limit_days = args.days
    elif args.weeks:
        limit_days = args.weeks * 7
    elif args.mode == 'quick':
        limit_days = 7  # 1 week for quick test

    # Load data
    data_file = Path(__file__).parent.parent.parent / args.data_file
    if not data_file.exists():
        logger.error("Data file not found: %s", data_file)
        logger.error("Please update --data-file argument")
        return

    country_data = load_data(str(data_file), args.country, limit_days, use_ev_weighting=args.use_ev_weighting)

    # Execute based on mode
    if args.mode == 'validation':
        # Run comprehensive validation test suite
        run_validation_tests(country_data)

    elif args.mode in ['quick', 'basic']:
        test_model_iii_basic(country_data, alpha=args.alpha, use_ev_weighting=args.use_ev_weighting)

    if args.mode in ['quick', 'mpc']:
        max_iter = 7 if args.mode == 'quick' else None
        test_mpc_simulation(country_data, alpha=args.alpha, max_iterations=max_iter, use_ev_weighting=args.use_ev_weighting)

    if args.mode in ['quick', 'meta', 'full']:
        if args.mode == 'quick':
            alpha_values = [0.5, 1.0, 1.5]  # Quick test
        elif args.mode == 'full':
            alpha_values = [0.1, 0.2, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]  # Full sweep
        else:
            alpha_values = [0.5, 1.0, 1.5, 2.0]  # Medium sweep

        test_meta_optimization(country_data, alpha_values, use_ev_weighting=args.use_ev_weighting)

    logger.info("")
    logger.info("=" * 80)
    logger.info("DEMONSTRATION COMPLETE")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
