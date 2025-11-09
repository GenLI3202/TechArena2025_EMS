#!/usr/bin/env python3
"""
Comprehensive visualization comparing all optimization scenarios.

Scenarios:
1. Original (Buggy): FCR-only strategy with Cst-6 bug
2. FCR Limited: Fixed Cst-6 + 50% FCR limit (alpha=1.5)
3. Balanced: Fixed Cst-6, no FCR limit, alpha=0.5
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import json
import seaborn as sns

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
plt.rcParams['figure.dpi'] = 100
plt.rcParams['savefig.dpi'] = 150
plt.rcParams['font.size'] = 10

def load_all_solutions():
    """Load solution files for all scenarios."""
    results_dir = Path("results/model_iii_detailed_solutions")

    solutions = {}
    summaries = {}

    # Define scenarios to load
    scenarios = [
        ("solution_24h_cst8_enabled.csv", "summary_24h_cst8_enabled.json", "Original (Buggy)"),
        ("solution_24h_fcr_limit.csv", "summary_24h_fcr_limit.json", "FCR Limited (a=1.5)"),
        ("solution_24h_balanced.csv", "summary_24h_balanced.json", "Balanced (a=0.5)")
    ]

    for csv_file, json_file, label in scenarios:
        csv_path = results_dir / csv_file
        json_path = results_dir / json_file

        if csv_path.exists():
            solutions[label] = pd.read_csv(csv_path)
            print(f"Loaded {label}: {len(solutions[label])} intervals")
        else:
            print(f"Warning: {csv_file} not found")

        if json_path.exists():
            with open(json_path, 'r') as f:
                summaries[label] = json.load(f)

    return solutions, summaries

def create_comprehensive_comparison(solutions, summaries):
    """Create detailed comparison visualizations."""
    output_dir = Path("results/model_iii_validation/comprehensive_comparison")
    output_dir.mkdir(exist_ok=True, parents=True)

    # Figure 1: Market Participation Comparison
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    fig.suptitle('Market Participation Across Scenarios', fontsize=16, fontweight='bold')

    scenario_order = ["Original (Buggy)", "FCR Limited (a=1.5)", "Balanced (a=0.5)"]
    colors_map = {
        'FCR': '#FF6B6B',
        'aFRR+': '#FFA07A',
        'aFRR-': '#FFD700',
        'DA Charge': '#4ECDC4',
        'DA Discharge': '#45B7D1'
    }

    for idx, scenario in enumerate(scenario_order):
        if scenario not in solutions:
            continue

        df = solutions[scenario]
        ax = axes[idx // 3, idx % 3]

        # Calculate participation rates
        fcr_pct = (df['c_fcr_mw'] > 0.01).sum() / len(df) * 100
        da_charge_pct = (df['p_ch_kw'] > 10).sum() / len(df) * 100
        da_discharge_pct = (df['p_dis_kw'] > 10).sum() / len(df) * 100
        afrr_pos_e_pct = (df['p_afrr_pos_e_kw'] > 10).sum() / len(df) * 100
        afrr_neg_e_pct = (df['p_afrr_neg_e_kw'] > 10).sum() / len(df) * 100

        # Create stacked bar chart
        markets = ['FCR\nCapacity', 'DA\nCharge', 'DA\nDischarge', 'aFRR+\nEnergy', 'aFRR-\nEnergy']
        values = [fcr_pct, da_charge_pct, da_discharge_pct, afrr_pos_e_pct, afrr_neg_e_pct]
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#FFD700']

        bars = ax.bar(markets, values, color=colors, edgecolor='black', linewidth=1.2)
        ax.set_ylabel('Time Active (%)', fontsize=11)
        ax.set_title(scenario, fontsize=12, fontweight='bold')
        ax.set_ylim(0, 100)
        ax.grid(axis='y', alpha=0.3)

        # Add value labels
        for bar, val in zip(bars, values):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                       f'{val:.1f}%', ha='center', va='bottom', fontsize=9)

        # Add max FCR capacity annotation
        max_fcr = df['c_fcr_mw'].max()
        ax.text(0.5, 0.95, f'Max FCR: {max_fcr:.2f} MW',
                transform=ax.transAxes, fontsize=9, ha='center',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    # Add summary statistics box
    ax_summary = axes[1, 0]
    ax_summary.axis('off')
    summary_text = "Key Insights:\n\n"
    summary_text += "• Original: FCR-only strategy (66.7% time)\n"
    summary_text += "• FCR Limited: Capped at 50% capacity\n"
    summary_text += "• Balanced: No FCR cap, lower degradation weight\n"
    summary_text += "\nAll scenarios show zero DA participation\n"
    summary_text += "due to high AS market prices"

    ax_summary.text(0.1, 0.5, summary_text, transform=ax_summary.transAxes,
                   fontsize=11, verticalalignment='center',
                   bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.3))

    # Revenue comparison in remaining subplot
    ax_revenue = axes[1, 1]
    if summaries:
        scenarios_with_data = []
        revenues = []

        for scenario in scenario_order:
            if scenario in summaries:
                summary = summaries[scenario]
                total_rev = summary.get('revenue', {}).get('total', 0)
                if total_rev == 0:  # Fallback for different data structure
                    total_rev = (summary.get('profit_da', 0) +
                               summary.get('profit_afrr_energy', 0) +
                               summary.get('profit_as_capacity', 0) +
                               summary.get('total_revenue_da', 0) +
                               summary.get('total_revenue_afrr_e', 0) +
                               summary.get('total_revenue_as_cap', 0))
                scenarios_with_data.append(scenario.replace(' (', '\n('))
                revenues.append(total_rev)

        bars = ax_revenue.bar(scenarios_with_data, revenues, color=['#FF6B6B', '#FFA07A', '#4ECDC4'],
                             edgecolor='black', linewidth=1.2)
        ax_revenue.set_ylabel('Total Revenue (EUR)', fontsize=11)
        ax_revenue.set_title('Revenue Comparison', fontsize=12, fontweight='bold')
        ax_revenue.grid(axis='y', alpha=0.3)

        # Add value labels
        for bar, val in zip(bars, revenues):
            ax_revenue.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 50,
                          f'{val:.0f}€', ha='center', va='bottom', fontsize=10, fontweight='bold')

    # Objective value comparison
    ax_obj = axes[1, 2]
    if summaries:
        objectives = []
        for scenario in scenario_order:
            if scenario in summaries:
                obj = summaries[scenario].get('objective_value', 0)
                objectives.append(obj)

        if objectives:
            bars = ax_obj.bar(scenarios_with_data, objectives, color=['#98D8C8', '#F7DC6F', '#AED6F1'],
                            edgecolor='black', linewidth=1.2)
            ax_obj.set_ylabel('Objective Value (EUR)', fontsize=11)
            ax_obj.set_title('Optimization Objective', fontsize=12, fontweight='bold')
            ax_obj.grid(axis='y', alpha=0.3)

            for bar, val in zip(bars, objectives):
                ax_obj.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 50,
                          f'{val:.0f}€', ha='center', va='bottom', fontsize=10, fontweight='bold')

    plt.tight_layout()
    plt.savefig(output_dir / 'market_participation_comprehensive.png', bbox_inches='tight')
    plt.show()

    # Figure 2: Power Profiles Comparison
    fig, axes = plt.subplots(3, 1, figsize=(14, 12))
    fig.suptitle('Power Scheduling Profiles Comparison', fontsize=16, fontweight='bold')

    for idx, scenario in enumerate(scenario_order):
        if scenario not in solutions:
            continue

        df = solutions[scenario]
        ax = axes[idx]

        # Create FCR profile for visualization
        fcr_profile = []
        for t in range(len(df)):
            fcr_profile.append(df.iloc[t]['c_fcr_mw'])

        hours = df['hour']

        # Plot power components
        ax.fill_between(hours, 0, fcr_profile, alpha=0.4, color='red', label='FCR Capacity')
        ax.plot(hours, df['p_total_ch_kw']/1000, 'b-', alpha=0.8, label='Total Charge', linewidth=1.5)
        ax.plot(hours, -df['p_total_dis_kw']/1000, 'g-', alpha=0.8, label='Total Discharge', linewidth=1.5)

        # Add aFRR energy if present
        if 'p_afrr_pos_e_kw' in df.columns:
            ax.plot(hours, -df['p_afrr_pos_e_kw']/1000, '--', color='orange',
                   alpha=0.6, label='aFRR+ Energy', linewidth=1)
            ax.plot(hours, df['p_afrr_neg_e_kw']/1000, '--', color='purple',
                   alpha=0.6, label='aFRR- Energy', linewidth=1)

        ax.axhline(y=0, color='k', linestyle='-', alpha=0.3)
        ax.set_xlim(0, 24)
        ax.set_ylabel('Power (MW)', fontsize=11)
        ax.set_title(f'{scenario}', fontsize=12, fontweight='bold')
        ax.legend(loc='upper right', fontsize=9, ncol=2)
        ax.grid(True, alpha=0.3)

        # Add annotations
        max_fcr = max(fcr_profile)
        avg_fcr = np.mean(fcr_profile)
        ax.text(0.02, 0.95, f'Max FCR: {max_fcr:.2f} MW\nAvg FCR: {avg_fcr:.2f} MW',
               transform=ax.transAxes, fontsize=9,
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8),
               verticalalignment='top')

    axes[-1].set_xlabel('Hour', fontsize=11)
    plt.tight_layout()
    plt.savefig(output_dir / 'power_profiles_comprehensive.png', bbox_inches='tight')
    plt.show()

    # Figure 3: Detailed Metrics Comparison Table
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.axis('tight')
    ax.axis('off')

    # Prepare comparison data
    headers = ['Metric'] + [s.replace(' (', '\n(') for s in scenario_order]
    rows = []

    # FCR metrics
    fcr_row = ['Max FCR (MW)']
    for scenario in scenario_order:
        if scenario in solutions:
            max_fcr = solutions[scenario]['c_fcr_mw'].max()
            fcr_row.append(f'{max_fcr:.3f}')
        else:
            fcr_row.append('-')
    rows.append(fcr_row)

    # FCR time percentage
    fcr_time_row = ['FCR Active (%)']
    for scenario in scenario_order:
        if scenario in summaries:
            summary = summaries[scenario]
            fcr_intervals = summary.get('as_intervals', {}).get('fcr', 0)
            if fcr_intervals == 0:  # Try alternative key
                fcr_intervals = summary.get('as_reservation_intervals', {}).get('fcr', 0)
            fcr_time_row.append(f'{fcr_intervals/96*100:.1f}%')
        else:
            fcr_time_row.append('-')
    rows.append(fcr_time_row)

    # Alpha parameter
    alpha_row = ['Alpha (a)']
    for scenario in scenario_order:
        if scenario in summaries:
            alpha = summaries[scenario].get('alpha', 1.5)
            alpha_row.append(f'{alpha:.1f}')
        else:
            alpha_row.append('-')
    rows.append(alpha_row)

    # Revenue breakdown
    da_rev_row = ['DA Revenue (EUR)']
    afrr_e_rev_row = ['aFRR-E Revenue (EUR)']
    as_cap_rev_row = ['AS Capacity Revenue (EUR)']
    total_rev_row = ['Total Revenue (EUR)']

    for scenario in scenario_order:
        if scenario in summaries:
            summary = summaries[scenario]
            revenue = summary.get('revenue', {})

            da_rev = revenue.get('da', 0) or summary.get('profit_da', 0) or summary.get('total_revenue_da', 0)
            afrr_e_rev = revenue.get('afrr_energy', 0) or summary.get('profit_afrr_energy', 0) or summary.get('total_revenue_afrr_e', 0)
            as_cap_rev = revenue.get('as_capacity', 0) or summary.get('profit_as_capacity', 0) or summary.get('total_revenue_as_cap', 0)
            total_rev = revenue.get('total', 0) or da_rev + afrr_e_rev + as_cap_rev

            da_rev_row.append(f'{da_rev:.0f}')
            afrr_e_rev_row.append(f'{afrr_e_rev:.0f}')
            as_cap_rev_row.append(f'{as_cap_rev:.0f}')
            total_rev_row.append(f'{total_rev:.0f}')
        else:
            da_rev_row.append('-')
            afrr_e_rev_row.append('-')
            as_cap_rev_row.append('-')
            total_rev_row.append('-')

    rows.extend([da_rev_row, afrr_e_rev_row, as_cap_rev_row, total_rev_row])

    # Objective value
    obj_row = ['Objective (EUR)']
    for scenario in scenario_order:
        if scenario in summaries:
            obj = summaries[scenario].get('objective_value', 0)
            obj_row.append(f'{obj:.0f}')
        else:
            obj_row.append('-')
    rows.append(obj_row)

    # Create table
    table = ax.table(cellText=rows, colLabels=headers,
                    cellLoc='center', loc='center',
                    colWidths=[0.25] + [0.25]*len(scenario_order))
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2)

    # Style the table
    for i in range(len(headers)):
        table[(0, i)].set_facecolor('#4ECDC4')
        table[(0, i)].set_text_props(weight='bold', color='white')

    # Highlight important rows
    for row_idx in [3, 7, 8]:  # FCR time, Total revenue, Objective
        for col_idx in range(len(headers)):
            table[(row_idx, col_idx)].set_facecolor('#E8F6F3')

    # Color code improvements
    for row_idx in range(1, len(rows) + 1):
        metric = rows[row_idx - 1][0]
        if 'Revenue' in metric or metric == 'Objective (EUR)':
            values = []
            for col_idx in range(1, len(headers)):
                val_str = rows[row_idx - 1][col_idx]
                if val_str != '-':
                    try:
                        values.append(float(val_str.replace('%', '').replace('€', '')))
                    except:
                        values.append(0)
                else:
                    values.append(0)

            if values:
                max_val = max(values)
                for col_idx, val in enumerate(values, 1):
                    if val == max_val and val > 0:
                        table[(row_idx, col_idx)].set_facecolor('#90EE90')

    ax.set_title('Comprehensive Metrics Comparison', fontsize=16, fontweight='bold', pad=20)
    plt.savefig(output_dir / 'metrics_table_comprehensive.png', bbox_inches='tight')
    plt.show()

    # Figure 4: Revenue Distribution Pie Charts
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle('Revenue Distribution by Market', fontsize=16, fontweight='bold')

    for idx, scenario in enumerate(scenario_order):
        if scenario not in summaries:
            continue

        ax = axes[idx]
        summary = summaries[scenario]

        # Get revenue components
        revenue = summary.get('revenue', {})
        da_rev = revenue.get('da', 0) or summary.get('profit_da', 0) or summary.get('total_revenue_da', 0)
        afrr_e_rev = revenue.get('afrr_energy', 0) or summary.get('profit_afrr_energy', 0) or summary.get('total_revenue_afrr_e', 0)
        as_cap_rev = revenue.get('as_capacity', 0) or summary.get('profit_as_capacity', 0) or summary.get('total_revenue_as_cap', 0)

        sizes = []
        labels = []
        colors = []

        if da_rev > 0:
            sizes.append(da_rev)
            labels.append(f'DA Energy\n{da_rev:.0f}€')
            colors.append('#4ECDC4')

        if afrr_e_rev > 0:
            sizes.append(afrr_e_rev)
            labels.append(f'aFRR Energy\n{afrr_e_rev:.0f}€')
            colors.append('#FFA07A')

        if as_cap_rev > 0:
            sizes.append(as_cap_rev)
            labels.append(f'AS Capacity\n{as_cap_rev:.0f}€')
            colors.append('#FF6B6B')

        if sizes:
            wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors,
                                              autopct='%1.1f%%', startangle=90,
                                              explode=[0.05] * len(sizes))

            for text in texts:
                text.set_fontsize(9)
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
                autotext.set_fontsize(10)

        total_rev = sum(sizes) if sizes else 0
        ax.set_title(f'{scenario}\nTotal: {total_rev:.0f} EUR', fontsize=11, fontweight='bold')

    plt.tight_layout()
    plt.savefig(output_dir / 'revenue_distribution_comprehensive.png', bbox_inches='tight')
    plt.show()

    print(f"\nAll visualizations saved to: {output_dir}")
    return output_dir

def print_analysis_summary(summaries):
    """Print key insights from the analysis."""
    print("\n" + "="*80)
    print("COMPREHENSIVE ANALYSIS SUMMARY")
    print("="*80)

    if "Original (Buggy)" in summaries and "Balanced (a=0.5)" in summaries:
        orig = summaries["Original (Buggy)"]
        balanced = summaries["Balanced (a=0.5)"]

        # Calculate improvements
        orig_obj = orig.get('objective_value', 0)
        balanced_obj = balanced.get('objective_value', 0)

        print("\nKey Findings:")
        print(f"1. Fixing Cst-6 bug reduced objective from {orig_obj:.0f} to {balanced_obj:.0f} EUR")
        print(f"   (Difference: {orig_obj - balanced_obj:.0f} EUR)")

        print("\n2. Market Participation Changes:")
        orig_fcr = orig.get('as_reservation_intervals', {}).get('fcr', 0) / 96 * 100
        balanced_fcr = balanced.get('as_intervals', {}).get('fcr', 0) / 96 * 100
        print(f"   - FCR: {orig_fcr:.1f}% → {balanced_fcr:.1f}% of time")

        print("\n3. Revenue Impact:")
        orig_afrr_e = orig.get('total_revenue_afrr_e', 0)
        balanced_afrr_e = balanced.get('revenue', {}).get('afrr_energy', 0)
        print(f"   - aFRR Energy revenue: {orig_afrr_e:.0f} → {balanced_afrr_e:.0f} EUR")

        print("\n4. Configuration Changes:")
        print("   - Removed FCR capacity constraint (Cst-10)")
        print("   - Reduced degradation weight (a: 1.5 -> 0.5)")
        print("   - Fixed energy reserve constraints (Cst-6)")

    print("\nConclusion:")
    print("The model now behaves more realistically with proper energy reserve accounting")
    print("and flexible market participation based on economic optimization.")
    print("="*80)

def main():
    """Run comprehensive comparison analysis."""
    print("Loading all solution data...")
    solutions, summaries = load_all_solutions()

    if not solutions:
        print("No solution files found!")
        return

    print(f"\nLoaded {len(solutions)} scenarios")
    print("Creating comprehensive visualizations...")

    output_dir = create_comprehensive_comparison(solutions, summaries)
    print_analysis_summary(summaries)

    print(f"\nAnalysis complete! Check {output_dir} for all visualizations.")

if __name__ == "__main__":
    main()