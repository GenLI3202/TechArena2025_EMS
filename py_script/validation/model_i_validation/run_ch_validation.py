"""
Model (i) Seasonal Validation - Switzerland Market
Tests 4 weeks across Q1, Q2, Q3, Q4 of 2024

Based on: doc/dev_plan/model_i_vali_plan.md
Modified for CH market
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from py_script.core.optimizer import BESSOptimizerModelI
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import json
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import configurations from the base validation script
exec(open('py_script/validation/run_seasonal_validation.py').read().split('def main():')[0])

# Override the report title for CH
def generate_report_ch(all_results, output_dir):
    """Generate comprehensive validation report for CH"""
    report_text = generate_report(all_results, output_dir)
    # Replace Hungary with Switzerland
    report_text = report_text.replace('Hungary Market', 'Switzerland Market')
    return report_text

def main():
    """Main test execution for CH market"""
    logger.info("="*80)
    logger.info("Model (i) Seasonal Validation - Switzerland Market")
    logger.info("Based on: doc/dev_plan/model_i_vali_plan.md")
    logger.info("="*80)

    # Set up output directory for CH
    output_dir = Path("results/model_i_validation/CH_seasonal")
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {output_dir}")

    # Initialize optimizer
    optimizer = BESSOptimizerModelI()
    all_results = []

    # Run all test combinations
    total_tests = len(TEST_WEEKS) * len(SCENARIOS)
    current_test = 0

    for week_name, week_info in TEST_WEEKS.items():
        for scenario in SCENARIOS:
            current_test += 1
            logger.info(f"\n[Test {current_test}/{total_tests}]")

            # Run test with CH instead of HU
            try:
                logger.info(f"\n{'='*80}")
                logger.info(f"Testing {week_name} - {week_info['season']} (Week {week_info['week']})")
                logger.info(f"Scenario: {scenario['name']} (c_rate={scenario['c_rate']}, cycle_limit={scenario['daily_cycle_limit']})")
                logger.info(f"{'='*80}")

                # Load full data
                logger.info("Loading data...")
                data = optimizer.load_and_preprocess_data("data/TechArena2025_data_tidy.jsonl")

                # Extract week
                start_date = pd.to_datetime(week_info['start_date'])
                end_date = start_date + timedelta(days=7)
                mask = (data.index >= start_date) & (data.index < end_date)
                week_data = data[mask]
                logger.info(f"Extracted {len(week_data)} intervals ({len(week_data)/96:.1f} days)")

                # Extract Switzerland data (CH instead of HU)
                country_data = optimizer.extract_country_data(week_data, 'CH')
                logger.info(f"Switzerland data shape: {country_data.shape}")

                # Build model
                logger.info("Building optimization model...")
                model = optimizer.build_optimization_model(
                    country_data,
                    c_rate=scenario['c_rate'],
                    daily_cycle_limit=scenario['daily_cycle_limit']
                )

                logger.info(f"Model size: {model.nvariables()} variables, {model.nconstraints()} constraints")

                # Solve
                logger.info("Solving...")
                solution = optimizer.solve_model(model)

                logger.info(f"Solution status: {solution['status']}")
                logger.info(f"Objective value: {solution['objective_value']:.2f} EUR")
                logger.info(f"Solve time: {solution['solve_time']:.2f} seconds")

                # Compute metrics
                logger.info("Computing metrics...")
                metrics = compute_metrics(solution, model, country_data, scenario)

                # Validate constraints
                logger.info("Validating constraints...")
                violations = validate_constraints(solution, model, scenario)
                metrics['SQ4_constraint_violations'] = len(violations)

                if violations:
                    logger.warning(f"Found {len(violations)} constraint violations:")
                    for v in violations[:5]:
                        logger.warning(f"  - {v}")
                else:
                    logger.info("✓ All constraints satisfied")

                # Check must-pass criteria
                must_pass = check_must_pass_criteria(metrics, solution, violations)
                all_passed = all(must_pass.values())

                if all_passed:
                    logger.info("✓ All must-pass criteria satisfied")
                else:
                    logger.warning("✗ Some must-pass criteria failed:")
                    for key, val in must_pass.items():
                        if not val:
                            logger.warning(f"  - {key}: FAILED")

                # Save results
                result = {
                    'week': week_name,
                    'week_info': week_info,
                    'scenario': scenario,
                    'metrics': metrics,
                    'violations': violations,
                    'must_pass': must_pass,
                    'all_passed': all_passed
                }

                # Save to JSON
                output_file = output_dir / f"{week_name}_{scenario['name']}.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json_result = {
                        'week': week_name,
                        'week_info': week_info,
                        'scenario': scenario,
                        'metrics': {k: float(v) if isinstance(v, (int, float, np.number)) else v
                                   for k, v in metrics.items()},
                        'violations': violations,
                        'must_pass': must_pass,
                        'all_passed': all_passed
                    }
                    json.dump(json_result, f, indent=2)

                logger.info(f"✓ Results saved to {output_file}")

                # Save timeseries
                timeseries = pd.DataFrame({
                    't': list(solution.get('p_ch', {}).keys()),
                    'p_ch': list(solution.get('p_ch', {}).values()),
                    'p_dis': list(solution.get('p_dis', {}).values()),
                    'p_afrr_pos_e': [solution.get('p_afrr_pos_e', {}).get(t, 0) for t in solution.get('p_ch', {}).keys()],
                    'p_afrr_neg_e': [solution.get('p_afrr_neg_e', {}).get(t, 0) for t in solution.get('p_ch', {}).keys()],
                    'e_soc': [solution.get('e_soc', {}).get(t, 0) for t in solution.get('p_ch', {}).keys()],
                })
                timeseries_file = output_dir / f"{week_name}_{scenario['name']}_timeseries.csv"
                timeseries.to_csv(timeseries_file, index=False)

                all_results.append(result)

            except Exception as e:
                logger.error(f"Test failed: {e}", exc_info=True)
                all_results.append({
                    'week': week_name,
                    'week_info': week_info,
                    'scenario': scenario,
                    'error': str(e),
                    'all_passed': False
                })

    # Generate final report
    logger.info("\n" + "="*80)
    logger.info("Generating validation report...")
    report = generate_report_ch(all_results, output_dir)

    report_file = output_dir / "VALIDATION_REPORT.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    logger.info(f"✓ Report saved to {report_file}")

    # Print summary
    passed = sum(1 for r in all_results if r.get('all_passed', False))
    logger.info("\n" + "="*80)
    logger.info("VALIDATION COMPLETE!")
    logger.info(f"Results: {passed}/{len(all_results)} tests passed ({passed/len(all_results)*100:.1f}%)")
    logger.info(f"Report: {report_file}")
    logger.info("="*80)


if __name__ == "__main__":
    main()
