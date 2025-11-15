# -*- coding: utf-8 -*-
"""
Phase 2 BESS Optimizer - Interactive Version

This version has cell markers (# %%) for block-by-block execution in VS Code.
Run cells individually using Shift+Enter or clicking "Run Cell" above each block.

Quick start:
1. Modify the CONFIGURATION section below
2. Run cells one by one using Shift+Enter
3. Inspect variables in the Interactive Window
"""

# %%
# ============================================================================
# IMPORTS
# ============================================================================

import sys
import json
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np

from py_script.core.optimizer import (
    BESSOptimizerModelI,
    BESSOptimizerModelII,
    BESSOptimizerModelIII
)

from py_script.visualization.optimization_analysis import (
    extract_detailed_solution,
    plot_da_market_price_bid,
    plot_afrr_energy_market_price_bid,
    plot_capacity_markets_price_bid,
    plot_soc_and_power_bids
)

from py_script.validation.results_exporter import save_optimization_results
from py_script.visualization.aging_analysis import (
    plot_stacked_cyclic_soc,
    plot_calendar_aging_curve,
)
from py_script.data.load_process_market_data import load_preprocessed_country_data

print("[OK] All imports successful!")

# %%
# ============================================================================
# LOAD CONFIGURATION FILES
# ============================================================================

config_dir = project_root / "data" / "p2_config"

# Load solver config
solver_config_path = config_dir / "solver_config.json"
with open(solver_config_path, 'r') as f:
    solver_config = json.load(f)

# Load aging config
aging_config_path = config_dir / "aging_config.json"
with open(aging_config_path, 'r') as f:
    aging_config = json.load(f)

# Load aFRR EV weights config (if needed for EV weighting)
afrr_ev_config_path = config_dir / "afrr_ev_weights_config.json"
with open(afrr_ev_config_path, 'r') as f:
    afrr_ev_config = json.load(f)

# Extract default values
DEFAULT_REQUIRE_SEQUENTIAL = aging_config.get('REQUIRE_SEQUENTIAL_SEGMENT_ACTIVATION', False)
DEFAULT_LIFO_EPSILON = aging_config.get('lifo_epsilon_kwh', 5.0)
DEFAULT_SOLVER = solver_config.get('default_solver', 'cbc')
DEFAULT_SOLVER_TIME_LIMIT = solver_config.get('solver_time_limit_sec', 600)

# Extract degradation model parameters
cyclic_costs = aging_config['cyclic_aging']['costs']
calendar_breakpoints = aging_config['calendar_aging']['breakpoints']

print(f"[OK] Loaded configuration files:")
print(f"   - {solver_config_path.name}")
print(f"   - {aging_config_path.name}")
print(f"   - {afrr_ev_config_path.name}")

print(f"\n[DEFAULTS] From solver_config.json:")
print(f"   default_solver: {DEFAULT_SOLVER}")
print(f"   solver_time_limit_sec: {DEFAULT_SOLVER_TIME_LIMIT}")

print(f"\n[DEFAULTS] From aging_config.json:")
print(f"   REQUIRE_SEQUENTIAL_SEGMENT_ACTIVATION: {DEFAULT_REQUIRE_SEQUENTIAL}")
print(f"   lifo_epsilon_kwh: {DEFAULT_LIFO_EPSILON} kWh")

print(f"\n[DEGRADATION] Cyclic Aging Parameters:")
print(f"   Num segments: {len(cyclic_costs)}")
print(f"   Segment capacity: {4472 / len(cyclic_costs):.2f} kWh")
print(f"   Marginal costs (EUR/kWh):")
print(f"      Segment 1-5:  {cyclic_costs[:5]}")
print(f"      Segment 6-10: {cyclic_costs[5:]}")
print(f"   Cost range: {min(cyclic_costs):.4f} - {max(cyclic_costs):.4f} EUR/kWh")

print(f"\n[DEGRADATION] Calendar Aging Parameters:")
print(f"   Num breakpoints: {len(calendar_breakpoints)}")
print(f"   SOC breakpoints (kWh): {[bp['soc_kwh'] for bp in calendar_breakpoints]}")
print(f"   Cost range: {calendar_breakpoints[0]['cost_eur_hr']:.2f} - {calendar_breakpoints[-1]['cost_eur_hr']:.2f} EUR/hr")

# %%
# ============================================================================
# CONFIGURATION - MODIFY THESE VALUES
# ============================================================================

# Test scenario configuration
TEST_COUNTRY = "DE_LU"              # Options: DE_LU, AT, CH, HU, CZ
TEST_C_RATE = 0.5                   # Options: 0.25, 0.33, 0.5
TEST_ALPHA = 1.0                    # Degradation weight
TEST_TIME_HORIZON_HOURS = 24        # Time horizon in hours
TEST_START_STEP = 0                 # Starting time step
TEST_MODEL = "III"                  # Options: "I", "II", "III"
USE_EV_WEIGHTING = False            # Enable aFRR EV weighting
MAX_AS_RATIO = 0.8                  # Max ancillary service ratio

# Use defaults from aging_config.json (can override below if needed)
LIFO_EPSILON_KWH = DEFAULT_LIFO_EPSILON          # From config (default: 5.0 kWh)
REQUIRE_SEQUENTIAL = DEFAULT_REQUIRE_SEQUENTIAL  # From config (default: False)

# To override config defaults, uncomment and modify:
# LIFO_EPSILON_KWH = 0.0              # Override: perfect LIFO (no tolerance)
# REQUIRE_SEQUENTIAL = True           # Override: strict sequential activation

# Battery SOC limits
MAX_SOC = 1.0                       # Max state of charge
MIN_SOC = 0.0                       # Min state of charge

# Output options
SAVE_RESULTS = False                # Save results to disk
GENERATE_PLOTS = True               # Generate validation plots

print("=" * 80)
print("[CONFIG] SCENARIO CONFIGURATION")
print("=" * 80)
print(f"Model:              {TEST_MODEL}")
print(f"Country:            {TEST_COUNTRY}")
print(f"Time Horizon:       {TEST_TIME_HORIZON_HOURS} hours")
print(f"C-Rate:             {TEST_C_RATE}")
print(f"LIFO Epsilon:       {LIFO_EPSILON_KWH} kWh (from aging_config.json)")
print(f"Sequential:         {REQUIRE_SEQUENTIAL} (from aging_config.json)")
print("=" * 80)

# %%
# ============================================================================
# LOAD MARKET DATA
# ============================================================================

print("\n[DATA] Loading market data...")

preprocessed_dir = project_root / "data" / "parquet" / "preprocessed"
country_data = load_preprocessed_country_data(TEST_COUNTRY, data_dir=preprocessed_dir)

print(f"[OK] Loaded {len(country_data)} time steps for {TEST_COUNTRY}")

# Extract time window
horizon_steps = TEST_TIME_HORIZON_HOURS * 4
end_step = TEST_START_STEP + horizon_steps
data_slice = country_data.iloc[TEST_START_STEP:end_step].copy()
data_slice.reset_index(drop=True, inplace=True)

print(f"[OK] Extracted {len(data_slice)} time steps ({TEST_TIME_HORIZON_HOURS} hours)")
print(f"\nData shape: {data_slice.shape}")
print(f"Columns: {list(data_slice.columns)}")

# %%
# ============================================================================
# INITIALIZE OPTIMIZER
# ============================================================================

print("\n[INIT] Initializing optimizer...")

if TEST_MODEL == "I":
    optimizer = BESSOptimizerModelI()
elif TEST_MODEL == "II":
    optimizer = BESSOptimizerModelII(
        alpha=TEST_ALPHA,
        require_sequential_segment_activation=REQUIRE_SEQUENTIAL,
        use_afrr_ev_weighting=USE_EV_WEIGHTING
    )
    optimizer.degradation_params['lifo_epsilon_kwh'] = LIFO_EPSILON_KWH
elif TEST_MODEL == "III":
    optimizer = BESSOptimizerModelIII(
        alpha=TEST_ALPHA,
        require_sequential_segment_activation=REQUIRE_SEQUENTIAL,
        use_afrr_ev_weighting=USE_EV_WEIGHTING
    )
    optimizer.degradation_params['lifo_epsilon_kwh'] = LIFO_EPSILON_KWH

# Configure optimizer
optimizer.max_as_ratio = MAX_AS_RATIO
optimizer.battery_params['soc_min'] = MIN_SOC
optimizer.battery_params['soc_max'] = MAX_SOC

print(f"[OK] Initialized Model {TEST_MODEL}")
print(f"Battery Capacity: {optimizer.battery_params['capacity_kwh']} kWh")
print(f"Max AS Ratio: {MAX_AS_RATIO * 100:.0f}%")

# %%
# ============================================================================
# BUILD OPTIMIZATION MODEL
# ============================================================================

print("\n[BUILD] Building optimization model...")

build_start = time.time()
model = optimizer.build_optimization_model(data_slice, c_rate=TEST_C_RATE)
build_time = time.time() - build_start

print(f"[OK] Model built in {build_time:.2f} seconds")
print(f"Variables:   {model.nvariables()}")
print(f"Constraints: {model.nconstraints()}")

# %%
# ============================================================================
# SOLVE OPTIMIZATION MODEL
# ============================================================================

print("\n[SOLVE] Solving optimization model...")
print("This may take a few minutes...")

solve_start = time.time()
solved_model, solver_results = optimizer.solve_model(model)
solve_time = time.time() - solve_start

print(f"[OK] Model solved in {solve_time:.2f} seconds")
print(f"Status:      {solver_results.solver.status}")
print(f"Termination: {solver_results.solver.termination_condition}")

# %%
# ============================================================================
# EXTRACT SOLUTION
# ============================================================================

print("\n[EXTRACT] Extracting solution...")

solution_dict = optimizer.extract_solution(solved_model, solver_results)

print(f"[OK] Solution extracted")
print(f"\n[PROFIT] Objective Value: {solution_dict['objective_value']:.2f} EUR")

# Display profit components
if 'profit_components' in solution_dict:
    print(f"\n[BREAKDOWN] Profit Components:")
    for key, value in solution_dict['profit_components'].items():
        print(f"   {key:30s}: {value:10.2f} EUR")

# Display degradation metrics (Model II/III)
if 'degradation_metrics' in solution_dict:
    print(f"\n[DEGRADATION] Degradation Metrics:")
    for key, value in solution_dict['degradation_metrics'].items():
        if isinstance(value, (int, float)):
            print(f"   {key:30s}: {value:10.4f}")

print(f"\n[TIME] Total Time: {build_time + solve_time:.2f}s")

# Create solution DataFrame
solution_df = extract_detailed_solution(solution_dict, data_slice, TEST_TIME_HORIZON_HOURS)
print(f"\n[INFO] Solution DataFrame: {solution_df.shape}")

# %%
# ============================================================================
# INSPECT SOLUTION (INTERACTIVE)
# ============================================================================

solution_df

# %%
# ============================================================================
# SAVE RESULTS (OPTIONAL)
# ============================================================================

if SAVE_RESULTS:
    print("\n[SAVE] Saving results...")

    # Calculate revenue breakdown
    revenue_da = solution_df['revenue_da_eur'].sum() if 'revenue_da_eur' in solution_df.columns else 0
    revenue_fcr = solution_df['revenue_fcr_eur'].sum() if 'revenue_fcr_eur' in solution_df.columns else 0
    revenue_afrr_cap = solution_df['revenue_afrr_capacity_eur'].sum() if 'revenue_afrr_capacity_eur' in solution_df.columns else 0
    revenue_afrr_energy = solution_df['revenue_afrr_energy_eur'].sum() if 'revenue_afrr_energy_eur' in solution_df.columns else 0

    summary_metrics = {
        'model': TEST_MODEL,
        'country': TEST_COUNTRY,
        'time_horizon_hours': TEST_TIME_HORIZON_HOURS,
        'c_rate': TEST_C_RATE,
        'alpha': TEST_ALPHA,
        'lifo_epsilon_kwh': LIFO_EPSILON_KWH,
        'total_profit_eur': solution_dict['objective_value'],
        'total_revenue_eur': revenue_da + revenue_fcr + revenue_afrr_cap + revenue_afrr_energy,
        'solver_status': solution_dict['status'],
        'solve_time_sec': solve_time,
        'build_time_sec': build_time,
        'n_variables': model.nvariables(),
        'n_constraints': model.nconstraints()
    }

    if 'degradation_metrics' in solution_dict:
        summary_metrics['degradation_metrics'] = solution_dict['degradation_metrics']

    run_name = f"interactive_model{TEST_MODEL}_{TEST_COUNTRY}_{TEST_TIME_HORIZON_HOURS}h_eps{LIFO_EPSILON_KWH}"

    output_directory = save_optimization_results(
        solution_df,
        summary_metrics,
        run_name,
        base_output_dir=str(project_root / "validation_results" / "optimizer_validation")
    )

    print(f"[OK] Results saved to: {output_directory}")
else:
    print("\n[SKIP] Results not saved (SAVE_RESULTS=False)")


# %%
# ============================================================================
# GENERATE PLOTS (OPTIONAL)
# ============================================================================


# %%

if SAVE_RESULTS:
    plots_dir = output_directory / "plots"
    print("   [INFO] plots will be saved to output directory...")

title_suffix = f"{TEST_COUNTRY} - {TEST_TIME_HORIZON_HOURS}h - Model {TEST_MODEL}"

# %%

# Plot 1: Day-Ahead Market
print("\n[1/4] Day-Ahead Market...")
fig_da = plot_da_market_price_bid(solution_df, title_suffix=title_suffix, use_timestamp=False)
fig_da.show()  # Display in Interactive Window
if SAVE_RESULTS:
    fig_da.write_html(str(plots_dir / "da_market_price_bid.html"))
    print("   [OK] Saved: da_market_price_bid.html")


# %%
# Plot 2: aFRR Energy Market
print("\n[2/4] aFRR Energy Market...")
fig_afrr = plot_afrr_energy_market_price_bid(solution_df, title_suffix=title_suffix, use_timestamp=False)
fig_afrr.show()  # Display in Interactive Window
if SAVE_RESULTS:
    fig_afrr.write_html(str(plots_dir / "afrr_energy_market_price_bid.html"))
    print("   [OK] Saved: afrr_energy_market_price_bid.html")

# %%
# Plot 3: Capacity Markets
print("\n[3/4] Capacity Markets...")
fig_cap = plot_capacity_markets_price_bid(solution_df, title_suffix=title_suffix, use_timestamp=False)
fig_cap.show()  # Display in Interactive Window
if SAVE_RESULTS:
    fig_cap.write_html(str(plots_dir / "capacity_markets_price_bid.html"))
    print("   [OK] Saved: capacity_markets_price_bid.html")

# %%
# Plot 4: SOC & Power
print("\n[4/4] SOC & Power Bids...")
fig_soc = plot_soc_and_power_bids(solution_df, title_suffix=title_suffix, use_timestamp=False)
fig_soc.show()  # Display in Interactive Window
if SAVE_RESULTS:
    fig_soc.write_html(str(plots_dir / "soc_and_power_bids.html"))
    print("   [OK] Saved: soc_and_power_bids.html")

# %%
# Check if aging plots are applicable based on model
if TEST_MODEL in ['II', 'III']:
    print("\nGenerating aging validation plots...")
    print("=" * 80)
    
    # Plot 5: Stacked Cyclic SOC (Model II/III)
    if 'e_soc_j' in solution_dict and solution_dict['e_soc_j']:
        print("\n[5/6] Cyclic SOC Stacked Segments...")
        try:
            fig_cyclic = plot_stacked_cyclic_soc(
                solution_dict,
                title_suffix=title_suffix,
                # save_path=str(plots_dir / "cyclic_soc_stacked.html")
            )
            fig_cyclic.show()
            print("   ✅ Saved: cyclic_soc_stacked.html")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    else:
        print("\n[5/6] Cyclic SOC plot skipped (no segment data)")
    
    # Plot 6: Calendar Aging Curve (Model III only)
    if TEST_MODEL == 'III' and 'c_cal_cost' in solution_dict and solution_dict['c_cal_cost']:
        print("\n[6/6] Calendar Aging Cost Curve...")
        try:
            fig_calendar = plot_calendar_aging_curve(
                solution_dict,
                aging_config=aging_config,
                title_suffix=title_suffix,
                # save_path=str(plots_dir / "calendar_aging_curve.html")
            )
            fig_calendar.show()
            print("   ✅ Saved: calendar_aging_curve.html")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    else:
        print("\n[6/6] Calendar aging plot skipped (Model III required)")
    
    print("\n" + "=" * 80)
    print("✅ All aging validation plots generated!")
    print("=" * 80)


# %%
# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "=" * 80)
print("[COMPLETE] OPTIMIZATION COMPLETE!")
print("=" * 80)
print(f"Total Profit: {solution_dict['objective_value']:.2f} EUR")
print(f"Total Time:   {build_time + solve_time:.2f}s")
print("=" * 80)

# %%
# Optional: Quick parameter sweep
# Uncomment and run this cell to test different epsilon values

# epsilon_values = [0.0, 1.0, 5.0, 10.0]
# results = []
#
# for eps in epsilon_values:
#     print(f"\nTesting epsilon = {eps} kWh...")
#     optimizer.degradation_params['lifo_epsilon_kwh'] = eps
#     model = optimizer.build_optimization_model(data_slice, c_rate=TEST_C_RATE)
#     solved_model, solver_results = optimizer.solve_model(model)
#     solution_dict = optimizer.extract_solution(solved_model, solver_results)
#
#     results.append({
#         'epsilon': eps,
#         'profit': solution_dict['objective_value'],
#         'status': solution_dict['status']
#     })
#
# results_df = pd.DataFrame(results)
# print("\n[RESULTS] Epsilon Sweep:")
# print(results_df)
