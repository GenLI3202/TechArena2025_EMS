"""
Fair Comparison: Baseline (ALL constraints) vs Partial Optimized (Cst-3 only)
==============================================================================

This script compares:
- Baseline: optimizer_original_to_compare.py (ALL Cst-3, Cst-8, Cst-9 enabled)
- Partial Optimized: optimizer.py (ONLY Cst-3 enabled, Cst-8 & Cst-9 disabled)

Both run on the EXACT SAME 1-day test data for fair comparison.
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import logging

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import both optimizers
from py_script.core.optimizer import BESSOptimizerModelII as PartialOptimizer
from py_script.core.optimizer_all_activated_slow import BESSOptimizerModelII as BaselineOptimizer

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
TEST_CONFIG = {
    'country': 'HU',
    'c_rate': 0.5,
    'alpha': 1.0,
    'num_days': 2,  # Changed to 2 days for performance testing
    'week': 14,
    'base_date': '2024-04-01'
}

# Data files
DATA_FILE = project_root / 'data' / 'TechArena2025_data_tidy.jsonl'
AFRR_ENERGY_FILE = project_root / 'data' / 'phase2_processed' / 'parquet' / 'afrr_energy.parquet'

# Output directory
OUTPUT_DIR = project_root / 'results/model_ii_validation/baseline_vs_partial'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def run_optimizer(optimizer_name, optimizer, week_data, c_rate):
    """Run a single optimizer and return results."""

    logger.info(f"\n{'='*80}")
    logger.info(f"Running {optimizer_name}")
    logger.info(f"{'='*80}")

    # Build model
    logger.info("Building optimization model...")
    build_start = datetime.now()
    model = optimizer.build_optimization_model(week_data, c_rate, daily_cycle_limit=None)
    build_time = (datetime.now() - build_start).total_seconds()

    num_vars = model.nvariables()
    num_constraints = model.nconstraints()

    logger.info(f"Model built: {num_vars:,} variables, {num_constraints:,} constraints")
    logger.info(f"Build time: {build_time:.2f}s")

    # Solve model
    logger.info("Solving optimization model...")
    solution = optimizer.solve_model(model)

    if solution['status'] not in ['optimal', 'feasible']:
        logger.error(f"Optimization FAILED: {solution['status']}")
        return None

    # Extract metrics
    obj_value = solution['objective_value']
    solve_time = solution['solve_time']

    # Calculate revenue breakdown
    da_revenue = sum(
        (week_data.loc[t, 'price_day_ahead'] / 1000) * (solution['p_dis'].get(t, 0) - solution['p_ch'].get(t, 0)) * 0.25
        for t in range(len(week_data))
    )

    afrr_e_revenue = sum(
        (week_data.loc[t, 'price_afrr_energy_pos'] / 1000) * solution.get('p_afrr_pos_e', {}).get(t, 0) * 0.25 +
        (week_data.loc[t, 'price_afrr_energy_neg'] / 1000) * solution.get('p_afrr_neg_e', {}).get(t, 0) * 0.25
        for t in range(len(week_data))
    )

    # Extract degradation cost from degradation_metrics
    degradation_cost = solution.get('degradation_metrics', {}).get('total_cyclic_cost_eur', 0)

    # Correct capacity revenue calculation: obj = da + afrr_e + capacity - degradation
    # Therefore: capacity = obj - da - afrr_e + degradation
    capacity_revenue = obj_value - da_revenue - afrr_e_revenue + degradation_cost

    # Print results
    logger.info(f"\n{optimizer_name} RESULTS:")
    logger.info(f"  Status: {solution['status']}")
    logger.info(f"  Build Time: {build_time:.2f}s")
    logger.info(f"  Solve Time: {solve_time:.2f}s")
    logger.info(f"  Total Time: {build_time + solve_time:.2f}s")
    logger.info(f"  ")
    logger.info(f"  Model Size:")
    logger.info(f"    Variables: {num_vars:,}")
    logger.info(f"    Constraints: {num_constraints:,}")
    logger.info(f"  ")
    logger.info(f"  Objective Value: €{obj_value:,.2f}")
    logger.info(f"    DA Revenue: €{da_revenue:,.2f}")
    logger.info(f"    aFRR Energy Revenue: €{afrr_e_revenue:,.2f}")
    logger.info(f"    Capacity Revenue: €{capacity_revenue:,.2f}")
    logger.info(f"  ")
    logger.info(f"  Degradation:")
    logger.info(f"    Cost: €{degradation_cost:,.2f}")

    # Show detailed degradation metrics if available
    deg_metrics = solution.get('degradation_metrics', {})
    if deg_metrics:
        logger.info(f"    Equivalent Full Cycles: {deg_metrics.get('equivalent_full_cycles', 0):.2f}")
        logger.info(f"    Total Throughput: {deg_metrics.get('total_throughput_kwh', 0):.2f} kWh")
        logger.info(f"    Average DOD: {deg_metrics.get('average_dod', 0):.4f}")

    return {
        'optimizer_name': optimizer_name,
        'status': solution['status'],
        'build_time_sec': build_time,
        'solve_time_sec': solve_time,
        'total_time_sec': build_time + solve_time,
        'num_variables': num_vars,
        'num_constraints': num_constraints,
        'objective_value': obj_value,
        'da_revenue': da_revenue,
        'afrr_e_revenue': afrr_e_revenue,
        'capacity_revenue': capacity_revenue,
        'degradation_cost': degradation_cost,
        'solution': solution,
    }


def main():
    logger.info("="*80)
    logger.info(f"FAIR COMPARISON: Baseline vs Partial Optimized ({TEST_CONFIG['num_days']}-day test)")
    logger.info("="*80)
    logger.info("Baseline: ALL constraints (Cst-3, Cst-8, Cst-9)")
    logger.info("Partial: ONLY Cst-3 enabled (Cst-8, Cst-9 disabled)")
    logger.info("="*80)

    # Initialize optimizers
    logger.info("\nInitializing optimizers...")
    baseline_opt = BaselineOptimizer(alpha=TEST_CONFIG['alpha'])
    partial_opt = PartialOptimizer(alpha=TEST_CONFIG['alpha'])

    # Load data (shared for both)
    logger.info(f"\nLoading data for Week {TEST_CONFIG['week']}, {TEST_CONFIG['num_days']} days...")
    full_data = baseline_opt.load_and_preprocess_data(
        str(DATA_FILE),
        afrr_energy_file=str(AFRR_ENERGY_FILE)
    )

    # Extract country data
    country_data = baseline_opt.extract_country_data(full_data, TEST_CONFIG['country'])

    # Filter to Week 14
    base_date = pd.Timestamp(TEST_CONFIG['base_date'])
    week_start_date = base_date + timedelta(weeks=TEST_CONFIG['week'] - 1)
    end_date = week_start_date + timedelta(days=TEST_CONFIG['num_days'])

    week_data = country_data[
        (country_data['timestamp'] >= week_start_date) &
        (country_data['timestamp'] < end_date)
    ].reset_index(drop=True)

    logger.info(f"Date range: {week_data['timestamp'].min()} to {week_data['timestamp'].max()}")
    logger.info(f"Loaded {len(week_data)} intervals for {TEST_CONFIG['num_days']} days")

    # Run baseline
    baseline_results = run_optimizer(
        "BASELINE (ALL constraints)",
        baseline_opt,
        week_data,
        TEST_CONFIG['c_rate']
    )

    # Run partial optimized
    partial_results = run_optimizer(
        "PARTIAL OPTIMIZED (Cst-3 only)",
        partial_opt,
        week_data,
        TEST_CONFIG['c_rate']
    )

    # Comparison
    logger.info("\n" + "="*80)
    logger.info("COMPARISON SUMMARY")
    logger.info("="*80)

    if baseline_results and partial_results:
        logger.info(f"\n{'Metric':<40} {'Baseline':<20} {'Partial Opt':<20} {'Difference'}")
        logger.info("-"*100)

        # Model size
        logger.info(f"{'Variables':<40} {baseline_results['num_variables']:<20,} {partial_results['num_variables']:<20,} "
                   f"{partial_results['num_variables'] - baseline_results['num_variables']:+,}")
        logger.info(f"{'Constraints':<40} {baseline_results['num_constraints']:<20,} {partial_results['num_constraints']:<20,} "
                   f"{partial_results['num_constraints'] - baseline_results['num_constraints']:+,}")

        # Timing
        logger.info(f"{'Build Time (s)':<40} {baseline_results['build_time_sec']:<20.2f} {partial_results['build_time_sec']:<20.2f} "
                   f"{partial_results['build_time_sec'] - baseline_results['build_time_sec']:+.2f}")
        logger.info(f"{'Solve Time (s)':<40} {baseline_results['solve_time_sec']:<20.2f} {partial_results['solve_time_sec']:<20.2f} "
                   f"{partial_results['solve_time_sec'] - baseline_results['solve_time_sec']:+.2f}")
        logger.info(f"{'Total Time (s)':<40} {baseline_results['total_time_sec']:<20.2f} {partial_results['total_time_sec']:<20.2f} "
                   f"{partial_results['total_time_sec'] - baseline_results['total_time_sec']:+.2f}")

        # Speedup
        speedup = baseline_results['solve_time_sec'] / partial_results['solve_time_sec'] if partial_results['solve_time_sec'] > 0 else float('inf')
        logger.info(f"{'Speedup (Baseline/Partial)':<40} {'-':<20} {speedup:<20.2f}x {'SLOWER' if speedup < 1 else 'FASTER'}")

        # Revenue
        logger.info("")
        logger.info(f"{'Objective Value (€)':<40} {baseline_results['objective_value']:<20,.2f} {partial_results['objective_value']:<20,.2f} "
                   f"{partial_results['objective_value'] - baseline_results['objective_value']:+,.2f}")
        logger.info(f"{'DA Revenue (€)':<40} {baseline_results['da_revenue']:<20,.2f} {partial_results['da_revenue']:<20,.2f} "
                   f"{partial_results['da_revenue'] - baseline_results['da_revenue']:+,.2f}")
        logger.info(f"{'aFRR Energy Revenue (€)':<40} {baseline_results['afrr_e_revenue']:<20,.2f} {partial_results['afrr_e_revenue']:<20,.2f} "
                   f"{partial_results['afrr_e_revenue'] - baseline_results['afrr_e_revenue']:+,.2f}")
        logger.info(f"{'Capacity Revenue (€)':<40} {baseline_results['capacity_revenue']:<20,.2f} {partial_results['capacity_revenue']:<20,.2f} "
                   f"{partial_results['capacity_revenue'] - baseline_results['capacity_revenue']:+,.2f}")

        # Percentage difference
        pct_diff = ((partial_results['objective_value'] - baseline_results['objective_value']) / baseline_results['objective_value'] * 100) if baseline_results['objective_value'] != 0 else 0
        logger.info(f"{'Profit Improvement (%)':<40} {'-':<20} {pct_diff:<20.2f}% {''}")

        logger.info("="*80)

        # Key findings
        logger.info("\nKEY FINDINGS:")
        if pct_diff > 1:
            logger.info(f"✅ Partial optimization achieves {pct_diff:.1f}% HIGHER profit")
        elif pct_diff < -1:
            logger.info(f"❌ Partial optimization achieves {abs(pct_diff):.1f}% LOWER profit")
        else:
            logger.info(f"≈ Partial optimization achieves similar profit ({pct_diff:.2f}% difference)")

        if speedup > 1:
            logger.info(f"✅ Partial optimization is {speedup:.2f}x FASTER")
        elif speedup < 1:
            logger.info(f"❌ Partial optimization is {1/speedup:.2f}x SLOWER")
        else:
            logger.info(f"≈ Similar solve time")

        logger.info(f"📊 Model size reduction: {baseline_results['num_constraints'] - partial_results['num_constraints']:,} fewer constraints")

    logger.info("\n" + "="*80)


if __name__ == "__main__":
    main()
