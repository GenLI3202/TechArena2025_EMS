"""
Comparison Test: Optimized Model (ii) vs Baseline
===================================================

This script compares the performance of the surgically optimized Model (ii)
(with T-indexed binaries removed) against the baseline Model (ii).

Test Matrix:
- Week 14 (Spring) - 2 days
- Week 50 (Winter) - 2 days
- Both weeks tested with optimized and baseline versions

Comparison Metrics:
1. Solve times
2. Optimal profit values
3. Profit composition (DA, aFRR-E, Capacity)
4. Scheduling decisions (charge/discharge patterns)
5. Degradation costs

Author: Gen's BESS Optimization Team
Date: November 2025
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import optimized version (with surgical optimization)
from py_script.core.optimizer import BESSOptimizerModelII as OptimizedModel

# Import baseline version (original, no optimization)
sys.path.insert(0, str(project_root / 'py_script' / 'core'))
from optimizer_original_to_compare import BESSOptimizerModelII as BaselineModel

# Configuration
DATA_FILE = project_root / 'data' / 'TechArena2025_data_tidy.jsonl'
AFRR_ENERGY_FILE = project_root / 'data' / 'phase2_processed' / 'parquet' / 'afrr_energy.parquet'
OUTPUT_DIR = project_root / 'results' / 'model_ii_validation' / 'optimized_vs_baseline'

# Test configuration
TEST_CONFIG = {
    'country': 'HU',
    'c_rate': 0.5,
    'alpha': 1.0,
    'num_days': 2,
    'weeks': [
        {'week': 14, 'season': 'Spring', 'base_date': '2024-04-01'},  # Week 14 (early April)
        {'week': 50, 'season': 'Winter', 'base_date': '2024-12-09'},  # Week 50 (mid-December)
    ]
}


def save_decision_variables(solution, week_config, optimizer_name):
    """Save decision variable values to a JSON file."""

    # Create output directory for decision variables
    dec_vars_dir = OUTPUT_DIR / 'decision_variables'
    dec_vars_dir.mkdir(parents=True, exist_ok=True)

    # Prepare file name
    filename = f"{optimizer_name}_week{week_config['week']}_vars.json"
    filepath = dec_vars_dir / filename

    # Extract key decision variables
    decision_vars = {
        'optimizer': optimizer_name,
        'week': week_config['week'],
        'season': week_config['season'],
        'base_date': week_config['base_date'],

        # Power variables
        'p_ch': solution.get('p_ch', {}),
        'p_dis': solution.get('p_dis', {}),
        'p_total_ch': solution.get('p_total_ch', {}),
        'p_total_dis': solution.get('p_total_dis', {}),

        # aFRR capacity variables
        'p_afrr_pos': solution.get('p_afrr_pos', {}),
        'p_afrr_neg': solution.get('p_afrr_neg', {}),

        # aFRR energy variables
        'p_afrr_pos_e': solution.get('p_afrr_pos_e', {}),
        'p_afrr_neg_e': solution.get('p_afrr_neg_e', {}),

        # State of charge
        'soc': solution.get('soc', {}),

        # Binary variables (if present)
        'y_ch': solution.get('y_ch', {}),
        'y_dis': solution.get('y_dis', {}),
        'y_idle': solution.get('y_idle', {}),
    }

    # Convert any numpy types to native Python types for JSON serialization
    def convert_to_serializable(obj):
        if isinstance(obj, dict):
            return {str(k): convert_to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [convert_to_serializable(item) for item in obj]
        elif hasattr(obj, 'item'):  # numpy scalar
            return obj.item()
        else:
            return float(obj) if isinstance(obj, (int, float)) else obj

    decision_vars = convert_to_serializable(decision_vars)

    # Save to file
    with open(filepath, 'w') as f:
        json.dump(decision_vars, f, indent=2)

    return str(filepath)


def check_constraint_violations(solution, week_data, optimizer):
    """Check if solution violates any of the removed constraints."""

    violations = {
        'no_simultaneous_rule': [],
        'cross_market_exclusivity': [],
        'min_bid_rule_da': [],
        'min_bid_rule_afrr_pos': [],
        'min_bid_rule_afrr_neg': [],
        'total_violations': 0
    }

    # Get parameters
    P_MIN_BID = 1.0  # Minimum bid power (MW)
    EPSILON = 1e-6  # Tolerance for numerical errors

    num_intervals = len(week_data)

    for t in range(num_intervals):
        # Get decision variable values
        p_ch = solution['p_ch'].get(t, 0)
        p_dis = solution['p_dis'].get(t, 0)
        p_afrr_pos = solution.get('p_afrr_pos', {}).get(t, 0)
        p_afrr_neg = solution.get('p_afrr_neg', {}).get(t, 0)
        p_afrr_pos_e = solution.get('p_afrr_pos_e', {}).get(t, 0)
        p_afrr_neg_e = solution.get('p_afrr_neg_e', {}).get(t, 0)

        # Check 1: No simultaneous charging and discharging (Cst-3)
        if p_ch > EPSILON and p_dis > EPSILON:
            violations['no_simultaneous_rule'].append({
                'interval': t,
                'p_ch': p_ch,
                'p_dis': p_dis,
                'violation': f"Both p_ch={p_ch:.4f} and p_dis={p_dis:.4f} are positive"
            })

        # Check 2: Cross-market exclusivity rules (Cst-8)
        # DA discharge vs aFRR positive capacity
        if p_dis > EPSILON and p_afrr_pos > EPSILON:
            violations['cross_market_exclusivity'].append({
                'interval': t,
                'type': 'DA_dis_vs_aFRR_pos',
                'p_dis': p_dis,
                'p_afrr_pos': p_afrr_pos,
                'violation': f"Both p_dis={p_dis:.4f} and p_afrr_pos={p_afrr_pos:.4f} are positive"
            })

        # DA charge vs aFRR negative capacity
        if p_ch > EPSILON and p_afrr_neg > EPSILON:
            violations['cross_market_exclusivity'].append({
                'interval': t,
                'type': 'DA_ch_vs_aFRR_neg',
                'p_ch': p_ch,
                'p_afrr_neg': p_afrr_neg,
                'violation': f"Both p_ch={p_ch:.4f} and p_afrr_neg={p_afrr_neg:.4f} are positive"
            })

        # aFRR positive vs negative capacity
        if p_afrr_pos > EPSILON and p_afrr_neg > EPSILON:
            violations['cross_market_exclusivity'].append({
                'interval': t,
                'type': 'aFRR_pos_vs_neg',
                'p_afrr_pos': p_afrr_pos,
                'p_afrr_neg': p_afrr_neg,
                'violation': f"Both p_afrr_pos={p_afrr_pos:.4f} and p_afrr_neg={p_afrr_neg:.4f} are positive"
            })

        # Check 3: Minimum bid rules (Cst-9)
        # DA discharge minimum bid
        if 0 < p_dis < P_MIN_BID - EPSILON:
            violations['min_bid_rule_da'].append({
                'interval': t,
                'type': 'DA_discharge',
                'p_dis': p_dis,
                'min_bid': P_MIN_BID,
                'violation': f"p_dis={p_dis:.4f} < P_MIN_BID={P_MIN_BID}"
            })

        # DA charge minimum bid
        if 0 < p_ch < P_MIN_BID - EPSILON:
            violations['min_bid_rule_da'].append({
                'interval': t,
                'type': 'DA_charge',
                'p_ch': p_ch,
                'min_bid': P_MIN_BID,
                'violation': f"p_ch={p_ch:.4f} < P_MIN_BID={P_MIN_BID}"
            })

        # aFRR positive capacity minimum bid
        if 0 < p_afrr_pos < P_MIN_BID - EPSILON:
            violations['min_bid_rule_afrr_pos'].append({
                'interval': t,
                'p_afrr_pos': p_afrr_pos,
                'min_bid': P_MIN_BID,
                'violation': f"p_afrr_pos={p_afrr_pos:.4f} < P_MIN_BID={P_MIN_BID}"
            })

        # aFRR negative capacity minimum bid
        if 0 < p_afrr_neg < P_MIN_BID - EPSILON:
            violations['min_bid_rule_afrr_neg'].append({
                'interval': t,
                'p_afrr_neg': p_afrr_neg,
                'min_bid': P_MIN_BID,
                'violation': f"p_afrr_neg={p_afrr_neg:.4f} < P_MIN_BID={P_MIN_BID}"
            })

    # Count total violations
    violations['total_violations'] = (
        len(violations['no_simultaneous_rule']) +
        len(violations['cross_market_exclusivity']) +
        len(violations['min_bid_rule_da']) +
        len(violations['min_bid_rule_afrr_pos']) +
        len(violations['min_bid_rule_afrr_neg'])
    )

    return violations


def run_single_test(optimizer_class, optimizer_name, country, week_config, c_rate, alpha, num_days):
    """Run a single optimization test."""

    print(f"\n{'='*80}")
    print(f"Running: {optimizer_name} - Week {week_config['week']} ({week_config['season']})")
    print(f"{'='*80}")

    try:
        # Initialize optimizer
        optimizer = optimizer_class(alpha=alpha)

        # Load data
        print(f"Loading data from {DATA_FILE}...")
        full_data = optimizer.load_and_preprocess_data(
            str(DATA_FILE),
            afrr_energy_file=str(AFRR_ENERGY_FILE)
        )

        # Extract country data
        country_data = optimizer.extract_country_data(full_data, country)

        # Filter to specific week
        base_date = pd.Timestamp(week_config['base_date'])
        end_date = base_date + timedelta(days=num_days)

        week_data = country_data[
            (country_data['timestamp'] >= base_date) &
            (country_data['timestamp'] < end_date)
        ].reset_index(drop=True)

        print(f"Date range: {week_data['timestamp'].min()} to {week_data['timestamp'].max()}")
        print(f"Data points: {len(week_data)} intervals ({len(week_data) * 0.25} hours)")

        # Build model
        print("Building optimization model...")
        build_start = datetime.now()
        model = optimizer.build_optimization_model(week_data, c_rate, daily_cycle_limit=None)
        build_time = (datetime.now() - build_start).total_seconds()

        num_vars = model.nvariables()
        num_constraints = model.nconstraints()

        print(f"Model built: {num_vars:,} variables, {num_constraints:,} constraints")
        print(f"Build time: {build_time:.2f}s")

        # Solve model
        print("Solving optimization model...")
        solution = optimizer.solve_model(model)

        if solution['status'] not in ['optimal', 'feasible']:
            print(f"❌ Solver failed: {solution['status']}")
            return {
                'success': False,
                'error': solution.get('termination_condition', 'Unknown error'),
                'optimizer': optimizer_name,
                'week': week_config['week'],
                'season': week_config['season']
            }

        # Extract metrics
        obj_value = solution['objective_value']
        solve_time = solution['solve_time']

        # Calculate revenue breakdown
        da_revenue = sum(
            (week_data['price_day_ahead'].iloc[t] / 1000 * solution['p_dis'].get(t, 0) -
             week_data['price_day_ahead'].iloc[t] / 1000 * solution['p_ch'].get(t, 0)) * 0.25
            for t in range(len(week_data))
        )

        afrr_e_revenue = sum(
            (week_data['price_afrr_energy_pos'].iloc[t] / 1000 * solution['p_afrr_pos_e'].get(t, 0) -
             week_data['price_afrr_energy_neg'].iloc[t] / 1000 * solution['p_afrr_neg_e'].get(t, 0)) * 0.25
            for t in range(len(week_data))
        )

        # Capacity revenue (approximate - need block mapping)
        capacity_revenue = obj_value - da_revenue - afrr_e_revenue

        # Degradation metrics
        deg_metrics = solution.get('degradation_metrics', {})
        total_deg_cost = deg_metrics.get('total_cyclic_cost_eur', 0)
        efc = deg_metrics.get('equivalent_full_cycles', 0)

        # Energy statistics
        total_charge = sum(solution['p_total_ch'].get(t, 0) * 0.25 for t in range(len(week_data)))
        total_discharge = sum(solution['p_total_dis'].get(t, 0) * 0.25 for t in range(len(week_data)))

        # Check constraint violations for removed constraints
        violations = check_constraint_violations(solution, week_data, optimizer)

        # Save decision variables
        decision_vars = save_decision_variables(solution, week_config, optimizer_name)

        result = {
            'success': True,
            'optimizer': optimizer_name,
            'week': week_config['week'],
            'season': week_config['season'],
            'country': country,
            'c_rate': c_rate,
            'alpha': alpha,
            'num_days': num_days,
            'base_date': week_config['base_date'],

            # Performance metrics
            'build_time_sec': build_time,
            'solve_time_sec': solve_time,
            'total_time_sec': build_time + solve_time,
            'solver_status': solution['status'],

            # Model size
            'num_variables': num_vars,
            'num_constraints': num_constraints,
            'num_intervals': len(week_data),

            # Economic metrics
            'objective_value': obj_value,
            'da_revenue': da_revenue,
            'afrr_e_revenue': afrr_e_revenue,
            'capacity_revenue': capacity_revenue,
            'gross_revenue': da_revenue + afrr_e_revenue + capacity_revenue,
            'net_profit': obj_value,

            # Degradation metrics
            'degradation_cost': total_deg_cost,
            'num_full_cycles': efc,
            'degradation_ratio_pct': (total_deg_cost / (obj_value + total_deg_cost) * 100) if obj_value > 0 else 0,

            # Energy metrics
            'energy_charged_kwh': total_charge,
            'energy_discharged_kwh': total_discharge,

            # Constraint violations
            'violations': violations,
            'decision_vars_file': decision_vars,

            # Timestamp
            'timestamp': datetime.now().isoformat()
        }

        print(f"[SUCCESS]")
        print(f"   Objective: EUR {obj_value:,.2f}")
        print(f"   Solve time: {solve_time:.2f}s")
        print(f"   DA Revenue: EUR {da_revenue:,.2f}")
        print(f"   aFRR-E Revenue: EUR {afrr_e_revenue:,.2f}")
        print(f"   Capacity Revenue: EUR {capacity_revenue:,.2f}")
        print(f"   Degradation Cost: EUR {total_deg_cost:,.2f}")
        print(f"   Full Cycles: {efc:.2f}")
        print(f"   Constraint Violations: {violations['total_violations']}")
        if violations['total_violations'] > 0:
            print(f"      - No simultaneous rule: {len(violations['no_simultaneous_rule'])}")
            print(f"      - Cross-market exclusivity: {len(violations['cross_market_exclusivity'])}")
            print(f"      - Min bid DA: {len(violations['min_bid_rule_da'])}")
            print(f"      - Min bid aFRR pos: {len(violations['min_bid_rule_afrr_pos'])}")
            print(f"      - Min bid aFRR neg: {len(violations['min_bid_rule_afrr_neg'])}")

        return result

    except Exception as e:
        print(f"[ERROR]: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'optimizer': optimizer_name,
            'week': week_config['week'],
            'season': week_config['season']
        }


def generate_comparison_report(results, output_file):
    """Generate markdown comparison report."""

    report = []
    report.append("# Model (ii) Surgical Optimization: Performance Comparison")
    report.append("")
    report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    report.append("## Overview")
    report.append("")
    report.append("This report compares the surgically optimized Model (ii) (T-indexed binaries removed)")
    report.append("against the baseline Model (ii) for two test weeks:")
    report.append("")
    report.append(f"- **Test Configuration:** {TEST_CONFIG['num_days']}-day optimization")
    report.append(f"- **Country:** {TEST_CONFIG['country']}")
    report.append(f"- **C-rate:** {TEST_CONFIG['c_rate']}")
    report.append(f"- **Alpha:** {TEST_CONFIG['alpha']}")
    report.append("")

    # Organize results by week
    weeks_data = {}
    for r in results:
        if not r['success']:
            continue
        week = r['week']
        if week not in weeks_data:
            weeks_data[week] = {'optimized': None, 'baseline': None}

        if r['optimizer'] == 'Optimized':
            weeks_data[week]['optimized'] = r
        else:
            weeks_data[week]['baseline'] = r

    # Summary table
    report.append("## Performance Summary")
    report.append("")
    report.append("| Week | Season | Optimizer | Solve Time (s) | Objective (EUR) | Degradation (EUR) | Full Cycles |")
    report.append("|------|--------|-----------|----------------|-----------------|-------------------|-------------|")

    for week_num in sorted(weeks_data.keys()):
        week_results = weeks_data[week_num]
        if week_results['optimized']:
            r = week_results['optimized']
            report.append(f"| {r['week']} | {r['season']} | **Optimized** | "
                         f"**{r['solve_time_sec']:.2f}** | "
                         f"**{r['objective_value']:,.2f}** | "
                         f"**{r['degradation_cost']:,.2f}** | "
                         f"**{r['num_full_cycles']:.2f}** |")
        if week_results['baseline']:
            r = week_results['baseline']
            report.append(f"| {r['week']} | {r['season']} | Baseline | "
                         f"{r['solve_time_sec']:.2f} | "
                         f"{r['objective_value']:,.2f} | "
                         f"{r['degradation_cost']:,.2f} | "
                         f"{r['num_full_cycles']:.2f} |")

    report.append("")

    # Detailed comparison by week
    for week_num in sorted(weeks_data.keys()):
        week_results = weeks_data[week_num]
        optimized = week_results['optimized']
        baseline = week_results['baseline']

        if not optimized or not baseline:
            continue

        report.append(f"## Week {week_num} ({optimized['season']}) - Detailed Comparison")
        report.append("")

        # Performance comparison
        speedup = baseline['solve_time_sec'] / optimized['solve_time_sec'] if optimized['solve_time_sec'] > 0 else 0
        profit_diff = optimized['objective_value'] - baseline['objective_value']
        profit_diff_pct = (profit_diff / baseline['objective_value'] * 100) if baseline['objective_value'] != 0 else 0

        report.append("### Solve Time Performance")
        report.append("")
        report.append(f"- **Optimized:** {optimized['solve_time_sec']:.2f}s")
        report.append(f"- **Baseline:** {baseline['solve_time_sec']:.2f}s")
        report.append(f"- **Speedup:** {speedup:.2f}x {'' if speedup <= 1 else '(FASTER)'}")
        report.append("")

        # Model size comparison
        report.append("### Model Size")
        report.append("")
        report.append("| Metric | Optimized | Baseline | Reduction |")
        report.append("|--------|-----------|----------|-----------|")

        var_reduction = baseline['num_variables'] - optimized['num_variables']
        var_reduction_pct = (var_reduction / baseline['num_variables'] * 100) if baseline['num_variables'] > 0 else 0

        const_reduction = baseline['num_constraints'] - optimized['num_constraints']
        const_reduction_pct = (const_reduction / baseline['num_constraints'] * 100) if baseline['num_constraints'] > 0 else 0

        report.append(f"| Variables | {optimized['num_variables']:,} | {baseline['num_variables']:,} | "
                     f"{var_reduction:,} ({var_reduction_pct:.1f}%) |")
        report.append(f"| Constraints | {optimized['num_constraints']:,} | {baseline['num_constraints']:,} | "
                     f"{const_reduction:,} ({const_reduction_pct:.1f}%) |")
        report.append("")

        # Profit comparison
        report.append("### Profit Comparison")
        report.append("")
        report.append(f"- **Optimized:** €{optimized['objective_value']:,.2f}")
        report.append(f"- **Baseline:** €{baseline['objective_value']:,.2f}")
        report.append(f"- **Difference:** €{profit_diff:,.2f} ({profit_diff_pct:+.3f}%)")
        report.append("")

        # Revenue breakdown
        report.append("### Revenue Breakdown")
        report.append("")
        report.append("| Revenue Source | Optimized (EUR) | Baseline (EUR) | Diff (%) |")
        report.append("|----------------|-----------------|----------------|----------|")

        da_diff_pct = ((optimized['da_revenue'] - baseline['da_revenue']) / baseline['da_revenue'] * 100) if baseline['da_revenue'] != 0 else 0
        afrr_diff_pct = ((optimized['afrr_e_revenue'] - baseline['afrr_e_revenue']) / baseline['afrr_e_revenue'] * 100) if baseline['afrr_e_revenue'] != 0 else 0
        cap_diff_pct = ((optimized['capacity_revenue'] - baseline['capacity_revenue']) / baseline['capacity_revenue'] * 100) if baseline['capacity_revenue'] != 0 else 0

        report.append(f"| Day-Ahead | {optimized['da_revenue']:,.2f} | {baseline['da_revenue']:,.2f} | {da_diff_pct:+.2f}% |")
        report.append(f"| aFRR Energy | {optimized['afrr_e_revenue']:,.2f} | {baseline['afrr_e_revenue']:,.2f} | {afrr_diff_pct:+.2f}% |")
        report.append(f"| Capacity | {optimized['capacity_revenue']:,.2f} | {baseline['capacity_revenue']:,.2f} | {cap_diff_pct:+.2f}% |")
        report.append("")

        # Degradation comparison
        report.append("### Degradation Metrics")
        report.append("")
        report.append("| Metric | Optimized | Baseline | Diff (%) |")
        report.append("|--------|-----------|----------|----------|")

        deg_diff_pct = ((optimized['degradation_cost'] - baseline['degradation_cost']) / baseline['degradation_cost'] * 100) if baseline['degradation_cost'] != 0 else 0
        cycles_diff_pct = ((optimized['num_full_cycles'] - baseline['num_full_cycles']) / baseline['num_full_cycles'] * 100) if baseline['num_full_cycles'] != 0 else 0

        report.append(f"| Degradation Cost (EUR) | {optimized['degradation_cost']:,.2f} | {baseline['degradation_cost']:,.2f} | {deg_diff_pct:+.2f}% |")
        report.append(f"| Full Cycles | {optimized['num_full_cycles']:.2f} | {baseline['num_full_cycles']:.2f} | {cycles_diff_pct:+.2f}% |")
        report.append(f"| Deg. Ratio (%) | {optimized['degradation_ratio_pct']:.2f}% | {baseline['degradation_ratio_pct']:.2f}% | - |")
        report.append("")

    # Overall conclusions
    report.append("## Conclusions")
    report.append("")

    # Calculate overall speedup
    total_speedup = []
    for week_num in sorted(weeks_data.keys()):
        week_results = weeks_data[week_num]
        if week_results['optimized'] and week_results['baseline']:
            speedup = week_results['baseline']['solve_time_sec'] / week_results['optimized']['solve_time_sec']
            total_speedup.append(speedup)

    if total_speedup:
        avg_speedup = np.mean(total_speedup)
        report.append(f"**Average Speedup:** {avg_speedup:.2f}x")
        report.append("")

    # Check if solutions are equivalent
    max_profit_diff = 0
    for week_num in sorted(weeks_data.keys()):
        week_results = weeks_data[week_num]
        if week_results['optimized'] and week_results['baseline']:
            diff_pct = abs((week_results['optimized']['objective_value'] - week_results['baseline']['objective_value']) / week_results['baseline']['objective_value'] * 100)
            max_profit_diff = max(max_profit_diff, diff_pct)

    if max_profit_diff < 0.1:
        report.append("[PASS] **Solution Quality:** Optimized and baseline solutions are numerically equivalent (< 0.1% difference)")
    elif max_profit_diff < 1.0:
        report.append("[WARNING] **Solution Quality:** Minor differences detected (< 1% difference)")
    else:
        report.append("[FAIL] **Solution Quality:** Significant differences detected (> 1% difference)")

    report.append("")
    report.append("---")
    report.append(f"**Generated by:** compare_optimized_vs_baseline.py")
    report.append(f"**Report saved to:** {output_file}")

    return "\n".join(report)


def main():
    """Main execution function."""

    print("\n" + "="*80)
    print("Model (ii) Surgical Optimization: Comparison Test")
    print("="*80)

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Run all tests
    all_results = []

    for week_config in TEST_CONFIG['weeks']:
        # Test optimized version
        result_optimized = run_single_test(
            optimizer_class=OptimizedModel,
            optimizer_name='Optimized',
            country=TEST_CONFIG['country'],
            week_config=week_config,
            c_rate=TEST_CONFIG['c_rate'],
            alpha=TEST_CONFIG['alpha'],
            num_days=TEST_CONFIG['num_days']
        )
        all_results.append(result_optimized)

        # Test baseline version
        result_baseline = run_single_test(
            optimizer_class=BaselineModel,
            optimizer_name='Baseline',
            country=TEST_CONFIG['country'],
            week_config=week_config,
            c_rate=TEST_CONFIG['c_rate'],
            alpha=TEST_CONFIG['alpha'],
            num_days=TEST_CONFIG['num_days']
        )
        all_results.append(result_baseline)

    # Save detailed results
    results_file = OUTPUT_DIR / 'comparison_results.json'
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\n[SAVED] Detailed results saved to: {results_file}")

    # Generate comparison report
    report_file = OUTPUT_DIR / 'COMPARISON_REPORT.md'
    report_content = generate_comparison_report(all_results, report_file)
    with open(report_file, 'w') as f:
        f.write(report_content)
    print(f"[SAVED] Comparison report saved to: {report_file}")

    print("\n" + "="*80)
    print("Comparison test completed successfully!")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
