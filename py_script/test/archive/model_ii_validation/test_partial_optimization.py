"""
Test the partially optimized Model (ii) on Week 14
- Cst-3 (Simultaneous Ops): ENABLED
- Cst-8 (Cross-Market): DISABLED
- Cst-9 (MinBid): DISABLED

Compare performance and validate constraints.
"""
import sys
from pathlib import Path
import json
import logging
from datetime import datetime, timedelta
import pandas as pd

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from py_script.core.optimizer import BESSOptimizerModelII

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
TEST_CONFIG = {
    'country': 'HU',
    'c_rate': 0.5,
    'alpha': 1.0,
    'num_days': 1,  # Changed from 2 to 1 day
    'week': 14,
    'base_date': '2024-04-01'
}

# Data files
DATA_FILE = project_root / 'data' / 'TechArena2025_data_tidy.jsonl'
AFRR_ENERGY_FILE = project_root / 'data' / 'phase2_processed' / 'parquet' / 'afrr_energy.parquet'

# Output directory
OUTPUT_DIR = project_root / 'results/model_ii_validation/partial_optimization_test'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_week_data(week_num, num_days, base_date, country):
    """Load data for a specific week."""

    # Parse base date
    start_date = datetime.strptime(base_date, '%Y-%m-%d')

    # Calculate week offset
    week_start_date = start_date + timedelta(weeks=week_num - 1)
    end_date = week_start_date + timedelta(days=num_days)

    # Load main data
    df = pd.read_json(DATA_FILE, lines=True)

    # Filter by country and date range
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df[(df['country'] == country) &
            (df['timestamp'] >= week_start_date) &
            (df['timestamp'] < end_date)]

    # Load aFRR energy data
    afrr_df = pd.read_parquet(AFRR_ENERGY_FILE)
    afrr_df['timestamp'] = pd.to_datetime(afrr_df['timestamp'])
    afrr_df = afrr_df[(afrr_df['timestamp'] >= week_start_date) &
                      (afrr_df['timestamp'] < end_date)]

    # Select country-specific columns
    pos_col = f'{country}_Pos'
    neg_col = f'{country}_Neg'
    afrr_df = afrr_df[['timestamp', pos_col, neg_col]].rename(columns={
        pos_col: 'afrr_pos_price',
        neg_col: 'afrr_neg_price'
    })

    # Merge data
    merged_df = df.merge(afrr_df,
                         on='timestamp',
                         how='left')

    # Fill NaN values with 0
    merged_df['afrr_pos_price'] = merged_df['afrr_pos_price'].fillna(0)
    merged_df['afrr_neg_price'] = merged_df['afrr_neg_price'].fillna(0)

    # Convert to list of dictionaries
    week_data = merged_df.to_dict('records')

    return week_data


def check_constraint_violations(solution, week_data):
    """Check if solution violates any of the removed constraints (Cst-8, Cst-9)."""

    violations = {
        'no_simultaneous_rule': [],
        'cross_market_exclusivity': [],
        'min_bid_rule_da': [],
        'min_bid_rule_afrr_pos': [],
        'min_bid_rule_afrr_neg': [],
        'total_violations': 0
    }

    P_MIN_BID = 1.0  # Minimum bid power (MW)
    EPSILON = 1e-6  # Tolerance for numerical errors

    num_intervals = len(week_data)

    for t in range(num_intervals):
        # Get decision variable values
        p_ch = solution['p_ch'].get(t, 0)
        p_dis = solution['p_dis'].get(t, 0)
        p_total_ch = solution.get('p_total_ch', {}).get(t, 0)
        p_total_dis = solution.get('p_total_dis', {}).get(t, 0)
        p_afrr_pos = solution.get('p_afrr_pos', {}).get(t, 0)
        p_afrr_neg = solution.get('p_afrr_neg', {}).get(t, 0)

        # Check 1: No simultaneous charging and discharging (Cst-3)
        # NOTE: This should be 0 now that we re-enabled Cst-3
        if p_total_ch > EPSILON and p_total_dis > EPSILON:
            violations['no_simultaneous_rule'].append({
                'interval': t,
                'p_total_ch': p_total_ch,
                'p_total_dis': p_total_dis,
                'violation': f"p_total_ch={p_total_ch:.2f} AND p_total_dis={p_total_dis:.2f}"
            })

        # Check 2: Cross-market exclusivity rules (Cst-8) - STILL DISABLED
        if p_dis > EPSILON and p_afrr_pos > EPSILON:
            violations['cross_market_exclusivity'].append({
                'interval': t,
                'type': 'DA_discharge_with_aFRR_pos',
                'p_dis': p_dis,
                'p_afrr_pos': p_afrr_pos
            })

        if p_ch > EPSILON and p_afrr_neg > EPSILON:
            violations['cross_market_exclusivity'].append({
                'interval': t,
                'type': 'DA_charge_with_aFRR_neg',
                'p_ch': p_ch,
                'p_afrr_neg': p_afrr_neg
            })

        if p_afrr_pos > EPSILON and p_afrr_neg > EPSILON:
            violations['cross_market_exclusivity'].append({
                'interval': t,
                'type': 'aFRR_pos_and_neg',
                'p_afrr_pos': p_afrr_pos,
                'p_afrr_neg': p_afrr_neg
            })

        # Check 3: Minimum bid rules (Cst-9) - STILL DISABLED
        if 0 < p_dis < P_MIN_BID - EPSILON:
            violations['min_bid_rule_da'].append({
                'interval': t,
                'type': 'DA_discharge',
                'p_dis': p_dis,
                'min_bid': P_MIN_BID
            })

        if 0 < p_ch < P_MIN_BID - EPSILON:
            violations['min_bid_rule_da'].append({
                'interval': t,
                'type': 'DA_charge',
                'p_ch': p_ch,
                'min_bid': P_MIN_BID
            })

    violations['total_violations'] = (
        len(violations['no_simultaneous_rule']) +
        len(violations['cross_market_exclusivity']) +
        len(violations['min_bid_rule_da']) +
        len(violations['min_bid_rule_afrr_pos']) +
        len(violations['min_bid_rule_afrr_neg'])
    )

    return violations


def run_test():
    """Run the partially optimized model test on Week 14."""

    logger.info("="*80)
    logger.info(f"PARTIAL OPTIMIZATION TEST - Week 14 ({TEST_CONFIG['num_days']} day)")
    logger.info("Cst-3: ENABLED | Cst-8: DISABLED | Cst-9: DISABLED")
    logger.info("="*80)

    # Initialize optimizer
    logger.info("Initializing optimizer with partial optimization (Cst-3 enabled)...")
    optimizer = BESSOptimizerModelII(alpha=TEST_CONFIG['alpha'])

    # Load data
    logger.info(f"Loading data...")
    full_data = optimizer.load_and_preprocess_data(
        str(DATA_FILE),
        afrr_energy_file=str(AFRR_ENERGY_FILE)
    )

    # Extract country data
    country_data = optimizer.extract_country_data(full_data, TEST_CONFIG['country'])

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

    # Build model
    logger.info("Building optimization model...")
    build_start = datetime.now()
    model = optimizer.build_optimization_model(week_data, TEST_CONFIG['c_rate'], daily_cycle_limit=None)
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
        return None, None

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

    degradation_cost = sum(
        solution.get('deg_cost_j', {}).get((t, j), 0)
        for t in range(len(week_data))
        for j in range(10)  # 10 segments
    )

    capacity_revenue = obj_value - da_revenue - afrr_e_revenue

    # Extract results
    logger.info("\n" + "="*80)
    logger.info("OPTIMIZATION RESULTS")
    logger.info("="*80)
    logger.info(f"Status: {solution['status']}")
    logger.info(f"Build Time: {build_time:.2f}s")
    logger.info(f"Solve Time: {solve_time:.2f}s")
    logger.info(f"Total Time: {build_time + solve_time:.2f}s")
    logger.info(f"")
    logger.info(f"Model Size:")
    logger.info(f"  Variables: {num_vars:,}")
    logger.info(f"  Constraints: {num_constraints:,}")
    logger.info(f"")
    logger.info(f"Objective Value: €{obj_value:,.2f}")
    logger.info(f"  DA Revenue: €{da_revenue:,.2f}")
    logger.info(f"  aFRR Energy Revenue: €{afrr_e_revenue:,.2f}")
    logger.info(f"  Capacity Revenue: €{capacity_revenue:,.2f}")
    logger.info(f"")
    logger.info(f"Degradation:")
    logger.info(f"  Cost: €{degradation_cost:,.2f}")

    # Create result dict for compatibility
    result = {
        'solver_status': solution['status'],
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
    }

    # Validate constraints
    logger.info("\n" + "="*80)
    logger.info("CONSTRAINT VIOLATION CHECK")
    logger.info("="*80)

    violations = check_constraint_violations(solution, week_data)

    logger.info(f"Cst-3 (Simultaneous Ops): {len(violations['no_simultaneous_rule'])} violations")
    logger.info(f"Cst-8 (Cross-Market): {len(violations['cross_market_exclusivity'])} violations")
    logger.info(f"Cst-9 (MinBid DA): {len(violations['min_bid_rule_da'])} violations")
    logger.info(f"")
    logger.info(f"TOTAL VIOLATIONS: {violations['total_violations']}")

    if violations['total_violations'] == 0:
        logger.info("\n[PASS] All constraints satisfied!")
    else:
        logger.info(f"\n[INFO] {violations['total_violations']} violations of disabled constraints detected")

    # Show first few violations if any
    if len(violations['no_simultaneous_rule']) > 0:
        logger.warning("\n** CST-3 VIOLATIONS DETECTED **")
        logger.warning("This should be 0 since Cst-3 is re-enabled!")
        for i, v in enumerate(violations['no_simultaneous_rule'][:5]):
            logger.warning(f"  Interval {v['interval']}: {v['violation']}")

    # Save results
    output_file = OUTPUT_DIR / 'week14_partial_opt_results.json'
    with open(output_file, 'w') as f:
        # Prepare serializable result
        result_copy = result.copy()
        result_copy['violations'] = violations
        result_copy['config'] = TEST_CONFIG
        json.dump(result_copy, f, indent=2, default=float)

    logger.info(f"\nResults saved to: {output_file}")

    # Generate comparison summary
    logger.info("\n" + "="*80)
    logger.info("EXPECTED COMPARISON WITH PREVIOUS TESTS")
    logger.info("="*80)
    logger.info("Baseline (all constraints): ~12s solve time, €3,872 profit")
    logger.info("Fully optimized (no Cst-3/8/9): ~0.8s solve time, €5,694 profit, 2,700+ Cst-3 violations")
    logger.info("Partial optimized (Cst-3 only): ??? solve time, ??? profit, 0 Cst-3 violations (expected)")
    logger.info("="*80)

    return result, violations


if __name__ == "__main__":
    result, violations = run_test()
