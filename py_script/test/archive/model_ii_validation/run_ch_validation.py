"""
Model (ii) Seasonal Validation - Switzerland Market
Tests 4 weeks across Q1, Q2, Q3, Q4 of 2024 with cyclic degradation cost integration

Based on: py_script/validation/model_ii_validation/VALIDATION_PLAN.md
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from py_script.core.optimizer import BESSOptimizerModelII
import logging
from datetime import datetime

# Import shared functions from HU validation
from run_seasonal_validation import (
    TEST_WEEKS,
    SCENARIOS,
    run_test_week,
    generate_report
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main test execution for Switzerland"""
    logger.info("="*80)
    logger.info("Model (ii) Seasonal Validation - Switzerland Market")
    logger.info("Based on: py_script/validation/model_ii_validation/VALIDATION_PLAN.md")
    logger.info("="*80)

    # Set up output directory
    output_dir = project_root / "results" / "model_ii_validation" / "CH_seasonal"
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {output_dir}")

    all_results = []

    # Run all test combinations for Switzerland
    total_tests = len(TEST_WEEKS) * len(SCENARIOS)
    current_test = 0

    for week_name, week_info in TEST_WEEKS.items():
        for scenario in SCENARIOS:
            current_test += 1
            logger.info(f"\n[Test {current_test}/{total_tests}]")

            # Create optimizer with correct alpha for this scenario
            scenario_optimizer = BESSOptimizerModelII(alpha=scenario['alpha'])

            result = run_test_week(scenario_optimizer, week_name, week_info, scenario, output_dir, country='CH')
            all_results.append(result)

    # Generate final report
    logger.info("\n" + "="*80)
    logger.info("Generating validation report...")

    # Customize report header for Switzerland
    report_lines = generate_report(all_results, output_dir).split('\n')
    report_lines[0] = "# Model (ii) Seasonal Validation Report - Switzerland Market"
    report = '\n'.join(report_lines)

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
