#!/usr/bin/env python3
"""
Test 24h optimization with all fixes:
1. Cst-6 bug fixed (energy reserve constraints properly reference e_soc Expression)
2. Cst-10: Minimum DA participation (default 10%)
3. Cst-11: AS capacity upper limit (default 80%)

This should prevent the "FCR-only" behavior and force more realistic market diversification.
"""

import sys
from pathlib import Path
import pandas as pd
import time
import json
import logging

sys.path.append(str(Path(__file__).parent / 'py_script'))
from core.optimizer import BESSOptimizerModelIII

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Run 24h test with all fixes enabled."""

    logger.info("=" * 80)
    logger.info("24H OPTIMIZATION TEST - WITH ALL FIXES")
    logger.info("=" * 80)
    logger.info("Fixes Applied:")
    logger.info("  1. Cst-6 bug fixed (energy reserve constraints)")
    logger.info("  2. Cst-10: Minimum 10% DA participation")
    logger.info("  3. Cst-11: Maximum 80% AS capacity")
    logger.info("=" * 80)

    # Initialize optimizer WITH the new constraints enabled
    optimizer = BESSOptimizerModelIII(alpha=1.5)

    # Set the new constraint parameters
    optimizer.min_da_participation_ratio = 0.1  # 10% minimum DA
    optimizer.max_as_capacity_ratio = 0.8      # 80% max AS

    # Load data
    data_file = "data/phase_1_data_TechArena2025_data_tidy.jsonl"
    horizon_hours = 24
    country = "CH"

    logger.info("\nLoading data...")
    full_data = optimizer.load_and_preprocess_data(data_file)
    country_data = optimizer.extract_country_data(full_data, country)

    # Extract first 24h
    intervals_needed = int(horizon_hours * 4)
    test_data = country_data.iloc[:intervals_needed].copy().reset_index(drop=True)
    logger.info(f"Test data: {len(test_data)} intervals ({horizon_hours}h)")

    # Build and solve
    logger.info("\nBuilding Model III with fixes...")
    start_time = time.time()
    model = optimizer.build_optimization_model(test_data, c_rate=0.5)
    build_time = time.time() - start_time

    logger.info(f"Model built in {build_time:.2f}s")
    logger.info(f"  Variables: {model.nvariables()}")
    logger.info(f"  Constraints: {model.nconstraints()}")

    # Verify new constraints exist
    if hasattr(model, 'min_da_participation'):
        logger.info("  ✓ Cst-10 (Min DA participation) added")
    else:
        logger.warning("  ✗ Cst-10 NOT found!")

    if hasattr(model, 'max_as_capacity'):
        logger.info("  ✓ Cst-11 (Max AS capacity) added")
    else:
        logger.warning("  ✗ Cst-11 NOT found!")

    # Check if Cst-6 references Expression (not Variable)
    if hasattr(model, 'energy_reserve_pos'):
        logger.info("  ✓ Cst-6 (Energy reserve) exists")
        if isinstance(model.e_soc, pyo.Expression):
            logger.info("    ✓ e_soc is Expression (fix applied)")
        else:
            logger.warning("    ✗ e_soc is not Expression!")
    else:
        logger.warning("  ✗ Cst-6 NOT found!")

    logger.info("\nSolving...")
    solve_start = time.time()
    solution = optimizer.solve_model(model)
    solve_time = time.time() - solve_start

    status = solution.get('status', 'unknown')
    obj = solution.get('objective_value', 0)

    logger.info(f"\nSolved in {solve_time:.2f}s:")
    logger.info(f"  Status: {status}")
    logger.info(f"  Objective: {obj:,.2f} EUR")

    if status not in ['optimal', 'feasible']:
        logger.error("Optimization failed!")
        return

    # Extract and analyze solution
    logger.info("\nAnalyzing solution...")

    # Count market participation
    da_charge_intervals = 0
    da_discharge_intervals = 0
    fcr_intervals = 0
    afrr_pos_intervals = 0
    afrr_neg_intervals = 0

    # Check power levels
    max_fcr_mw = 0
    max_as_total_mw = 0

    for t in range(len(solution.get('e_soc', {}))):
        # DA participation
        if solution.get('p_ch', {}).get(t, 0) > 10:  # > 10 kW
            da_charge_intervals += 1
        if solution.get('p_dis', {}).get(t, 0) > 10:  # > 10 kW
            da_discharge_intervals += 1

    for b in range(len(solution.get('c_fcr', {}))):
        # AS participation
        fcr = solution.get('c_fcr', {}).get(b, 0)
        afrr_pos = solution.get('c_afrr_pos', {}).get(b, 0)
        afrr_neg = solution.get('c_afrr_neg', {}).get(b, 0)

        if fcr > 0.1:  # > 0.1 MW
            fcr_intervals += 16  # Each block is 16 intervals
            max_fcr_mw = max(max_fcr_mw, fcr)

        if afrr_pos > 0.1:
            afrr_pos_intervals += 16

        if afrr_neg > 0.1:
            afrr_neg_intervals += 16

        total_as = fcr + afrr_pos + afrr_neg
        max_as_total_mw = max(max_as_total_mw, total_as)

    total_da_intervals = da_charge_intervals + da_discharge_intervals

    logger.info("\n" + "=" * 80)
    logger.info("MARKET PARTICIPATION ANALYSIS")
    logger.info("=" * 80)

    logger.info(f"Day-Ahead Market:")
    logger.info(f"  Charge intervals:    {da_charge_intervals}/96 ({da_charge_intervals/96*100:.1f}%)")
    logger.info(f"  Discharge intervals: {da_discharge_intervals}/96 ({da_discharge_intervals/96*100:.1f}%)")
    logger.info(f"  Total DA activity:   {total_da_intervals}/96 ({total_da_intervals/96*100:.1f}%)")

    logger.info(f"\nAncillary Services:")
    logger.info(f"  FCR reserved:     {fcr_intervals}/96 intervals ({fcr_intervals/96*100:.1f}%)")
    logger.info(f"  aFRR+ reserved:   {afrr_pos_intervals}/96 intervals ({afrr_pos_intervals/96*100:.1f}%)")
    logger.info(f"  aFRR- reserved:   {afrr_neg_intervals}/96 intervals ({afrr_neg_intervals/96*100:.1f}%)")

    logger.info(f"\nCapacity Utilization:")
    logger.info(f"  Max FCR bid:         {max_fcr_mw:.3f} MW")
    logger.info(f"  Max total AS:        {max_as_total_mw:.3f} MW")
    logger.info(f"  Battery capacity:    2.236 MW")

    # Revenue breakdown
    revenue_da = solution.get('profit_da', 0)
    revenue_afrr_e = solution.get('profit_afrr_energy', 0)
    revenue_as_cap = solution.get('profit_as_capacity', 0)
    total_revenue = revenue_da + revenue_afrr_e + revenue_as_cap

    logger.info(f"\nRevenue Breakdown:")
    logger.info(f"  DA energy:        {revenue_da:>10.2f} EUR ({revenue_da/total_revenue*100:5.1f}%)")
    logger.info(f"  aFRR energy:      {revenue_afrr_e:>10.2f} EUR ({revenue_afrr_e/total_revenue*100:5.1f}%)")
    logger.info(f"  AS capacity:      {revenue_as_cap:>10.2f} EUR ({revenue_as_cap/total_revenue*100:5.1f}%)")
    logger.info(f"  TOTAL:            {total_revenue:>10.2f} EUR")

    # Verification of constraints
    logger.info("\n" + "=" * 80)
    logger.info("CONSTRAINT VERIFICATION")
    logger.info("=" * 80)

    # Check Cst-10: Minimum DA participation
    min_required = int(0.1 * 96)  # 10% of 96 intervals
    if total_da_intervals >= min_required:
        logger.info(f"✓ Cst-10 satisfied: DA activity {total_da_intervals} >= {min_required} required")
    else:
        logger.error(f"✗ Cst-10 VIOLATED: DA activity {total_da_intervals} < {min_required} required")

    # Check Cst-11: AS capacity limit
    max_allowed = 0.8 * 2.236  # 80% of 2.236 MW
    if max_as_total_mw <= max_allowed + 0.01:  # Small tolerance for rounding
        logger.info(f"✓ Cst-11 satisfied: Max AS {max_as_total_mw:.3f} MW <= {max_allowed:.3f} MW")
    else:
        logger.error(f"✗ Cst-11 VIOLATED: Max AS {max_as_total_mw:.3f} MW > {max_allowed:.3f} MW")

    logger.info("\n" + "=" * 80)
    logger.info("COMPARISON WITH PREVIOUS (BUGGY) VERSION")
    logger.info("=" * 80)
    logger.info("Previous behavior (with bugs):")
    logger.info("  - FCR only: 66.7% of time")
    logger.info("  - DA participation: 0%")
    logger.info("  - Full power FCR: 2.236 MW")
    logger.info("\nNew behavior (with fixes):")
    logger.info(f"  - FCR: {fcr_intervals/96*100:.1f}% of time")
    logger.info(f"  - DA participation: {total_da_intervals/96*100:.1f}%")
    logger.info(f"  - Max AS capacity: {max_as_total_mw:.3f} MW")

    # Save detailed solution
    if status in ['optimal', 'feasible']:
        from test_cst8_detailed_solution import extract_detailed_solution

        df_solution = extract_detailed_solution(solution, test_data, horizon_hours)

        output_dir = Path("results/model_iii_detailed_solutions")
        output_dir.mkdir(exist_ok=True, parents=True)

        csv_file = output_dir / "solution_24h_with_fixes.csv"
        df_solution.to_csv(csv_file, index=False, float_format='%.4f')
        logger.info(f"\nSaved detailed solution to: {csv_file}")

        # Save summary
        summary = {
            'horizon_hours': horizon_hours,
            'country': country,
            'alpha': 1.5,
            'min_da_participation_ratio': 0.1,
            'max_as_capacity_ratio': 0.8,
            'fixes_applied': [
                'Cst-6 bug fixed',
                'Cst-10 Min DA participation',
                'Cst-11 Max AS capacity'
            ],
            'solve_time_seconds': solve_time,
            'status': status,
            'objective_value': obj,
            'da_intervals': {
                'charge': da_charge_intervals,
                'discharge': da_discharge_intervals,
                'total': total_da_intervals,
                'percentage': total_da_intervals / 96 * 100
            },
            'as_intervals': {
                'fcr': fcr_intervals,
                'afrr_pos': afrr_pos_intervals,
                'afrr_neg': afrr_neg_intervals
            },
            'max_capacities': {
                'fcr_mw': max_fcr_mw,
                'total_as_mw': max_as_total_mw
            },
            'revenue': {
                'da': revenue_da,
                'afrr_energy': revenue_afrr_e,
                'as_capacity': revenue_as_cap,
                'total': total_revenue
            }
        }

        json_file = output_dir / "summary_24h_with_fixes.json"
        with open(json_file, 'w') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"Saved summary to: {json_file}")

if __name__ == "__main__":
    import pyomo.environ as pyo
    main()