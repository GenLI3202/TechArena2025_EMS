"""
Comparison script for Expected Value (EV) weighting in aFRR energy markets.

This script runs the BESS optimizer with and without EV weighting to compare:
1. Bidding behavior (DA vs aFRR-E allocation)
2. Revenue estimates (deterministic vs probabilistic)
3. Profit changes when accounting for activation probability

Reference:
    doc/p2_model/p2_bi_model_ggdp.tex Section "Solving the aFRR Energy Trap"
"""

import sys
from pathlib import Path
import pandas as pd
import json
from datetime import datetime
from typing import Dict, Any

# Add py_script to path
sys.path.append(str(Path(__file__).parent / 'py_script'))

from core.optimizer import BESSOptimizerModelI, BESSOptimizerModelII, BESSOptimizerModelIII


def run_comparison(
    model_class,
    model_name: str,
    country: str = 'CH',
    num_days: int = 7,
    alpha: float = 1.0,
    data_file: str = None,
) -> Dict[str, Any]:
    """
    Run optimizer with and without EV weighting and compare results.

    Args:
        model_class: Optimizer class to test (ModelI, ModelII, or ModelIII)
        model_name: Name of the model for reporting ("Model I", "Model II", etc.)
        country: Country code to test
        num_days: Number of days to simulate
        alpha: Degradation price weight (for Model II/III)
        data_file: Path to data file (if None, uses default)

    Returns:
        Dictionary with comparison results
    """
    print("=" * 80)
    print(f"Testing {model_name} - EV Weighting Comparison")
    print("=" * 80)
    print(f"Country: {country}")
    print(f"Duration: {num_days} days")
    if model_name != "Model I":
        print(f"Alpha: {alpha}")
    print()

    # Default data file
    if data_file is None:
        data_file = Path(__file__).parent / 'data' / 'TechArena2025_data_tidy.jsonl'

    # Initialize results storage
    results = {
        'model': model_name,
        'country': country,
        'num_days': num_days,
        'alpha': alpha if model_name != "Model I" else None,
        'timestamp': datetime.now().isoformat(),
    }

    # Run without EV weighting (deterministic, w=1.0)
    print("[1/2] Running WITHOUT EV weighting (deterministic, w=1.0)...")
    try:
        if model_name == "Model I":
            optimizer_no_ev = model_class(use_afrr_ev_weighting=False)
        else:
            optimizer_no_ev = model_class(alpha=alpha, use_afrr_ev_weighting=False)

        # Load and preprocess data
        data = optimizer_no_ev.load_and_preprocess_data(str(data_file))

        # Filter to requested number of days
        data = data.iloc[:num_days * 96]  # 96 intervals per day (15-min)

        # Extract country data
        country_data_no_ev = optimizer_no_ev.extract_country_data(data, country)

        # Build and solve model
        model_no_ev = optimizer_no_ev.build_optimization_model(
            country_data_no_ev,
            c_rate=0.5,
            daily_cycle_limit=1.0 if model_name == "Model I" else None
        )
        solution_no_ev = optimizer_no_ev.solve_model(model_no_ev)

        results['without_ev'] = {
            'status': solution_no_ev['status'],
            'objective_value': solution_no_ev.get('objective_value', 0),
            'revenue': solution_no_ev.get('revenue_breakdown', {}),
            'solve_time': solution_no_ev.get('solve_time', 0),
        }

        if model_name in ["Model II", "Model III"]:
            results['without_ev']['degradation_cost'] = solution_no_ev.get('degradation_metrics', {}).get('total_degradation_cost_eur', 0)

        print(f"  Status: {solution_no_ev['status']}")
        print(f"  Objective: EUR {solution_no_ev.get('objective_value', 0):,.2f}")
        print(f"  Solve time: {solution_no_ev.get('solve_time', 0):.2f} seconds")
        print()

    except Exception as e:
        print(f"  [ERROR] {str(e)}")
        results['without_ev'] = {'status': 'error', 'error': str(e)}
        print()

    # Run with EV weighting (probabilistic)
    print("[2/2] Running WITH EV weighting (probabilistic)...")
    try:
        if model_name == "Model I":
            optimizer_with_ev = model_class(use_afrr_ev_weighting=True)
        else:
            optimizer_with_ev = model_class(alpha=alpha, use_afrr_ev_weighting=True)

        # Load and preprocess data (reuse same data)
        data_with_ev = optimizer_with_ev.load_and_preprocess_data(str(data_file))
        data_with_ev = data_with_ev.iloc[:num_days * 96]

        # Extract country data (will include activation weights)
        country_data_with_ev = optimizer_with_ev.extract_country_data(data_with_ev, country)

        # Build and solve model
        model_with_ev = optimizer_with_ev.build_optimization_model(
            country_data_with_ev,
            c_rate=0.5,
            daily_cycle_limit=1.0 if model_name == "Model I" else None
        )
        solution_with_ev = optimizer_with_ev.solve_model(model_with_ev)

        results['with_ev'] = {
            'status': solution_with_ev['status'],
            'objective_value': solution_with_ev.get('objective_value', 0),
            'revenue': solution_with_ev.get('revenue_breakdown', {}),
            'solve_time': solution_with_ev.get('solve_time', 0),
        }

        if model_name in ["Model II", "Model III"]:
            results['with_ev']['degradation_cost'] = solution_with_ev.get('degradation_metrics', {}).get('total_degradation_cost_eur', 0)

        print(f"  Status: {solution_with_ev['status']}")
        print(f"  Objective: EUR {solution_with_ev.get('objective_value', 0):,.2f}")
        print(f"  Solve time: {solution_with_ev.get('solve_time', 0):.2f} seconds")
        print()

    except Exception as e:
        print(f"  [ERROR] {str(e)}")
        results['with_ev'] = {'status': 'error', 'error': str(e)}
        print()

    # Calculate comparison metrics
    if results['without_ev']['status'] in ['optimal', 'feasible'] and \
       results['with_ev']['status'] in ['optimal', 'feasible']:

        obj_no_ev = results['without_ev']['objective_value']
        obj_with_ev = results['with_ev']['objective_value']
        obj_diff = obj_with_ev - obj_no_ev
        obj_pct = (obj_diff / obj_no_ev * 100) if obj_no_ev != 0 else 0

        results['comparison'] = {
            'objective_diff_eur': obj_diff,
            'objective_diff_pct': obj_pct,
            'interpretation': _interpret_difference(obj_pct, model_name),
        }

        print("=" * 80)
        print("COMPARISON RESULTS")
        print("=" * 80)
        print(f"Objective without EV: EUR {obj_no_ev:,.2f}")
        print(f"Objective with EV:    EUR {obj_with_ev:,.2f}")
        print(f"Difference:           EUR {obj_diff:,.2f} ({obj_pct:+.2f}%)")
        print()
        print(f"Interpretation: {results['comparison']['interpretation']}")
        print()

    else:
        results['comparison'] = {'status': 'comparison_failed'}
        print("[WARNING] Could not compare results - one or both runs failed")
        print()

    return results


def _interpret_difference(pct_diff: float, model_name: str) -> str:
    """Interpret the percentage difference in objective values."""
    if abs(pct_diff) < 0.5:
        return "Negligible impact - EV weighting has minimal effect on this scenario"
    elif pct_diff < -5:
        return f"Significant decrease - EV weighting substantially reduces expected {model_name} profit (more realistic estimate)"
    elif pct_diff < 0:
        return f"Moderate decrease - EV weighting lowers expected {model_name} profit (realistic adjustment)"
    elif pct_diff > 5:
        return "Unexpected increase - This may indicate model changes beyond just EV weighting"
    else:
        return "Small increase - Possible slight optimization improvement with EV weighting"


def main():
    """Main comparison workflow."""
    print("\n")
    print("*" * 80)
    print("Expected Value (EV) Weighting Comparison for aFRR Energy Markets")
    print("*" * 80)
    print()
    print("This script compares optimizer behavior with and without EV weighting.")
    print("EV weighting accounts for the probability that aFRR bids will be activated.")
    print()

    # Configuration
    country = 'CH'
    num_days = 7
    alpha = 1.5

    # Test Model I (base + aFRR energy)
    print("\n" + "=" * 80)
    print("TEST 1: Model I (Base + aFRR Energy Market)")
    print("=" * 80)
    results_i = run_comparison(
        BESSOptimizerModelI,
        "Model I",
        country=country,
        num_days=num_days,
    )

    # Test Model II (Model I + Cyclic Aging)
    print("\n" + "=" * 80)
    print("TEST 2: Model II (Model I + Cyclic Aging Cost)")
    print("=" * 80)
    results_ii = run_comparison(
        BESSOptimizerModelII,
        "Model II",
        country=country,
        num_days=num_days,
        alpha=alpha,
    )

    # Test Model III (Model II + Calendar Aging)
    print("\n" + "=" * 80)
    print("TEST 3: Model III (Model II + Calendar Aging Cost)")
    print("=" * 80)
    results_iii = run_comparison(
        BESSOptimizerModelIII,
        "Model III",
        country=country,
        num_days=num_days,
        alpha=alpha,
    )

    # Export results
    output_file = Path(__file__).parent / 'results' / 'ev_weighting_comparison.json'
    output_file.parent.mkdir(parents=True, exist_ok=True)

    all_results = {
        'test_config': {
            'country': country,
            'num_days': num_days,
            'alpha': alpha,
            'timestamp': datetime.now().isoformat(),
        },
        'model_i': results_i,
        'model_ii': results_ii,
        'model_iii': results_iii,
    }

    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Results exported to: {output_file}")
    print()

    # Summary table
    summary_data = []
    for model_key, model_results in [('Model I', results_i), ('Model II', results_ii), ('Model III', results_iii)]:
        if 'comparison' in model_results and 'objective_diff_pct' in model_results['comparison']:
            summary_data.append({
                'Model': model_key,
                'Obj without EV (EUR)': f"{model_results['without_ev']['objective_value']:,.2f}",
                'Obj with EV (EUR)': f"{model_results['with_ev']['objective_value']:,.2f}",
                'Difference (%)': f"{model_results['comparison']['objective_diff_pct']:+.2f}%",
            })

    if summary_data:
        summary_df = pd.DataFrame(summary_data)
        print(summary_df.to_string(index=False))
        print()

    print("=" * 80)
    print("CONCLUSIONS")
    print("=" * 80)
    print("1. Without EV weighting: Model assumes 100% activation of aFRR bids (optimistic)")
    print("2. With EV weighting: Model accounts for activation probability (realistic)")
    print("3. Expected impact: EV weighting should reduce objective value (more conservative)")
    print("4. Use case: Enable EV weighting for realistic profit estimates and bidding strategy")
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()
