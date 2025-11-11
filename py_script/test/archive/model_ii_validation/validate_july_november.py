"""
Validation Test: July and November Optimization with Constraint Violation Checks
=================================================================================

This script validates the optimized Model (ii) on July and November data,
with thorough constraint violation checking for removed constraints.

Test Configuration:
- July (Summer): Entire month (July 1-31, 2024) - 31 days
- November (Autumn): Entire month (November 1-30, 2024) - 30 days
- Country: HU
- C-rate: 0.5
- Alpha: 1.0

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

# Import optimized version
from py_script.core.optimizer import BESSOptimizerModelII

# Configuration
DATA_FILE = project_root / 'data' / 'TechArena2025_data_tidy.jsonl'
AFRR_ENERGY_FILE = project_root / 'data' / 'phase2_processed' / 'parquet' / 'afrr_energy.parquet'
OUTPUT_DIR = project_root / 'results' / 'model_ii_validation' / 'july_november'

# Test configuration
TEST_CONFIG = {
    'country': 'HU',
    'c_rate': 0.5,
    'alpha': 1.0,
    'months': [
        {'month': 'July', 'base_date': '2024-07-01', 'num_days': 31},  # Full July (31 days)
        {'month': 'November', 'base_date': '2024-11-01', 'num_days': 30},  # Full November (30 days)
    ]
}


def check_constraint_violations(solution, week_data):
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

        # Get timestamp for reporting
        timestamp = week_data['timestamp'].iloc[t]

        # Check 1: No simultaneous charging and discharging (Cst-3)
        if p_ch > EPSILON and p_dis > EPSILON:
            violations['no_simultaneous_rule'].append({
                'interval': t,
                'timestamp': str(timestamp),
                'p_ch': p_ch,
                'p_dis': p_dis,
                'violation': f"Both p_ch={p_ch:.4f} and p_dis={p_dis:.4f} are positive"
            })

        # Check 2: Cross-market exclusivity rules (Cst-8)
        # DA discharge vs aFRR positive capacity
        if p_dis > EPSILON and p_afrr_pos > EPSILON:
            violations['cross_market_exclusivity'].append({
                'interval': t,
                'timestamp': str(timestamp),
                'type': 'DA_dis_vs_aFRR_pos',
                'p_dis': p_dis,
                'p_afrr_pos': p_afrr_pos,
                'violation': f"Both p_dis={p_dis:.4f} and p_afrr_pos={p_afrr_pos:.4f} are positive"
            })

        # DA charge vs aFRR negative capacity
        if p_ch > EPSILON and p_afrr_neg > EPSILON:
            violations['cross_market_exclusivity'].append({
                'interval': t,
                'timestamp': str(timestamp),
                'type': 'DA_ch_vs_aFRR_neg',
                'p_ch': p_ch,
                'p_afrr_neg': p_afrr_neg,
                'violation': f"Both p_ch={p_ch:.4f} and p_afrr_neg={p_afrr_neg:.4f} are positive"
            })

        # aFRR positive vs negative capacity
        if p_afrr_pos > EPSILON and p_afrr_neg > EPSILON:
            violations['cross_market_exclusivity'].append({
                'interval': t,
                'timestamp': str(timestamp),
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
                'timestamp': str(timestamp),
                'type': 'DA_discharge',
                'p_dis': p_dis,
                'min_bid': P_MIN_BID,
                'violation': f"p_dis={p_dis:.4f} < P_MIN_BID={P_MIN_BID}"
            })

        # DA charge minimum bid
        if 0 < p_ch < P_MIN_BID - EPSILON:
            violations['min_bid_rule_da'].append({
                'interval': t,
                'timestamp': str(timestamp),
                'type': 'DA_charge',
                'p_ch': p_ch,
                'min_bid': P_MIN_BID,
                'violation': f"p_ch={p_ch:.4f} < P_MIN_BID={P_MIN_BID}"
            })

        # aFRR positive capacity minimum bid
        if 0 < p_afrr_pos < P_MIN_BID - EPSILON:
            violations['min_bid_rule_afrr_pos'].append({
                'interval': t,
                'timestamp': str(timestamp),
                'p_afrr_pos': p_afrr_pos,
                'min_bid': P_MIN_BID,
                'violation': f"p_afrr_pos={p_afrr_pos:.4f} < P_MIN_BID={P_MIN_BID}"
            })

        # aFRR negative capacity minimum bid
        if 0 < p_afrr_neg < P_MIN_BID - EPSILON:
            violations['min_bid_rule_afrr_neg'].append({
                'interval': t,
                'timestamp': str(timestamp),
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


def save_decision_variables(solution, month_config):
    """Save decision variable values to a JSON file."""

    # Create output directory for decision variables
    dec_vars_dir = OUTPUT_DIR / 'decision_variables'
    dec_vars_dir.mkdir(parents=True, exist_ok=True)

    # Prepare file name
    filename = f"{month_config['month']}_{month_config['num_days']}days_vars.json"
    filepath = dec_vars_dir / filename

    # Extract key decision variables
    decision_vars = {
        'month': month_config['month'],
        'num_days': month_config['num_days'],
        'base_date': month_config['base_date'],

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


def run_optimization(country, month_config, c_rate, alpha):
    """Run optimization for a specific month."""

    num_days = month_config['num_days']

    print(f"\n{'='*80}")
    print(f"Running: {month_config['month']} ({num_days} days)")
    print(f"{'='*80}")

    try:
        # Initialize optimizer
        optimizer = BESSOptimizerModelII(alpha=alpha)

        # Load data
        print(f"Loading data from {DATA_FILE}...")
        full_data = optimizer.load_and_preprocess_data(
            str(DATA_FILE),
            afrr_energy_file=str(AFRR_ENERGY_FILE)
        )

        # Extract country data
        country_data = optimizer.extract_country_data(full_data, country)

        # Filter to specific period
        base_date = pd.Timestamp(month_config['base_date'])
        end_date = base_date + timedelta(days=num_days)

        period_data = country_data[
            (country_data['timestamp'] >= base_date) &
            (country_data['timestamp'] < end_date)
        ].reset_index(drop=True)

        print(f"Date range: {period_data['timestamp'].min()} to {period_data['timestamp'].max()}")
        print(f"Data points: {len(period_data)} intervals ({len(period_data) * 0.25} hours)")

        # Build model
        print("Building optimization model...")
        build_start = datetime.now()
        model = optimizer.build_optimization_model(period_data, c_rate, daily_cycle_limit=None)
        build_time = (datetime.now() - build_start).total_seconds()

        num_vars = model.nvariables()
        num_constraints = model.nconstraints()

        print(f"Model built: {num_vars:,} variables, {num_constraints:,} constraints")
        print(f"Build time: {build_time:.2f}s")

        # Solve model
        print("Solving optimization model...")
        solution = optimizer.solve_model(model)

        if solution['status'] not in ['optimal', 'feasible']:
            print(f"[ERROR] Solver failed: {solution['status']}")
            return {
                'success': False,
                'error': solution.get('termination_condition', 'Unknown error'),
                'month': month_config['month'],
                'num_days': num_days
            }

        # Extract metrics
        obj_value = solution['objective_value']
        solve_time = solution['solve_time']

        # Calculate revenue breakdown
        da_revenue = sum(
            (period_data['price_day_ahead'].iloc[t] / 1000 * solution['p_dis'].get(t, 0) -
             period_data['price_day_ahead'].iloc[t] / 1000 * solution['p_ch'].get(t, 0)) * 0.25
            for t in range(len(period_data))
        )

        afrr_e_revenue = sum(
            (period_data['price_afrr_energy_pos'].iloc[t] / 1000 * solution['p_afrr_pos_e'].get(t, 0) -
             period_data['price_afrr_energy_neg'].iloc[t] / 1000 * solution['p_afrr_neg_e'].get(t, 0)) * 0.25
            for t in range(len(period_data))
        )

        # Capacity revenue
        capacity_revenue = obj_value - da_revenue - afrr_e_revenue

        # Degradation metrics
        deg_metrics = solution.get('degradation_metrics', {})
        total_deg_cost = deg_metrics.get('total_cyclic_cost_eur', 0)
        efc = deg_metrics.get('equivalent_full_cycles', 0)

        # Energy statistics
        total_charge = sum(solution['p_total_ch'].get(t, 0) * 0.25 for t in range(len(period_data)))
        total_discharge = sum(solution['p_total_dis'].get(t, 0) * 0.25 for t in range(len(period_data)))

        # Check constraint violations
        violations = check_constraint_violations(solution, period_data)

        # Save decision variables
        decision_vars_file = save_decision_variables(solution, month_config)

        result = {
            'success': True,
            'month': month_config['month'],
            'base_date': month_config['base_date'],
            'country': country,
            'c_rate': c_rate,
            'alpha': alpha,
            'num_days': num_days,

            # Performance metrics
            'build_time_sec': build_time,
            'solve_time_sec': solve_time,
            'total_time_sec': build_time + solve_time,
            'solver_status': solution['status'],

            # Model size
            'num_variables': num_vars,
            'num_constraints': num_constraints,
            'num_intervals': len(period_data),

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
            'decision_vars_file': decision_vars_file,

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
            'month': month_config['month'],
            'num_days': num_days
        }


def main():
    """Main execution function."""

    print("\n" + "="*80)
    print("July and November Validation Test - Optimized Model (ii)")
    print("="*80)

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Run all tests
    all_results = []

    for month_config in TEST_CONFIG['months']:
        result = run_optimization(
            country=TEST_CONFIG['country'],
            month_config=month_config,
            c_rate=TEST_CONFIG['c_rate'],
            alpha=TEST_CONFIG['alpha']
        )
        all_results.append(result)

    # Save detailed results
    results_file = OUTPUT_DIR / 'validation_results.json'
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\n[SAVED] Detailed results saved to: {results_file}")

    # Generate summary report
    report_file = OUTPUT_DIR / 'VALIDATION_REPORT.md'
    report_content = generate_report(all_results, report_file)
    with open(report_file, 'w') as f:
        f.write(report_content)
    print(f"[SAVED] Validation report saved to: {report_file}")

    print("\n" + "="*80)
    print("Validation test completed successfully!")
    print("="*80 + "\n")


def generate_report(results, output_file):
    """Generate markdown validation report."""

    report = []
    report.append("# July and November Validation Test - Model (ii)")
    report.append("")
    report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    report.append("## Overview")
    report.append("")
    report.append("This report validates the optimized Model (ii) on July and November data,")
    report.append("with thorough constraint violation checking for removed constraints.")
    report.append("")
    report.append(f"- **Country:** {TEST_CONFIG['country']}")
    report.append(f"- **C-rate:** {TEST_CONFIG['c_rate']}")
    report.append(f"- **Alpha:** {TEST_CONFIG['alpha']}")
    report.append("")

    # Summary table
    report.append("## Performance Summary")
    report.append("")
    report.append("| Month | Days | Solve Time (s) | Objective (EUR) | Degradation (EUR) | Full Cycles | Violations |")
    report.append("|-------|------|----------------|-----------------|-------------------|-------------|------------|")

    for r in results:
        if r['success']:
            report.append(f"| {r['month']} | {r['num_days']} | "
                         f"{r['solve_time_sec']:.2f} | "
                         f"{r['objective_value']:,.2f} | "
                         f"{r['degradation_cost']:,.2f} | "
                         f"{r['num_full_cycles']:.2f} | "
                         f"**{r['violations']['total_violations']}** |")
        else:
            report.append(f"| {r['month']} | {r['num_days']} | FAILED | - | - | - | - |")

    report.append("")

    # Detailed constraint violation analysis
    report.append("## Constraint Violation Analysis")
    report.append("")

    for r in results:
        if not r['success']:
            continue

        violations = r['violations']
        report.append(f"### {r['month']} ({r['num_days']} days)")
        report.append("")

        if violations['total_violations'] == 0:
            report.append("[PASS] **No constraint violations detected**")
            report.append("")
        else:
            report.append(f"[FAIL] **{violations['total_violations']} violations detected**")
            report.append("")

            if violations['no_simultaneous_rule']:
                report.append(f"**No Simultaneous Rule Violations:** {len(violations['no_simultaneous_rule'])}")
                report.append("")
                for v in violations['no_simultaneous_rule'][:5]:  # Show first 5
                    report.append(f"- Interval {v['interval']} ({v['timestamp']}): {v['violation']}")
                if len(violations['no_simultaneous_rule']) > 5:
                    report.append(f"- ... and {len(violations['no_simultaneous_rule']) - 5} more")
                report.append("")

            if violations['cross_market_exclusivity']:
                report.append(f"**Cross-Market Exclusivity Violations:** {len(violations['cross_market_exclusivity'])}")
                report.append("")
                for v in violations['cross_market_exclusivity'][:5]:
                    report.append(f"- Interval {v['interval']} ({v['timestamp']}, {v['type']}): {v['violation']}")
                if len(violations['cross_market_exclusivity']) > 5:
                    report.append(f"- ... and {len(violations['cross_market_exclusivity']) - 5} more")
                report.append("")

            if violations['min_bid_rule_da']:
                report.append(f"**Minimum Bid DA Violations:** {len(violations['min_bid_rule_da'])}")
                report.append("")
                for v in violations['min_bid_rule_da'][:5]:
                    report.append(f"- Interval {v['interval']} ({v['timestamp']}, {v['type']}): {v['violation']}")
                if len(violations['min_bid_rule_da']) > 5:
                    report.append(f"- ... and {len(violations['min_bid_rule_da']) - 5} more")
                report.append("")

            if violations['min_bid_rule_afrr_pos']:
                report.append(f"**Minimum Bid aFRR Pos Violations:** {len(violations['min_bid_rule_afrr_pos'])}")
                report.append("")

            if violations['min_bid_rule_afrr_neg']:
                report.append(f"**Minimum Bid aFRR Neg Violations:** {len(violations['min_bid_rule_afrr_neg'])}")
                report.append("")

    # Overall conclusion
    report.append("## Overall Conclusion")
    report.append("")

    total_violations = sum(r['violations']['total_violations'] for r in results if r['success'])
    if total_violations == 0:
        report.append("[PASS] **All tests passed with no constraint violations**")
        report.append("")
        report.append("The optimized Model (ii) successfully satisfies all removed constraints")
        report.append("across different seasonal conditions (July summer, November autumn).")
    else:
        report.append(f"[FAIL] **Total violations detected: {total_violations}**")
        report.append("")
        report.append("Please review the violation details above.")

    report.append("")
    report.append("---")
    report.append(f"**Generated by:** validate_july_november.py")
    report.append(f"**Report saved to:** {output_file}")

    return "\n".join(report)


if __name__ == "__main__":
    main()
