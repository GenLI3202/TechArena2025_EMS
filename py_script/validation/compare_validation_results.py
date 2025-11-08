"""
Compare Old vs New Model (i) Validation Results
Analyzes the impact of the capacity market revenue bug fix (EUR/MW -> EUR/MW/h with * db)
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Paths
OLD_DIR = Path("results/model_i_validation_old_EUR_MW_unit_ver/HU_seasonal")
NEW_DIR = Path("results/model_i_validation/HU_seasonal")
OUTPUT_DIR = Path("results/model_i_validation/comparison")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Test configurations
WEEKS = ["Q1_Winter", "Q2_Spring", "Q3_Summer", "Q4_Fall"]
SCENARIOS = ["baseline", "conservative", "aggressive"]

def load_results(directory, week, scenario):
    """Load validation results from JSON file"""
    filepath = directory / f"{week}_{scenario}.json"
    with open(filepath, 'r') as f:
        return json.load(f)

def extract_comparison_metrics(old_data, new_data):
    """Extract key metrics for comparison"""
    om = old_data['metrics']
    nm = new_data['metrics']

    return {
        'total_profit_old': om['RP1_total_profit'],
        'total_profit_new': nm['RP1_total_profit'],
        'da_profit_old': om['RP2_da_profit'],
        'da_profit_new': nm['RP2_da_profit'],
        'afrr_e_profit_old': om['RP3_afrr_energy_profit'],
        'afrr_e_profit_new': nm['RP3_afrr_energy_profit'],
        'fcr_revenue_old': om['RP4_fcr_revenue'],
        'fcr_revenue_new': nm['RP4_fcr_revenue'],
        'afrr_cap_revenue_old': om['RP5_afrr_capacity_revenue'],
        'afrr_cap_revenue_new': nm['RP5_afrr_capacity_revenue'],
        'fcr_blocks_old': om['MP7_fcr_blocks'],
        'fcr_blocks_new': nm['MP7_fcr_blocks'],
        'afrr_pos_blocks_old': om['MP8_afrr_pos_blocks'],
        'afrr_pos_blocks_new': nm['MP8_afrr_pos_blocks'],
        'afrr_neg_blocks_old': om['MP9_afrr_neg_blocks'],
        'afrr_neg_blocks_new': nm['MP9_afrr_neg_blocks'],
        'solve_time_old': om['SQ3_solve_time'],
        'solve_time_new': nm['SQ3_solve_time'],
    }

# Collect all comparison data
comparison_data = []

for week in WEEKS:
    for scenario in SCENARIOS:
        old_data = load_results(OLD_DIR, week, scenario)
        new_data = load_results(NEW_DIR, week, scenario)

        metrics = extract_comparison_metrics(old_data, new_data)
        metrics['week'] = week
        metrics['scenario'] = scenario
        comparison_data.append(metrics)

df = pd.DataFrame(comparison_data)

# Calculate percentage changes
df['profit_change_pct'] = ((df['total_profit_new'] - df['total_profit_old']) / df['total_profit_old']) * 100
df['fcr_change_abs'] = df['fcr_revenue_new'] - df['fcr_revenue_old']
df['fcr_blocks_change'] = df['fcr_blocks_new'] - df['fcr_blocks_old']

# Save comparison data
df.to_csv(OUTPUT_DIR / 'comparison_summary.csv', index=False)

print("=" * 80)
print("MODEL (i) VALIDATION COMPARISON: OLD vs NEW")
print("=" * 80)
print("\nBug Fix: Added '* model.db' to capacity market revenue calculation")
print("Impact: Capacity prices are EUR/MW/h, must multiply by block duration (4h)\n")

# Overall statistics
baseline_df = df[df['scenario'] == 'baseline']
print("\nOVERALL IMPACT (Baseline Scenario):")
print(f"  Average Profit Change: {baseline_df['profit_change_pct'].mean():+.2f}%")
print(f"  Profit Change Range: {baseline_df['profit_change_pct'].min():+.2f}% to {baseline_df['profit_change_pct'].max():+.2f}%")
print(f"  Average FCR Revenue Change: {baseline_df['fcr_change_abs'].mean():+.2f} EUR/week")
print(f"  Average FCR Blocks Change: {baseline_df['fcr_blocks_change'].mean():+.1f} blocks/week")

# Seasonal breakdown
print("\n" + "-" * 80)
print("SEASONAL BREAKDOWN (Baseline Scenario):")
print("-" * 80)
for week in WEEKS:
    row = baseline_df[baseline_df['week'] == week].iloc[0]
    print(f"\n{week}:")
    print(f"  Total Profit: {row['total_profit_old']:.2f} EUR -> {row['total_profit_new']:.2f} EUR ({row['profit_change_pct']:+.2f}%)")
    print(f"  FCR Revenue:  {row['fcr_revenue_old']:.2f} EUR -> {row['fcr_revenue_new']:.2f} EUR ({row['fcr_change_abs']:+.2f} EUR)")
    print(f"  FCR Blocks:   {row['fcr_blocks_old']:.0f} -> {row['fcr_blocks_new']:.0f} ({row['fcr_blocks_change']:+.0f})")

    # Revenue mix
    old_total = row['da_profit_old'] + row['afrr_e_profit_old'] + row['fcr_revenue_old']
    new_total = row['da_profit_new'] + row['afrr_e_profit_new'] + row['fcr_revenue_new']

    old_da_pct = (row['da_profit_old'] / old_total) * 100
    new_da_pct = (row['da_profit_new'] / new_total) * 100
    old_afrr_pct = (row['afrr_e_profit_old'] / old_total) * 100
    new_afrr_pct = (row['afrr_e_profit_new'] / new_total) * 100
    old_fcr_pct = (row['fcr_revenue_old'] / old_total) * 100
    new_fcr_pct = (row['fcr_revenue_new'] / new_total) * 100

    print(f"  Revenue Mix Old: DA {old_da_pct:.1f}%, aFRR-E {old_afrr_pct:.1f}%, FCR {old_fcr_pct:.2f}%")
    print(f"  Revenue Mix New: DA {new_da_pct:.1f}%, aFRR-E {new_afrr_pct:.1f}%, FCR {new_fcr_pct:.2f}%")

# Create visualizations
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('Model (i) Validation: Old vs New Comparison\nBug Fix: Capacity Revenue Calculation (EUR/MW -> EUR/MW/h)',
             fontsize=14, fontweight='bold')

# 1. Profit Comparison by Week and Scenario
ax1 = axes[0, 0]
x = np.arange(len(WEEKS))
width = 0.25
scenarios_list = ['baseline', 'conservative', 'aggressive']
colors = {'baseline': '#2E86AB', 'conservative': '#A23B72', 'aggressive': '#F18F01'}

for i, scenario in enumerate(scenarios_list):
    scenario_df = df[df['scenario'] == scenario]
    old_profits = [scenario_df[scenario_df['week'] == w]['total_profit_old'].values[0] for w in WEEKS]
    new_profits = [scenario_df[scenario_df['week'] == w]['total_profit_new'].values[0] for w in WEEKS]

    offset = (i - 1) * width
    ax1.bar(x + offset, old_profits, width, alpha=0.5, color=colors[scenario],
            label=f'{scenario} (old)', edgecolor='black', linewidth=0.5)
    ax1.bar(x + offset, new_profits, width, alpha=1.0, color=colors[scenario],
            label=f'{scenario} (new)', edgecolor='black', linewidth=1.5)

ax1.set_xlabel('Season')
ax1.set_ylabel('Total Profit (EUR)')
ax1.set_title('Total Profit Comparison')
ax1.set_xticks(x)
ax1.set_xticklabels([w.replace('_', '\n') for w in WEEKS])
ax1.legend(fontsize=8, ncol=2)
ax1.grid(axis='y', alpha=0.3)

# 2. Profit Change Percentage
ax2 = axes[0, 1]
for scenario in scenarios_list:
    scenario_df = df[df['scenario'] == scenario]
    changes = [scenario_df[scenario_df['week'] == w]['profit_change_pct'].values[0] for w in WEEKS]
    ax2.plot(WEEKS, changes, marker='o', linewidth=2, markersize=8,
             label=scenario, color=colors[scenario])

ax2.axhline(y=0, color='black', linestyle='--', linewidth=1, alpha=0.5)
ax2.set_xlabel('Season')
ax2.set_ylabel('Profit Change (%)')
ax2.set_title('Profit Change: New vs Old')
ax2.set_xticklabels([w.replace('_', '\n') for w in WEEKS])
ax2.legend()
ax2.grid(True, alpha=0.3)

# 3. FCR Revenue Comparison
ax3 = axes[1, 0]
baseline_df_sorted = baseline_df.sort_values('week')
x_pos = np.arange(len(WEEKS))

old_fcr = baseline_df_sorted['fcr_revenue_old'].values
new_fcr = baseline_df_sorted['fcr_revenue_new'].values

ax3.bar(x_pos - width/2, old_fcr, width, label='Old (Buggy)',
        color='#E63946', alpha=0.7, edgecolor='black')
ax3.bar(x_pos + width/2, new_fcr, width, label='New (Fixed)',
        color='#06A77D', alpha=0.7, edgecolor='black')

# Add change labels
for i, (old_val, new_val) in enumerate(zip(old_fcr, new_fcr)):
    change = new_val - old_val
    ax3.text(i, max(old_val, new_val) + 0.3, f'+{change:.1f}',
             ha='center', fontsize=9, fontweight='bold')

ax3.set_xlabel('Season')
ax3.set_ylabel('FCR Revenue (EUR/week)')
ax3.set_title('FCR Capacity Revenue Comparison (Baseline)')
ax3.set_xticks(x_pos)
ax3.set_xticklabels([w.replace('_', '\n') for w in WEEKS])
ax3.legend()
ax3.grid(axis='y', alpha=0.3)

# 4. Revenue Mix Comparison (Baseline)
ax4 = axes[1, 1]
old_da = baseline_df_sorted['da_profit_old'].values
new_da = baseline_df_sorted['da_profit_new'].values
old_afrr = baseline_df_sorted['afrr_e_profit_old'].values
new_afrr = baseline_df_sorted['afrr_e_profit_new'].values
old_fcr = baseline_df_sorted['fcr_revenue_old'].values
new_fcr = baseline_df_sorted['fcr_revenue_new'].values

x_pos = np.arange(len(WEEKS))
width = 0.35

# Stacked bars
ax4.bar(x_pos - width/2, old_da, width, label='DA (old)', color='#FFB703', alpha=0.6)
ax4.bar(x_pos - width/2, old_afrr, width, bottom=old_da, label='aFRR-E (old)', color='#219EBC', alpha=0.6)
ax4.bar(x_pos - width/2, old_fcr, width, bottom=old_da+old_afrr, label='FCR (old)', color='#E63946', alpha=0.6)

ax4.bar(x_pos + width/2, new_da, width, label='DA (new)', color='#FFB703', alpha=1.0, edgecolor='black')
ax4.bar(x_pos + width/2, new_afrr, width, bottom=new_da, label='aFRR-E (new)', color='#219EBC', alpha=1.0, edgecolor='black')
ax4.bar(x_pos + width/2, new_fcr, width, bottom=new_da+new_afrr, label='FCR (new)', color='#E63946', alpha=1.0, edgecolor='black')

ax4.set_xlabel('Season')
ax4.set_ylabel('Revenue (EUR)')
ax4.set_title('Revenue Mix Comparison (Baseline)')
ax4.set_xticks(x_pos)
ax4.set_xticklabels([w.replace('_', '\n') for w in WEEKS])
ax4.legend(fontsize=8, ncol=2)
ax4.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'validation_comparison.png', dpi=300, bbox_inches='tight')
print(f"\n[OK] Saved: {OUTPUT_DIR / 'validation_comparison.png'}")

# Additional detailed comparison table
print("\n" + "=" * 80)
print("DETAILED COMPARISON TABLE")
print("=" * 80)

summary_table = baseline_df[['week', 'total_profit_old', 'total_profit_new', 'profit_change_pct',
                               'fcr_revenue_old', 'fcr_revenue_new', 'fcr_change_abs',
                               'fcr_blocks_old', 'fcr_blocks_new']].copy()

summary_table.columns = ['Week', 'Profit Old (EUR)', 'Profit New (EUR)', 'Change (%)',
                          'FCR Old (EUR)', 'FCR New (EUR)', 'FCR Delta (EUR)',
                          'FCR Blocks Old', 'FCR Blocks New']

print(summary_table.to_string(index=False))

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)
print(f"\nComparison results saved to: {OUTPUT_DIR}")
print("Files created:")
print(f"  - comparison_summary.csv")
print(f"  - validation_comparison.png")
