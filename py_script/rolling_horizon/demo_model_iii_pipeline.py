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

from core.optimizer import BESSOptimizerModelIII
from rolling_horizon import MPCSimulator, MetaOptimizer
import pandas as pd
import numpy as np

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


def main():
    """Main demonstration function."""
    parser = argparse.ArgumentParser(description='Model III Pipeline Demonstration')
    parser.add_argument('--mode', choices=['quick', 'basic', 'mpc', 'meta', 'full'],
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
    if args.mode in ['quick', 'basic']:
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
