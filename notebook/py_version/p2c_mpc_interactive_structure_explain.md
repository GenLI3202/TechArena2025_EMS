  ⎿  Read notebook\py_version\p2c_mpc_interactive.py (784 lines)

● 📋 Structure of p2c_mpc_interactive.py

  This is a modular, cell-based interactive script for running rolling-horizon MPC simulations. Here's the complete structure:

  ---
  🎯 Overview: 7 Main Sections

  [SECTION 1] SETUP & IMPORTS
      ↓
  [SECTION 2] CONFIGURATION (Load configs & set parameters)
      ↓
  [SECTION 3] RUN MPC SIMULATION (or load saved results)
      ↓
  [SECTION 4] TRANSFORM & SAVE RESULTS
      ↓
  [SECTION 5] STANDARD VALIDATION PLOTS
      ↓
  [SECTION 6] MPC-SPECIFIC ANALYSIS PLOTS
      ↓
  [COMPLETE] Summary & Next Steps

  ---
  📦 SECTION 1: SETUP & IMPORTS (Lines 11-65)

  Purpose: Import all necessary modules and verify environment

  - Standard libraries (sys, json, time, Path, datetime)
  - Data processing (pandas, numpy)
  - Optimization models (BESSOptimizerModelIII)
  - MPC simulation (MPCSimulator, MetaOptimizer)
  - Visualization utilities
  - Results export tools

  Output: [OK] All imports successful!

  ---
  📋 SECTION 2: CONFIGURATION (Lines 67-278)

  2A: Load Option (Lines 72-80)
  - LOAD_FROM_SAVED: Skip simulation, load previous results

  2B: Load Config Files (Lines 82-127)
  ├── mpc_config.json          → MPC parameters (horizon, execution)
  ├── mpc_test_config.json     → Test scenario (country, duration, alpha)
  ├── solver_config.json       → Solver settings (Gurobi/CPLEX/CBC)
  ├── aging_config.json        → Degradation model parameters
  └── afrr_ev_weights_config.json → aFRR activation probabilities

  2C: Extract Parameters (Lines 128-218)
  # From configs:
  TEST_COUNTRY, TEST_DURATION_DAYS, TEST_C_RATE
  HORIZON_HOURS, EXECUTION_HOURS, INITIAL_SOC_FRACTION
  SINGLE_ALPHA, ALPHA_MODE
  DEFAULT_SOLVER, DEFAULT_SOLVER_TIME_LIMIT

  # Hardcoded (can override):
  ENABLE_CROSS_MARKET_EXCLUSIVITY = True
  MAX_AS_RATIO = 0.8
  ENABLE_CHECKPOINTING = True  # ← NEW!
  CHECKPOINT_INTERVAL_MINUTES = 30  # ← NEW!

  2D: Display Configuration (Lines 180-218)
  - Shows all settings in organized summary
  - Includes solver, checkpointing status

  2E: Load Market Data (Lines 220-278)
  if DATA_SOURCE == 'preprocessed':
      # Fast path: Load .parquet (10-100x faster)
  elif DATA_SOURCE == 'excel':
      # Submission path: Load from Excel

  ---
  🚀 SECTION 3: RUN MPC SIMULATION (Lines 280-489)

  Branch A: Load Saved Results (Lines 285-367)
  if LOAD_FROM_SAVED:
      ├── Load performance_summary.json
      ├── Load iteration_summary.csv
      ├── Load solution_timeseries.csv
      └── Reconstruct mpc_results dictionary

  Branch B: Run New Simulation (Lines 369-474)

  Option 1: MetaOptimizer Mode (Lines 380-427)
  - ⚠️ Currently DISABLED (raises NotImplementedError)
  - Would do alpha sweep to find optimal degradation price

  Option 2: Single-Alpha MPC (Lines 429-472) ✅
  1. Initialize BESSOptimizerModelIII(alpha)
  2. Configure optimizer settings (max_as_ratio, exclusivity)
  3. Create MPCSimulator
  4. Run simulation with checkpointing:

     if ENABLE_CHECKPOINTING:
         mpc_results = simulator.run_full_simulation(
             checkpoint_interval_minutes=30,  # ← Saves every 30 min
             checkpoint_path="mpc_checkpoint_backup.pkl"
         )
     else:
         mpc_results = simulator.run_full_simulation()

  Output: Results dictionary with:
  - total_revenue, total_degradation_cost, net_profit
  - final_soc, soc_trajectory
  - iteration_results (per-iteration metrics)
  - annual_bids_df (all decision variables for full year)

  ---
  💾 SECTION 4: TRANSFORM & SAVE (Lines 491-641)

  4A: Transform Results (Lines 496-524)
  1. Extract annual_bids_df from mpc_results
  2. Transform to visualization format (viz_df)
  3. Extract iteration summary

  4B: Prepare Summary Metrics (Lines 526-593)
  summary_metrics = {
      'model': 'Model_III_MPC',
      'country', 'duration', 'alpha', 'c_rate',
      'mpc_horizon_hours', 'mpc_execution_hours',
      'total_profit_eur', 'total_revenue_eur',
      'revenue_da_eur', 'revenue_afrr_energy_eur',
      'degradation_cyclic_eur', 'degradation_calendar_eur',
      'solver': DEFAULT_SOLVER,  # ← NEW!
      'solver_time_limit_sec',   # ← NEW!
      'simulation_time_sec',
      ...
  }

  4C: Save to Disk (Lines 595-641)
  if SAVE_RESULTS:
      ├── Generate run_name (timestamped)
      ├── Save solution_timeseries.csv
      ├── Save iteration_summary.csv
      ├── Save performance_summary.json
      └── Create plots/ directory

  Output: Timestamped directory in validation_results/mpc_validation/

  ---
  📊 SECTION 5: STANDARD PLOTS (Lines 643-693)

  4 Standard Market Plots:
  if ENABLE_STANDARD_PLOTS:
      1. Day-Ahead Market (price + bids)
      2. aFRR Energy Market (price + bids)
      3. Capacity Markets (FCR + aFRR capacity)
      4. SOC & Power Bids (battery operation)

  Output: Interactive HTML plots (or PNG if configured)

  ---
  📈 SECTION 6: MPC-SPECIFIC PLOTS (Lines 695-752)

  3 MPC Analysis Plots:
  if ENABLE_MPC_PLOTS:
      1. Iteration Boundaries (time windows)
      2. Iteration Performance (profit per iteration)
      3. State Continuity (SOC handoff between iterations)

  Purpose: Validate MPC implementation quality

  ---
  ✅ COMPLETE: Summary (Lines 754-784)

  Documentation section listing:
  - What was accomplished
  - Output location
  - Next steps
  - Configuration file reference

  ---
  🔄 Execution Flow Diagram

  ┌─────────────────────────────────────────────┐
  │ 1. SETUP: Import all modules               │
  └─────────────────┬───────────────────────────┘
                    ↓
  ┌─────────────────────────────────────────────┐
  │ 2. CONFIG: Load 5 JSON files               │
  │    Extract parameters                       │
  │    Display configuration summary            │
  │    Load market data (parquet or Excel)      │
  └─────────────────┬───────────────────────────┘
                    ↓
           ┌────────┴────────┐
           ↓                 ↓
      LOAD_FROM_SAVED?    Run new simulation
           │                 │
           │                 ├─ Create optimizer
           │                 ├─ Create MPCSimulator
           │                 ├─ Run simulation (with checkpointing!)
           │                 └─ Get mpc_results
           └────────┬────────┘
                    ↓
  ┌─────────────────────────────────────────────┐
  │ 4. TRANSFORM & SAVE                         │
  │    ├─ Transform to viz_df                   │
  │    ├─ Build summary_metrics                 │
  │    └─ Save CSV/JSON files                   │
  └─────────────────┬───────────────────────────┘
                    ↓
  ┌─────────────────────────────────────────────┐
  │ 5. STANDARD PLOTS (4 plots)                 │
  └─────────────────┬───────────────────────────┘
                    ↓
  ┌─────────────────────────────────────────────┐
  │ 6. MPC PLOTS (3 plots)                      │
  └─────────────────┬───────────────────────────┘
                    ↓
  ┌─────────────────────────────────────────────┐
  │ ✅ COMPLETE: Results saved!                 │
  └─────────────────────────────────────────────┘

  ---
  🎛️ Key Control Variables

  | Variable              | Purpose                     | Default             |
  |-----------------------|-----------------------------|---------------------|
  | LOAD_FROM_SAVED       | Skip simulation, load saved | False               |
  | TEST_DURATION_DAYS    | Simulation length           | 2 (from config)     |
  | ENABLE_CHECKPOINTING  | Auto-save every 30min       | True ✅              |
  | ENABLE_META_OPTIMIZER | Alpha sweep mode            | False (disabled)    |
  | SAVE_RESULTS          | Save outputs to disk        | True (from config)  |
  | ENABLE_STANDARD_PLOTS | Generate market plots       | False (from config) |
  | ENABLE_MPC_PLOTS      | Generate MPC analysis       | False (from config) |

  ---
  📁 Output Structure

  validation_results/mpc_validation/
  └── 20251115_141102_mpc_DE_LU_365d_alpha1.0/
      ├── solution_timeseries.csv      # All timesteps
      ├── iteration_summary.csv        # Per-iteration metrics
      ├── performance_summary.json     # Overall statistics
      └── plots/                       # Visualizations
          ├── da_market_price_bid.html
          ├── afrr_energy_market_price_bid.html
          ├── capacity_markets_price_bid.html
          ├── soc_and_power_bids.html
          ├── mpc_iteration_boundaries.html
          ├── mpc_iteration_performance.html
          └── mpc_state_continuity.html

  Plus: mpc_checkpoint_backup.pkl in project root (auto-saves every 30 min!)
