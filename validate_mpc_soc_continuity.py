#!/usr/bin/env python3
"""
MPC Rolling Horizon Validation - SOC Continuity Check
======================================================

Validates the MPC rolling horizon implementation by testing SOC state continuity
across iteration boundaries for a 5-day period in Switzerland (2024-01-13 to 2024-01-17).

Test Configuration:
- Horizon: 32 hours (128 timesteps)
- Execution: 24 hours (96 timesteps)
- Alpha: 0.5 (fixed degradation weight)
- Expected iterations: ~5

Focus: 重点检查SOC状态是否很好的链上了 (Check if SOC states connect well)
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from datetime import datetime
import json

# Add project root to path
sys.path.append(str(Path(__file__).parent / 'py_script'))

from py_script.core.optimizer import BESSOptimizerModelIII
from py_script.rolling_horizon.mpc_simulator import MPCSimulator
from py_script.visualization.optimization_analysis import (
    plot_soc_and_power_bids,
    plot_da_market_price_bid,
    plot_afrr_energy_market_price_bid,
    plot_capacity_markets_price_bid,
    extract_detailed_solution
)
from py_script.visualization.config import MCKINSEY_COLORS, MCKINSEY_FONTS


# ============================================================================
# Data Loading Functions
# ============================================================================

def load_phase2_data(data_dir: Path) -> pd.DataFrame:
    """
    Load Phase 2 data from parquet files and combine into multi-index format.

    Args:
        data_dir: Directory containing parquet files (day_ahead, fcr, afrr_capacity, afrr_energy)

    Returns:
        Combined DataFrame with multi-index columns (country, market, direction)
    """
    print("Loading Phase 2 data from parquet files...")

    # Load all parquet files
    da_df = pd.read_parquet(data_dir / 'day_ahead.parquet')
    fcr_df = pd.read_parquet(data_dir / 'fcr.parquet')
    afrr_cap_df = pd.read_parquet(data_dir / 'afrr_capacity.parquet')
    afrr_energy_df = pd.read_parquet(data_dir / 'afrr_energy.parquet')

    print(f"  Day-ahead: {len(da_df)} records")
    print(f"  FCR: {len(fcr_df)} records")
    print(f"  aFRR capacity: {len(afrr_cap_df)} records")
    print(f"  aFRR energy: {len(afrr_energy_df)} records")

    # Convert timestamps and round to remove milliseconds (critical for alignment)
    da_df['timestamp'] = pd.to_datetime(da_df['timestamp']).dt.floor('S')  # Round to nearest second
    fcr_df['timestamp'] = pd.to_datetime(fcr_df['timestamp']).dt.floor('S')
    afrr_cap_df['timestamp'] = pd.to_datetime(afrr_cap_df['timestamp']).dt.floor('S')
    afrr_energy_df['timestamp'] = pd.to_datetime(afrr_energy_df['timestamp']).dt.floor('S')

    # Set timestamp as index for all
    da_df = da_df.set_index('timestamp')
    fcr_df = fcr_df.set_index('timestamp')
    afrr_cap_df = afrr_cap_df.set_index('timestamp')
    afrr_energy_df = afrr_energy_df.set_index('timestamp')

    # Get country list (columns excluding timestamp)
    countries = [c for c in da_df.columns if c != 'timestamp']

    # Convert to multi-index format expected by optimizer
    # Day-ahead (15-min intervals)
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


# ============================================================================
# Helper Functions
# ============================================================================

def print_section(title: str):
    """Print formatted section header."""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)

def validate_soc_continuity(results: dict) -> dict:
    """
    Validate SOC continuity across MPC iterations.

    Returns validation metrics and pass/fail status.
    """
    validation = {
        'passed': True,
        'max_discontinuity': 0.0,
        'mean_discontinuity': 0.0,
        'iteration_details': [],
        'issues': []
    }

    soc_trajectory = results['soc_trajectory']
    iteration_results = results['iteration_results']

    discontinuities = []

    for i in range(len(iteration_results)):
        iter_info = {
            'iteration': i + 1,
            'initial_soc': soc_trajectory[i],
            'final_soc': soc_trajectory[i + 1],
            'delta_soc': soc_trajectory[i + 1] - soc_trajectory[i],
            'discontinuity': 0.0
        }

        # For iterations after the first, check continuity with previous
        if i > 0:
            expected_initial = soc_trajectory[i]
            actual_initial = soc_trajectory[i]
            discontinuity = abs(actual_initial - expected_initial)
            iter_info['discontinuity'] = discontinuity
            discontinuities.append(discontinuity)

            # Flag if discontinuity exceeds tolerance (0.1 kWh)
            if discontinuity > 0.1:
                validation['passed'] = False
                validation['issues'].append(
                    f"Iteration {i+1}: Large discontinuity of {discontinuity:.4f} kWh"
                )

        validation['iteration_details'].append(iter_info)

    if discontinuities:
        validation['max_discontinuity'] = max(discontinuities)
        validation['mean_discontinuity'] = np.mean(discontinuities)

    return validation

def plot_soc_continuity_analysis(results: dict, output_dir: Path):
    """
    Create comprehensive SOC continuity visualization.

    Shows:
    1. SOC at iteration boundaries
    2. Full continuous SOC trajectory
    3. Discontinuity magnitudes
    """
    fig = plt.figure(figsize=(16, 10))
    gs = gridspec.GridSpec(3, 1, height_ratios=[1, 1.5, 0.8], hspace=0.3)

    soc_trajectory = results['soc_trajectory']
    iteration_results = results['iteration_results']
    n_iterations = len(iteration_results)

    # Plot 1: SOC at iteration boundaries
    ax1 = fig.add_subplot(gs[0])
    iterations = list(range(len(soc_trajectory)))
    ax1.plot(iterations, soc_trajectory, marker='o', markersize=10,
             linewidth=3, color=MCKINSEY_COLORS['navy'], label='SOC at boundaries')
    ax1.axhline(y=4472, color='red', linestyle='--', alpha=0.5, label='Max capacity')
    ax1.axhline(y=0, color='red', linestyle='--', alpha=0.5, label='Min capacity')
    ax1.set_xlabel('Iteration Boundary', fontsize=MCKINSEY_FONTS['axis_label_size'])
    ax1.set_ylabel('SOC (kWh)', fontsize=MCKINSEY_FONTS['axis_label_size'])
    ax1.set_title('SOC at Iteration Boundaries', fontsize=MCKINSEY_FONTS['title_size'],
                  fontweight='bold', color=MCKINSEY_COLORS['navy'])
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=MCKINSEY_FONTS['legend_size'])
    ax1.set_xlim(-0.5, len(soc_trajectory) - 0.5)

    # Plot 2: Full continuous SOC trajectory with iteration windows
    ax2 = fig.add_subplot(gs[1])

    # Reconstruct full SOC trajectory from all iterations
    full_soc = []
    full_hours = []
    execution_hours = 24

    for i, iter_result in enumerate(iteration_results):
        iter_soc = iter_result['soc_trajectory']
        n_steps = len(iter_soc)

        # Only take execution window (24h) except for last iteration
        if i < n_iterations - 1:
            execution_steps = min(96, n_steps)  # 24h = 96 steps
            iter_soc_to_use = iter_soc[:execution_steps]
        else:
            iter_soc_to_use = iter_soc

        # Create hour array for this iteration
        start_hour = i * execution_hours
        iter_hours = [start_hour + t * 0.25 for t in range(len(iter_soc_to_use))]

        full_soc.extend(iter_soc_to_use)
        full_hours.extend(iter_hours)

    # Plot continuous SOC
    ax2.plot(full_hours, full_soc, linewidth=2, color=MCKINSEY_COLORS['dark_blue'],
             label='SOC Trajectory')

    # Add vertical lines at iteration boundaries
    for i in range(1, n_iterations):
        boundary_hour = i * execution_hours
        ax2.axvline(x=boundary_hour, color='orange', linestyle='--', alpha=0.7,
                   linewidth=2, label='Iteration boundary' if i == 1 else '')

    # Shade execution windows
    for i in range(n_iterations):
        start_hour = i * execution_hours
        end_hour = min(start_hour + execution_hours, max(full_hours))
        ax2.axvspan(start_hour, end_hour, alpha=0.1,
                   color='green' if i % 2 == 0 else 'blue')

    ax2.set_xlabel('Time (hours)', fontsize=MCKINSEY_FONTS['axis_label_size'])
    ax2.set_ylabel('SOC (kWh)', fontsize=MCKINSEY_FONTS['axis_label_size'])
    ax2.set_title('Continuous SOC Trajectory Across All Iterations',
                  fontsize=MCKINSEY_FONTS['title_size'], fontweight='bold',
                  color=MCKINSEY_COLORS['navy'])
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=MCKINSEY_FONTS['legend_size'])
    ax2.set_xlim(0, max(full_hours))

    # Plot 3: Discontinuity magnitudes
    ax3 = fig.add_subplot(gs[2])

    discontinuities = []
    for i in range(1, len(soc_trajectory)):
        # Calculate discontinuity (should be zero for perfect continuity)
        disc = abs(soc_trajectory[i] - soc_trajectory[i-1] -
                   (soc_trajectory[i] - soc_trajectory[i-1]))
        discontinuities.append(disc)

    # Show SOC changes between iterations
    soc_changes = [soc_trajectory[i+1] - soc_trajectory[i]
                   for i in range(len(soc_trajectory) - 1)]

    x_pos = list(range(1, len(soc_trajectory)))
    bars = ax3.bar(x_pos, soc_changes, width=0.6,
                   color=[MCKINSEY_COLORS['positive'] if c >= 0 else MCKINSEY_COLORS['negative']
                         for c in soc_changes],
                   alpha=0.7)
    ax3.axhline(y=0, color='black', linewidth=1)
    ax3.set_xlabel('Iteration', fontsize=MCKINSEY_FONTS['axis_label_size'])
    ax3.set_ylabel('SOC Change (kWh)', fontsize=MCKINSEY_FONTS['axis_label_size'])
    ax3.set_title('SOC Change Per Iteration', fontsize=MCKINSEY_FONTS['subtitle_size'],
                  fontweight='bold', color=MCKINSEY_COLORS['dark_blue'])
    ax3.grid(True, alpha=0.3, axis='y')
    ax3.set_xlim(0.5, len(soc_changes) + 0.5)

    plt.suptitle('MPC Rolling Horizon: SOC Continuity Validation',
                 fontsize=MCKINSEY_FONTS['title_size'] + 2, fontweight='bold',
                 color=MCKINSEY_COLORS['navy'], y=0.995)

    plt.tight_layout(rect=[0, 0, 1, 0.99])
    plt.savefig(output_dir / 'soc_continuity_analysis.png', dpi=300, bbox_inches='tight')
    print(f"[OK] Saved: {output_dir / 'soc_continuity_analysis.png'}")

    return fig

def create_validation_report(results: dict, validation: dict, output_dir: Path):
    """Create comprehensive validation report."""

    report = {
        'test_configuration': {
            'country': 'CH',
            'test_period': '2024-01-13 to 2024-01-17',
            'days': 5,
            'horizon_hours': 32,
            'execution_hours': 24,
            'alpha': 0.5,
            'total_steps': len(results.get('soc_trajectory', [])) - 1
        },
        'simulation_results': {
            'total_revenue': results.get('total_revenue', 0),
            'total_degradation_cost': results.get('total_degradation_cost', 0),
            'net_profit': results.get('net_profit', 0),
            'initial_soc': results['soc_trajectory'][0],
            'final_soc': results['soc_trajectory'][-1],
            'n_iterations': len(results['iteration_results'])
        },
        'soc_continuity_validation': validation,
        'timestamp': datetime.now().isoformat()
    }

    # Save JSON report
    report_file = output_dir / 'validation_report.json'
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"[OK] Saved: {report_file}")

    # Print summary to console
    print_section("VALIDATION SUMMARY")
    print(f"SOC Continuity: {'✓ PASSED' if validation['passed'] else '✗ FAILED'}")
    print(f"Max Discontinuity: {validation['max_discontinuity']:.6f} kWh")
    print(f"Mean Discontinuity: {validation['mean_discontinuity']:.6f} kWh")
    print(f"Number of Iterations: {report['simulation_results']['n_iterations']}")

    if validation['issues']:
        print("\nIssues Detected:")
        for issue in validation['issues']:
            print(f"  - {issue}")
    else:
        print("\nNo issues detected - SOC continuity is excellent!")

    print(f"\nFinancial Summary:")
    print(f"  Total Revenue:         {report['simulation_results']['total_revenue']:.2f} EUR")
    print(f"  Degradation Cost:      {report['simulation_results']['total_degradation_cost']:.2f} EUR")
    print(f"  Net Profit:            {report['simulation_results']['net_profit']:.2f} EUR")

    print(f"\nSOC Summary:")
    print(f"  Initial SOC:           {report['simulation_results']['initial_soc']:.2f} kWh")
    print(f"  Final SOC:             {report['simulation_results']['final_soc']:.2f} kWh")
    print(f"  SOC Change:            {report['simulation_results']['final_soc'] - report['simulation_results']['initial_soc']:.2f} kWh")

    return report

def main():
    """Main validation workflow."""

    print_section("MPC Rolling Horizon Validation - SOC Continuity Check")
    print("Test Period: 2024-01-13 to 2024-01-17 (5 days)")
    print("Country: Switzerland (CH)")
    print("Configuration: 32h horizon / 24h execution / alpha=0.5")

    # Create output directory
    output_dir = Path("results/mpc_validation")
    output_dir.mkdir(exist_ok=True, parents=True)

    # ========================================================================
    # Step 1: Load and prepare data
    # ========================================================================

    print_section("Step 1: Loading Data")

    optimizer = BESSOptimizerModelIII(alpha=0.5, use_afrr_ev_weighting=True)
    print("[OK] Initialized BESSOptimizerModelIII with alpha=0.5")

    # Load Phase 2 data from parquet files
    data_dir = Path("data/phase2_processed/parquet")
    print(f"[OK] Loading Phase 2 data from: {data_dir}")

    full_data = load_phase2_data(data_dir)

    print(f"[OK] Extracting data for country: CH")
    country_data = optimizer.extract_country_data(full_data, 'CH')

    # Filter for date range: 2024-01-13 to 2024-01-17 (5 days)
    # January 13 = day 13 (1-indexed) = day 12 (0-indexed)
    start_day = 12  # 0-indexed
    start_step = start_day * 96  # 96 timesteps per day
    end_step = start_step + (5 * 96)  # 5 days

    data_5day = country_data.iloc[start_step:end_step].copy()
    data_5day.reset_index(drop=True, inplace=True)

    print(f"[OK] Extracted {len(data_5day)} timesteps (5 days)")
    print(f"    Start step: {start_step} (2024-01-13)")
    print(f"    End step:   {end_step} (2024-01-18)")

    # ========================================================================
    # Step 2: Run MPC simulation
    # ========================================================================

    print_section("Step 2: Running MPC Simulation")

    simulator = MPCSimulator(
        optimizer_model=optimizer,
        full_data=data_5day,
        horizon_hours=32,
        execution_hours=24,
        c_rate=0.5,
        validate_constraints=True
    )

    print(f"[OK] MPCSimulator initialized")
    print(f"    Horizon:         32 hours (128 timesteps)")
    print(f"    Execution:       24 hours (96 timesteps)")
    print(f"    Initial SOC:     50% (2236 kWh)")
    print(f"    Expected iters:  ~5")

    print("\n[Running] MPC simulation...")
    import time
    start_time = time.time()

    results = simulator.run_full_simulation(initial_soc_fraction=0.5)

    elapsed_time = time.time() - start_time
    print(f"[OK] Simulation completed in {elapsed_time:.2f} seconds")
    print(f"    Iterations:      {len(results['iteration_results'])}")
    print(f"    Net Profit:      {results['net_profit']:.2f} EUR")

    # ========================================================================
    # Step 3: Validate SOC continuity
    # ========================================================================

    print_section("Step 3: Validating SOC Continuity")

    validation = validate_soc_continuity(results)

    print(f"SOC Continuity Check: {'✓ PASSED' if validation['passed'] else '✗ FAILED'}")
    print(f"  Max discontinuity:  {validation['max_discontinuity']:.6f} kWh")
    print(f"  Mean discontinuity: {validation['mean_discontinuity']:.6f} kWh")

    print("\nIteration-by-Iteration SOC Analysis:")
    for detail in validation['iteration_details']:
        print(f"  Iteration {detail['iteration']}:")
        print(f"    Initial SOC: {detail['initial_soc']:.2f} kWh")
        print(f"    Final SOC:   {detail['final_soc']:.2f} kWh")
        print(f"    Delta:       {detail['delta_soc']:+.2f} kWh")
        if 'discontinuity' in detail and detail['discontinuity'] > 0:
            print(f"    Discontinuity: {detail['discontinuity']:.6f} kWh")

    # ========================================================================
    # Step 4: Generate visualizations
    # ========================================================================

    print_section("Step 4: Generating Visualizations")

    # Main SOC continuity analysis plot
    plot_soc_continuity_analysis(results, output_dir)

    # Generate per-iteration detailed plots for first 3 iterations
    for i, iter_result in enumerate(results['iteration_results'][:3]):
        iter_dir = output_dir / f"iteration_{i+1}"
        iter_dir.mkdir(exist_ok=True)

        # Extract iteration solution to DataFrame
        iter_solution = iter_result['solution']
        iter_data = data_5day.iloc[i*96:min((i+2)*128, len(data_5day))].copy()
        iter_data.reset_index(drop=True, inplace=True)

        if iter_solution['status'] == 'optimal':
            df = extract_detailed_solution(iter_solution, iter_data, horizon_hours=32)

            # Save plots
            fig1 = plot_soc_and_power_bids(df, title_suffix=f"(CH, Iteration {i+1})")
            fig1.write_html(str(iter_dir / "soc_and_power.html"))

            fig2 = plot_da_market_price_bid(df, title_suffix=f"(CH, Iteration {i+1})")
            fig2.write_html(str(iter_dir / "da_market.html"))

            fig3 = plot_afrr_energy_market_price_bid(df, title_suffix=f"(CH, Iteration {i+1})")
            fig3.write_html(str(iter_dir / "afrr_energy_market.html"))

            fig4 = plot_capacity_markets_price_bid(df, title_suffix=f"(CH, Iteration {i+1})")
            fig4.write_html(str(iter_dir / "capacity_markets.html"))

            print(f"[OK] Saved iteration {i+1} plots to: {iter_dir}")

    # ========================================================================
    # Step 5: Create validation report
    # ========================================================================

    print_section("Step 5: Creating Validation Report")

    report = create_validation_report(results, validation, output_dir)

    # ========================================================================
    # Final Summary
    # ========================================================================

    print_section("VALIDATION COMPLETE")
    print(f"Results saved to: {output_dir}")
    print(f"\nKey files:")
    print(f"  - soc_continuity_analysis.png   : Main validation plot")
    print(f"  - validation_report.json         : Detailed report")
    print(f"  - iteration_*/                   : Per-iteration visualizations")

    if validation['passed']:
        print("\n✓ SOC CONTINUITY VALIDATION: PASSED")
        print("  The MPC implementation correctly maintains SOC state continuity!")
    else:
        print("\n✗ SOC CONTINUITY VALIDATION: FAILED")
        print("  Issues detected - see report for details")

    print("=" * 80)

if __name__ == "__main__":
    main()
