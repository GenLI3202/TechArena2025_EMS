"""
Generate Visualizations for Model (ii) Validation Results
Creates comprehensive plots comparing Model (ii) with Model (i)

Based on: py_script/validation/model_ii_validation/VALIDATION_PLAN.md
"""

import sys
from pathlib import Path
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set plotting style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10


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


def plot_profit_comparison(model_i_results, model_ii_results, output_dir, country='HU'):
    """Plot 1: Profit comparison between Model (i) and Model (ii)"""
    logger.info("Generating profit comparison plot...")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

    # Prepare data
    seasons = ['Winter', 'Spring', 'Summer', 'Fall']
    scenarios = ['baseline', 'conservative', 'aggressive']

    data = []
    for result_ii in model_ii_results:
        if 'metrics' not in result_ii:
            continue

        week = result_ii['week']
        scenario = result_ii['scenario']['name']
        season = result_ii['week_info']['season']

        # Find matching Model (i) result
        result_i = next((r for r in model_i_results
                        if r.get('week') == week and r.get('scenario', {}).get('name') == scenario),
                       None)

        if result_i and 'metrics' in result_i:
            data.append({
                'season': season,
                'scenario': scenario,
                'model_i_profit': result_i['metrics']['RP1_total_profit'],
                'model_ii_profit': result_ii['metrics']['RP1_total_profit'],
                'degradation_cost': result_ii['metrics'].get('DG1_degradation_cost', 0)
            })

    df = pd.DataFrame(data)

    # Plot 1: Grouped bar chart by season (baseline scenario only)
    baseline_data = df[df['scenario'] == 'baseline']

    x = np.arange(len(seasons))
    width = 0.35

    model_i_profits = [baseline_data[baseline_data['season'] == s]['model_i_profit'].values[0]
                      if len(baseline_data[baseline_data['season'] == s]) > 0 else 0
                      for s in seasons]
    model_ii_profits = [baseline_data[baseline_data['season'] == s]['model_ii_profit'].values[0]
                       if len(baseline_data[baseline_data['season'] == s]) > 0 else 0
                       for s in seasons]

    ax1.bar(x - width/2, model_i_profits, width, label='Model (i)', color='steelblue', alpha=0.8)
    ax1.bar(x + width/2, model_ii_profits, width, label='Model (ii)', color='coral', alpha=0.8)

    ax1.set_xlabel('Season', fontweight='bold')
    ax1.set_ylabel('Weekly Profit (EUR)', fontweight='bold')
    ax1.set_title(f'{country} Market: Profit Comparison (Baseline Scenario)', fontsize=14, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(seasons)
    ax1.legend()
    ax1.grid(axis='y', alpha=0.3)

    # Add value labels on bars
    for i, (v1, v2) in enumerate(zip(model_i_profits, model_ii_profits)):
        ax1.text(i - width/2, v1 + 500, f'{v1:.0f}', ha='center', va='bottom', fontsize=9)
        ax1.text(i + width/2, v2 + 500, f'{v2:.0f}', ha='center', va='bottom', fontsize=9)

    # Plot 2: Profit reduction by scenario
    scenarios_data = df.groupby('scenario').agg({
        'model_i_profit': 'mean',
        'model_ii_profit': 'mean',
        'degradation_cost': 'mean'
    }).reset_index()

    x2 = np.arange(len(scenarios))

    ax2.bar(x2 - width/2, scenarios_data['model_i_profit'], width,
           label='Model (i)', color='steelblue', alpha=0.8)
    ax2.bar(x2 + width/2, scenarios_data['model_ii_profit'], width,
           label='Model (ii)', color='coral', alpha=0.8)

    ax2.set_xlabel('Scenario', fontweight='bold')
    ax2.set_ylabel('Average Weekly Profit (EUR)', fontweight='bold')
    ax2.set_title('Average Profit by Scenario', fontsize=14, fontweight='bold')
    ax2.set_xticks(x2)
    ax2.set_xticklabels(scenarios)
    ax2.legend()
    ax2.grid(axis='y', alpha=0.3)

    # Add reduction percentage labels
    for i, row in scenarios_data.iterrows():
        reduction_pct = (row['model_i_profit'] - row['model_ii_profit']) / row['model_i_profit'] * 100
        ax2.text(i, max(row['model_i_profit'], row['model_ii_profit']) + 1000,
                f'-{reduction_pct:.1f}%', ha='center', va='bottom',
                fontsize=9, color='red', fontweight='bold')

    plt.tight_layout()
    output_file = output_dir / f"profit_comparison_model_i_vs_ii_{country}.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()

    logger.info(f"✓ Saved to {output_file}")


def plot_degradation_cost_breakdown(model_ii_results, output_dir, country='HU'):
    """Plot 2: Degradation cost breakdown by season and scenario"""
    logger.info("Generating degradation cost breakdown plot...")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    # Prepare data
    data = []
    for result in model_ii_results:
        if 'metrics' in result:
            data.append({
                'season': result['week_info']['season'],
                'scenario': result['scenario']['name'],
                'degradation_cost': result['metrics'].get('DG1_degradation_cost', 0),
                'degradation_ratio': result['metrics'].get('DG3_degradation_ratio', 0),
                'net_profit': result['metrics']['RP1_total_profit']
            })

    df = pd.DataFrame(data)

    # Plot 1: Degradation cost by season (baseline scenario)
    baseline_data = df[df['scenario'] == 'baseline']
    seasons = ['Winter', 'Spring', 'Summer', 'Fall']

    deg_costs = [baseline_data[baseline_data['season'] == s]['degradation_cost'].values[0]
                if len(baseline_data[baseline_data['season'] == s]) > 0 else 0
                for s in seasons]

    ax1.bar(seasons, deg_costs, color='darkorange', alpha=0.7)
    ax1.set_xlabel('Season', fontweight='bold')
    ax1.set_ylabel('Degradation Cost (EUR/week)', fontweight='bold')
    ax1.set_title('Cyclic Degradation Cost by Season (Baseline)', fontsize=12, fontweight='bold')
    ax1.grid(axis='y', alpha=0.3)

    # Add value labels
    for i, v in enumerate(deg_costs):
        ax1.text(i, v + 50, f'{v:.0f}', ha='center', va='bottom', fontsize=9)

    # Plot 2: Degradation ratio by scenario
    scenarios = ['baseline', 'conservative', 'aggressive']
    scenario_data = df.groupby('scenario')['degradation_ratio'].mean()

    colors = ['steelblue', 'green', 'red']
    bars = ax2.bar(scenarios, [scenario_data.get(s, 0) for s in scenarios],
                   color=colors, alpha=0.7)

    ax2.set_xlabel('Scenario', fontweight='bold')
    ax2.set_ylabel('Degradation Cost Ratio (% of Revenue)', fontweight='bold')
    ax2.set_title('Degradation Cost as % of Revenue', fontsize=12, fontweight='bold')
    ax2.grid(axis='y', alpha=0.3)
    ax2.set_ylim(0, max(scenario_data.values) * 1.2)

    # Add value labels
    for i, (s, bar) in enumerate(zip(scenarios, bars)):
        val = scenario_data.get(s, 0)
        ax2.text(i, val + 0.5, f'{val:.1f}%', ha='center', va='bottom', fontsize=9)

    plt.tight_layout()
    output_file = output_dir / f"degradation_cost_breakdown_{country}.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()

    logger.info(f"✓ Saved to {output_file}")


def plot_cycle_reduction_analysis(model_i_results, model_ii_results, output_dir, country='HU'):
    """Plot 3: Cycle reduction analysis"""
    logger.info("Generating cycle reduction analysis plot...")

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

    # Prepare data
    data = []
    for result_ii in model_ii_results:
        if 'metrics' not in result_ii:
            continue

        week = result_ii['week']
        scenario = result_ii['scenario']['name']

        result_i = next((r for r in model_i_results
                        if r.get('week') == week and r.get('scenario', {}).get('name') == scenario),
                       None)

        if result_i and 'metrics' in result_i:
            m_i = result_i['metrics']
            m_ii = result_ii['metrics']

            data.append({
                'season': result_ii['week_info']['season'],
                'scenario': scenario,
                'model_i_cycles': m_i['SC7_num_full_cycles'],
                'model_ii_cycles': m_ii['SC7_num_full_cycles'],
                'cycle_reduction_pct': ((m_i['SC7_num_full_cycles'] - m_ii['SC7_num_full_cycles']) /
                                       m_i['SC7_num_full_cycles'] * 100) if m_i['SC7_num_full_cycles'] > 0 else 0,
                'avg_dod': m_ii.get('DG7_avg_dod_pct', 0),
                'shallow_cycles': m_ii.get('DG8_shallow_cycles', 0),
                'deep_cycles': m_ii.get('DG9_deep_cycles', 0)
            })

    df = pd.DataFrame(data)

    # Plot 1: Cycle count comparison (baseline scenario)
    baseline_data = df[df['scenario'] == 'baseline']
    seasons = ['Winter', 'Spring', 'Summer', 'Fall']

    x = np.arange(len(seasons))
    width = 0.35

    model_i_cycles = [baseline_data[baseline_data['season'] == s]['model_i_cycles'].values[0]
                     if len(baseline_data[baseline_data['season'] == s]) > 0 else 0
                     for s in seasons]
    model_ii_cycles = [baseline_data[baseline_data['season'] == s]['model_ii_cycles'].values[0]
                      if len(baseline_data[baseline_data['season'] == s]) > 0 else 0
                      for s in seasons]

    ax1.bar(x - width/2, model_i_cycles, width, label='Model (i)', color='steelblue', alpha=0.8)
    ax1.bar(x + width/2, model_ii_cycles, width, label='Model (ii)', color='coral', alpha=0.8)

    ax1.set_xlabel('Season', fontweight='bold')
    ax1.set_ylabel('Full Cycles per Week', fontweight='bold')
    ax1.set_title('Cycle Count by Season (Baseline)', fontsize=12, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(seasons)
    ax1.legend()
    ax1.grid(axis='y', alpha=0.3)

    # Plot 2: Cycle reduction percentage by scenario
    scenarios = ['baseline', 'conservative', 'aggressive']
    scenario_data = df.groupby('scenario')['cycle_reduction_pct'].mean()

    ax2.bar(scenarios, [scenario_data.get(s, 0) for s in scenarios],
           color=['steelblue', 'green', 'red'], alpha=0.7)
    ax2.set_xlabel('Scenario', fontweight='bold')
    ax2.set_ylabel('Cycle Reduction (%)', fontweight='bold')
    ax2.set_title('Average Cycle Reduction vs Model (i)', fontsize=12, fontweight='bold')
    ax2.grid(axis='y', alpha=0.3)
    ax2.axhline(y=0, color='black', linestyle='--', linewidth=0.8)

    # Add value labels
    for i, s in enumerate(scenarios):
        val = scenario_data.get(s, 0)
        ax2.text(i, val + 1, f'{val:.1f}%', ha='center', va='bottom', fontsize=9)

    # Plot 3: Average DOD by scenario
    dod_data = df.groupby('scenario')['avg_dod'].mean()

    ax3.bar(scenarios, [dod_data.get(s, 0) for s in scenarios],
           color=['steelblue', 'green', 'red'], alpha=0.7)
    ax3.set_xlabel('Scenario', fontweight='bold')
    ax3.set_ylabel('Average Depth of Discharge (%)', fontweight='bold')
    ax3.set_title('Average DOD per Cycle (Model ii)', fontsize=12, fontweight='bold')
    ax3.grid(axis='y', alpha=0.3)

    # Plot 4: Shallow vs Deep cycles (baseline scenario)
    baseline_shallow = baseline_data['shallow_cycles'].sum()
    baseline_deep = baseline_data['deep_cycles'].sum()

    cycle_types = ['Shallow\n(DOD < 50%)', 'Deep\n(DOD > 80%)']
    cycle_counts = [baseline_shallow, baseline_deep]

    bars = ax4.bar(cycle_types, cycle_counts, color=['lightgreen', 'darkred'], alpha=0.7)
    ax4.set_ylabel('Total Cycle Count', fontweight='bold')
    ax4.set_title('Shallow vs Deep Cycles (Baseline, All Seasons)', fontsize=12, fontweight='bold')
    ax4.grid(axis='y', alpha=0.3)

    # Add value labels
    for bar, count in zip(bars, cycle_counts):
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                f'{int(count)}', ha='center', va='bottom', fontsize=10, fontweight='bold')

    plt.tight_layout()
    output_file = output_dir / f"cycle_reduction_analysis_{country}.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()

    logger.info(f"✓ Saved to {output_file}")


def plot_seasonal_performance(model_ii_results, output_dir, country='HU'):
    """Plot 4: Seasonal performance trends"""
    logger.info("Generating seasonal performance plot...")

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

    # Prepare baseline scenario data
    baseline_data = [r for r in model_ii_results
                    if r.get('scenario', {}).get('name') == 'baseline' and 'metrics' in r]

    seasons = ['Winter', 'Spring', 'Summer', 'Fall']
    metrics = {}

    for result in baseline_data:
        season = result['week_info']['season']
        m = result['metrics']

        metrics[season] = {
            'profit': m['RP1_total_profit'],
            'degradation': m.get('DG1_degradation_cost', 0),
            'cycles': m['SC7_num_full_cycles'],
            'solve_time': m['SQ3_solve_time']
        }

    # Plot 1: Profit by season
    profits = [metrics.get(s, {}).get('profit', 0) for s in seasons]
    ax1.plot(seasons, profits, marker='o', linewidth=2, markersize=8, color='steelblue')
    ax1.fill_between(range(len(seasons)), profits, alpha=0.3, color='steelblue')
    ax1.set_xlabel('Season', fontweight='bold')
    ax1.set_ylabel('Weekly Profit (EUR)', fontweight='bold')
    ax1.set_title('Profit Seasonality (Baseline)', fontsize=12, fontweight='bold')
    ax1.grid(alpha=0.3)

    # Plot 2: Degradation cost by season
    deg_costs = [metrics.get(s, {}).get('degradation', 0) for s in seasons]
    ax2.plot(seasons, deg_costs, marker='s', linewidth=2, markersize=8, color='darkorange')
    ax2.fill_between(range(len(seasons)), deg_costs, alpha=0.3, color='darkorange')
    ax2.set_xlabel('Season', fontweight='bold')
    ax2.set_ylabel('Degradation Cost (EUR/week)', fontweight='bold')
    ax2.set_title('Degradation Cost Seasonality', fontsize=12, fontweight='bold')
    ax2.grid(alpha=0.3)

    # Plot 3: Cycles by season
    cycles = [metrics.get(s, {}).get('cycles', 0) for s in seasons]
    ax3.plot(seasons, cycles, marker='^', linewidth=2, markersize=8, color='green')
    ax3.fill_between(range(len(seasons)), cycles, alpha=0.3, color='green')
    ax3.set_xlabel('Season', fontweight='bold')
    ax3.set_ylabel('Full Cycles per Week', fontweight='bold')
    ax3.set_title('Cycling Intensity by Season', fontsize=12, fontweight='bold')
    ax3.grid(alpha=0.3)

    # Plot 4: Solve time by season
    solve_times = [metrics.get(s, {}).get('solve_time', 0) for s in seasons]
    ax4.bar(seasons, solve_times, color='purple', alpha=0.7)
    ax4.set_xlabel('Season', fontweight='bold')
    ax4.set_ylabel('Solve Time (seconds)', fontweight='bold')
    ax4.set_title('Computational Performance', fontsize=12, fontweight='bold')
    ax4.grid(axis='y', alpha=0.3)

    # Add value labels
    for i, v in enumerate(solve_times):
        ax4.text(i, v + 0.2, f'{v:.1f}s', ha='center', va='bottom', fontsize=9)

    plt.tight_layout()
    output_file = output_dir / f"seasonal_performance_{country}.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()

    logger.info(f"✓ Saved to {output_file}")


def plot_alpha_sensitivity(model_ii_results, output_dir, country='HU'):
    """Plot 5: Alpha parameter sensitivity analysis"""
    logger.info("Generating alpha sensitivity plot...")

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

    # Prepare data
    data = []
    for result in model_ii_results:
        if 'metrics' in result:
            data.append({
                'alpha': result['scenario']['alpha'],
                'scenario': result['scenario']['name'],
                'profit': result['metrics']['RP1_total_profit'],
                'degradation': result['metrics'].get('DG1_degradation_cost', 0),
                'cycles': result['metrics']['SC7_num_full_cycles'],
                'effectiveness': result['metrics'].get('DG10_alpha_effectiveness', 0)
            })

    df = pd.DataFrame(data)
    avg_by_alpha = df.groupby('alpha').mean()

    alphas = sorted(df['alpha'].unique())

    # Plot 1: Profit vs Alpha
    profits = [avg_by_alpha.loc[a, 'profit'] for a in alphas]
    ax1.plot(alphas, profits, marker='o', linewidth=2, markersize=10, color='steelblue')
    ax1.set_xlabel('Alpha Parameter (α)', fontweight='bold')
    ax1.set_ylabel('Average Weekly Profit (EUR)', fontweight='bold')
    ax1.set_title('Profit vs Alpha', fontsize=12, fontweight='bold')
    ax1.grid(alpha=0.3)

    # Plot 2: Degradation cost vs Alpha
    deg_costs = [avg_by_alpha.loc[a, 'degradation'] for a in alphas]
    ax2.plot(alphas, deg_costs, marker='s', linewidth=2, markersize=10, color='darkorange')
    ax2.set_xlabel('Alpha Parameter (α)', fontweight='bold')
    ax2.set_ylabel('Average Degradation Cost (EUR/week)', fontweight='bold')
    ax2.set_title('Degradation Cost vs Alpha', fontsize=12, fontweight='bold')
    ax2.grid(alpha=0.3)

    # Plot 3: Cycles vs Alpha
    cycles = [avg_by_alpha.loc[a, 'cycles'] for a in alphas]
    ax3.plot(alphas, cycles, marker='^', linewidth=2, markersize=10, color='green')
    ax3.set_xlabel('Alpha Parameter (α)', fontweight='bold')
    ax3.set_ylabel('Average Full Cycles per Week', fontweight='bold')
    ax3.set_title('Cycling Intensity vs Alpha', fontsize=12, fontweight='bold')
    ax3.grid(alpha=0.3)

    # Plot 4: Alpha effectiveness score
    effectiveness = [avg_by_alpha.loc[a, 'effectiveness'] for a in alphas]
    ax4.bar(alphas, effectiveness, color=['red', 'steelblue', 'green'], alpha=0.7, width=0.15)
    ax4.set_xlabel('Alpha Parameter (α)', fontweight='bold')
    ax4.set_ylabel('Alpha Effectiveness Score', fontweight='bold')
    ax4.set_title('Alpha Effectiveness (Higher = Better Balance)', fontsize=12, fontweight='bold')
    ax4.grid(axis='y', alpha=0.3)

    # Add value labels
    for i, (a, e) in enumerate(zip(alphas, effectiveness)):
        ax4.text(a, e + 0.05, f'{e:.2f}', ha='center', va='bottom', fontsize=9)

    plt.tight_layout()
    output_file = output_dir / f"alpha_sensitivity_{country}.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()

    logger.info(f"✓ Saved to {output_file}")


def main():
    """Generate all validation visualizations"""

    logger.info("="*80)
    logger.info("Model (ii) Validation Visualization Generator")
    logger.info("="*80)

    # Process both countries
    for country in ['HU', 'CH']:
        logger.info(f"\n{'='*80}")
        logger.info(f"Generating visualizations for {country}...")
        logger.info(f"{'='*80}")

        # Load Model (i) and Model (ii) results
        model_i_dir = project_root / "results" / "model_i_validation" / f"{country}_seasonal"
        model_ii_dir = project_root / "results" / "model_ii_validation" / f"{country}_seasonal"

        if not model_i_dir.exists():
            logger.warning(f"Model (i) results not found: {model_i_dir}")
            continue

        if not model_ii_dir.exists():
            logger.warning(f"Model (ii) results not found: {model_ii_dir}")
            logger.info(f"Please run validation first")
            continue

        logger.info(f"Loading results...")
        model_i_results = load_results(model_i_dir)
        model_ii_results = load_results(model_ii_dir)

        logger.info(f"✓ Loaded {len(model_i_results)} Model (i) and {len(model_ii_results)} Model (ii) results")

        # Create visualization directory
        vis_dir = project_root / "results" / "model_ii_validation" / "visualizations"
        vis_dir.mkdir(parents=True, exist_ok=True)

        # Generate all plots
        plot_profit_comparison(model_i_results, model_ii_results, vis_dir, country)
        plot_degradation_cost_breakdown(model_ii_results, vis_dir, country)
        plot_cycle_reduction_analysis(model_i_results, model_ii_results, vis_dir, country)
        plot_seasonal_performance(model_ii_results, vis_dir, country)
        plot_alpha_sensitivity(model_ii_results, vis_dir, country)

    logger.info("\n" + "="*80)
    logger.info("VISUALIZATION COMPLETE!")
    logger.info("="*80)
    logger.info(f"\nGenerated plots saved to: {vis_dir}")
    logger.info("\nPlots created (per country):")
    logger.info("  1. profit_comparison_model_i_vs_ii_{country}.png")
    logger.info("  2. degradation_cost_breakdown_{country}.png")
    logger.info("  3. cycle_reduction_analysis_{country}.png")
    logger.info("  4. seasonal_performance_{country}.png")
    logger.info("  5. alpha_sensitivity_{country}.png")


if __name__ == "__main__":
    main()
