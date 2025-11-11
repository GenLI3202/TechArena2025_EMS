"""
Seasonal EV Weighting Test for Model II

Tests EV weighting impact on Model II (cyclic aging) using one representative day
from each season to understand seasonal variations in aFRR market behavior.

Season definitions:
- Winter: January 1 (day 1)
- Spring: April 1 (day 91)
- Summer: July 1 (day 182)
- Autumn: October 1 (day 274)
"""

import sys
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta

# Add py_script to path
sys.path.append(str(Path(__file__).parent / 'py_script'))

from core.optimizer import BESSOptimizerModelII


def get_seasonal_day_data(full_data: pd.DataFrame, season: str) -> pd.DataFrame:
    """Extract one day of data for the specified season."""

    # Define first day of each season (day of year)
    season_days = {
        'Winter': 1,    # January 1
        'Spring': 91,   # April 1
        'Summer': 182,  # July 1
        'Autumn': 274,  # October 1
    }

    day_of_year = season_days[season]

    # Filter to the specific day (96 intervals = 24 hours @ 15-min resolution)
    start_idx = (day_of_year - 1) * 96
    end_idx = start_idx + 96

    season_data = full_data.iloc[start_idx:end_idx].copy()
    season_data = season_data.reset_index(drop=True)

    return season_data


def run_seasonal_test(country: str = 'CH', alpha: float = 1.5):
    """Run EV weighting comparison for Model II across all seasons."""

    print("=" * 80)
    print("Seasonal EV Weighting Test - Model II (Cyclic Aging)")
    print("=" * 80)
    print(f"Country: {country}")
    print(f"Alpha: {alpha}")
    print(f"Timeframe: 24 hours per season (1st day)")
    print()

    # Load data
    data_file = Path(__file__).parent / 'data' / 'TechArena2025_data_tidy.jsonl'

    print("Loading full year data...")
    optimizer_temp = BESSOptimizerModelII(alpha=alpha, use_afrr_ev_weighting=False)
    full_data = optimizer_temp.load_and_preprocess_data(str(data_file))
    country_data_full = optimizer_temp.extract_country_data(full_data, country)
    print(f"Loaded {len(country_data_full)} intervals (full year)")
    print()

    # Test each season
    seasons = ['Winter', 'Spring', 'Summer', 'Autumn']
    results = []

    for season in seasons:
        print("=" * 80)
        print(f"SEASON: {season} (24 hours)")
        print("=" * 80)

        # Get season data
        season_data = get_seasonal_day_data(country_data_full, season)
        print(f"Testing {season}: {len(season_data)} intervals (24 hours)")
        print()

        # Run WITHOUT EV weighting
        print(f"[1/2] {season} - WITHOUT EV weighting (w=1.0)...")
        try:
            optimizer_no_ev = BESSOptimizerModelII(alpha=alpha, use_afrr_ev_weighting=False)
            model_no_ev = optimizer_no_ev.build_optimization_model(season_data, c_rate=0.5, daily_cycle_limit=None)
            solution_no_ev = optimizer_no_ev.solve_model(model_no_ev)

            obj_no_ev = solution_no_ev.get('objective_value', 0)
            status_no_ev = solution_no_ev.get('status', 'unknown')
            time_no_ev = solution_no_ev.get('solve_time', 0)

            print(f"  Status: {status_no_ev}")
            print(f"  Objective: EUR {obj_no_ev:,.2f}")
            print(f"  Solve time: {time_no_ev:.2f}s")
            print()

        except Exception as e:
            print(f"  [ERROR] {str(e)}")
            obj_no_ev = None
            status_no_ev = 'error'
            time_no_ev = 0
            print()

        # Run WITH EV weighting
        print(f"[2/2] {season} - WITH EV weighting (probabilistic)...")
        try:
            optimizer_with_ev = BESSOptimizerModelII(alpha=alpha, use_afrr_ev_weighting=True)
            model_with_ev = optimizer_with_ev.build_optimization_model(season_data, c_rate=0.5, daily_cycle_limit=None)
            solution_with_ev = optimizer_with_ev.solve_model(model_with_ev)

            obj_with_ev = solution_with_ev.get('objective_value', 0)
            status_with_ev = solution_with_ev.get('status', 'unknown')
            time_with_ev = solution_with_ev.get('solve_time', 0)

            print(f"  Status: {status_with_ev}")
            print(f"  Objective: EUR {obj_with_ev:,.2f}")
            print(f"  Solve time: {time_with_ev:.2f}s")
            print()

        except Exception as e:
            print(f"  [ERROR] {str(e)}")
            obj_with_ev = None
            status_with_ev = 'error'
            time_with_ev = 0
            print()

        # Calculate comparison
        if obj_no_ev is not None and obj_with_ev is not None and obj_no_ev != 0:
            diff_eur = obj_with_ev - obj_no_ev
            diff_pct = (diff_eur / obj_no_ev) * 100

            print(f"COMPARISON - {season}:")
            print(f"  Without EV: EUR {obj_no_ev:,.2f}")
            print(f"  With EV:    EUR {obj_with_ev:,.2f}")
            print(f"  Difference: EUR {diff_eur:,.2f} ({diff_pct:+.2f}%)")
            print()

            results.append({
                'Season': season,
                'No EV (EUR)': obj_no_ev,
                'With EV (EUR)': obj_with_ev,
                'Diff (EUR)': diff_eur,
                'Diff (%)': diff_pct,
                'Status': 'success' if status_no_ev == 'optimal' and status_with_ev == 'optimal' else 'partial',
            })
        else:
            print(f"[WARNING] Could not compare {season} results")
            print()
            results.append({
                'Season': season,
                'No EV (EUR)': obj_no_ev if obj_no_ev else 0,
                'With EV (EUR)': obj_with_ev if obj_with_ev else 0,
                'Diff (EUR)': 0,
                'Diff (%)': 0,
                'Status': 'failed',
            })

    # Summary table
    print("\n" + "=" * 80)
    print("SEASONAL SUMMARY - Model II EV Weighting Impact")
    print("=" * 80)

    if results:
        df = pd.DataFrame(results)
        print(df.to_string(index=False))
        print()

        # Calculate average impact
        successful = [r for r in results if r['Status'] == 'success']
        if successful:
            avg_diff_pct = sum(r['Diff (%)'] for r in successful) / len(successful)
            print(f"Average EV weighting impact: {avg_diff_pct:+.2f}%")
            print()

    print("=" * 80)
    print("INTERPRETATION")
    print("=" * 80)
    print("1. Negative difference: EV weighting reduces objective (more realistic)")
    print("2. Seasonal variation: Different seasons may show different aFRR allocation patterns")
    print("3. Switzerland (CH) activation rates: w_pos=0.22, w_neg=0.28")
    print("4. Model II includes cyclic aging cost with alpha=" + str(alpha))
    print("=" * 80)
    print()

    # Export results
    output_file = Path(__file__).parent / 'results' / 'ev_seasonal_model_ii.csv'
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if results:
        df.to_csv(output_file, index=False)
        print(f"Results exported to: {output_file}")
        print()


if __name__ == "__main__":
    run_seasonal_test(country='CH', alpha=1.5)
