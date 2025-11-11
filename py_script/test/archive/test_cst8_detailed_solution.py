"""
Test Cst-8 Fix with Detailed Solution Export
==============================================

Runs 24h, 36h, 48h tests and exports complete decision variables:
- Power schedules (p_ch, p_dis, p_total_ch, p_total_dis)
- Market bids (c_fcr, c_afrr_pos, c_afrr_neg, p_afrr_pos_e, p_afrr_neg_e)
- Binary decisions (y_ch, y_dis, y_fcr, y_afrr_pos, y_afrr_neg)
- SOC profile (e_soc, segment SOCs)
- Market prices

Usage:
    python test_cst8_detailed_solution.py
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


def extract_detailed_solution(solution: dict, test_data: pd.DataFrame, horizon_hours: int):
    """Extract all decision variables and market data into a DataFrame."""

    T = len(solution.get('e_soc', {}))

    # Initialize data dictionary
    data = {
        'time_step': list(range(T)),
        'hour': [t * 0.25 for t in range(T)],  # 15-min intervals
    }

    # SOC and segment data
    data['soc_kwh'] = [solution.get('e_soc', {}).get(t, 0) for t in range(T)]
    data['soc_pct'] = [solution.get('e_soc', {}).get(t, 0) / 4472 * 100 for t in range(T)]

    # Power variables
    data['p_ch_kw'] = [solution.get('p_ch', {}).get(t, 0) for t in range(T)]
    data['p_dis_kw'] = [solution.get('p_dis', {}).get(t, 0) for t in range(T)]
    data['p_total_ch_kw'] = [solution.get('p_total_ch', {}).get(t, 0) for t in range(T)]
    data['p_total_dis_kw'] = [solution.get('p_total_dis', {}).get(t, 0) for t in range(T)]

    # aFRR energy power
    data['p_afrr_pos_e_kw'] = [solution.get('p_afrr_pos_e', {}).get(t, 0) for t in range(T)]
    data['p_afrr_neg_e_kw'] = [solution.get('p_afrr_neg_e', {}).get(t, 0) for t in range(T)]

    # Binary decisions (time-indexed)
    data['y_ch'] = [solution.get('y_ch', {}).get(t, 0) for t in range(T)]
    data['y_dis'] = [solution.get('y_dis', {}).get(t, 0) for t in range(T)]
    data['y_total_ch'] = [solution.get('y_total_ch', {}).get(t, 0) for t in range(T)]
    data['y_total_dis'] = [solution.get('y_total_dis', {}).get(t, 0) for t in range(T)]

    # Block-indexed variables (need to map to time steps)
    block_map = solution.get('block_map', {})

    # Capacity bids (MW)
    data['c_fcr_mw'] = [solution.get('c_fcr', {}).get(block_map.get(t, 0), 0) for t in range(T)]
    data['c_afrr_pos_mw'] = [solution.get('c_afrr_pos', {}).get(block_map.get(t, 0), 0) for t in range(T)]
    data['c_afrr_neg_mw'] = [solution.get('c_afrr_neg', {}).get(block_map.get(t, 0), 0) for t in range(T)]

    # Binary decisions (block-indexed)
    data['y_fcr'] = [solution.get('y_fcr', {}).get(block_map.get(t, 0), 0) for t in range(T)]
    data['y_afrr_pos'] = [solution.get('y_afrr_pos', {}).get(block_map.get(t, 0), 0) for t in range(T)]
    data['y_afrr_neg'] = [solution.get('y_afrr_neg', {}).get(block_map.get(t, 0), 0) for t in range(T)]

    # Market prices (from test_data)
    if len(test_data) >= T:
        data['price_da_eur_mwh'] = test_data['price_day_ahead'].iloc[:T].values
        data['price_fcr_eur_mw'] = test_data['price_fcr'].iloc[:T].values
        # aFRR capacity prices (price_afrr_pos/neg are capacity prices)
        data['price_afrr_cap_pos_eur_mw'] = test_data['price_afrr_pos'].iloc[:T].values
        data['price_afrr_cap_neg_eur_mw'] = test_data['price_afrr_neg'].iloc[:T].values

        # aFRR energy prices - store both original and preprocessed versions
        if 'price_afrr_energy_pos_original' in test_data.columns:
            # Original prices for visualization (includes 0 values)
            data['price_afrr_energy_pos_eur_mwh'] = test_data['price_afrr_energy_pos_original'].iloc[:T].values
            data['price_afrr_energy_neg_eur_mwh'] = test_data['price_afrr_energy_neg_original'].iloc[:T].values
            # Preprocessed prices for revenue calculation (0 -> NaN, so no revenue when not activated)
            price_afrr_pos_for_revenue = test_data['price_afrr_energy_pos'].iloc[:T].values
            price_afrr_neg_for_revenue = test_data['price_afrr_energy_neg'].iloc[:T].values
        else:
            # Fallback for old data without original columns
            data['price_afrr_energy_pos_eur_mwh'] = test_data['price_afrr_energy_pos'].iloc[:T].values
            data['price_afrr_energy_neg_eur_mwh'] = test_data['price_afrr_energy_neg'].iloc[:T].values
            price_afrr_pos_for_revenue = data['price_afrr_energy_pos_eur_mwh']
            price_afrr_neg_for_revenue = data['price_afrr_energy_neg_eur_mwh']

    # Cst-8 check values
    data['cst8_discharge_sum'] = [
        data['y_total_dis'][t] + data['y_fcr'][t] + data['y_afrr_neg'][t]
        for t in range(T)
    ]
    data['cst8_charge_sum'] = [
        data['y_total_ch'][t] + data['y_fcr'][t] + data['y_afrr_pos'][t]
        for t in range(T)
    ]

    # Revenue calculations (per time step)
    data['revenue_da_eur'] = [
        (data['p_dis_kw'][t] * data['price_da_eur_mwh'][t] / 1000 -
         data['p_ch_kw'][t] * data['price_da_eur_mwh'][t] / 1000) * 0.25
        if 'price_da_eur_mwh' in data else 0
        for t in range(T)
    ]

    # aFRR energy revenue - use preprocessed prices (NaN for non-activated periods)
    # This ensures revenue is 0 when market is not activated
    data['revenue_afrr_energy_eur'] = []
    for t in range(T):
        if 'price_afrr_pos_for_revenue' in locals():
            # Use preprocessed prices for revenue (NaN becomes 0 revenue)
            pos_price = price_afrr_pos_for_revenue[t] if not pd.isna(price_afrr_pos_for_revenue[t]) else 0
            neg_price = price_afrr_neg_for_revenue[t] if not pd.isna(price_afrr_neg_for_revenue[t]) else 0
            revenue = (data['p_afrr_pos_e_kw'][t] * pos_price / 1000 +
                      data['p_afrr_neg_e_kw'][t] * neg_price / 1000) * 0.25
        elif 'price_afrr_energy_pos_eur_mwh' in data:
            # Fallback: use displayed prices (may overestimate if original has 0s)
            revenue = (data['p_afrr_pos_e_kw'][t] * data['price_afrr_energy_pos_eur_mwh'][t] / 1000 +
                      data['p_afrr_neg_e_kw'][t] * data['price_afrr_energy_neg_eur_mwh'][t] / 1000) * 0.25
        else:
            revenue = 0
        data['revenue_afrr_energy_eur'].append(revenue)

    data['revenue_as_capacity_eur'] = [
        (data['c_fcr_mw'][t] * data['price_fcr_eur_mw'][t] +
         data['c_afrr_pos_mw'][t] * data['price_afrr_cap_pos_eur_mw'][t] +
         data['c_afrr_neg_mw'][t] * data['price_afrr_cap_neg_eur_mw'][t]) * 0.25
        if 'price_fcr_eur_mw' in data else 0
        for t in range(T)
    ]

    df = pd.DataFrame(data)

    # Add metadata
    df.attrs['horizon_hours'] = horizon_hours
    df.attrs['intervals'] = T
    df.attrs['objective_value'] = solution.get('objective_value', 0)
    df.attrs['status'] = solution.get('status', 'unknown')

    return df


def run_detailed_test(horizon_hours: int, data_file: str, country: str = 'CH', alpha: float = 1.5):
    """Run a single test and save detailed solution."""

    logger.info("=" * 80)
    logger.info(f"TESTING {horizon_hours}h HORIZON WITH DETAILED OUTPUT")
    logger.info("=" * 80)

    # Load data
    logger.info(f"Loading data for {country}, {horizon_hours}h horizon")
    optimizer = BESSOptimizerModelIII(alpha=alpha, use_afrr_ev_weighting=True)
    full_data = optimizer.load_and_preprocess_data(data_file)
    country_data = optimizer.extract_country_data(full_data, country)

    # Extract first N hours (simplified - not using date extraction)
    intervals_needed = int(horizon_hours * 4)
    test_data = country_data.iloc[:intervals_needed].copy().reset_index(drop=True)

    logger.info(f"Testing with {len(test_data)} intervals ({horizon_hours}h)")

    # Build and solve
    logger.info("Building Model III...")
    start_time = time.time()
    model = optimizer.build_optimization_model(test_data, c_rate=0.5)
    solution = optimizer.solve_model(model)
    solve_time = time.time() - start_time

    status = solution.get('status', 'unknown')
    obj = solution.get('objective_value', 0)

    logger.info(f"Solved in {solve_time:.2f}s: Status={status}, Obj={obj:,.2f} EUR")

    if status not in ['optimal', 'feasible']:
        logger.error(f"Optimization failed: {status}")
        return None

    # Extract detailed solution
    logger.info("Extracting detailed decision variables...")
    df_solution = extract_detailed_solution(solution, test_data, horizon_hours)

    # Run validation
    logger.info("Validating constraints...")
    from validation.constraint_validator import ConstraintValidator
    validator = ConstraintValidator(model, solution, tolerance=1e-6)
    validation_report = validator.generate_validation_report()

    violations = validation_report['summary']['total_violations']
    logger.info(f"Validation: {violations} violations")

    # Save results
    output_dir = Path("results/model_iii_detailed_solutions")
    output_dir.mkdir(exist_ok=True, parents=True)

    # Save decision variables CSV
    csv_file = output_dir / f"solution_{horizon_hours}h_cst8_enabled.csv"
    df_solution.to_csv(csv_file, index=False, float_format='%.4f')
    logger.info(f"Saved decision variables to: {csv_file}")

    # Save summary JSON
    summary = {
        'horizon_hours': horizon_hours,
        'country': country,
        'alpha': alpha,
        'cst8_enabled': True,
        'solve_time_seconds': solve_time,
        'status': status,
        'objective_value': obj,
        'violations': violations,
        'degradation': solution.get('degradation_metrics', {}),
        'profit_da': solution.get('profit_da', 0),
        'profit_afrr_energy': solution.get('profit_afrr_energy', 0),
        'profit_as_capacity': solution.get('profit_as_capacity', 0),
        'avg_soc_kwh': df_solution['soc_kwh'].mean(),
        'avg_soc_pct': df_solution['soc_pct'].mean(),
        'max_cst8_discharge': df_solution['cst8_discharge_sum'].max(),
        'max_cst8_charge': df_solution['cst8_charge_sum'].max(),
        'total_revenue_da': df_solution['revenue_da_eur'].sum(),
        'total_revenue_afrr_e': df_solution['revenue_afrr_energy_eur'].sum(),
        'total_revenue_as_cap': df_solution['revenue_as_capacity_eur'].sum(),
    }

    json_file = output_dir / f"summary_{horizon_hours}h_cst8_enabled.json"
    with open(json_file, 'w') as f:
        json.dump(summary, f, indent=2)
    logger.info(f"Saved summary to: {json_file}")

    # Print key statistics
    logger.info("\nKey Statistics:")
    logger.info(f"  SOC: {df_solution['soc_kwh'].min():.1f} - {df_solution['soc_kwh'].max():.1f} kWh "
                f"(avg {df_solution['soc_kwh'].mean():.1f} kWh)")
    logger.info(f"  Max discharge power: {df_solution['p_total_dis_kw'].max():.1f} kW")
    logger.info(f"  Max charge power: {df_solution['p_total_ch_kw'].max():.1f} kW")
    logger.info(f"  FCR bids: {(df_solution['c_fcr_mw'] > 0).sum()} intervals, max {df_solution['c_fcr_mw'].max():.2f} MW")
    logger.info(f"  aFRR+ bids: {(df_solution['c_afrr_pos_mw'] > 0).sum()} intervals, max {df_solution['c_afrr_pos_mw'].max():.2f} MW")
    logger.info(f"  aFRR- bids: {(df_solution['c_afrr_neg_mw'] > 0).sum()} intervals, max {df_solution['c_afrr_neg_mw'].max():.2f} MW")
    logger.info(f"  Cst-8 discharge sum: max {df_solution['cst8_discharge_sum'].max():.6f} (should be ≤1.0)")
    logger.info(f"  Cst-8 charge sum: max {df_solution['cst8_charge_sum'].max():.6f} (should be ≤1.0)")

    # Check for any Cst-8 violations
    discharge_violations = (df_solution['cst8_discharge_sum'] > 1.000001).sum()
    charge_violations = (df_solution['cst8_charge_sum'] > 1.000001).sum()

    if discharge_violations > 0 or charge_violations > 0:
        logger.warning(f"  ⚠️ Cst-8 violations found: {discharge_violations} discharge, {charge_violations} charge")
    else:
        logger.info(f"  ✓ Cst-8 validated: All binary sums ≤ 1.0")

    return df_solution


def main():
    """Run detailed solution export for all horizons."""

    logger.info("=" * 80)
    logger.info("MODEL III DETAILED SOLUTION EXPORT (CST-8 ENABLED)")
    logger.info("=" * 80)
    logger.info("Testing: 24h, 36h, 48h horizons")
    logger.info("Exporting: Complete decision variables + market data")
    logger.info("=" * 80)

    data_file = "data/phase_1_data_TechArena2025_data_tidy.jsonl"
    country = "CH"
    alpha = 1.5
    horizons = [24, 36, 48]

    results = {}

    for hours in horizons:
        logger.info(f"\n{'=' * 80}\n")

        df_solution = run_detailed_test(
            horizon_hours=hours,
            data_file=data_file,
            country=country,
            alpha=alpha
        )

        if df_solution is not None:
            results[f"{hours}h"] = df_solution
            logger.info(f"✓ {hours}h test completed successfully")
        else:
            logger.error(f"✗ {hours}h test failed")

    # Final summary
    logger.info("\n" + "=" * 80)
    logger.info("ALL TESTS COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Results saved to: results/model_iii_detailed_solutions/")
    logger.info(f"Files generated:")
    logger.info(f"  - solution_24h_cst8_enabled.csv")
    logger.info(f"  - solution_36h_cst8_enabled.csv")
    logger.info(f"  - solution_48h_cst8_enabled.csv")
    logger.info(f"  - summary_*h_cst8_enabled.json (3 files)")
    logger.info("\nYou can now analyze:")
    logger.info("  - Power schedules and market bids")
    logger.info("  - SOC profiles over time")
    logger.info("  - Binary decision patterns")
    logger.info("  - Revenue by market and time")
    logger.info("  - Cst-8 constraint compliance")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
