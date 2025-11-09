"""
Regenerate Validation Report from Existing Results
Useful for updating report without rerunning validation

Based on: py_script/validation/model_ii_validation/VALIDATION_PLAN.md
"""

import sys
from pathlib import Path
import json
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import report generation function
from run_seasonal_validation import generate_report

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_results(results_dir):
    """Load all JSON result files from a directory"""
    results = []
    json_files = sorted(results_dir.glob("*.json"))

    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                results.append(data)
                logger.info(f"  Loaded: {json_file.name}")
        except Exception as e:
            logger.warning(f"  Error loading {json_file}: {e}")

    return results


def main():
    """Regenerate validation reports from existing results"""

    logger.info("="*80)
    logger.info("Model (ii) Validation Report Generator")
    logger.info("="*80)

    # Process both countries
    for country in ['HU', 'CH']:
        logger.info(f"\n{'='*80}")
        logger.info(f"Regenerating report for {country}...")
        logger.info(f"{'='*80}")

        # Load results
        results_dir = project_root / "results" / "model_ii_validation" / f"{country}_seasonal"

        if not results_dir.exists():
            logger.warning(f"Results directory not found: {results_dir}")
            logger.info(f"Please run validation first: python run_seasonal_validation.py (HU) or run_ch_validation.py (CH)")
            continue

        logger.info(f"\nLoading results from {results_dir}...")
        all_results = load_results(results_dir)

        if not all_results:
            logger.warning("No results found!")
            continue

        logger.info(f"✓ Loaded {len(all_results)} results\n")

        # Generate report
        logger.info("Generating validation report...")
        report = generate_report(all_results, results_dir)

        # Customize header for country
        report_lines = report.split('\n')
        report_lines[0] = f"# Model (ii) Seasonal Validation Report - {'Hungary' if country == 'HU' else 'Switzerland'} Market"
        report = '\n'.join(report_lines)

        # Save report
        report_file = results_dir / "VALIDATION_REPORT.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"✓ Report saved to {report_file}")

        # Print summary
        passed = sum(1 for r in all_results if r.get('all_passed', False))
        logger.info(f"\nResults: {passed}/{len(all_results)} tests passed ({passed/len(all_results)*100:.1f}%)")

    logger.info("\n" + "="*80)
    logger.info("REPORT GENERATION COMPLETE!")
    logger.info("="*80)


if __name__ == "__main__":
    main()
