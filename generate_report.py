"""
Quick script to regenerate validation report from existing JSON results
"""

import json
from pathlib import Path
from collections import defaultdict
import numpy as np
from datetime import datetime

output_dir = Path("results/model_i_validation/HU_seasonal")

# Load all JSON results
all_results = []
for json_file in output_dir.glob("*.json"):
    with open(json_file, 'r', encoding='utf-8') as f:
        result = json.load(f)
        all_results.append(result)

print(f"Loaded {len(all_results)} test results")

# Generate report (copied from run_seasonal_validation.py)
report = []
report.append("# Model (i) Seasonal Validation Report - Hungary Market")
report.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
report.append(f"\n**Model:** BESSOptimizerModelI (Phase II Model i)")
report.append(f"\n**Total Tests:** {len(all_results)}")
report.append("\n" + "="*80 + "\n")

# Executive Summary
report.append("## 1. Executive Summary\n")

passed_tests = sum(1 for r in all_results if r.get('all_passed', False))
failed_tests = len(all_results) - passed_tests

report.append(f"**Overall Results:**")
report.append(f"- Tests Passed: {passed_tests}/{len(all_results)} ({passed_tests/len(all_results)*100:.1f}%)")
report.append(f"- Tests Failed: {failed_tests}/{len(all_results)}")
report.append("")

# Summary table
report.append("## 2. Test Results Summary\n")
report.append("| Week | Scenario | Status | Profit (EUR) | Solve Time (s) | Gap (%) | Violations |")
report.append("|------|----------|--------|--------------|----------------|---------|------------|")

for result in sorted(all_results, key=lambda x: (x['week'], x['scenario']['name'])):
    if 'error' in result:
        report.append(f"| {result['week']} | {result['scenario']['name']} | ERROR | - | - | - | - |")
    else:
        m = result['metrics']
        status = "✓ PASS" if result['all_passed'] else "✗ FAIL"
        report.append(f"| {result['week']} | {result['scenario']['name']} | {status} | "
                     f"{m['RP1_total_profit']:.2f} | {m['SQ3_solve_time']:.2f} | "
                     f"{m['SQ2_optimality_gap']*100:.2f} | {m['SQ4_constraint_violations']} |")

report.append("")

# Revenue Analysis by Season (baseline scenario only)
report.append("## 3. Seasonal Performance Analysis (Baseline Scenario)\n")

baseline_results = [r for r in all_results if r.get('scenario', {}).get('name') == 'baseline' and 'metrics' in r]
if baseline_results:
    report.append("### 3.1 Total Profit by Season\n")
    report.append("| Season | Week | Total Profit (EUR) | Profit/Day (EUR/day) |")
    report.append("|--------|------|--------------------|----------------------|")

    for result in sorted(baseline_results, key=lambda x: x['week']):
        m = result['metrics']
        report.append(f"| {result['week_info']['season']} | {result['week_info']['week']} | "
                     f"{m['RP1_total_profit']:.2f} | {m['RP6_profit_per_day']:.2f} |")
    report.append("")

    # Revenue breakdown
    report.append("### 3.2 Revenue Mix by Season\n")
    report.append("| Season | DA Energy | aFRR Energy | FCR Cap | aFRR Cap |")
    report.append("|--------|-----------|-------------|---------|----------|")

    for result in sorted(baseline_results, key=lambda x: x['week']):
        m = result['metrics']
        total = m['RP1_total_profit']
        if total > 0:
            da_pct = m['RP2_da_profit'] / total * 100
            afrr_e_pct = m['RP3_afrr_energy_profit'] / total * 100
            fcr_pct = m['RP4_fcr_revenue'] / total * 100
            afrr_cap_pct = m['RP5_afrr_capacity_revenue'] / total * 100
            report.append(f"| {result['week_info']['season']} | {da_pct:.1f}% | {afrr_e_pct:.1f}% | "
                         f"{fcr_pct:.1f}% | {afrr_cap_pct:.1f}% |")
    report.append("")

# Must-Pass Criteria Summary
report.append("## 4. Must-Pass Criteria Summary\n")

# Count passes for each criterion
criteria_counts = defaultdict(int)
for result in all_results:
    if 'must_pass' in result:
        for key, val in result['must_pass'].items():
            if val:
                criteria_counts[key] += 1

report.append("| Criterion | Passed | Total | Success Rate |")
report.append("|-----------|--------|-------|--------------|")

for key in sorted(criteria_counts.keys()):
    count = criteria_counts[key]
    total = len([r for r in all_results if 'must_pass' in r])
    rate = count / total * 100 if total > 0 else 0
    report.append(f"| {key} | {count} | {total} | {rate:.1f}% |")

report.append("")

# Key Metrics Summary
report.append("## 5. Key Performance Metrics\n")

if baseline_results:
    report.append("### Average Metrics (Baseline Scenario)\n")

    avg_solve_time = np.mean([r['metrics']['SQ3_solve_time'] for r in baseline_results])
    avg_profit = np.mean([r['metrics']['RP1_total_profit'] for r in baseline_results])
    avg_utilization = np.mean([r['metrics']['EP9_power_capacity_utilization'] for r in baseline_results])
    avg_cycles = np.mean([r['metrics']['SC7_num_full_cycles'] for r in baseline_results])

    report.append(f"- Average Solve Time: {avg_solve_time:.2f} seconds")
    report.append(f"- Average Weekly Profit: {avg_profit:.2f} EUR")
    report.append(f"- Average Power Utilization: {avg_utilization:.1f}%")
    report.append(f"- Average Full Cycles per Week: {avg_cycles:.2f}")
    report.append("")

# Violations Summary
report.append("## 6. Constraint Violations\n")

tests_with_violations = [r for r in all_results if 'violations' in r and len(r['violations']) > 0]

if tests_with_violations:
    report.append(f"**{len(tests_with_violations)} tests had constraint violations:**\n")
    for result in tests_with_violations:
        report.append(f"### {result['week']} - {result['scenario']['name']}")
        report.append(f"Violations: {len(result['violations'])}\n")
        for v in result['violations'][:10]:  # Show up to 10
            report.append(f"- {v}")
        if len(result['violations']) > 10:
            report.append(f"- ... and {len(result['violations']) - 10} more")
        report.append("")
else:
    report.append("✓ **No constraint violations detected in any test!**\n")

# Conclusions
report.append("## 7. Conclusions\n")

if passed_tests == len(all_results):
    report.append("✅ **ALL TESTS PASSED**")
    report.append("\nModel (i) successfully validated across all 4 seasonal weeks and 3 configuration scenarios.")
    report.append("The implementation correctly handles:")
    report.append("- Four-market co-optimization (DA, aFRR-E, FCR, aFRR capacity)")
    report.append("- Total power tracking (p_total = p_DA + p_aFRR_E)")
    report.append("- Cross-market exclusivity constraints")
    report.append("- aFRR Energy Market integration")
elif passed_tests / len(all_results) >= 0.8:
    report.append("⚠️ **PARTIAL PASS** (≥80% tests passed)")
    report.append("\nMost tests passed, but some issues require investigation.")
else:
    report.append("❌ **VALIDATION FAILED** (<80% tests passed)")
    report.append("\nSignificant issues detected. Review violations and must-pass criteria.")

report.append("")
report.append("## 8. Next Steps\n")
report.append("- Review detailed metrics in individual JSON files")
report.append("- Analyze timeseries CSVs for operational patterns")
report.append("- Compare with expected seasonal behaviors (see validation plan)")
report.append("- Use insights to inform Model (ii) cyclic aging implementation")
report.append("")
report.append("---")
report.append(f"\n**Report Location:** {output_dir / 'VALIDATION_REPORT.md'}")
report.append(f"\n**Individual Results:** {output_dir / '*.json'}")

# Write report
report_file = output_dir / "VALIDATION_REPORT.md"
with open(report_file, 'w', encoding='utf-8') as f:
    f.write("\n".join(report))

print(f"✓ Report saved to {report_file}")
print(f"\nValidation Summary:")
print(f"  - Total Tests: {len(all_results)}")
print(f"  - Passed: {passed_tests}/{len(all_results)} ({passed_tests/len(all_results)*100:.1f}%)")
print(f"  - Failed: {failed_tests}")
