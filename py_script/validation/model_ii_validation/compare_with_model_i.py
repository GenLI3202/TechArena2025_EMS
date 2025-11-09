"""
Compare Model (ii) with Model (i) Validation Results
Generates detailed comparison CSVs and analysis

Based on: py_script/validation/model_ii_validation/VALIDATION_PLAN.md
"""

import sys
from pathlib import Path
import json
import pandas as pd
import numpy as np
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_results(results_dir):
    """Load all JSON result files from a directory"""
    results = []
    json_files = list(results_dir.glob("*.json"))

    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                results.append(data)
        except Exception as e:
            logger.warning(f"Error loading {json_file}: {e}")

    return results


def compare_results(model_i_results, model_ii_results):
    """Generate detailed comparison between Model (i) and Model (ii)"""

    comparison_data = []

    # Match Model (i) and Model (ii) results by week and scenario
    for result_ii in model_ii_results:
        if 'week' not in result_ii or 'scenario' not in result_ii:
            continue

        week = result_ii['week']
        scenario = result_ii['scenario']['name']

        # Find matching Model (i) result
        result_i = next((r for r in model_i_results
                        if r.get('week') == week and r.get('scenario', {}).get('name') == scenario),
                       None)

        if not result_i or 'metrics' not in result_i or 'metrics' not in result_ii:
            logger.warning(f"No matching Model (i) result for {week} - {scenario}")
            continue

        m_i = result_i['metrics']
        m_ii = result_ii['metrics']

        # Compute comparison metrics
        comp = {
            'week': week,
            'season': result_ii['week_info']['season'],
            'scenario': scenario,

            # Profit comparison
            'model_i_profit': m_i['RP1_total_profit'],
            'model_ii_profit': m_ii['RP1_total_profit'],
            'profit_delta_eur': m_i['RP1_total_profit'] - m_ii['RP1_total_profit'],
            'profit_delta_pct': ((m_i['RP1_total_profit'] - m_ii['RP1_total_profit']) /
                                m_i['RP1_total_profit'] * 100) if m_i['RP1_total_profit'] > 0 else 0,

            # Degradation cost
            'degradation_cost': m_ii.get('DG1_degradation_cost', 0),
            'degradation_ratio': m_ii.get('DG3_degradation_ratio', 0),

            # Cycling comparison
            'model_i_cycles': m_i['SC7_num_full_cycles'],
            'model_ii_cycles': m_ii['SC7_num_full_cycles'],
            'cycle_delta': m_i['SC7_num_full_cycles'] - m_ii['SC7_num_full_cycles'],
            'cycle_delta_pct': ((m_i['SC7_num_full_cycles'] - m_ii['SC7_num_full_cycles']) /
                               m_i['SC7_num_full_cycles'] * 100) if m_i['SC7_num_full_cycles'] > 0 else 0,

            # Energy throughput
            'model_i_throughput': m_i['EP3_energy_throughput'],
            'model_ii_throughput': m_ii['EP3_energy_throughput'],
            'throughput_delta_pct': ((m_i['EP3_energy_throughput'] - m_ii['EP3_energy_throughput']) /
                                    m_i['EP3_energy_throughput'] * 100) if m_i['EP3_energy_throughput'] > 0 else 0,

            # DOD analysis
            'avg_dod': m_ii.get('DG7_avg_dod_pct', 0),
            'shallow_cycles': m_ii.get('DG8_shallow_cycles', 0),
            'deep_cycles': m_ii.get('DG9_deep_cycles', 0),

            # Alpha effectiveness
            'alpha': result_ii['scenario']['alpha'],
            'alpha_effectiveness': m_ii.get('DG10_alpha_effectiveness', 0),

            # Solve performance
            'model_i_solve_time': m_i['SQ3_solve_time'],
            'model_ii_solve_time': m_ii['SQ3_solve_time'],
            'solve_time_delta_pct': ((m_ii['SQ3_solve_time'] - m_i['SQ3_solve_time']) /
                                    m_i['SQ3_solve_time'] * 100) if m_i['SQ3_solve_time'] > 0 else 0,
        }

        comparison_data.append(comp)

    return pd.DataFrame(comparison_data)


def generate_revenue_mix_comparison(model_i_results, model_ii_results):
    """Compare revenue mix between Model (i) and Model (ii)"""

    revenue_data = []

    for result_ii in model_ii_results:
        if 'week' not in result_ii or 'scenario' not in result_ii:
            continue

        week = result_ii['week']
        scenario = result_ii['scenario']['name']

        result_i = next((r for r in model_i_results
                        if r.get('week') == week and r.get('scenario', {}).get('name') == scenario),
                       None)

        if not result_i or 'metrics' not in result_i or 'metrics' not in result_ii:
            continue

        m_i = result_i['metrics']
        m_ii = result_ii['metrics']

        # Model (i) revenue mix
        total_i = m_i['RP1_total_profit']
        if total_i > 0:
            revenue_data.append({
                'week': week,
                'season': result_ii['week_info']['season'],
                'scenario': scenario,
                'model': 'Model (i)',
                'da_pct': m_i['RP2_da_profit'] / total_i * 100,
                'afrr_e_pct': m_i['RP3_afrr_energy_profit'] / total_i * 100,
                'fcr_pct': m_i['RP4_fcr_revenue'] / total_i * 100,
                'afrr_cap_pct': m_i['RP5_afrr_capacity_revenue'] / total_i * 100,
            })

        # Model (ii) revenue mix
        total_ii = m_ii['RP1_total_profit']
        if total_ii > 0:
            revenue_data.append({
                'week': week,
                'season': result_ii['week_info']['season'],
                'scenario': scenario,
                'model': 'Model (ii)',
                'da_pct': m_ii['RP2_da_profit'] / total_ii * 100,
                'afrr_e_pct': m_ii['RP3_afrr_energy_profit'] / total_ii * 100,
                'fcr_pct': m_ii['RP4_fcr_revenue'] / total_ii * 100,
                'afrr_cap_pct': m_ii['RP5_afrr_capacity_revenue'] / total_ii * 100,
            })

    return pd.DataFrame(revenue_data)


def generate_summary_statistics(comparison_df):
    """Generate summary statistics for the comparison"""

    summary = {
        'total_tests': len(comparison_df),
        'avg_profit_reduction_pct': comparison_df['profit_delta_pct'].mean(),
        'avg_cycle_reduction_pct': comparison_df['cycle_delta_pct'].mean(),
        'avg_degradation_cost': comparison_df['degradation_cost'].mean(),
        'avg_degradation_ratio': comparison_df['degradation_ratio'].mean(),
        'avg_alpha_effectiveness': comparison_df['alpha_effectiveness'].mean(),
    }

    # By scenario
    scenarios = {}
    for scenario in comparison_df['scenario'].unique():
        scenario_data = comparison_df[comparison_df['scenario'] == scenario]
        scenarios[scenario] = {
            'avg_profit_reduction_pct': scenario_data['profit_delta_pct'].mean(),
            'avg_cycle_reduction_pct': scenario_data['cycle_delta_pct'].mean(),
            'avg_degradation_cost': scenario_data['degradation_cost'].mean(),
        }

    summary['by_scenario'] = scenarios

    # By season
    seasons = {}
    for season in comparison_df['season'].unique():
        season_data = comparison_df[comparison_df['season'] == season]
        seasons[season] = {
            'avg_profit_reduction_pct': season_data['profit_delta_pct'].mean(),
            'avg_cycle_reduction_pct': season_data['cycle_delta_pct'].mean(),
            'avg_degradation_cost': season_data['degradation_cost'].mean(),
        }

    summary['by_season'] = seasons

    return summary


def main():
    """Generate comparison analysis between Model (i) and Model (ii)"""

    logger.info("="*80)
    logger.info("Model (ii) vs Model (i) Comparison Analysis")
    logger.info("="*80)

    # Process both countries
    for country in ['HU', 'CH']:
        logger.info(f"\n{'='*80}")
        logger.info(f"Processing {country} results...")
        logger.info(f"{'='*80}")

        # Load Model (i) results
        model_i_dir = project_root / "results" / "model_i_validation" / f"{country}_seasonal"
        if not model_i_dir.exists():
            logger.warning(f"Model (i) results not found: {model_i_dir}")
            continue

        logger.info(f"Loading Model (i) results from {model_i_dir}...")
        model_i_results = load_results(model_i_dir)
        logger.info(f"✓ Loaded {len(model_i_results)} Model (i) results")

        # Load Model (ii) results
        model_ii_dir = project_root / "results" / "model_ii_validation" / f"{country}_seasonal"
        if not model_ii_dir.exists():
            logger.warning(f"Model (ii) results not found: {model_ii_dir}")
            logger.info(f"Please run validation first: python run_seasonal_validation.py (HU) or run_ch_validation.py (CH)")
            continue

        logger.info(f"Loading Model (ii) results from {model_ii_dir}...")
        model_ii_results = load_results(model_ii_dir)
        logger.info(f"✓ Loaded {len(model_ii_results)} Model (ii) results")

        # Create comparison directory
        comparison_dir = model_ii_dir / "comparison_with_model_i"
        comparison_dir.mkdir(exist_ok=True)

        # Generate comparison dataframe
        logger.info("\nGenerating comparison analysis...")
        comparison_df = compare_results(model_i_results, model_ii_results)

        if comparison_df.empty:
            logger.warning("No matching results found for comparison!")
            continue

        logger.info(f"✓ Matched {len(comparison_df)} test results")

        # Save profit comparison
        profit_file = comparison_dir / "profit_comparison.csv"
        profit_cols = ['week', 'season', 'scenario', 'model_i_profit', 'model_ii_profit',
                      'profit_delta_eur', 'profit_delta_pct', 'degradation_cost']
        comparison_df[profit_cols].to_csv(profit_file, index=False)
        logger.info(f"✓ Saved profit comparison to {profit_file}")

        # Save cycle comparison
        cycle_file = comparison_dir / "cycle_comparison.csv"
        cycle_cols = ['week', 'season', 'scenario', 'model_i_cycles', 'model_ii_cycles',
                     'cycle_delta', 'cycle_delta_pct', 'avg_dod', 'shallow_cycles', 'deep_cycles']
        comparison_df[cycle_cols].to_csv(cycle_file, index=False)
        logger.info(f"✓ Saved cycle comparison to {cycle_file}")

        # Save degradation analysis
        degradation_file = comparison_dir / "degradation_analysis.csv"
        degradation_cols = ['week', 'season', 'scenario', 'alpha', 'degradation_cost',
                           'degradation_ratio', 'alpha_effectiveness']
        comparison_df[degradation_cols].to_csv(degradation_file, index=False)
        logger.info(f"✓ Saved degradation analysis to {degradation_file}")

        # Generate revenue mix comparison
        logger.info("\nGenerating revenue mix comparison...")
        revenue_mix_df = generate_revenue_mix_comparison(model_i_results, model_ii_results)
        revenue_mix_file = comparison_dir / "revenue_mix_changes.csv"
        revenue_mix_df.to_csv(revenue_mix_file, index=False)
        logger.info(f"✓ Saved revenue mix comparison to {revenue_mix_file}")

        # Generate summary statistics
        logger.info("\nGenerating summary statistics...")
        summary = generate_summary_statistics(comparison_df)

        # Print summary
        logger.info("\n" + "="*80)
        logger.info(f"SUMMARY STATISTICS - {country}")
        logger.info("="*80)
        logger.info(f"Total tests compared: {summary['total_tests']}")
        logger.info(f"Average profit reduction: {summary['avg_profit_reduction_pct']:.1f}%")
        logger.info(f"Average cycle reduction: {summary['avg_cycle_reduction_pct']:.1f}%")
        logger.info(f"Average degradation cost: {summary['avg_degradation_cost']:.2f} EUR/week")
        logger.info(f"Average degradation ratio: {summary['avg_degradation_ratio']:.1f}%")
        logger.info(f"Average alpha effectiveness: {summary['avg_alpha_effectiveness']:.2f}")

        logger.info("\nBy Scenario:")
        for scenario, stats in summary['by_scenario'].items():
            logger.info(f"  {scenario}:")
            logger.info(f"    Profit reduction: {stats['avg_profit_reduction_pct']:.1f}%")
            logger.info(f"    Cycle reduction: {stats['avg_cycle_reduction_pct']:.1f}%")
            logger.info(f"    Degradation cost: {stats['avg_degradation_cost']:.2f} EUR/week")

        logger.info("\nBy Season:")
        for season, stats in summary['by_season'].items():
            logger.info(f"  {season}:")
            logger.info(f"    Profit reduction: {stats['avg_profit_reduction_pct']:.1f}%")
            logger.info(f"    Cycle reduction: {stats['avg_cycle_reduction_pct']:.1f}%")
            logger.info(f"    Degradation cost: {stats['avg_degradation_cost']:.2f} EUR/week")

        # Save summary to JSON
        summary_file = comparison_dir / "comparison_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"\n✓ Saved summary statistics to {summary_file}")

    logger.info("\n" + "="*80)
    logger.info("COMPARISON COMPLETE!")
    logger.info("="*80)
    logger.info("\nGenerated files (per country):")
    logger.info("  - profit_comparison.csv: Profit impact analysis")
    logger.info("  - cycle_comparison.csv: Cycling behavior comparison")
    logger.info("  - degradation_analysis.csv: Degradation metrics")
    logger.info("  - revenue_mix_changes.csv: Market participation shifts")
    logger.info("  - comparison_summary.json: Statistical summary")


if __name__ == "__main__":
    main()
