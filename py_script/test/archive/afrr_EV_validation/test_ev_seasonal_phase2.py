"""
Phase 2 EV Weighting Test - Seasonal Instances with aFRR Energy

Tests EV weighting impact using Phase 2 parquet data with full aFRR energy markets.
Tests 24h and 36h time scopes for seasonal representative days.

Seasons:
- Winter: January 1 (day 1)
- Spring: April 1 (day 91)
- Summer: July 1 (day 182)
- Autumn: October 1 (day 274)
"""

import sys
from pathlib import Path
import pandas as pd
import json
from datetime import datetime, timedelta
import time

# Add py_script to path
sys.path.append(str(Path(__file__).parent / 'py_script'))

from core.optimizer import BESSOptimizerModelII


def load_phase2_data(data_dir: Path) -> pd.DataFrame:
    """Load Phase 2 data from parquet files and combine."""

    print("Loading Phase 2 data from parquet files...")

    # Load all parquet files (already have countries as columns)
    da_df = pd.read_parquet(data_dir / 'day_ahead.parquet')
    fcr_df = pd.read_parquet(data_dir / 'fcr.parquet')
    afrr_cap_df = pd.read_parquet(data_dir / 'afrr_capacity.parquet')
    afrr_energy_df = pd.read_parquet(data_dir / 'afrr_energy.parquet')

    print(f"  Day-ahead: {len(da_df)} records")
    print(f"  FCR: {len(fcr_df)} records")
    print(f"  aFRR capacity: {len(afrr_cap_df)} records")
    print(f"  aFRR energy: {len(afrr_energy_df)} records")

    # Set timestamp as index for all
    da_df = da_df.set_index('timestamp')
    fcr_df = fcr_df.set_index('timestamp')
    afrr_cap_df = afrr_cap_df.set_index('timestamp')
    afrr_energy_df = afrr_energy_df.set_index('timestamp')

    # Convert to multi-index format expected by optimizer
    # Day-ahead (15-min intervals) - already has countries as columns
    countries = [c for c in da_df.columns if c != 'timestamp']
    da_multi = pd.DataFrame()
    for country in countries:
        da_multi[(country, 'day_ahead', '')] = da_df[country]

    # FCR (4-hour blocks, resample to 15-min)
    fcr_resampled = fcr_df.resample('15min').ffill()
    fcr_multi = pd.DataFrame()
    for country in countries:
        if country in fcr_resampled.columns:
            fcr_multi[(country, 'fcr', '')] = fcr_resampled[country]

    # aFRR capacity - split positive and negative columns
    afrr_cap_resampled = afrr_cap_df.resample('15min').ffill()
    afrr_multi = pd.DataFrame()
    for country in countries:
        pos_col = f'{country}_Pos'
        neg_col = f'{country}_Neg'
        if pos_col in afrr_cap_resampled.columns:
            afrr_multi[(country, 'afrr', 'positive')] = afrr_cap_resampled[pos_col]
        if neg_col in afrr_cap_resampled.columns:
            afrr_multi[(country, 'afrr', 'negative')] = afrr_cap_resampled[neg_col]

    # aFRR energy (15-min intervals) - split positive and negative
    afrr_e_multi = pd.DataFrame()
    for country in countries:
        pos_col = f'{country}_Pos'
        neg_col = f'{country}_Neg'
        if pos_col in afrr_energy_df.columns:
            afrr_e_multi[(country, 'afrr_energy', 'positive')] = afrr_energy_df[pos_col]
        if neg_col in afrr_energy_df.columns:
            afrr_e_multi[(country, 'afrr_energy', 'negative')] = afrr_energy_df[neg_col]

    # Combine all data
    combined = pd.concat([da_multi, fcr_multi, afrr_multi, afrr_e_multi], axis=1)
    combined.columns = pd.MultiIndex.from_tuples(combined.columns)
    combined = combined.sort_index()

    print(f"Combined data shape: {combined.shape}")
    print(f"Date range: {combined.index.min()} to {combined.index.max()}")

    return combined


def extract_seasonal_data(full_data: pd.DataFrame, country: str, season: str, hours: int = 24) -> pd.DataFrame:
    """Extract data for a seasonal day."""

    # Season definitions (day of year)
    season_days = {
        'Winter': 1,    # January 1
        'Spring': 91,   # April 1
        'Summer': 182,  # July 1
        'Autumn': 274,  # October 1
    }

    day_of_year = season_days[season]

    # Create temporary optimizer to extract country data
    temp_opt = BESSOptimizerModelII(alpha=1.5, use_afrr_ev_weighting=False)
    country_data_full = temp_opt.extract_country_data(full_data, country)

    # Extract the specific period
    intervals_per_hour = 4  # 15-min intervals
    start_idx = (day_of_year - 1) * 24 * intervals_per_hour
    end_idx = start_idx + (hours * intervals_per_hour)

    season_data = country_data_full.iloc[start_idx:end_idx].copy()
    season_data = season_data.reset_index(drop=True)

    return season_data


def run_single_test(season_data: pd.DataFrame, season: str, hours: int,
                    use_ev_weighting: bool, alpha: float = 1.5) -> dict:
    """Run a single optimization test."""

    ev_label = "WITH EV" if use_ev_weighting else "WITHOUT EV"

    try:
        optimizer = BESSOptimizerModelII(alpha=alpha, use_afrr_ev_weighting=use_ev_weighting)

        start_time = time.time()
        model = optimizer.build_optimization_model(season_data, c_rate=0.5, daily_cycle_limit=None)
        solution = optimizer.solve_model(model)
        solve_time = time.time() - start_time

        # Extract aFRR energy revenue specifically
        revenue_breakdown = solution.get('revenue_breakdown', {})
        afrr_energy_revenue = revenue_breakdown.get('afrr_energy_total', 0)

        result = {
            'status': solution.get('status', 'unknown'),
            'objective': solution.get('objective_value', 0),
            'solve_time': solve_time,
            'afrr_energy_revenue': afrr_energy_revenue,
            'revenue_breakdown': revenue_breakdown,
            'degradation_cost': solution.get('degradation_metrics', {}).get('total_degradation_cost_eur', 0),
        }

        print(f"  {ev_label:12} | Status: {result['status']:8} | Obj: EUR {result['objective']:>10,.2f} | "
              f"aFRR-E: EUR {afrr_energy_revenue:>8,.2f} | Time: {solve_time:>6.2f}s")

        return result

    except Exception as e:
        print(f"  {ev_label:12} | [ERROR] {str(e)}")
        return {'status': 'error', 'objective': 0, 'solve_time': 0, 'afrr_energy_revenue': 0, 'error': str(e)}


def run_seasonal_tests(country: str = 'CH', alpha: float = 1.5):
    """Run complete seasonal test suite."""

    print("=" * 100)
    print("PHASE 2 EV WEIGHTING TEST - Seasonal Instances with Full aFRR Energy Market")
    print("=" * 100)
    print(f"Country: {country}")
    print(f"Alpha: {alpha}")
    print(f"Activation rates (CH): w_pos=0.22, w_neg=0.28")
    print()

    # Load Phase 2 data
    data_dir = Path(__file__).parent / 'data' / 'phase2_processed' / 'parquet'
    full_data = load_phase2_data(data_dir)
    print()

    # Test configurations
    seasons = ['Winter', 'Spring', 'Summer', 'Autumn']
    time_scopes = [24]  # Start with 24h

    all_results = []

    # Test 24h first
    print("=" * 100)
    print("PHASE 1: Testing 24-hour instances")
    print("=" * 100)

    fast_enough_for_36h = True

    for season in seasons:
        print(f"\n{season} - 24 hours")
        print("-" * 100)

        season_data = extract_seasonal_data(full_data, country, season, hours=24)
        print(f"Data: {len(season_data)} intervals")

        # Run without EV
        result_no_ev = run_single_test(season_data, season, 24, use_ev_weighting=False, alpha=alpha)

        # Run with EV
        result_with_ev = run_single_test(season_data, season, 24, use_ev_weighting=True, alpha=alpha)

        # Calculate difference
        if result_no_ev['status'] == 'optimal' and result_with_ev['status'] == 'optimal':
            obj_diff = result_with_ev['objective'] - result_no_ev['objective']
            obj_diff_pct = (obj_diff / result_no_ev['objective'] * 100) if result_no_ev['objective'] != 0 else 0

            afrr_diff = result_with_ev['afrr_energy_revenue'] - result_no_ev['afrr_energy_revenue']
            afrr_diff_pct = (afrr_diff / result_no_ev['afrr_energy_revenue'] * 100) if result_no_ev['afrr_energy_revenue'] != 0 else 0

            print(f"  COMPARISON  | Obj diff: EUR {obj_diff:>10,.2f} ({obj_diff_pct:>+6.2f}%) | "
                  f"aFRR-E diff: EUR {afrr_diff:>8,.2f} ({afrr_diff_pct:>+6.2f}%)")

            all_results.append({
                'Season': season,
                'Hours': 24,
                'Obj_NoEV': result_no_ev['objective'],
                'Obj_WithEV': result_with_ev['objective'],
                'Obj_Diff_%': obj_diff_pct,
                'aFRR_E_NoEV': result_no_ev['afrr_energy_revenue'],
                'aFRR_E_WithEV': result_with_ev['afrr_energy_revenue'],
                'aFRR_E_Diff_%': afrr_diff_pct,
                'Time_NoEV': result_no_ev['solve_time'],
                'Time_WithEV': result_with_ev['solve_time'],
            })

            # Check if fast enough for 36h
            if max(result_no_ev['solve_time'], result_with_ev['solve_time']) > 10:
                fast_enough_for_36h = False
        else:
            print(f"  COMPARISON  | Could not compare - one or both runs failed")
            fast_enough_for_36h = False

    # Test 36h if all 24h tests were fast enough
    if fast_enough_for_36h:
        print("\n\n" + "=" * 100)
        print("PHASE 2: Testing 36-hour instances (24h tests were fast enough)")
        print("=" * 100)

        for season in seasons:
            print(f"\n{season} - 36 hours")
            print("-" * 100)

            season_data = extract_seasonal_data(full_data, country, season, hours=36)
            print(f"Data: {len(season_data)} intervals")

            # Run without EV
            result_no_ev = run_single_test(season_data, season, 36, use_ev_weighting=False, alpha=alpha)

            # Run with EV
            result_with_ev = run_single_test(season_data, season, 36, use_ev_weighting=True, alpha=alpha)

            # Calculate difference
            if result_no_ev['status'] == 'optimal' and result_with_ev['status'] == 'optimal':
                obj_diff = result_with_ev['objective'] - result_no_ev['objective']
                obj_diff_pct = (obj_diff / result_no_ev['objective'] * 100) if result_no_ev['objective'] != 0 else 0

                afrr_diff = result_with_ev['afrr_energy_revenue'] - result_no_ev['afrr_energy_revenue']
                afrr_diff_pct = (afrr_diff / result_no_ev['afrr_energy_revenue'] * 100) if result_no_ev['afrr_energy_revenue'] != 0 else 0

                print(f"  COMPARISON  | Obj diff: EUR {obj_diff:>10,.2f} ({obj_diff_pct:>+6.2f}%) | "
                      f"aFRR-E diff: EUR {afrr_diff:>8,.2f} ({afrr_diff_pct:>+6.2f}%)")

                all_results.append({
                    'Season': season,
                    'Hours': 36,
                    'Obj_NoEV': result_no_ev['objective'],
                    'Obj_WithEV': result_with_ev['objective'],
                    'Obj_Diff_%': obj_diff_pct,
                    'aFRR_E_NoEV': result_no_ev['afrr_energy_revenue'],
                    'aFRR_E_WithEV': result_with_ev['afrr_energy_revenue'],
                    'aFRR_E_Diff_%': afrr_diff_pct,
                    'Time_NoEV': result_no_ev['solve_time'],
                    'Time_WithEV': result_with_ev['solve_time'],
                })
    else:
        print("\n\n" + "=" * 100)
        print("PHASE 2: SKIPPED (24h tests took >10s)")
        print("=" * 100)

    # Summary
    print("\n\n" + "=" * 100)
    print("SUMMARY - EV Weighting Impact on aFRR Energy Performance")
    print("=" * 100)

    if all_results:
        df = pd.DataFrame(all_results)
        print(df.to_string(index=False, float_format=lambda x: f'{x:.2f}'))
        print()

        # Export results
        output_file = Path(__file__).parent / 'results' / 'ev_seasonal_phase2_afrr.csv'
        output_file.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_file, index=False)
        print(f"Results exported to: {output_file}")
        print()

    print("=" * 100)
    print("KEY INSIGHTS")
    print("=" * 100)
    print("1. Obj_Diff_%: Impact on total objective value (negative = EV weighting reduces profit)")
    print("2. aFRR_E_Diff_%: Impact on aFRR energy revenue specifically")
    print("3. EV weighting multiplies aFRR-E bids by activation probability (CH: ~22-28%)")
    print("4. Expected: aFRR-E revenue should decrease significantly with EV weighting")
    print("=" * 100)


if __name__ == "__main__":
    run_seasonal_tests(country='CH', alpha=1.5)
