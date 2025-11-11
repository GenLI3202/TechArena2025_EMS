"""
Debug 24h Optimization - Verify Decision Variable Retrieval
============================================================

Run a single 24h optimization and carefully examine:
1. Raw solver output (Pyomo variable values)
2. Decision variable extraction (what goes into solution dict)
3. Block mapping (time → block index for AS variables)
4. Constraint binding analysis

Usage:
    python debug_24h_decision_vars.py
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import pyomo.environ as pyo
from pyomo.opt import SolverStatus, TerminationCondition
import json

sys.path.append(str(Path(__file__).parent / 'py_script'))

from core.optimizer import BESSOptimizerModelIII
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def inspect_pyomo_variables(model, solution: dict):
    """Inspect raw Pyomo model variables vs extracted solution."""

    logger.info("=" * 80)
    logger.info("PYOMO VARIABLE INSPECTION")
    logger.info("=" * 80)

    # Check time-indexed variables
    logger.info("\n1. TIME-INDEXED VARIABLES (first 10 intervals):")
    logger.info("-" * 80)

    for t in range(min(10, len(model.T))):
        logger.info(f"\nTime step t={t} (hour {t*0.25:.2f}):")

        # Power variables
        p_ch = pyo.value(model.p_ch[t])
        p_dis = pyo.value(model.p_dis[t])
        logger.info(f"  p_ch[{t}] = {p_ch:.4f} kW  (extracted: {solution.get('p_ch', {}).get(t, 'MISSING')})")
        logger.info(f"  p_dis[{t}] = {p_dis:.4f} kW  (extracted: {solution.get('p_dis', {}).get(t, 'MISSING')})")

        # Binary variables
        y_total_ch = pyo.value(model.y_total_ch[t])
        y_total_dis = pyo.value(model.y_total_dis[t])
        logger.info(f"  y_total_ch[{t}] = {y_total_ch:.6f}  (extracted: {solution.get('y_total_ch', {}).get(t, 'MISSING')})")
        logger.info(f"  y_total_dis[{t}] = {y_total_dis:.6f}  (extracted: {solution.get('y_total_dis', {}).get(t, 'MISSING')})")

    # Check block-indexed variables
    logger.info("\n2. BLOCK-INDEXED VARIABLES (AS markets):")
    logger.info("-" * 80)

    num_blocks = len(model.B)
    logger.info(f"Total blocks: {num_blocks}")

    for b in range(min(6, num_blocks)):  # First 6 blocks (24 hours = 6 blocks of 4h each)
        logger.info(f"\nBlock b={b}:")

        # Capacity bids
        c_fcr = pyo.value(model.c_fcr[b])
        c_afrr_pos = pyo.value(model.c_afrr_pos[b])
        c_afrr_neg = pyo.value(model.c_afrr_neg[b])

        logger.info(f"  c_fcr[{b}] = {c_fcr:.4f} MW  (extracted: {solution.get('c_fcr', {}).get(b, 'MISSING')})")
        logger.info(f"  c_afrr_pos[{b}] = {c_afrr_pos:.4f} MW  (extracted: {solution.get('c_afrr_pos', {}).get(b, 'MISSING')})")
        logger.info(f"  c_afrr_neg[{b}] = {c_afrr_neg:.4f} MW  (extracted: {solution.get('c_afrr_neg', {}).get(b, 'MISSING')})")

        # Binary decisions
        y_fcr = pyo.value(model.y_fcr[b])
        y_afrr_pos = pyo.value(model.y_afrr_pos[b])
        y_afrr_neg = pyo.value(model.y_afrr_neg[b])

        logger.info(f"  y_fcr[{b}] = {y_fcr:.6f}  (extracted: {solution.get('y_fcr', {}).get(b, 'MISSING')})")
        logger.info(f"  y_afrr_pos[{b}] = {y_afrr_pos:.6f}  (extracted: {solution.get('y_afrr_pos', {}).get(b, 'MISSING')})")
        logger.info(f"  y_afrr_neg[{b}] = {y_afrr_neg:.6f}  (extracted: {solution.get('y_afrr_neg', {}).get(b, 'MISSING')})")

    # Check block mapping
    logger.info("\n3. BLOCK MAPPING (time → block):")
    logger.info("-" * 80)

    block_map = solution.get('block_map', {})
    logger.info(f"Block map entries: {len(block_map)}")

    # Show first 20 time steps
    logger.info("First 20 time steps:")
    for t in range(min(20, len(model.T))):
        block = block_map.get(t, 'MISSING')
        logger.info(f"  t={t:3d} (hour {t*0.25:5.2f}) → block {block}")

    # Verify block consistency
    logger.info("\nBlock mapping verification:")
    blocks_seen = set()
    for t in range(len(model.T)):
        b = block_map.get(t, -1)
        if b not in blocks_seen:
            logger.info(f"  Block {b} starts at t={t} (hour {t*0.25:.2f})")
            blocks_seen.add(b)

    # Check aFRR energy variables
    logger.info("\n4. aFRR ENERGY VARIABLES (first 10 intervals):")
    logger.info("-" * 80)

    for t in range(min(10, len(model.T))):
        p_afrr_pos_e = pyo.value(model.p_afrr_pos_e[t])
        p_afrr_neg_e = pyo.value(model.p_afrr_neg_e[t])

        logger.info(f"t={t}: p_afrr_pos_e={p_afrr_pos_e:.4f} kW, p_afrr_neg_e={p_afrr_neg_e:.4f} kW")


def analyze_decision_variable_patterns(solution: dict, test_data: pd.DataFrame):
    """Analyze patterns in decision variables."""

    logger.info("\n" + "=" * 80)
    logger.info("DECISION VARIABLE PATTERN ANALYSIS")
    logger.info("=" * 80)

    # Extract variables
    c_fcr = solution.get('c_fcr', {})
    c_afrr_pos = solution.get('c_afrr_pos', {})
    c_afrr_neg = solution.get('c_afrr_neg', {})

    y_fcr = solution.get('y_fcr', {})
    y_afrr_pos = solution.get('y_afrr_pos', {})
    y_afrr_neg = solution.get('y_afrr_neg', {})

    p_ch = solution.get('p_ch', {})
    p_dis = solution.get('p_dis', {})

    logger.info("\n1. AS CAPACITY BIDS (block-indexed):")
    logger.info("-" * 80)

    logger.info(f"c_fcr: {len(c_fcr)} values")
    logger.info(f"  Unique values: {len(set(c_fcr.values()))}")
    logger.info(f"  Min: {min(c_fcr.values()):.4f} MW, Max: {max(c_fcr.values()):.4f} MW")
    logger.info(f"  Non-zero blocks: {sum(1 for v in c_fcr.values() if v > 1e-6)}/{len(c_fcr)}")

    logger.info(f"\nc_afrr_pos: {len(c_afrr_pos)} values")
    logger.info(f"  Unique values: {len(set(c_afrr_pos.values()))}")
    logger.info(f"  Min: {min(c_afrr_pos.values()):.4f} MW, Max: {max(c_afrr_pos.values()):.4f} MW")
    logger.info(f"  Non-zero blocks: {sum(1 for v in c_afrr_pos.values() if v > 1e-6)}/{len(c_afrr_pos)}")

    logger.info(f"\nc_afrr_neg: {len(c_afrr_neg)} values")
    logger.info(f"  Unique values: {len(set(c_afrr_neg.values()))}")
    logger.info(f"  Min: {min(c_afrr_neg.values()):.4f} MW, Max: {max(c_afrr_neg.values()):.4f} MW")
    logger.info(f"  Non-zero blocks: {sum(1 for v in c_afrr_neg.values() if v > 1e-6)}/{len(c_afrr_neg)}")

    logger.info("\n2. AS BINARY DECISIONS (block-indexed):")
    logger.info("-" * 80)

    logger.info(f"y_fcr: Active blocks: {sum(1 for v in y_fcr.values() if v > 0.5)}/{len(y_fcr)}")
    logger.info(f"y_afrr_pos: Active blocks: {sum(1 for v in y_afrr_pos.values() if v > 0.5)}/{len(y_afrr_pos)}")
    logger.info(f"y_afrr_neg: Active blocks: {sum(1 for v in y_afrr_neg.values() if v > 0.5)}/{len(y_afrr_neg)}")

    # Check if binaries are truly binary
    logger.info("\n3. BINARY VARIABLE VERIFICATION:")
    logger.info("-" * 80)

    def check_binary(var_dict, name):
        non_binary = [v for v in var_dict.values() if not (abs(v) < 1e-6 or abs(v - 1.0) < 1e-6)]
        if non_binary:
            logger.warning(f"  {name}: {len(non_binary)} non-binary values! Range: {min(non_binary):.6f} - {max(non_binary):.6f}")
        else:
            logger.info(f"  {name}: All binary (0 or 1) ✓")

    check_binary(y_fcr, "y_fcr")
    check_binary(y_afrr_pos, "y_afrr_pos")
    check_binary(y_afrr_neg, "y_afrr_neg")

    logger.info("\n4. POWER VARIABLES (time-indexed):")
    logger.info("-" * 80)

    logger.info(f"p_ch: {len(p_ch)} values")
    logger.info(f"  Non-zero intervals: {sum(1 for v in p_ch.values() if v > 1e-3)}/{len(p_ch)}")
    logger.info(f"  Max: {max(p_ch.values()):.2f} kW")

    logger.info(f"\np_dis: {len(p_dis)} values")
    logger.info(f"  Non-zero intervals: {sum(1 for v in p_dis.values() if v > 1e-3)}/{len(p_dis)}")
    logger.info(f"  Max: {max(p_dis.values()):.2f} kW")

    # Check if there's ANY variation
    logger.info("\n5. VARIATION ANALYSIS:")
    logger.info("-" * 80)

    c_fcr_unique = len(set(c_fcr.values()))
    if c_fcr_unique == 1:
        logger.warning(f"  WARNING: c_fcr has only 1 unique value: {list(c_fcr.values())[0]:.4f} MW")
        logger.warning("  Battery is reserving CONSTANT FCR capacity across ALL blocks!")

    # Check price variation to see if optimization should vary
    logger.info("\n6. PRICE VARIATION (input data check):")
    logger.info("-" * 80)

    logger.info(f"DA prices: {test_data['price_day_ahead'].min():.2f} - {test_data['price_day_ahead'].max():.2f} EUR/MWh (spread: {test_data['price_day_ahead'].max() - test_data['price_day_ahead'].min():.2f})")
    logger.info(f"FCR prices: {test_data['price_fcr'].min():.2f} - {test_data['price_fcr'].max():.2f} EUR/MW (spread: {test_data['price_fcr'].max() - test_data['price_fcr'].min():.2f})")
    logger.info(f"aFRR+ prices: {test_data['price_afrr_pos'].min():.2f} - {test_data['price_afrr_pos'].max():.2f} EUR/MW (spread: {test_data['price_afrr_pos'].max() - test_data['price_afrr_pos'].min():.2f})")
    logger.info(f"aFRR- prices: {test_data['price_afrr_neg'].min():.2f} - {test_data['price_afrr_neg'].max():.2f} EUR/MW (spread: {test_data['price_afrr_neg'].max() - test_data['price_afrr_neg'].min():.2f})")


def main():
    """Run focused 24h debug analysis."""

    logger.info("=" * 80)
    logger.info("24H OPTIMIZATION DEBUG - DECISION VARIABLE RETRIEVAL CHECK")
    logger.info("=" * 80)

    # Load data
    data_file = "data/phase_1_data_TechArena2025_data_tidy.jsonl"
    country = "CH"
    target_date = "2024-07-22"
    horizon_hours = 24

    logger.info(f"\nConfiguration:")
    logger.info(f"  Country: {country}")
    logger.info(f"  Date: {target_date}")
    logger.info(f"  Horizon: {horizon_hours}h")
    logger.info(f"  Alpha: 1.5")
    logger.info(f"  Cst-8: ENABLED")

    # Initialize optimizer
    optimizer = BESSOptimizerModelIII(alpha=1.5, use_afrr_ev_weighting=True)

    # Load and extract data
    logger.info("\n" + "=" * 80)
    logger.info("DATA LOADING")
    logger.info("=" * 80)

    full_data = optimizer.load_and_preprocess_data(data_file)
    country_data = optimizer.extract_country_data(full_data, country)

    # Extract date window
    target_dt = pd.to_datetime(target_date)
    intervals_needed = int(horizon_hours * 4)

    if 'datetime' in country_data.columns:
        time_diffs = abs(country_data['datetime'] - target_dt)
        start_idx = time_diffs.argmin()
        actual_start = country_data.iloc[start_idx]['datetime']
        logger.info(f"Extracted {intervals_needed} intervals starting from {actual_start}")
    else:
        logger.warning("No datetime column, using first intervals")
        start_idx = 0

    test_data = country_data.iloc[start_idx:start_idx + intervals_needed].copy().reset_index(drop=True)

    logger.info(f"Test data shape: {test_data.shape}")
    logger.info(f"Columns: {list(test_data.columns)}")

    # Build model
    logger.info("\n" + "=" * 80)
    logger.info("MODEL BUILDING")
    logger.info("=" * 80)

    model = optimizer.build_optimization_model(test_data, c_rate=0.5)

    logger.info(f"Model variables: {model.nvariables()}")
    logger.info(f"Model constraints: {model.nconstraints()}")
    logger.info(f"Time steps (T): {len(model.T)}")
    logger.info(f"Blocks (B): {len(model.B)}")

    # Solve
    logger.info("\n" + "=" * 80)
    logger.info("SOLVING")
    logger.info("=" * 80)

    solution = optimizer.solve_model(model)

    logger.info(f"Status: {solution.get('status')}")
    logger.info(f"Objective: {solution.get('objective_value', 0):,.2f} EUR")
    logger.info(f"Solve time: {solution.get('solve_time', 0):.2f}s")

    if solution.get('status') not in ['optimal', 'feasible']:
        logger.error("Optimization failed, cannot proceed with analysis")
        return

    # Detailed inspection
    inspect_pyomo_variables(model, solution)
    analyze_decision_variable_patterns(solution, test_data)

    # Save debug output
    output_dir = Path("results/model_iii_debug")
    output_dir.mkdir(exist_ok=True, parents=True)

    debug_output = {
        'config': {
            'country': country,
            'date': target_date,
            'horizon_hours': horizon_hours,
            'alpha': 1.5,
            'intervals': intervals_needed
        },
        'model_info': {
            'num_variables': model.nvariables(),
            'num_constraints': model.nconstraints(),
            'num_time_steps': len(model.T),
            'num_blocks': len(model.B)
        },
        'solution_status': {
            'status': solution.get('status'),
            'objective_value': solution.get('objective_value'),
            'solve_time': solution.get('solve_time')
        },
        'decision_var_summary': {
            'c_fcr_unique_values': len(set(solution.get('c_fcr', {}).values())),
            'c_afrr_pos_unique_values': len(set(solution.get('c_afrr_pos', {}).values())),
            'c_afrr_neg_unique_values': len(set(solution.get('c_afrr_neg', {}).values())),
            'fcr_active_blocks': sum(1 for v in solution.get('y_fcr', {}).values() if v > 0.5),
            'afrr_pos_active_blocks': sum(1 for v in solution.get('y_afrr_pos', {}).values() if v > 0.5),
            'afrr_neg_active_blocks': sum(1 for v in solution.get('y_afrr_neg', {}).values() if v > 0.5),
            'charging_intervals': sum(1 for v in solution.get('p_ch', {}).values() if v > 1e-3),
            'discharging_intervals': sum(1 for v in solution.get('p_dis', {}).values() if v > 1e-3),
        }
    }

    output_file = output_dir / "debug_24h_decision_vars.json"
    with open(output_file, 'w') as f:
        json.dump(debug_output, f, indent=2)

    logger.info(f"\nDebug output saved to: {output_file}")

    logger.info("\n" + "=" * 80)
    logger.info("DEBUG ANALYSIS COMPLETE")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
