#!/usr/bin/env python3
"""
Create comparison visualizations between different model versions.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import json

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
plt.rcParams['figure.dpi'] = 100
plt.rcParams['savefig.dpi'] = 150

def load_solutions():
    """Load all solution files for comparison."""

    results_dir = Path("results/model_iii_detailed_solutions")

    solutions = {}

    # Load original buggy solution
    if (results_dir / "solution_24h_cst8_enabled.csv").exists():
        solutions['Original (Buggy)'] = pd.read_csv(results_dir / "solution_24h_cst8_enabled.csv")

    # Load solution with FCR limits
    if (results_dir / "solution_24h_fcr_limit.csv").exists():
        solutions['Fixed (FCR Limit)'] = pd.read_csv(results_dir / "solution_24h_fcr_limit.csv")

    # Load summaries
    summaries = {}
    for name, label in [('summary_24h_cst8_enabled.json', 'Original'),
                         ('summary_24h_fcr_limit.json', 'Fixed')]:
        path = results_dir / name
        if path.exists():
            with open(path, 'r') as f:
                summaries[label] = json.load(f)

    return solutions, summaries

def create_comparison_plots(solutions, summaries):
    """Create comprehensive comparison visualizations."""

    # Create output directory
    output_dir = Path("results/model_iii_validation/comparison_plots")
    output_dir.mkdir(exist_ok=True, parents=True)

    # Figure 1: Market Participation Comparison
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Market Participation: Before vs After Fixes', fontsize=16, fontweight='bold')

    for idx, (name, df) in enumerate(solutions.items()):
        row = idx // 2
        col = idx % 2
        ax = axes[row, col] if len(solutions) > 1 else axes

        # Calculate participation
        fcr_participation = (df['c_fcr_mw'] > 0.01).sum() / len(df) * 100
        da_charge = (df['p_ch_kw'] > 10).sum() / len(df) * 100
        da_discharge = (df['p_dis_kw'] > 10).sum() / len(df) * 100
        afrr_pos_e = (df['p_afrr_pos_e_kw'] > 10).sum() / len(df) * 100
        afrr_neg_e = (df['p_afrr_neg_e_kw'] > 10).sum() / len(df) * 100

        # Bar plot
        markets = ['FCR\nCapacity', 'DA\nCharge', 'DA\nDischarge', 'aFRR+\nEnergy', 'aFRR-\nEnergy']
        values = [fcr_participation, da_charge, da_discharge, afrr_pos_e, afrr_neg_e]
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8']

        bars = ax.bar(markets, values, color=colors, edgecolor='black', linewidth=1.5)
        ax.set_ylabel('Participation (%)', fontsize=11)
        ax.set_title(name, fontsize=12, fontweight='bold')
        ax.set_ylim(0, 100)
        ax.grid(axis='y', alpha=0.3)

        # Add value labels
        for bar, val in zip(bars, values):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                       f'{val:.1f}%', ha='center', va='bottom', fontsize=9)

    # Hide unused subplots if any
    if len(solutions) < 4:
        for idx in range(len(solutions), 4):
            fig.delaxes(axes[idx // 2, idx % 2])

    plt.tight_layout()
    plt.savefig(output_dir / 'market_participation_comparison.png', bbox_inches='tight')
    plt.show()

    # Figure 2: Revenue Breakdown Comparison
    if summaries:
        fig, axes = plt.subplots(1, len(summaries), figsize=(6*len(summaries), 6))
        if len(summaries) == 1:
            axes = [axes]

        for idx, (name, summary) in enumerate(summaries.items()):
            ax = axes[idx]

            # Get revenue data
            revenue = summary.get('revenue', {})
            if not revenue:
                # Try alternative keys
                da_rev = summary.get('total_revenue_da', 0) or summary.get('profit_da', 0)
                afrr_e_rev = summary.get('total_revenue_afrr_e', 0) or summary.get('profit_afrr_energy', 0)
                as_cap_rev = summary.get('total_revenue_as_cap', 0) or summary.get('profit_as_capacity', 0)
            else:
                da_rev = revenue.get('da', 0)
                afrr_e_rev = revenue.get('afrr_energy', 0)
                as_cap_rev = revenue.get('as_capacity', 0)

            # Create pie chart
            sizes = [da_rev, afrr_e_rev, as_cap_rev]
            labels = ['DA Energy', 'aFRR Energy', 'AS Capacity']
            colors = ['#4ECDC4', '#FFA07A', '#FF6B6B']
            explode = (0.05, 0.05, 0.05)

            # Filter out zero values
            non_zero = [(s, l, c) for s, l, c in zip(sizes, labels, colors) if s > 0]
            if non_zero:
                sizes, labels, colors = zip(*non_zero)
                explode = tuple([0.05] * len(sizes))

                wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors,
                                                   explode=explode, autopct='%1.1f%%',
                                                   shadow=True, startangle=90)

                # Improve text
                for text in texts:
                    text.set_fontsize(10)
                for autotext in autotexts:
                    autotext.set_color('white')
                    autotext.set_fontweight('bold')
                    autotext.set_fontsize(9)

            total = sum(sizes) if non_zero else 0
            ax.set_title(f'{name}\nTotal: {total:.0f} EUR', fontsize=12, fontweight='bold')

        fig.suptitle('Revenue Breakdown Comparison', fontsize=16, fontweight='bold', y=1.02)
        plt.tight_layout()
        plt.savefig(output_dir / 'revenue_breakdown_comparison.png', bbox_inches='tight')
        plt.show()

    # Figure 3: Power Profile Comparison
    fig, axes = plt.subplots(len(solutions), 1, figsize=(14, 4*len(solutions)))
    if len(solutions) == 1:
        axes = [axes]

    for idx, (name, df) in enumerate(solutions.items()):
        ax = axes[idx]

        # Plot FCR capacity (convert to intervals)
        fcr_profile = []
        for t in range(len(df)):
            fcr_profile.append(df.iloc[t]['c_fcr_mw'])

        # Plot power profiles
        hours = df['hour']
        ax.fill_between(hours, 0, fcr_profile, alpha=0.5, color='red', label='FCR Capacity')
        ax.plot(hours, df['p_total_ch_kw']/1000, 'b-', alpha=0.7, label='Total Charge', linewidth=1)
        ax.plot(hours, -df['p_total_dis_kw']/1000, 'g-', alpha=0.7, label='Total Discharge', linewidth=1)

        ax.axhline(y=0, color='k', linestyle='-', alpha=0.3)
        ax.set_xlim(0, 24)
        ax.set_ylabel('Power (MW)', fontsize=11)
        ax.set_title(f'{name} - Power Schedule', fontsize=12, fontweight='bold')
        ax.legend(loc='upper right', fontsize=9)
        ax.grid(True, alpha=0.3)

        # Add max FCR annotation
        max_fcr = max(fcr_profile)
        ax.axhline(y=max_fcr, color='red', linestyle='--', alpha=0.5)
        ax.text(0.5, max_fcr, f'Max FCR: {max_fcr:.2f} MW',
                fontsize=9, color='red', va='bottom')

    axes[-1].set_xlabel('Hour', fontsize=11)
    fig.suptitle('Power Profiles: FCR Capacity and Total Power', fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_dir / 'power_profile_comparison.png', bbox_inches='tight')
    plt.show()

    # Figure 4: Key Metrics Comparison Table
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.axis('tight')
    ax.axis('off')

    # Prepare data for table
    metrics = []
    headers = ['Metric', 'Original (Buggy)', 'Fixed (FCR Limit)', 'Change']

    if len(summaries) >= 2:
        orig = summaries.get('Original', {})
        fixed = summaries.get('Fixed', {})

        # FCR metrics
        orig_fcr = orig.get('as_reservation_intervals', {}).get('fcr', 0) / 96 * 100
        fixed_fcr = fixed.get('as_intervals', {}).get('fcr', 0) / 96 * 100
        metrics.append(['FCR Time (%)', f'{orig_fcr:.1f}%', f'{fixed_fcr:.1f}%',
                       f'{fixed_fcr - orig_fcr:+.1f}%'])

        # Max capacities
        orig_max_fcr = orig.get('max_fcr_mw', 2.236)
        fixed_max_fcr = fixed.get('max_capacities', {}).get('fcr_mw', 0)
        metrics.append(['Max FCR (MW)', f'{orig_max_fcr:.3f}', f'{fixed_max_fcr:.3f}',
                       f'{fixed_max_fcr - orig_max_fcr:+.3f}'])

        # Revenue
        orig_total = orig.get('total_revenue_da', 0) + orig.get('total_revenue_afrr_e', 0) + orig.get('total_revenue_as_cap', 0)
        fixed_total = fixed.get('revenue', {}).get('total', 0)
        metrics.append(['Total Revenue (EUR)', f'{orig_total:.0f}', f'{fixed_total:.0f}',
                       f'{fixed_total - orig_total:+.0f}'])

        # Objective
        orig_obj = orig.get('objective_value', 0)
        fixed_obj = fixed.get('objective_value', 0)
        metrics.append(['Objective (EUR)', f'{orig_obj:.0f}', f'{fixed_obj:.0f}',
                       f'{fixed_obj - orig_obj:+.0f}'])

    if metrics:
        table = ax.table(cellText=metrics, colLabels=headers,
                        cellLoc='center', loc='center',
                        colWidths=[0.3, 0.25, 0.25, 0.2])
        table.auto_set_font_size(False)
        table.set_fontsize(11)
        table.scale(1, 2)

        # Style the table
        for i in range(len(headers)):
            table[(0, i)].set_facecolor('#4ECDC4')
            table[(0, i)].set_text_props(weight='bold', color='white')

        for i in range(1, len(metrics) + 1):
            for j in range(len(headers)):
                if j == 3:  # Change column
                    val = metrics[i-1][j]
                    if '+' in val and float(val.replace('%', '').replace('+', '')) > 0:
                        table[(i, j)].set_facecolor('#90EE90')
                    elif '-' in val and float(val.replace('%', '').replace('+', '')) < 0:
                        table[(i, j)].set_facecolor('#FFB6C1')

    ax.set_title('Key Metrics Comparison', fontsize=16, fontweight='bold', pad=20)
    plt.savefig(output_dir / 'metrics_comparison_table.png', bbox_inches='tight')
    plt.show()

    print(f"\nAll comparison plots saved to: {output_dir}")
    return output_dir

def main():
    """Generate all comparison visualizations."""
    print("Loading solutions...")
    solutions, summaries = load_solutions()

    if not solutions:
        print("No solution files found!")
        return

    print(f"Found {len(solutions)} solution(s) to compare")
    print("Creating comparison visualizations...")

    output_dir = create_comparison_plots(solutions, summaries)
    print("\nVisualization complete!")

    # Print summary statistics
    print("\n" + "="*60)
    print("SUMMARY STATISTICS")
    print("="*60)

    for name, summary in summaries.items():
        print(f"\n{name}:")
        print(f"  Objective: {summary.get('objective_value', 0):.2f} EUR")
        print(f"  Solve time: {summary.get('solve_time_seconds', 0):.2f} s")

        # Revenue breakdown
        revenue = summary.get('revenue', {})
        if revenue:
            print(f"  Revenue breakdown:")
            print(f"    DA: {revenue.get('da', 0):.2f} EUR")
            print(f"    aFRR Energy: {revenue.get('afrr_energy', 0):.2f} EUR")
            print(f"    AS Capacity: {revenue.get('as_capacity', 0):.2f} EUR")

if __name__ == "__main__":
    main()