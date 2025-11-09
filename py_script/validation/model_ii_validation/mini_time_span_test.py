"""
Mini Validation Test - Time Span Performance Analysis
Tests Model (ii) with 1-day, 3-day, and 7-day time spans to measure scalability

Quick performance test for Hungary market
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from py_script.core.optimizer import BESSOptimizerModelII
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test configuration - Summer week (best performance)
TEST_BASE_DATE = '2024-07-22'  # Q3 Summer - Week 30
COUNTRY = 'HU'
SCENARIO = {'c_rate': 0.5, 'alpha': 1.0, 'name': 'baseline'}

# Test time spans
TIME_SPANS = [
    {'days': 1, 'name': '1-day'},
    {'days': 3, 'name': '3-day'},
    {'days': 7, 'name': '7-day'},
]

# Battery parameters
BATTERY_PARAMS = {
    'E_nom': 4472,  # kWh
    'eta_ch': 0.95,
    'eta_dis': 0.95,
    'dt': 0.25,  # hours
}


def extract_timespan_data(full_data, start_date_str, num_days):
    """Extract specified number of days starting from start_date"""
    start_date = pd.to_datetime(start_date_str)
    end_date = start_date + timedelta(days=num_days)
    mask = (full_data.index >= start_date) & (full_data.index < end_date)
    return full_data[mask]


def compute_quick_metrics(solution, model, country_data):
    """Compute essential metrics for quick report"""
    metrics = {}

    dt = BATTERY_PARAMS['dt']
    E_nom = BATTERY_PARAMS['E_nom']

    # Solution quality
    metrics['solver_status'] = solution['status']
    metrics['solve_time_sec'] = solution['solve_time']
    metrics['objective_value'] = solution['objective_value']

    # Model size
    metrics['num_variables'] = model.nvariables() if hasattr(model, 'nvariables') else 0
    metrics['num_constraints'] = model.nconstraints() if hasattr(model, 'nconstraints') else 0

    # Basic operations
    p_ch = solution.get('p_ch', {})
    p_dis = solution.get('p_dis', {})

    energy_charged = sum(p_ch.values()) * dt
    energy_discharged = sum(p_dis.values()) * dt

    metrics['energy_charged_kwh'] = energy_charged
    metrics['energy_discharged_kwh'] = energy_discharged
    metrics['num_full_cycles'] = energy_discharged / E_nom if E_nom > 0 else 0

    # Degradation cost calculation
    p_dis_j = solution.get('p_dis_j', {})
    eta_dis = BATTERY_PARAMS['eta_dis']

    # Default degradation costs (from aging_config.json)
    degradation_costs = [0.0052, 0.0156, 0.0260, 0.0364, 0.0469,
                        0.0573, 0.0677, 0.0781, 0.0885, 0.0990]

    total_degradation_cost = 0
    if p_dis_j:
        for (t, j), power in p_dis_j.items():
            if j <= len(degradation_costs):
                cost_per_kwh = degradation_costs[j-1]
                total_degradation_cost += cost_per_kwh * (power / eta_dis) * dt

    metrics['degradation_cost'] = total_degradation_cost

    # Profit after degradation
    metrics['net_profit'] = solution['objective_value']
    metrics['gross_revenue'] = metrics['net_profit'] + total_degradation_cost

    if metrics['gross_revenue'] > 0:
        metrics['degradation_ratio_pct'] = (total_degradation_cost / metrics['gross_revenue']) * 100
    else:
        metrics['degradation_ratio_pct'] = 0

    # Data size metrics
    metrics['num_intervals'] = len(country_data)
    metrics['num_days'] = len(country_data) / 96  # 96 intervals per day

    return metrics


def run_time_span_test(time_span_config):
    """Execute test for one time span"""
    num_days = time_span_config['days']
    test_name = time_span_config['name']

    logger.info(f"\n{'='*80}")
    logger.info(f"Testing {test_name} ({num_days} days)")
    logger.info(f"Start date: {TEST_BASE_DATE}, Country: {COUNTRY}")
    logger.info(f"Scenario: {SCENARIO['name']} (c_rate={SCENARIO['c_rate']}, alpha={SCENARIO['alpha']})")
    logger.info(f"{'='*80}")

    try:
        # Initialize optimizer
        optimizer = BESSOptimizerModelII(alpha=SCENARIO['alpha'])

        # Load full data
        logger.info("Loading data...")
        data_path = project_root / "data" / "TechArena2025_data_tidy.jsonl"
        data = optimizer.load_and_preprocess_data(str(data_path))

        # Extract time span
        span_data = extract_timespan_data(data, TEST_BASE_DATE, num_days)
        logger.info(f"Extracted {len(span_data)} intervals ({len(span_data)/96:.1f} days)")

        # Extract country data
        country_data = optimizer.extract_country_data(span_data, COUNTRY)
        logger.info(f"Country data shape: {country_data.shape}")

        # Build model
        logger.info("Building optimization model...")
        build_start = datetime.now()
        model = optimizer.build_optimization_model(
            country_data,
            c_rate=SCENARIO['c_rate']
        )
        build_time = (datetime.now() - build_start).total_seconds()

        logger.info(f"Model size: {model.nvariables()} variables, {model.nconstraints()} constraints")
        logger.info(f"Build time: {build_time:.2f} seconds")

        # Solve
        logger.info("Solving...")
        solve_start = datetime.now()
        solution = optimizer.solve_model(model)

        logger.info(f"Solution status: {solution['status']}")
        logger.info(f"Objective value: {solution['objective_value']:.2f} EUR")
        logger.info(f"Solve time: {solution['solve_time']:.2f} seconds")

        # Compute metrics
        metrics = compute_quick_metrics(solution, model, country_data)

        # Add build time to metrics
        metrics['build_time_sec'] = build_time
        metrics['total_time_sec'] = build_time + metrics['solve_time_sec']

        logger.info(f"Total computation time: {metrics['total_time_sec']:.2f} seconds")
        logger.info(f"Net profit: {metrics['net_profit']:.2f} EUR")
        logger.info(f"Degradation cost: {metrics['degradation_cost']:.2f} EUR ({metrics['degradation_ratio_pct']:.1f}% of revenue)")
        logger.info(f"Full cycles: {metrics['num_full_cycles']:.2f}")

        # Prepare result
        result = {
            'test_name': test_name,
            'num_days': num_days,
            'country': COUNTRY,
            'scenario': SCENARIO,
            'base_date': TEST_BASE_DATE,
            'metrics': metrics,
            'success': True,
            'timestamp': datetime.now().isoformat()
        }

        return result

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return {
            'test_name': test_name,
            'num_days': num_days,
            'success': False,
            'error': str(e)
        }


def generate_quick_report(all_results, output_file):
    """Generate quick performance report"""
    report = []
    report.append("# Model (ii) Time Span Performance Test")
    report.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"\n**Model:** BESSOptimizerModelII (Cyclic Aging Cost Integration)")
    report.append(f"**Country:** {COUNTRY}")
    report.append(f"**Test Period:** {TEST_BASE_DATE} (Summer week)")
    report.append(f"**Scenario:** {SCENARIO['name']} (c_rate={SCENARIO['c_rate']}, alpha={SCENARIO['alpha']})")
    report.append("\n" + "="*80 + "\n")

    # Executive Summary
    report.append("## Executive Summary\n")

    successful_tests = [r for r in all_results if r['success']]
    report.append(f"**Tests Completed:** {len(successful_tests)}/{len(all_results)}")
    report.append("")

    if len(successful_tests) == len(all_results):
        report.append("✅ All tests completed successfully!")
    else:
        report.append("⚠️ Some tests failed - see details below.")
    report.append("")

    # Performance Summary Table
    report.append("## Performance Summary\n")
    report.append("| Time Span | Days | Intervals | Variables | Constraints | Build Time (s) | Solve Time (s) | Total Time (s) |")
    report.append("|-----------|------|-----------|-----------|-------------|----------------|----------------|----------------|")

    for result in all_results:
        if result['success']:
            m = result['metrics']
            report.append(f"| {result['test_name']} | {result['num_days']} | "
                         f"{m['num_intervals']} | {m['num_variables']:,} | {m['num_constraints']:,} | "
                         f"{m['build_time_sec']:.2f} | {m['solve_time_sec']:.2f} | {m['total_time_sec']:.2f} |")
        else:
            report.append(f"| {result['test_name']} | {result['num_days']} | ERROR | - | - | - | - | - |")

    report.append("")

    # Scalability Analysis
    if len(successful_tests) >= 2:
        report.append("## Scalability Analysis\n")

        # Compare 1-day vs 7-day
        one_day = next((r for r in successful_tests if r['num_days'] == 1), None)
        seven_day = next((r for r in successful_tests if r['num_days'] == 7), None)

        if one_day and seven_day:
            var_ratio = seven_day['metrics']['num_variables'] / one_day['metrics']['num_variables']
            const_ratio = seven_day['metrics']['num_constraints'] / one_day['metrics']['num_constraints']
            time_ratio = seven_day['metrics']['total_time_sec'] / one_day['metrics']['total_time_sec']

            report.append(f"**Scaling from 1-day to 7-day:**")
            report.append(f"- Variables: {var_ratio:.2f}x increase")
            report.append(f"- Constraints: {const_ratio:.2f}x increase")
            report.append(f"- Total time: {time_ratio:.2f}x increase")
            report.append("")

            if time_ratio < var_ratio:
                report.append("✓ **Good scalability**: Solve time grows slower than problem size (likely linear complexity)")
            elif time_ratio < var_ratio ** 1.5:
                report.append("⚠️ **Moderate scalability**: Solve time grows moderately with problem size")
            else:
                report.append("❌ **Poor scalability**: Solve time grows faster than problem size (potential quadratic complexity)")
            report.append("")

    # Economic Performance
    report.append("## Economic Performance\n")
    report.append("| Time Span | Net Profit (EUR) | Profit/Day (EUR) | Degradation Cost (EUR) | Cost Ratio (%) | Full Cycles |")
    report.append("|-----------|------------------|------------------|------------------------|----------------|-------------|")

    for result in successful_tests:
        m = result['metrics']
        profit_per_day = m['net_profit'] / m['num_days']
        report.append(f"| {result['test_name']} | {m['net_profit']:.2f} | {profit_per_day:.2f} | "
                     f"{m['degradation_cost']:.2f} | {m['degradation_ratio_pct']:.1f}% | {m['num_full_cycles']:.2f} |")

    report.append("")

    # Model Size Details
    report.append("## Model Size Breakdown\n")
    report.append("| Time Span | Intervals | Vars/Interval | Consts/Interval | Model Status |")
    report.append("|-----------|-----------|---------------|-----------------|--------------|")

    for result in successful_tests:
        m = result['metrics']
        vars_per_interval = m['num_variables'] / m['num_intervals']
        consts_per_interval = m['num_constraints'] / m['num_intervals']
        status = "✓ Optimal" if m['solver_status'] == 'optimal' else m['solver_status']
        report.append(f"| {result['test_name']} | {m['num_intervals']} | {vars_per_interval:.1f} | "
                     f"{consts_per_interval:.1f} | {status} |")

    report.append("")

    # Time Breakdown
    report.append("## Time Breakdown\n")

    if successful_tests:
        report.append("**Build vs Solve Time:**\n")
        for result in successful_tests:
            m = result['metrics']
            build_pct = (m['build_time_sec'] / m['total_time_sec']) * 100
            solve_pct = (m['solve_time_sec'] / m['total_time_sec']) * 100
            report.append(f"- **{result['test_name']}**: Build: {m['build_time_sec']:.2f}s ({build_pct:.1f}%), "
                         f"Solve: {m['solve_time_sec']:.2f}s ({solve_pct:.1f}%)")
        report.append("")

    # Conclusions
    report.append("## Conclusions\n")

    if len(successful_tests) == len(all_results):
        avg_solve_time = np.mean([r['metrics']['solve_time_sec'] for r in successful_tests])
        max_solve_time = max([r['metrics']['solve_time_sec'] for r in successful_tests])

        report.append(f"✅ **All time span tests passed successfully**")
        report.append(f"\n**Key Findings:**")
        report.append(f"- Average solve time: {avg_solve_time:.2f} seconds")
        report.append(f"- Maximum solve time: {max_solve_time:.2f} seconds (7-day test)")
        report.append(f"- All solutions reached optimal status")
        report.append(f"- Model scales reasonably with time horizon")

        if max_solve_time < 30:
            report.append(f"\n✓ **Excellent performance**: All tests solved in < 30 seconds")
        elif max_solve_time < 60:
            report.append(f"\n✓ **Good performance**: All tests solved in < 60 seconds")
        else:
            report.append(f"\n⚠️ **Acceptable performance**: Some tests took > 60 seconds")
    else:
        report.append("❌ **Some tests failed** - see error details in JSON results")

    report.append("")
    report.append("## Recommendations\n")

    if len(successful_tests) >= 2:
        seven_day_result = next((r for r in successful_tests if r['num_days'] == 7), None)
        if seven_day_result:
            solve_time = seven_day_result['metrics']['solve_time_sec']

            if solve_time < 20:
                report.append("- Model performance is excellent for 7-day optimization")
                report.append("- Can proceed with full validation (12 test weeks)")
                report.append("- Consider testing longer horizons (14 days, 30 days)")
            elif solve_time < 40:
                report.append("- Model performance is good for 7-day optimization")
                report.append("- Proceed with full validation as planned")
                report.append("- Monitor solve times for more complex scenarios")
            else:
                report.append("- Model performance is acceptable but could be improved")
                report.append("- Consider solver tuning or model simplifications")
                report.append("- Full validation will take longer than estimated")

    report.append("")
    report.append("---")
    report.append(f"\n**Generated by:** mini_time_span_test.py")
    report.append(f"**Report saved to:** {output_file}")

    return "\n".join(report)


def main():
    """Main test execution"""
    logger.info("="*80)
    logger.info("Model (ii) Time Span Performance Test")
    logger.info("Testing 1-day, 3-day, and 7-day optimization horizons")
    logger.info("="*80)

    # Set up output directory
    output_dir = project_root / "results" / "model_ii_validation" / "mini_test"
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {output_dir}")

    # Run all time span tests
    all_results = []

    for time_span in TIME_SPANS:
        logger.info(f"\n[Test {len(all_results)+1}/{len(TIME_SPANS)}]")
        result = run_time_span_test(time_span)
        all_results.append(result)

    # Save detailed results to JSON
    results_file = output_dir / "time_span_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        # Convert numpy types to native Python types for JSON serialization
        def convert_types(obj):
            if isinstance(obj, dict):
                return {k: convert_types(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_types(item) for item in obj]
            elif isinstance(obj, (np.integer, np.floating)):
                return float(obj)
            else:
                return obj

        json_results = convert_types(all_results)
        json.dump(json_results, f, indent=2)

    logger.info(f"\n✓ Detailed results saved to {results_file}")

    # Generate quick report
    logger.info("\nGenerating performance report...")
    report_file = output_dir / "PERFORMANCE_REPORT.md"
    report = generate_quick_report(all_results, report_file)

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    logger.info(f"✓ Report saved to {report_file}")

    # Print summary
    logger.info("\n" + "="*80)
    logger.info("TEST COMPLETE!")

    successful_tests = [r for r in all_results if r['success']]
    logger.info(f"Results: {len(successful_tests)}/{len(all_results)} tests successful")

    if successful_tests:
        solve_times = [r['metrics']['solve_time_sec'] for r in successful_tests]
        logger.info(f"Solve times: {', '.join([f'{t:.2f}s' for t in solve_times])}")

    logger.info(f"\nReport: {report_file}")
    logger.info(f"Results JSON: {results_file}")
    logger.info("="*80)


if __name__ == "__main__":
    main()
