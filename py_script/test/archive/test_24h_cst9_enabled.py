"""
Test 24h Optimization with Cst-9 Enabled
=========================================

Runs a 24h test with Cst-9 (minimum bid size) constraints re-enabled.
Saves results to compare with Cst-9 disabled version.

Usage:
    python test_24h_cst9_enabled.py
"""

import sys
from pathlib import Path
import pandas as pd
import time
import json

sys.path.append(str(Path(__file__).parent / 'py_script'))

from core.optimizer import BESSOptimizerModelIII
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    """Run 24h test with Cst-9 enabled."""

    logger.info("=" * 80)
    logger.info("24H OPTIMIZATION TEST - CST-9 ENABLED")
    logger.info("=" * 80)
    logger.info("Configuration:")
    logger.info("  Country: CH")
    logger.info("  Horizon: 24h")
    logger.info("  Alpha: 1.5")
    logger.info("  Cst-8: ENABLED")
    logger.info("  Cst-9: ENABLED (MinBid constraints for DA and aFRR energy)")
    logger.info("=" * 80)

    # Load data
    data_file = "data/phase_1_data_TechArena2025_data_tidy.jsonl"
    country = "CH"
    horizon_hours = 24

    logger.info("\nInitializing optimizer...")
    optimizer = BESSOptimizerModelIII(alpha=1.5, use_afrr_ev_weighting=True)

    logger.info("Loading data...")
    full_data = optimizer.load_and_preprocess_data(data_file)
    country_data = optimizer.extract_country_data(full_data, country)

    # Extract first 24h
    intervals_needed = int(horizon_hours * 4)
    test_data = country_data.iloc[:intervals_needed].copy().reset_index(drop=True)

    logger.info(f"Test data: {len(test_data)} intervals ({horizon_hours}h)")

    # Build and solve
    logger.info("\nBuilding Model III...")
    start_time = time.time()
    model = optimizer.build_optimization_model(test_data, c_rate=0.5)
    build_time = time.time() - start_time

    logger.info(f"Model built in {build_time:.2f}s")
    logger.info(f"  Variables: {model.nvariables()}")
    logger.info(f"  Constraints: {model.nconstraints()}")

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

    # Extract detailed solution
    logger.info("\nExtracting detailed solution...")

    from test_cst8_detailed_solution import extract_detailed_solution

    df_solution = extract_detailed_solution(solution, test_data, horizon_hours)

    # Save results with CST9 label
    output_dir = Path("results/model_iii_detailed_solutions")
    output_dir.mkdir(exist_ok=True, parents=True)

    csv_file = output_dir / "solution_24h_cst9_enabled.csv"
    df_solution.to_csv(csv_file, index=False, float_format='%.4f')
    logger.info(f"Saved decision variables to: {csv_file}")

    # Save summary
    summary = {
        'horizon_hours': horizon_hours,
        'country': country,
        'alpha': 1.5,
        'cst8_enabled': True,
        'cst9_enabled': True,
        'build_time_seconds': build_time,
        'solve_time_seconds': solve_time,
        'status': status,
        'objective_value': obj,
        'model_variables': model.nvariables(),
        'model_constraints': model.nconstraints(),
        'degradation': solution.get('degradation_metrics', {}),
        'profit_da': solution.get('profit_da', 0),
        'profit_afrr_energy': solution.get('profit_afrr_energy', 0),
        'profit_as_capacity': solution.get('profit_as_capacity', 0),
        'avg_soc_kwh': df_solution['soc_kwh'].mean(),
        'avg_soc_pct': df_solution['soc_pct'].mean(),
        'total_revenue_da': df_solution['revenue_da_eur'].sum(),
        'total_revenue_afrr_e': df_solution['revenue_afrr_energy_eur'].sum(),
        'total_revenue_as_cap': df_solution['revenue_as_capacity_eur'].sum(),
        'da_trading_intervals': {
            'charge': (df_solution['p_ch_kw'] > 1).sum(),
            'discharge': (df_solution['p_dis_kw'] > 1).sum(),
        },
        'as_reservation_intervals': {
            'fcr': (df_solution['c_fcr_mw'] > 0).sum(),
            'afrr_pos': (df_solution['c_afrr_pos_mw'] > 0).sum(),
            'afrr_neg': (df_solution['c_afrr_neg_mw'] > 0).sum(),
        }
    }

    json_file = output_dir / "summary_24h_cst9_enabled.json"
    with open(json_file, 'w') as f:
        json.dump(summary, f, indent=2)
    logger.info(f"Saved summary to: {json_file}")

    # Print key statistics
    logger.info("\n" + "=" * 80)
    logger.info("KEY STATISTICS")
    logger.info("=" * 80)
    logger.info(f"SOC: {df_solution['soc_kwh'].min():.1f} - {df_solution['soc_kwh'].max():.1f} kWh "
                f"(avg {df_solution['soc_kwh'].mean():.1f} kWh)")
    logger.info(f"DA trading intervals: {summary['da_trading_intervals']['charge']} charge, "
                f"{summary['da_trading_intervals']['discharge']} discharge")
    logger.info(f"AS reservation intervals: FCR={summary['as_reservation_intervals']['fcr']}, "
                f"aFRR+={summary['as_reservation_intervals']['afrr_pos']}, "
                f"aFRR-={summary['as_reservation_intervals']['afrr_neg']}")
    logger.info(f"\nRevenue breakdown:")
    logger.info(f"  DA energy:    {summary['total_revenue_da']:>10.2f} EUR")
    logger.info(f"  aFRR energy:  {summary['total_revenue_afrr_e']:>10.2f} EUR")
    logger.info(f"  AS capacity:  {summary['total_revenue_as_cap']:>10.2f} EUR")
    logger.info(f"  TOTAL:        {sum([summary['total_revenue_da'], summary['total_revenue_afrr_e'], summary['total_revenue_as_cap']]):>10.2f} EUR")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
