# -*- coding: utf-8 -*-
"""
Batch Execution Script for Final Submission Results

Generates 15 annual MPC results for all country-crate combinations:
- 5 countries: DE_LU, AT, CH, HU, CZ
- 3 C-rates: 0.25, 0.33, 0.5

Execution order (priority-based):
1. All countries at C-rate=0.5
2. All countries at C-rate=0.33
3. All countries at C-rate=0.25
"""

import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime
import traceback

# Add project root to path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np

# Core optimizer
from py_script.core.optimizer import BESSOptimizerModelIII

# MPC simulation
from py_script.mpc.mpc_simulator import MPCSimulator
from py_script.mpc.transform_mpc_results import (
    transform_mpc_results_for_viz,
    extract_iteration_summary
)

# Data loading
from py_script.data.load_process_market_data import load_preprocessed_country_data

# Results export
from py_script.validation.results_exporter import save_optimization_results

# ================================================================================
# CONFIGURATION
# ================================================================================

# Test parameters
TEST_DURATION_DAYS = 365  # Full year for final submission
ALPHA = 1.0  # Full degradation cost
INITIAL_SOC_FRACTION = 0.5  # 50% initial SOC

# SOC limits (0-100% to avoid constraint bug)
SOC_MIN = 0.0
SOC_MAX = 1.0

# Degradation settings
REQUIRE_SEQUENTIAL = False  # Faster solving
LIFO_EPSILON_KWH = 0

# Optimizer settings
MAX_AS_RATIO = 0.8
ENABLE_CROSS_MARKET_EXCLUSIVITY = True

# MPC settings (load from config)
config_dir = project_root / "data" / "p2_config"
with open(config_dir / "mpc_config.json", 'r') as f:
    mpc_config = json.load(f)

HORIZON_HOURS = mpc_config['mpc_parameters']['horizon_hours']
EXECUTION_HOURS = mpc_config['mpc_parameters']['execution_hours']
VALIDATE_CONSTRAINTS = False  # Disable for speed

# Solver settings
with open(config_dir / "solver_config.json", 'r') as f:
    solver_config = json.load(f)

DEFAULT_SOLVER = solver_config.get('default_solver', 'gurobi')
DEFAULT_SOLVER_TIME_LIMIT = solver_config.get('solver_time_limit_sec', 900)

# Checkpointing
ENABLE_CHECKPOINTING = True
CHECKPOINT_INTERVAL_MINUTES = 2

# Output settings
SAVE_RESULTS = True
BASE_OUTPUT_DIR = "submission_results"

# ================================================================================
# SCENARIO DEFINITIONS (Priority-ordered)
# ================================================================================

SCENARIOS = [
    # Round 1: C-rate 0.5 (highest priority)
    ('CH', 0.5),
    ('DE_LU', 0.5),
    ('AT', 0.5),
    ('HU', 0.5),
    ('CZ', 0.5),

    # Round 2: C-rate 0.33
    ('CH', 0.33),
    ('DE_LU', 0.33),
    ('AT', 0.33),
    ('HU', 0.33),
    ('CZ', 0.33),

    # Round 3: C-rate 0.25
    ('CH', 0.25),
    ('DE_LU', 0.25),
    ('AT', 0.25),
    ('HU', 0.25),
    ('CZ', 0.25),
]

# ================================================================================
# LOGGING SETUP
# ================================================================================

def setup_logging():
    """Setup logging to both file and console"""
    log_file = project_root / BASE_OUTPUT_DIR / "batch_execution.log"

    # Create logger
    logger = logging.getLogger('batch_executor')
    logger.setLevel(logging.INFO)

    # File handler
    fh = logging.FileHandler(log_file, mode='w')
    fh.setLevel(logging.INFO)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger

# ================================================================================
# MAIN EXECUTION FUNCTION
# ================================================================================

def run_scenario(country, c_rate, logger):
    """
    Run MPC simulation for a single scenario.

    Parameters
    ----------
    country : str
        Country code (e.g., 'CH', 'DE_LU')
    c_rate : float
        C-rate (0.25, 0.33, or 0.5)
    logger : logging.Logger
        Logger instance

    Returns
    -------
    dict
        Results dictionary with keys: success, profit, revenue, degradation, etc.
    """
    scenario_start = time.time()

    try:
        logger.info("=" * 80)
        logger.info(f"STARTING: {country} | C-rate: {c_rate}")
        logger.info("=" * 80)

        # 1. Load market data
        logger.info(f"[1/5] Loading market data for {country}...")
        preprocessed_dir = project_root / "data" / "parquet" / "preprocessed"
        country_data = load_preprocessed_country_data(country, data_dir=preprocessed_dir)

        # Slice to test duration
        duration_timesteps = TEST_DURATION_DAYS * 96
        if duration_timesteps > len(country_data):
            logger.warning(f"Requested {duration_timesteps} timesteps but only {len(country_data)} available")
            country_data_slice = country_data.copy()
        else:
            country_data_slice = country_data.iloc[:duration_timesteps].copy()

        logger.info(f"  Loaded {len(country_data_slice)} timesteps ({TEST_DURATION_DAYS} days)")

        # 2. Initialize optimizer
        logger.info(f"[2/5] Initializing optimizer (Alpha={ALPHA})...")
        optimizer = BESSOptimizerModelIII(alpha=ALPHA)

        # Configure optimizer
        optimizer.max_as_ratio = MAX_AS_RATIO
        optimizer.market_params['enable_cross_market_exclusivity'] = ENABLE_CROSS_MARKET_EXCLUSIVITY
        optimizer.battery_params['soc_min'] = SOC_MIN
        optimizer.battery_params['soc_max'] = SOC_MAX
        optimizer.degradation_params['lifo_epsilon_kwh'] = LIFO_EPSILON_KWH
        optimizer.degradation_params['require_sequential_segment_activation'] = REQUIRE_SEQUENTIAL

        logger.info(f"  Battery: {optimizer.battery_params['capacity_kwh']} kWh")
        logger.info(f"  SOC Limits: {SOC_MIN*100:.0f}% - {SOC_MAX*100:.0f}%")
        logger.info(f"  Degradation segments: {len(optimizer.degradation_params.get('marginal_costs', []))}")

        # 3. Setup MPC simulator
        logger.info(f"[3/5] Setting up MPC simulator...")
        logger.info(f"  Horizon: {HORIZON_HOURS}h | Execution: {EXECUTION_HOURS}h")

        simulator = MPCSimulator(
            optimizer_model=optimizer,
            full_data=country_data_slice,
            horizon_hours=HORIZON_HOURS,
            execution_hours=EXECUTION_HOURS,
            c_rate=c_rate,
            validate_constraints=VALIDATE_CONSTRAINTS,
            solver_name=DEFAULT_SOLVER
        )

        # 4. Run MPC simulation
        logger.info(f"[4/5] Running MPC simulation...")
        logger.info(f"  Expected iterations: ~{len(country_data_slice) // (EXECUTION_HOURS * 4)}")

        if ENABLE_CHECKPOINTING:
            checkpoint_path = project_root / f"checkpoint_{country}_crate{c_rate}.pkl"
            logger.info(f"  Checkpointing enabled: every {CHECKPOINT_INTERVAL_MINUTES} min")

            mpc_results = simulator.run_full_simulation(
                initial_soc_fraction=INITIAL_SOC_FRACTION,
                checkpoint_interval_minutes=CHECKPOINT_INTERVAL_MINUTES,
                checkpoint_path=str(checkpoint_path)
            )

            # Clean up checkpoint file
            if checkpoint_path.exists():
                checkpoint_path.unlink()
        else:
            mpc_results = simulator.run_full_simulation(
                initial_soc_fraction=INITIAL_SOC_FRACTION
            )

        logger.info(f"  ✓ Simulation complete!")
        logger.info(f"  Profit: €{mpc_results['net_profit']:,.2f}")
        logger.info(f"  Revenue: €{mpc_results['total_revenue']:,.2f}")
        logger.info(f"  Degradation: €{mpc_results['total_degradation_cost']:,.2f}")

        # 5. Transform and save results
        logger.info(f"[5/5] Transforming and saving results...")

        # Transform to visualization format
        total_bids_df = mpc_results['total_bids_df']
        viz_df = transform_mpc_results_for_viz(
            total_bids_df,
            country_data_slice,
            battery_capacity_kwh=4472.0
        )

        # Extract iteration summary
        iteration_summary = extract_iteration_summary(mpc_results, include_soc_trajectory=True)

        # Build summary metrics
        summary_metrics = {
            'model': 'Model_III_MPC',
            'country': country,
            'test_duration_days': TEST_DURATION_DAYS,
            'alpha': ALPHA,
            'c_rate': c_rate,

            # MPC settings
            'mpc_horizon_hours': HORIZON_HOURS,
            'mpc_execution_hours': EXECUTION_HOURS,
            'mpc_initial_soc_fraction': INITIAL_SOC_FRACTION,
            'mpc_iterations': len(mpc_results['iteration_results']),

            # Financial results
            'total_profit_eur': mpc_results['net_profit'],
            'total_revenue_eur': mpc_results['total_revenue'],
            'total_degradation_eur': mpc_results['total_degradation_cost'],

            # Revenue breakdown
            'revenue_da_eur': mpc_results.get('da_revenue', 0),
            'revenue_afrr_energy_eur': mpc_results.get('afrr_e_revenue', 0),
            'revenue_as_capacity_eur': mpc_results.get('as_revenue', 0),

            # Degradation breakdown
            'degradation_cyclic_eur': mpc_results.get('cyclic_cost', 0),
            'degradation_calendar_eur': mpc_results.get('calendar_cost', 0),

            # SOC metrics
            'initial_soc_kwh': mpc_results.get('soc_trajectory', [INITIAL_SOC_FRACTION * 4472])[0],
            'final_soc_kwh': mpc_results.get('final_soc', INITIAL_SOC_FRACTION * 4472),

            # Timing
            'simulation_time_sec': time.time() - scenario_start,

            # Solver settings
            'solver': DEFAULT_SOLVER,
            'solver_time_limit_sec': DEFAULT_SOLVER_TIME_LIMIT,

            # Data source
            'data_source': 'preprocessed'
        }

        # Generate run name
        run_name = f"{country}_crate{c_rate}"

        # Save results
        output_directory = save_optimization_results(
            viz_df,
            summary_metrics,
            run_name,
            base_output_dir=str(project_root / BASE_OUTPUT_DIR)
        )

        # Save iteration summary
        iteration_csv_path = output_directory / "iteration_summary.csv"
        iteration_summary.to_csv(iteration_csv_path, index=False)

        logger.info(f"  ✓ Results saved to: {output_directory.name}")

        scenario_time = time.time() - scenario_start
        logger.info(f"✓ COMPLETED: {country} | C-rate: {c_rate} | Time: {scenario_time/60:.2f} min")

        return {
            'success': True,
            'country': country,
            'c_rate': c_rate,
            'profit': mpc_results['net_profit'],
            'revenue': mpc_results['total_revenue'],
            'degradation': mpc_results['total_degradation_cost'],
            'final_soc': mpc_results['final_soc'],
            'iterations': len(mpc_results['iteration_results']),
            'solve_time': scenario_time,
            'status': 'SUCCESS',
            'error': None,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    except Exception as e:
        scenario_time = time.time() - scenario_start
        error_msg = f"{type(e).__name__}: {str(e)}"
        logger.error(f"✗ FAILED: {country} | C-rate: {c_rate}")
        logger.error(f"  Error: {error_msg}")
        logger.error(f"  Traceback:\n{traceback.format_exc()}")

        return {
            'success': False,
            'country': country,
            'c_rate': c_rate,
            'profit': None,
            'revenue': None,
            'degradation': None,
            'final_soc': None,
            'iterations': None,
            'solve_time': scenario_time,
            'status': 'FAILED',
            'error': error_msg,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

# ================================================================================
# MAIN BATCH EXECUTION
# ================================================================================

def main():
    """Main batch execution function"""

    # Setup logging
    logger = setup_logging()

    logger.info("")
    logger.info("=" * 80)
    logger.info("BATCH EXECUTION: FINAL SUBMISSION RESULTS")
    logger.info("=" * 80)
    logger.info(f"Total scenarios: {len(SCENARIOS)}")
    logger.info(f"Test duration: {TEST_DURATION_DAYS} days")
    logger.info(f"Alpha: {ALPHA}")
    logger.info(f"MPC Settings: {HORIZON_HOURS}h horizon / {EXECUTION_HOURS}h execution")
    logger.info(f"Solver: {DEFAULT_SOLVER}")
    logger.info(f"Output directory: {BASE_OUTPUT_DIR}")
    logger.info("=" * 80)
    logger.info("")

    # Execute all scenarios
    batch_start = time.time()
    results_list = []

    for i, (country, c_rate) in enumerate(SCENARIOS, 1):
        logger.info(f"\n{'=' * 80}")
        logger.info(f"SCENARIO {i}/{len(SCENARIOS)}: {country} @ C-rate {c_rate}")
        logger.info(f"{'=' * 80}\n")

        result = run_scenario(country, c_rate, logger)
        results_list.append(result)

        # Brief summary
        if result['success']:
            logger.info(f"✓ Success | Profit: €{result['profit']:,.2f} | Time: {result['solve_time']/60:.1f} min")
        else:
            logger.info(f"✗ Failed | Error: {result['error']}")

    batch_time = time.time() - batch_start

    # Generate batch summary
    logger.info("\n" + "=" * 80)
    logger.info("BATCH SUMMARY")
    logger.info("=" * 80)

    summary_df = pd.DataFrame(results_list)
    summary_csv_path = project_root / BASE_OUTPUT_DIR / "batch_summary.csv"
    summary_df.to_csv(summary_csv_path, index=False)

    # Statistics
    n_success = summary_df['success'].sum()
    n_failed = len(summary_df) - n_success

    logger.info(f"Total scenarios: {len(SCENARIOS)}")
    logger.info(f"  Successful: {n_success}")
    logger.info(f"  Failed: {n_failed}")
    logger.info(f"Total time: {batch_time/60:.2f} min ({batch_time/3600:.2f} hours)")

    if n_success > 0:
        successful_results = summary_df[summary_df['success']]
        logger.info(f"\nFinancial Summary (Successful Runs):")
        logger.info(f"  Total Profit: €{successful_results['profit'].sum():,.2f}")
        logger.info(f"  Avg Profit: €{successful_results['profit'].mean():,.2f}")
        logger.info(f"  Profit Range: €{successful_results['profit'].min():,.2f} - €{successful_results['profit'].max():,.2f}")

    if n_failed > 0:
        logger.info(f"\nFailed Scenarios:")
        failed_results = summary_df[~summary_df['success']]
        for _, row in failed_results.iterrows():
            logger.info(f"  - {row['country']} @ C-rate {row['c_rate']}: {row['error']}")

    logger.info(f"\nBatch summary saved to: {summary_csv_path}")
    logger.info("=" * 80)
    logger.info("BATCH EXECUTION COMPLETE")
    logger.info("=" * 80)

    return summary_df

# ================================================================================
# ENTRY POINT
# ================================================================================

if __name__ == "__main__":
    summary = main()
    print(f"\n✓ Batch execution complete! Check {BASE_OUTPUT_DIR}/batch_summary.csv for results.")

# %%
