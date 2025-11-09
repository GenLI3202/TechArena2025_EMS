"""
Phase 2 EV Weighting Test - Using Existing Data Loading Infrastructure

Tests EV weighting impact on Model II using seasonal representative days.
Uses the optimizer's built-in data loading methods to avoid data format issues.

Seasons:
- Winter: January 1 (day 1)
- Spring: April 1 (day 91)
- Summer: July 1 (day 182)
- Autumn: October 1 (day 274)
"""

import sys
from pathlib import Path
import pandas as pd
import time

# Add py_script to path
sys.path.append(str(Path(__file__).parent / 'py_script'))

from core.optimizer import BESSOptimizerModelII


def calculate_afrr_energy_revenue_actual(solution: dict, season_data: pd.DataFrame) -> tuple:
    """Calculate ACTUAL aFRR energy revenue (if 100% activated) from raw variable values.

    This function is kept for calculating the "actual" revenue (without EV weighting).
    For expected revenue with EV weighting, use solution['profit_afrr_energy'] directly.

    Args:
        solution: Solution dict from solve_model() containing p_afrr_pos_e and p_afrr_neg_e
        season_data: DataFrame with price_afrr_energy_pos, price_afrr_energy_neg

    Returns:
        Tuple of (total_revenue, pos_revenue, neg_revenue, total_power_pos, total_power_neg) in EUR and kW
    """
    dt = 0.25  # 15-min intervals in hours
    pos_revenue = 0.0
    neg_revenue = 0.0
    total_power_pos = 0.0
    total_power_neg = 0.0

    # Positive aFRR energy revenue (actual, no EV weights)
    p_afrr_pos_e = solution.get('p_afrr_pos_e', {})
    for t, power_kw in p_afrr_pos_e.items():
        if power_kw > 0:
            price = season_data['price_afrr_energy_pos'].iloc[t]
            pos_revenue += (power_kw / 1000.0) * price * dt  # kW -> MW, EUR/MWh * MW * h
            total_power_pos += power_kw

    # Negative aFRR energy revenue (actual, no EV weights)
    p_afrr_neg_e = solution.get('p_afrr_neg_e', {})
    for t, power_kw in p_afrr_neg_e.items():
        if power_kw > 0:
            price = season_data['price_afrr_energy_neg'].iloc[t]
            neg_revenue += (power_kw / 1000.0) * price * dt  # kW -> MW, EUR/MWh * MW * h
            total_power_neg += power_kw

    total_revenue = pos_revenue + neg_revenue
    return total_revenue, pos_revenue, neg_revenue, total_power_pos, total_power_neg


def run_seasonal_tests(country: str = 'CH', alpha: float = 1.5):
    """Run complete seasonal EV weighting test."""

    print("=" * 100)
    print("PHASE 2 EV WEIGHTING TEST - Model II with Seasonal Instances")
    print("=" * 100)
    print(f"Country: {country}")
    print(f"Alpha: {alpha}")
    print(f"Activation rates (CH): w_pos=0.22, w_neg=0.28")
    print()

    # Use Phase 1 JSONL (which optimizer knows how to combine with Phase 2 parquet)
    data_file = Path(__file__).parent / 'data' / 'phase_1_data_TechArena2025_data_tidy.jsonl'

    if not data_file.exists():
        print(f"ERROR: Data file not found: {data_file}")
        print("Please ensure the Phase 1 JSONL file exists.")
        return

    # Season definitions (day of year)
    seasons = {
        'Winter': 1,    # January 1
        'Spring': 91,   # April 1
        'Summer': 182,  # July 1
        'Autumn': 274,  # October 1
    }

    all_results = []
    time_scopes = [24]  # Start with 24h
    fast_enough_for_36h = True

    # Test 24-hour instances
    print("=" * 100)
    print("PHASE 1: Testing 24-hour instances")
    print("=" * 100)
    print()

    for season_name, day_of_year in seasons.items():
        print(f"{season_name} (Day {day_of_year}) - 24 hours")
        print("-" * 100)

        # Calculate interval range for this season
        intervals_per_day = 96  # 15-min intervals
        start_idx = (day_of_year - 1) * intervals_per_day
        end_idx = start_idx + intervals_per_day

        # Test WITHOUT EV weighting
        print("  [1/2] WITHOUT EV weighting (w=1.0)...")
        try:
            optimizer_no_ev = BESSOptimizerModelII(alpha=alpha, use_afrr_ev_weighting=False)

            # Load full year data
            full_data = optimizer_no_ev.load_and_preprocess_data(str(data_file))

            # Extract country and filter to season day
            country_data = optimizer_no_ev.extract_country_data(full_data, country)
            season_data = country_data.iloc[start_idx:end_idx].copy().reset_index(drop=True)

            print(f"        Data: {len(season_data)} intervals")

            # Build and solve
            start_time = time.time()
            model_no_ev = optimizer_no_ev.build_optimization_model(season_data, c_rate=0.5, daily_cycle_limit=None)
            solution_no_ev = optimizer_no_ev.solve_model(model_no_ev)
            solve_time_no_ev = time.time() - start_time

            # Extract results - use profit components from solved model
            status_no_ev = solution_no_ev.get('status', 'unknown')
            obj_no_ev = solution_no_ev.get('objective_value', 0)

            # Use profit components directly from model
            profit_da_no_ev = solution_no_ev.get('profit_da', 0)
            profit_afrr_e_no_ev = solution_no_ev.get('profit_afrr_energy', 0)
            profit_as_no_ev = solution_no_ev.get('profit_as_capacity', 0)
            cost_cyclic_no_ev = solution_no_ev.get('cost_cyclic', 0)

            # Calculate actual revenue and power totals (for comparison)
            afrr_e_no_ev, afrr_e_pos_no_ev, afrr_e_neg_no_ev, power_pos_no_ev, power_neg_no_ev = \
                calculate_afrr_energy_revenue_actual(solution_no_ev, season_data)

            # Verify profit components sum to objective
            total_profit_no_ev = profit_da_no_ev + profit_afrr_e_no_ev + profit_as_no_ev
            obj_check_no_ev = total_profit_no_ev - 1.5 * cost_cyclic_no_ev  # alpha=1.5

            print(f"        Status: {status_no_ev:8} | Obj: EUR {obj_no_ev:>10,.2f} | "
                  f"aFRR-E: EUR {profit_afrr_e_no_ev:>8,.2f} (Pos: {afrr_e_pos_no_ev:>6,.2f}, Neg: {afrr_e_neg_no_ev:>6,.2f}) | Time: {solve_time_no_ev:>6.2f}s")
            print(f"        [Verify] TotalProfit: EUR {total_profit_no_ev:>10,.2f}, AgingCost: EUR {cost_cyclic_no_ev:>8,.2f}, "
                  f"Calc_Obj: EUR {obj_check_no_ev:>10,.2f} (diff: {abs(obj_no_ev - obj_check_no_ev):.6f})")

        except Exception as e:
            print(f"        [ERROR] {str(e)}")
            status_no_ev = 'error'
            obj_no_ev = 0
            profit_da_no_ev = 0
            profit_afrr_e_no_ev = 0
            profit_as_no_ev = 0
            afrr_e_no_ev = 0
            afrr_e_pos_no_ev = 0
            afrr_e_neg_no_ev = 0
            power_pos_no_ev = 0
            power_neg_no_ev = 0
            solve_time_no_ev = 0

        # Test WITH EV weighting
        print("  [2/2] WITH EV weighting (probabilistic)...")
        try:
            optimizer_with_ev = BESSOptimizerModelII(alpha=alpha, use_afrr_ev_weighting=True)

            # Load full year data
            full_data = optimizer_with_ev.load_and_preprocess_data(str(data_file))

            # Extract country and filter to season day
            country_data = optimizer_with_ev.extract_country_data(full_data, country)
            season_data = country_data.iloc[start_idx:end_idx].copy().reset_index(drop=True)

            # Build and solve
            start_time = time.time()
            model_with_ev = optimizer_with_ev.build_optimization_model(season_data, c_rate=0.5, daily_cycle_limit=None)
            solution_with_ev = optimizer_with_ev.solve_model(model_with_ev)
            solve_time_with_ev = time.time() - start_time

            # Extract results - use profit components from solved model
            status_with_ev = solution_with_ev.get('status', 'unknown')
            obj_with_ev = solution_with_ev.get('objective_value', 0)

            # Use profit components directly from model
            profit_da_with_ev = solution_with_ev.get('profit_da', 0)
            profit_afrr_e_with_ev = solution_with_ev.get('profit_afrr_energy', 0)  # Expected revenue (with EV weights)
            profit_as_with_ev = solution_with_ev.get('profit_as_capacity', 0)
            cost_cyclic_with_ev = solution_with_ev.get('cost_cyclic', 0)

            # Calculate actual revenue (what you'd get if activated 100%)
            afrr_e_actual_with_ev, afrr_e_pos_actual_with_ev, afrr_e_neg_actual_with_ev, power_pos_with_ev, power_neg_with_ev = \
                calculate_afrr_energy_revenue_actual(solution_with_ev, season_data)

            # Verify profit components sum to objective
            total_profit_with_ev = profit_da_with_ev + profit_afrr_e_with_ev + profit_as_with_ev
            obj_check_with_ev = total_profit_with_ev - 1.5 * cost_cyclic_with_ev  # alpha=1.5

            print(f"        Status: {status_with_ev:8} | Obj: EUR {obj_with_ev:>10,.2f} | "
                  f"aFRR-E Expected: EUR {profit_afrr_e_with_ev:>8,.2f} (Actual: {afrr_e_actual_with_ev:>8,.2f}) | Time: {solve_time_with_ev:>6.2f}s")
            print(f"        [Verify] TotalProfit: EUR {total_profit_with_ev:>10,.2f}, AgingCost: EUR {cost_cyclic_with_ev:>8,.2f}, "
                  f"Calc_Obj: EUR {obj_check_with_ev:>10,.2f} (diff: {abs(obj_with_ev - obj_check_with_ev):.6f})")

        except Exception as e:
            print(f"        [ERROR] {str(e)}")
            status_with_ev = 'error'
            obj_with_ev = 0
            profit_da_with_ev = 0
            profit_afrr_e_with_ev = 0
            profit_as_with_ev = 0
            afrr_e_actual_with_ev = 0
            afrr_e_pos_actual_with_ev = 0
            afrr_e_neg_actual_with_ev = 0
            power_pos_with_ev = 0
            power_neg_with_ev = 0
            solve_time_with_ev = 0

        # Comparison
        if status_no_ev == 'optimal' and status_with_ev == 'optimal':
            obj_diff = obj_with_ev - obj_no_ev
            obj_diff_pct = (obj_diff / obj_no_ev * 100) if obj_no_ev != 0 else 0

            # Compare expected revenues (apples-to-apples) - use profit components from model
            afrr_expected_diff = profit_afrr_e_with_ev - profit_afrr_e_no_ev
            afrr_expected_diff_pct = (afrr_expected_diff / profit_afrr_e_no_ev * 100) if profit_afrr_e_no_ev != 0 else 0

            # Power allocation changes
            power_pos_diff = power_pos_with_ev - power_pos_no_ev
            power_neg_diff = power_neg_with_ev - power_neg_no_ev

            print(f"  COMPARISON:")
            print(f"        Objective diff:        EUR {obj_diff:>10,.2f} ({obj_diff_pct:>+6.2f}%)")
            print(f"        aFRR-E Expected diff:  EUR {afrr_expected_diff:>8,.2f} ({afrr_expected_diff_pct:>+6.2f}%)")
            print(f"        Power allocation: Pos {power_pos_diff:>+8,.0f} kW, Neg {power_neg_diff:>+8,.0f} kW")

            all_results.append({
                'Season': season_name,
                'Day': day_of_year,
                'Hours': 24,
                'Obj_NoEV (EUR)': obj_no_ev,
                'Obj_WithEV (EUR)': obj_with_ev,
                'Obj_Diff (%)': obj_diff_pct,
                'Profit_DA_NoEV (EUR)': profit_da_no_ev,
                'Profit_DA_WithEV (EUR)': profit_da_with_ev,
                'Profit_aFRR_E_NoEV (EUR)': profit_afrr_e_no_ev,
                'Profit_aFRR_E_WithEV (EUR)': profit_afrr_e_with_ev,
                'Profit_AS_NoEV (EUR)': profit_as_no_ev,
                'Profit_AS_WithEV (EUR)': profit_as_with_ev,
                'aFRR_E_Actual_WithEV (EUR)': afrr_e_actual_with_ev,
                'aFRR_E_Expected_Diff (%)': afrr_expected_diff_pct,
                'Power_Pos_NoEV (kW)': power_pos_no_ev,
                'Power_Pos_WithEV (kW)': power_pos_with_ev,
                'Power_Neg_NoEV (kW)': power_neg_no_ev,
                'Power_Neg_WithEV (kW)': power_neg_with_ev,
                'Time_NoEV (s)': solve_time_no_ev,
                'Time_WithEV (s)': solve_time_with_ev,
                'Status': 'success'
            })

            # Check if fast enough for 36h
            if max(solve_time_no_ev, solve_time_with_ev) > 10:
                fast_enough_for_36h = False
        else:
            print(f"  COMPARISON: Could not compare - one or both runs failed")
            all_results.append({
                'Season': season_name,
                'Day': day_of_year,
                'Hours': 24,
                'Status': 'failed'
            })
            fast_enough_for_36h = False

        print()

    # Test 36-hour if all 24h were fast
    if fast_enough_for_36h:
        print("=" * 100)
        print("PHASE 2: Testing 36-hour instances (24h tests were <10s)")
        print("=" * 100)
        print()

        for season_name, day_of_year in seasons.items():
            print(f"{season_name} (Day {day_of_year}) - 36 hours")
            print("-" * 100)

            # Calculate interval range (36 hours = 144 intervals)
            start_idx = (day_of_year - 1) * 96
            end_idx = start_idx + 144

            # Test WITHOUT EV weighting
            print("  [1/2] WITHOUT EV weighting...")
            try:
                optimizer_no_ev = BESSOptimizerModelII(alpha=alpha, use_afrr_ev_weighting=False)
                full_data = optimizer_no_ev.load_and_preprocess_data(str(data_file))
                country_data = optimizer_no_ev.extract_country_data(full_data, country)
                season_data = country_data.iloc[start_idx:end_idx].copy().reset_index(drop=True)

                start_time = time.time()
                model_no_ev = optimizer_no_ev.build_optimization_model(season_data, c_rate=0.5, daily_cycle_limit=None)
                solution_no_ev = optimizer_no_ev.solve_model(model_no_ev)
                solve_time_no_ev = time.time() - start_time

                status_no_ev = solution_no_ev.get('status', 'unknown')
                obj_no_ev = solution_no_ev.get('objective_value', 0)

                profit_da_no_ev = solution_no_ev.get('profit_da', 0)
                profit_afrr_e_no_ev = solution_no_ev.get('profit_afrr_energy', 0)
                profit_as_no_ev = solution_no_ev.get('profit_as_capacity', 0)

                afrr_e_no_ev, afrr_e_pos_no_ev, afrr_e_neg_no_ev, power_pos_no_ev, power_neg_no_ev = \
                    calculate_afrr_energy_revenue_actual(solution_no_ev, season_data)

                print(f"        Status: {status_no_ev:8} | Obj: EUR {obj_no_ev:>10,.2f} | "
                      f"aFRR-E: EUR {profit_afrr_e_no_ev:>8,.2f} | Time: {solve_time_no_ev:>6.2f}s")

            except Exception as e:
                print(f"        [ERROR] {str(e)}")
                status_no_ev = 'error'
                obj_no_ev = 0
                profit_da_no_ev = 0
                profit_afrr_e_no_ev = 0
                profit_as_no_ev = 0
                afrr_e_no_ev = 0
                power_pos_no_ev = 0
                power_neg_no_ev = 0
                solve_time_no_ev = 0

            # Test WITH EV weighting
            print("  [2/2] WITH EV weighting...")
            try:
                optimizer_with_ev = BESSOptimizerModelII(alpha=alpha, use_afrr_ev_weighting=True)
                full_data = optimizer_with_ev.load_and_preprocess_data(str(data_file))
                country_data = optimizer_with_ev.extract_country_data(full_data, country)
                season_data = country_data.iloc[start_idx:end_idx].copy().reset_index(drop=True)

                start_time = time.time()
                model_with_ev = optimizer_with_ev.build_optimization_model(season_data, c_rate=0.5, daily_cycle_limit=None)
                solution_with_ev = optimizer_with_ev.solve_model(model_with_ev)
                solve_time_with_ev = time.time() - start_time

                status_with_ev = solution_with_ev.get('status', 'unknown')
                obj_with_ev = solution_with_ev.get('objective_value', 0)

                profit_da_with_ev = solution_with_ev.get('profit_da', 0)
                profit_afrr_e_with_ev = solution_with_ev.get('profit_afrr_energy', 0)
                profit_as_with_ev = solution_with_ev.get('profit_as_capacity', 0)

                afrr_e_actual_with_ev, afrr_e_pos_actual_with_ev, afrr_e_neg_actual_with_ev, power_pos_with_ev, power_neg_with_ev = \
                    calculate_afrr_energy_revenue_actual(solution_with_ev, season_data)

                print(f"        Status: {status_with_ev:8} | Obj: EUR {obj_with_ev:>10,.2f} | "
                      f"aFRR-E Expected: EUR {profit_afrr_e_with_ev:>8,.2f} | Time: {solve_time_with_ev:>6.2f}s")

            except Exception as e:
                print(f"        [ERROR] {str(e)}")
                status_with_ev = 'error'
                obj_with_ev = 0
                profit_da_with_ev = 0
                profit_afrr_e_with_ev = 0
                profit_as_with_ev = 0
                afrr_e_actual_with_ev = 0
                power_pos_with_ev = 0
                power_neg_with_ev = 0
                solve_time_with_ev = 0

            # Comparison
            if status_no_ev == 'optimal' and status_with_ev == 'optimal':
                obj_diff = obj_with_ev - obj_no_ev
                obj_diff_pct = (obj_diff / obj_no_ev * 100) if obj_no_ev != 0 else 0

                afrr_expected_diff = profit_afrr_e_with_ev - profit_afrr_e_no_ev
                afrr_expected_diff_pct = (afrr_expected_diff / profit_afrr_e_no_ev * 100) if profit_afrr_e_no_ev != 0 else 0

                power_pos_diff = power_pos_with_ev - power_pos_no_ev
                power_neg_diff = power_neg_with_ev - power_neg_no_ev

                print(f"  COMPARISON:")
                print(f"        Objective diff:        EUR {obj_diff:>10,.2f} ({obj_diff_pct:>+6.2f}%)")
                print(f"        aFRR-E Expected diff:  EUR {afrr_expected_diff:>8,.2f} ({afrr_expected_diff_pct:>+6.2f}%)")
                print(f"        Power allocation: Pos {power_pos_diff:>+8,.0f} kW, Neg {power_neg_diff:>+8,.0f} kW")

                all_results.append({
                    'Season': season_name,
                    'Day': day_of_year,
                    'Hours': 36,
                    'Obj_NoEV (EUR)': obj_no_ev,
                    'Obj_WithEV (EUR)': obj_with_ev,
                    'Obj_Diff (%)': obj_diff_pct,
                    'Profit_DA_NoEV (EUR)': profit_da_no_ev,
                    'Profit_DA_WithEV (EUR)': profit_da_with_ev,
                    'Profit_aFRR_E_NoEV (EUR)': profit_afrr_e_no_ev,
                    'Profit_aFRR_E_WithEV (EUR)': profit_afrr_e_with_ev,
                    'Profit_AS_NoEV (EUR)': profit_as_no_ev,
                    'Profit_AS_WithEV (EUR)': profit_as_with_ev,
                    'aFRR_E_Actual_WithEV (EUR)': afrr_e_actual_with_ev,
                    'aFRR_E_Expected_Diff (%)': afrr_expected_diff_pct,
                    'Power_Pos_NoEV (kW)': power_pos_no_ev,
                    'Power_Pos_WithEV (kW)': power_pos_with_ev,
                    'Power_Neg_NoEV (kW)': power_neg_no_ev,
                    'Power_Neg_WithEV (kW)': power_neg_with_ev,
                    'Time_NoEV (s)': solve_time_no_ev,
                    'Time_WithEV (s)': solve_time_with_ev,
                    'Status': 'success'
                })

            print()

    else:
        print("=" * 100)
        print("PHASE 2: SKIPPED (24h tests took >10s or failed)")
        print("=" * 100)
        print()

    # Summary
    print("=" * 100)
    print("SUMMARY - EV Weighting Impact on Model II")
    print("=" * 100)

    if all_results:
        df = pd.DataFrame(all_results)
        successful = df[df['Status'] == 'success']

        if not successful.empty:
            # Summary table with key metrics
            summary_cols = ['Season', 'Hours', 'Obj_Diff (%)', 'aFRR_E_Expected_Diff (%)',
                           'Power_Pos_NoEV (kW)', 'Power_Pos_WithEV (kW)',
                           'Power_Neg_NoEV (kW)', 'Power_Neg_WithEV (kW)']
            print(successful[summary_cols].to_string(index=False, float_format=lambda x: f'{x:.2f}'))
            print()

            # Detailed comparison with profit components
            print("DETAILED COMPARISON WITH PROFIT COMPONENTS:")
            print("=" * 100)
            for _, row in successful.iterrows():
                print(f"\n{row['Season']} ({row['Hours']}h):")
                print(f"  Total Obj:     NoEV EUR {row['Obj_NoEV (EUR)']:>10,.2f}  ->  WithEV EUR {row['Obj_WithEV (EUR)']:>10,.2f}  ({row['Obj_Diff (%)']:>+6.2f}%)")
                print(f"  - DA Profit:   NoEV EUR {row['Profit_DA_NoEV (EUR)']:>10,.2f}  ->  WithEV EUR {row['Profit_DA_WithEV (EUR)']:>10,.2f}")
                print(f"  - aFRR-E:      NoEV EUR {row['Profit_aFRR_E_NoEV (EUR)']:>10,.2f}  ->  WithEV EUR {row['Profit_aFRR_E_WithEV (EUR)']:>10,.2f}  ({row['aFRR_E_Expected_Diff (%)']:>+6.2f}%)")
                print(f"  - AS Capacity: NoEV EUR {row['Profit_AS_NoEV (EUR)']:>10,.2f}  ->  WithEV EUR {row['Profit_AS_WithEV (EUR)']:>10,.2f}")
                print(f"  aFRR-E Actual (100% activation): EUR {row['aFRR_E_Actual_WithEV (EUR)']:>10,.2f}")
                print(f"  Power Pos:     {row['Power_Pos_NoEV (kW)']:>10,.0f} kW  ->  {row['Power_Pos_WithEV (kW)']:>10,.0f} kW")
                print(f"  Power Neg:     {row['Power_Neg_NoEV (kW)']:>10,.0f} kW  ->  {row['Power_Neg_WithEV (kW)']:>10,.0f} kW")
            print()

            # Export
            output_file = Path(__file__).parent / 'results' / 'ev_phase2_seasonal_comparison.csv'
            output_file.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(output_file, index=False)
            print(f"Results exported to: {output_file}")
            print()
        else:
            print("No successful tests to display.")
            print()

    print("=" * 100)
    print("INTERPRETATION")
    print("=" * 100)
    print("- Obj_Diff (%): Negative = EV weighting reduces total profit (more realistic)")
    print("- aFRR_E_Diff (%): Shows specific impact on aFRR energy revenue")
    print("- EV weighting multiplies aFRR-E bids by activation probability (~22-28% for CH)")
    print("- Expected: Significant reduction in aFRR-E revenue with EV weighting")
    print("=" * 100)


if __name__ == "__main__":
    run_seasonal_tests(country='CH', alpha=1.5)
