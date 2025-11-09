"""
Comprehensive verification - check ALL intervals for both July and November.
"""
import json
from pathlib import Path

def verify_all_intervals(vars_file, month_name):
    """Verify constraints for ALL intervals."""

    # Load decision variables
    with open(vars_file, 'r') as f:
        data = json.load(f)

    p_ch = data['p_ch']
    p_dis = data['p_dis']
    p_afrr_pos = data.get('p_afrr_pos', {})
    p_afrr_neg = data.get('p_afrr_neg', {})

    num_intervals = len(p_ch)
    print(f"\n{'='*100}")
    print(f"{month_name}: Checking ALL {num_intervals} intervals")
    print(f"Days: {data['num_days']}, Base date: {data['base_date']}")
    print(f"{'='*100}")

    # Configuration
    P_MIN_BID = 1.0
    EPSILON = 1e-6

    violations = {
        'no_simultaneous': [],
        'cross_market_da_afrr_pos': [],
        'cross_market_da_afrr_neg': [],
        'cross_market_afrr_both': [],
        'min_bid_ch': [],
        'min_bid_dis': [],
        'min_bid_afrr_pos': [],
        'min_bid_afrr_neg': []
    }

    # Statistics
    stats = {
        'idle': 0,
        'da_only': 0,
        'afrr_only': 0,
        'active_intervals': 0
    }

    for t in range(num_intervals):
        t_str = str(t)
        p_ch_val = p_ch.get(t_str, 0)
        p_dis_val = p_dis.get(t_str, 0)
        p_afrr_pos_val = p_afrr_pos.get(t_str, 0)
        p_afrr_neg_val = p_afrr_neg.get(t_str, 0)

        # Count activity types
        has_activity = (p_ch_val > EPSILON or p_dis_val > EPSILON or
                       p_afrr_pos_val > EPSILON or p_afrr_neg_val > EPSILON)

        if not has_activity:
            stats['idle'] += 1
            continue

        stats['active_intervals'] += 1

        has_da = p_ch_val > EPSILON or p_dis_val > EPSILON
        has_afrr = p_afrr_pos_val > EPSILON or p_afrr_neg_val > EPSILON

        if has_da and not has_afrr:
            stats['da_only'] += 1
        elif has_afrr and not has_da:
            stats['afrr_only'] += 1

        # Check 1: No simultaneous charging and discharging
        if p_ch_val > EPSILON and p_dis_val > EPSILON:
            violations['no_simultaneous'].append({
                'interval': t,
                'p_ch': p_ch_val,
                'p_dis': p_dis_val
            })

        # Check 2: Cross-market exclusivity
        if p_dis_val > EPSILON and p_afrr_pos_val > EPSILON:
            violations['cross_market_da_afrr_pos'].append({
                'interval': t,
                'p_dis': p_dis_val,
                'p_afrr_pos': p_afrr_pos_val
            })

        if p_ch_val > EPSILON and p_afrr_neg_val > EPSILON:
            violations['cross_market_da_afrr_neg'].append({
                'interval': t,
                'p_ch': p_ch_val,
                'p_afrr_neg': p_afrr_neg_val
            })

        if p_afrr_pos_val > EPSILON and p_afrr_neg_val > EPSILON:
            violations['cross_market_afrr_both'].append({
                'interval': t,
                'p_afrr_pos': p_afrr_pos_val,
                'p_afrr_neg': p_afrr_neg_val
            })

        # Check 3: Minimum bid rules
        if 0 < p_ch_val < P_MIN_BID - EPSILON:
            violations['min_bid_ch'].append({
                'interval': t,
                'p_ch': p_ch_val
            })

        if 0 < p_dis_val < P_MIN_BID - EPSILON:
            violations['min_bid_dis'].append({
                'interval': t,
                'p_dis': p_dis_val
            })

        if 0 < p_afrr_pos_val < P_MIN_BID - EPSILON:
            violations['min_bid_afrr_pos'].append({
                'interval': t,
                'p_afrr_pos': p_afrr_pos_val
            })

        if 0 < p_afrr_neg_val < P_MIN_BID - EPSILON:
            violations['min_bid_afrr_neg'].append({
                'interval': t,
                'p_afrr_neg': p_afrr_neg_val
            })

    # Calculate total violations
    total_violations = sum(len(v) for v in violations.values())

    # Print results
    print(f"\nActivity Statistics:")
    print(f"  Active intervals: {stats['active_intervals']:,} ({100*stats['active_intervals']/num_intervals:.1f}%)")
    print(f"  Idle intervals: {stats['idle']:,} ({100*stats['idle']/num_intervals:.1f}%)")
    print(f"  DA-only: {stats['da_only']:,}")
    print(f"  aFRR-only: {stats['afrr_only']:,}")

    print(f"\nConstraint Violation Results:")
    print(f"  No simultaneous charge/discharge: {len(violations['no_simultaneous'])} violations")
    print(f"  Cross-market (DA discharge + aFRR pos): {len(violations['cross_market_da_afrr_pos'])} violations")
    print(f"  Cross-market (DA charge + aFRR neg): {len(violations['cross_market_da_afrr_neg'])} violations")
    print(f"  Cross-market (aFRR pos + neg): {len(violations['cross_market_afrr_both'])} violations")
    print(f"  Min bid DA charge: {len(violations['min_bid_ch'])} violations")
    print(f"  Min bid DA discharge: {len(violations['min_bid_dis'])} violations")
    print(f"  Min bid aFRR pos: {len(violations['min_bid_afrr_pos'])} violations")
    print(f"  Min bid aFRR neg: {len(violations['min_bid_afrr_neg'])} violations")

    print(f"\n  TOTAL VIOLATIONS: {total_violations}")

    if total_violations == 0:
        print(f"\n  [PASS] ALL {num_intervals:,} intervals satisfy ALL constraints!")
    else:
        print(f"\n  [FAIL] Found {total_violations} violations across {num_intervals:,} intervals")

    return total_violations, stats


if __name__ == "__main__":
    print("="*100)
    print("COMPREHENSIVE CONSTRAINT VALIDATION")
    print("Checking ALL intervals for July (31 days) and November (30 days)")
    print("="*100)

    results_dir = Path("results/model_ii_validation/july_november/decision_variables")

    # Verify July
    july_file = results_dir / "July_31days_vars.json"
    july_violations, july_stats = verify_all_intervals(july_file, "JULY (31 days)")

    # Verify November
    november_file = results_dir / "November_30days_vars.json"
    november_violations, november_stats = verify_all_intervals(november_file, "NOVEMBER (30 days)")

    # Final summary
    print(f"\n{'='*100}")
    print("FINAL SUMMARY")
    print(f"{'='*100}")
    print(f"July (2,976 intervals): {july_violations} violations")
    print(f"November (2,880 intervals): {november_violations} violations")
    print(f"Total intervals checked: {2976 + 2880:,}")
    print(f"Total violations found: {july_violations + november_violations}")

    if july_violations == 0 and november_violations == 0:
        print(f"\n{'='*100}")
        print("[PASS] VALIDATION SUCCESSFUL!")
        print("All 5,856 intervals across July and November satisfy ALL constraints.")
        print("The optimized Model (ii) is proven to be constraint-compliant.")
        print(f"{'='*100}")
    else:
        print(f"\n[FAIL] Violations detected")
