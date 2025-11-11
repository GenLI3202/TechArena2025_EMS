"""
Test Cst-8 Fix: Run single-horizon tests with re-enabled constraint
====================================================================

Tests 24h, 36h, 48h horizons for summer date (2024-07-22) with Cst-8 enabled
to verify that constraint violations are eliminated.

Usage:
    python test_cst8_fix.py
"""

import sys
from pathlib import Path
import pandas as pd
import time
import json

# Add parent directory to path
sys.path.append(str(Path(__file__).parent / 'py_script'))

from core.optimizer import BESSOptimizerModelIII, BESSOptimizerModelII
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_and_extract_data(data_file: str, country: str, target_date: str, hours: int):
    """Load data and extract specific date window."""
    logger.info(f"Loading data for {country}, {target_date}, {hours}h horizon")

    # Create temporary optimizer for data loading
    temp_optimizer = BESSOptimizerModelIII(alpha=1.5, use_afrr_ev_weighting=True)

    # Load full data
    full_data = temp_optimizer.load_and_preprocess_data(data_file)
    country_data = temp_optimizer.extract_country_data(full_data, country)

    # Extract date window
    target_dt = pd.to_datetime(target_date)
    intervals_needed = int(hours * 4)  # 4 intervals per hour

    if 'datetime' in country_data.columns:
        time_diffs = abs(country_data['datetime'] - target_dt)
        start_idx = time_diffs.argmin()
        actual_start = country_data.iloc[start_idx]['datetime']
        logger.info(f"Extracted {intervals_needed} intervals starting from {actual_start}")
    else:
        logger.warning("No datetime column, using first intervals")
        start_idx = 0

    extracted_data = country_data.iloc[start_idx:start_idx + intervals_needed].copy()
    extracted_data = extracted_data.reset_index(drop=True)

    return extracted_data

def test_single_horizon(test_data: pd.DataFrame, horizon_hours: int, alpha: float = 1.5):
    """Test a single horizon with both Model III and Model II."""

    logger.info("=" * 80)
    logger.info(f"Testing {horizon_hours}h horizon (α={alpha})")
    logger.info("=" * 80)

    results = {}

    # Test Model III (with Cst-8 RE-ENABLED)
    logger.info("\n[Model III] Building and solving...")
    optimizer_iii = BESSOptimizerModelIII(alpha=alpha, use_afrr_ev_weighting=True)

    start_time = time.time()
    model_iii = optimizer_iii.build_optimization_model(test_data, c_rate=0.5)
    solution_iii = optimizer_iii.solve_model(model_iii)
    solve_time_iii = time.time() - start_time

    # Extract Model III metrics
    status_iii = solution_iii.get('status', 'unknown')
    obj_iii = solution_iii.get('objective_value', 0)
    deg_iii = solution_iii.get('degradation_metrics', {})
    cyclic_iii = deg_iii.get('total_cyclic_cost_eur', 0)
    calendar_iii = deg_iii.get('total_calendar_cost_eur', 0)

    soc_values_iii = list(solution_iii.get('e_soc', {}).values())
    avg_soc_iii = sum(soc_values_iii) / len(soc_values_iii) if soc_values_iii else 0

    # Get profit components
    profit_da_iii = solution_iii.get('profit_da', 0)
    profit_afrr_iii = solution_iii.get('profit_afrr_energy', 0)
    profit_as_iii = solution_iii.get('profit_as_capacity', 0)

    logger.info(f"Model III: Status={status_iii}, Obj={obj_iii:,.2f} EUR, Time={solve_time_iii:.2f}s")
    logger.info(f"  - DA: {profit_da_iii:,.2f}, aFRR-E: {profit_afrr_iii:,.2f}, AS: {profit_as_iii:,.2f}")
    logger.info(f"  - Cyclic: {cyclic_iii:,.2f}, Calendar: {calendar_iii:,.2f}, Avg SOC: {avg_soc_iii:,.1f} kWh")

    # Run constraint validation
    logger.info("\n[Validation] Checking constraints...")
    from validation.constraint_validator import ConstraintValidator

    validator = ConstraintValidator(model_iii, solution_iii, tolerance=1e-6)
    validation_report = validator.generate_validation_report()

    total_violations = validation_report['summary']['total_violations']

    # Extract Cst-8 violations (key might be 'cst_8' or 'cst8')
    cst8_data = validation_report.get('cst_8', validation_report.get('cst8', {}))
    cst8_violations = cst8_data.get('count_discharge', 0) + cst8_data.get('count_charge', 0)

    if total_violations == 0:
        logger.info(f"✓ VALIDATION PASSED: 0 violations")
    else:
        logger.warning(f"✗ VALIDATION FAILED: {total_violations} violations")
        logger.warning(f"  - Cst-8 violations: {cst8_violations}")

    # Test Model II for comparison
    logger.info("\n[Model II] Building and solving...")
    optimizer_ii = BESSOptimizerModelII(alpha=alpha, use_afrr_ev_weighting=True)
    model_ii = optimizer_ii.build_optimization_model(test_data, c_rate=0.5)
    solution_ii = optimizer_ii.solve_model(model_ii)

    obj_ii = solution_ii.get('objective_value', 0)
    deg_ii = solution_ii.get('degradation_metrics', {})
    cyclic_ii = deg_ii.get('total_cyclic_cost_eur', 0)

    soc_values_ii = list(solution_ii.get('e_soc', {}).values())
    avg_soc_ii = sum(soc_values_ii) / len(soc_values_ii) if soc_values_ii else 0

    logger.info(f"Model II:  Obj={obj_ii:,.2f} EUR, Cyclic={cyclic_ii:,.2f}, Avg SOC={avg_soc_ii:,.1f} kWh")

    # Comparison
    obj_diff = obj_iii - obj_ii
    soc_reduction = avg_soc_ii - avg_soc_iii

    logger.info(f"\nComparison: Obj Δ={obj_diff:+,.2f} EUR, SOC Δ={soc_reduction:+,.1f} kWh")

    results = {
        'horizon_hours': horizon_hours,
        'alpha': alpha,
        'model_iii': {
            'status': status_iii,
            'objective': obj_iii,
            'cyclic_cost': cyclic_iii,
            'calendar_cost': calendar_iii,
            'avg_soc': avg_soc_iii,
            'profit_da': profit_da_iii,
            'profit_afrr': profit_afrr_iii,
            'profit_as': profit_as_iii,
            'solve_time': solve_time_iii,
        },
        'model_ii': {
            'objective': obj_ii,
            'cyclic_cost': cyclic_ii,
            'avg_soc': avg_soc_ii,
        },
        'comparison': {
            'obj_diff': obj_diff,
            'soc_reduction': soc_reduction,
        },
        'validation': {
            'total_violations': total_violations,
            'cst8_violations': cst8_violations,
            'passed': total_violations == 0,
        }
    }

    return results

def main():
    """Run Cst-8 fix validation tests."""

    logger.info("=" * 80)
    logger.info("CST-8 FIX VALIDATION TEST")
    logger.info("=" * 80)
    logger.info("Testing: 24h, 36h, 48h horizons")
    logger.info("Date: 2024-07-22 (Summer)")
    logger.info("Country: CH (Switzerland)")
    logger.info("Alpha: 1.5")
    logger.info("Cst-8: RE-ENABLED")
    logger.info("=" * 80)

    # Configuration
    data_file = "data/phase_1_data_TechArena2025_data_tidy.jsonl"
    country = "CH"
    target_date = "2024-07-22"
    horizons = [24, 36, 48]
    alpha = 1.5

    all_results = []

    for hours in horizons:
        logger.info(f"\n{'=' * 80}")
        logger.info(f"HORIZON: {hours}h")
        logger.info(f"{'=' * 80}\n")

        # Load data for this horizon
        test_data = load_and_extract_data(data_file, country, target_date, hours)

        # Run test
        results = test_single_horizon(test_data, hours, alpha)
        all_results.append(results)

        # Brief summary
        logger.info(f"\n[Summary {hours}h]")
        logger.info(f"  Model III Obj: {results['model_iii']['objective']:,.2f} EUR")
        logger.info(f"  Violations: {results['validation']['total_violations']}")
        logger.info(f"  Status: {'✓ PASS' if results['validation']['passed'] else '✗ FAIL'}")
        logger.info(f"  Solve Time: {results['model_iii']['solve_time']:.2f}s")

    # Final summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)

    summary_table = []
    for res in all_results:
        h = res['horizon_hours']
        obj = res['model_iii']['objective']
        cal = res['model_iii']['calendar_cost']
        viol = res['validation']['total_violations']
        time_s = res['model_iii']['solve_time']
        status = '✓ PASS' if res['validation']['passed'] else '✗ FAIL'

        summary_table.append({
            'Horizon': f"{h}h",
            'Objective (EUR)': f"{obj:,.0f}",
            'Calendar Cost (EUR)': f"{cal:,.0f}",
            'Violations': viol,
            'Solve Time (s)': f"{time_s:.2f}",
            'Status': status
        })

    df_summary = pd.DataFrame(summary_table)
    print("\n" + df_summary.to_string(index=False))

    # Save results
    output_file = Path("results/cst8_fix_validation.json")
    output_file.parent.mkdir(exist_ok=True, parents=True)

    with open(output_file, 'w') as f:
        json.dump({
            'test_config': {
                'date': target_date,
                'country': country,
                'horizons': horizons,
                'alpha': alpha,
                'cst8_enabled': True,
            },
            'results': all_results,
        }, f, indent=2)

    logger.info(f"\nResults saved to: {output_file}")

    # Overall assessment
    all_passed = all(res['validation']['passed'] for res in all_results)

    logger.info("\n" + "=" * 80)
    if all_passed:
        logger.info("✓ ALL TESTS PASSED - Cst-8 fix successful!")
    else:
        logger.warning("✗ SOME TESTS FAILED - Further investigation needed")
    logger.info("=" * 80)

if __name__ == "__main__":
    main()
