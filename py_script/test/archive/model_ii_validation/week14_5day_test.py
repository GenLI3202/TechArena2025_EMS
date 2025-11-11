"""
Week 14 (5-Day) Model (ii) Validation Test
Test period: April 1-5, 2024 (Mon-Fri)
Validates Model (ii) with only Cst-3 active (Cst-8 and Cst-9 are deactivated)
Then checks for violations of Cst-8 and Cst-9 in the solution
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import json
import matplotlib.pyplot as plt

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from py_script.core.optimizer import BESSOptimizerModelII
from validate_with_user_script import validate_solution

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test configuration
TEST_START_DATE = '2024-04-01'  # Week 14 - Monday
NUM_DAYS = 5  # Mon-Fri
COUNTRY = 'HU'
SCENARIO = {'c_rate': 0.5, 'alpha': 1.0, 'name': 'baseline'}
SOLVER_TIMEOUT = 1800  # 30 minutes in seconds (increased from 15)

# Battery parameters
BATTERY_PARAMS = {
    'E_nom': 4472,  # kWh
    'eta_ch': 0.95,
    'eta_dis': 0.95,
    'dt': 0.25,  # hours
}


def extract_timespan_data(full_data, start_date_str, num_days):
    """Extract specified number of days starting from start_date"""
    start_date = pd.to_datetime(start_date_str)
    end_date = start_date + timedelta(days=num_days)
    mask = (full_data.index >= start_date) & (full_data.index < end_date)
    return full_data[mask]


# Validation is now done using validate_with_user_script.py


def generate_violation_table(violations, num_intervals, output_dir):
    """Generate a violation summary table similar to validation_summary_table.png"""

    # Prepare data
    constraints = [
        'Cst-3: Simultaneous Ops',
        'Cst-8: Cross-Market (Dis+ChargeAS)',
        'Cst-8: Cross-Market (Charge+DisAS)',
        'Cst-8: Cross-Market (aFRR Pos+Neg)',
        'Cst-9: MinBid p_ch',
        'Cst-9: MinBid p_dis',
        'Cst-9: MinBid p_afrr_pos_e',
        'Cst-9: MinBid p_afrr_neg_e',
        'TOTAL',
    ]

    violation_counts = [
        violations['Cst_3_Simultaneous_Ops'],
        violations['Cst_8_Cross_Market_Discharge_vs_ChargeAS'],
        violations['Cst_8_Cross_Market_Charge_vs_DischargeAS'],
        violations['Cst_8_Cross_Market_aFRR_Pos_vs_Neg'],
        violations['Cst_9_MinBid_p_ch'],
        violations['Cst_9_MinBid_p_dis'],
        violations['Cst_9_MinBid_p_afrr_pos_e'],
        violations['Cst_9_MinBid_p_afrr_neg_e'],
        sum([v for v in violations.values()])
    ]

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.axis('tight')
    ax.axis('off')

    # Create table data
    cell_text = []
    for constraint, count in zip(constraints, violation_counts):
        if constraint == 'TOTAL':
            cell_text.append([constraint, f"{count:,}"])
        else:
            cell_text.append([constraint, f"{count:,} Violations"])

    # Create table
    table = ax.table(cellText=cell_text,
                    colLabels=['Constraint We Commented Out', f'Week 14 (5 days, {num_intervals} intervals)'],
                    cellLoc='left',
                    loc='center',
                    colWidths=[0.55, 0.45])

    # Style the table
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2.5)

    # Color cells based on violations
    for i in range(1, len(cell_text) + 1):
        for j in range(2):
            cell = table[(i, j)]

            if j == 0:  # Constraint name column
                cell.set_facecolor('#f0f0f0')
                cell.set_text_props(weight='bold')
            else:  # Violation column
                # Get violation count
                val_str = cell_text[i-1][j]
                if 'Violations' in val_str:
                    val = int(val_str.split()[0].replace(',', ''))
                else:
                    val = int(val_str.replace(',', ''))

                # Color based on severity
                if val == 0:
                    cell.set_facecolor('#d4edda')  # Green for no violations
                elif val < 50:
                    cell.set_facecolor('#fff3cd')  # Yellow for minor violations
                elif val < 500:
                    cell.set_facecolor('#f8d7da')  # Light red for moderate violations
                else:
                    cell.set_facecolor('#f5c6cb')  # Red for major violations

    # Style header row
    for j in range(2):
        cell = table[(0, j)]
        cell.set_facecolor('#4a6fa5')
        cell.set_text_props(weight='bold', color='white')

    # Style total row
    for j in range(2):
        cell = table[(len(cell_text), j)]
        cell.set_facecolor('#e9ecef')
        cell.set_text_props(weight='bold', size=11)

    plt.title('Constraint Violation Summary - Model (ii) Week 14 (5-Day) Validation',
              fontsize=14, fontweight='bold', pad=20)

    # Save figure
    output_path = output_dir / 'validation_summary_table.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    logger.info(f"Violation table saved to: {output_path}")
    plt.close()

    return output_path


def main():
    """Main test execution"""
    logger.info("="*80)
    logger.info("Model (ii) Week 14 (5-Day) Validation Test")
    logger.info(f"Period: {TEST_START_DATE} to {pd.to_datetime(TEST_START_DATE) + timedelta(days=NUM_DAYS)}")
    logger.info(f"Country: {COUNTRY}, Scenario: {SCENARIO['name']}")
    logger.info(f"Solver timeout: {SOLVER_TIMEOUT} seconds (15 minutes)")
    logger.info("="*80)

    # Set up output directory
    output_dir = project_root / "results" / "model_ii_validation" / "week14_5day_test"
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {output_dir}")

    try:
        # Initialize optimizer
        logger.info("\nInitializing BESSOptimizerModelII...")
        optimizer = BESSOptimizerModelII(alpha=SCENARIO['alpha'])

        # Set solver timeout
        optimizer.market_params['solver_time_limit'] = SOLVER_TIMEOUT
        logger.info(f"Set solver time limit to {SOLVER_TIMEOUT} seconds (15 minutes)")

        # Load full data
        logger.info("Loading data...")
        data_path = project_root / "data" / "TechArena2025_data_tidy.jsonl"
        data = optimizer.load_and_preprocess_data(str(data_path))

        # Extract week 14 (5 days)
        span_data = extract_timespan_data(data, TEST_START_DATE, NUM_DAYS)
        logger.info(f"Extracted {len(span_data)} intervals ({len(span_data)/96:.1f} days)")
        logger.info(f"Date range: {span_data.index.min()} to {span_data.index.max()}")

        # Extract country data
        country_data = optimizer.extract_country_data(span_data, COUNTRY)
        logger.info(f"Country data shape: {country_data.shape}")

        # Build model
        logger.info("\nBuilding optimization model...")
        build_start = datetime.now()
        model = optimizer.build_optimization_model(
            country_data,
            c_rate=SCENARIO['c_rate']
        )
        build_time = (datetime.now() - build_start).total_seconds()

        logger.info(f"Model size: {model.nvariables()} variables, {model.nconstraints()} constraints")
        logger.info(f"Build time: {build_time:.2f} seconds")

        # Solve with timeout and preferred solver
        logger.info(f"\nSolving with {SOLVER_TIMEOUT}s timeout...")
        logger.info("Attempting Gurobi first, will fall back to CPLEX if unavailable...")

        solve_start = datetime.now()

        # Try Gurobi first
        try:
            import gurobipy
            logger.info("Gurobi is available - using Gurobi solver")
            solution = optimizer.solve_model(model, solver_name='gurobi')
        except ImportError:
            logger.info("Gurobi not available - trying CPLEX...")
            try:
                solution = optimizer.solve_model(model, solver_name='cplex')
            except Exception as e:
                logger.warning(f"CPLEX not available: {e}")
                logger.info("Falling back to default solver (HiGHS)")
                solution = optimizer.solve_model(model, solver_name='highs')

        logger.info(f"\nSolution status: {solution['status']}")

        # Check if solution failed
        if solution['status'] == 'failed':
            logger.error(f"Solver failed to find a solution within {SOLVER_TIMEOUT}s time limit")
            logger.error("Try increasing SOLVER_TIMEOUT or using a more powerful solver")
            return None

        logger.info(f"Objective value: {solution['objective_value']:.2f} EUR")
        logger.info(f"Solve time: {solution['solve_time']:.2f} seconds")

        # Save decision variables first (needed for validation)
        vars_file = output_dir / "decision_variables.json"
        with open(vars_file, 'w', encoding='utf-8') as f:
            decision_vars = {
                'num_days': NUM_DAYS,
                'p_total_ch': solution.get('p_total_ch', {}),
                'p_total_dis': solution.get('p_total_dis', {}),
                'p_ch': solution.get('p_ch', {}),
                'p_dis': solution.get('p_dis', {}),
                'p_afrr_pos_e': solution.get('p_afrr_pos_e', {}),
                'p_afrr_neg_e': solution.get('p_afrr_neg_e', {}),
                'p_afrr_pos': solution.get('p_afrr_pos', {}),
                'p_afrr_neg': solution.get('p_afrr_neg', {}),
                'c_fcr': solution.get('c_fcr', {}),
                'c_afrr_pos': solution.get('c_afrr_pos', {}),
                'c_afrr_neg': solution.get('c_afrr_neg', {}),
                'e_soc': solution.get('e_soc', {}),
            }
            json.dump(decision_vars, f, indent=2)
        logger.info(f"Decision variables saved to: {vars_file}")

        # Validate constraints using user's preferred validation script
        logger.info("\n" + "="*80)
        logger.info("CONSTRAINT VALIDATION")
        logger.info("="*80)
        logger.info("Using validate_with_user_script.py to check constraints...")
        logger.info("Checking Cst-3, Cst-8 (cross-market exclusivity) and Cst-9 (minimum bid)...")
        logger.info("Note: Cst-8 and Cst-9 are currently COMMENTED OUT in the model")

        violations = validate_solution(str(vars_file))

        if violations is None:
            logger.error("Validation failed!")
            return None

        num_intervals = NUM_DAYS * 96

        # Print violations summary
        logger.info("\nViolation Summary:")
        logger.info("-" * 80)
        logger.info(f"{'Constraint':<50} {'Violations':>15}")
        logger.info("-" * 80)
        logger.info(f"{'Cst-3: Simultaneous Ops':<50} {violations['Cst_3_Simultaneous_Ops']:>15,}")
        logger.info(f"{'Cst-8: Cross-Market (Dis+ChargeAS)':<50} {violations['Cst_8_Cross_Market_Discharge_vs_ChargeAS']:>15,}")
        logger.info(f"{'Cst-8: Cross-Market (Charge+DisAS)':<50} {violations['Cst_8_Cross_Market_Charge_vs_DischargeAS']:>15,}")
        logger.info(f"{'Cst-8: Cross-Market (aFRR Pos+Neg)':<50} {violations['Cst_8_Cross_Market_aFRR_Pos_vs_Neg']:>15,}")
        logger.info(f"{'Cst-9: MinBid p_ch':<50} {violations['Cst_9_MinBid_p_ch']:>15,}")
        logger.info(f"{'Cst-9: MinBid p_dis':<50} {violations['Cst_9_MinBid_p_dis']:>15,}")
        logger.info(f"{'Cst-9: MinBid p_afrr_pos_e':<50} {violations['Cst_9_MinBid_p_afrr_pos_e']:>15,}")
        logger.info(f"{'Cst-9: MinBid p_afrr_neg_e':<50} {violations['Cst_9_MinBid_p_afrr_neg_e']:>15,}")
        logger.info("-" * 80)
        total_violations = sum([v for v in violations.values()])
        logger.info(f"{'TOTAL':<50} {total_violations:>15,}")
        logger.info("=" * 80)

        # Generate violation table
        logger.info("\nGenerating violation summary table...")
        table_path = generate_violation_table(violations, num_intervals, output_dir)

        # Save detailed results
        result = {
            'test_name': 'Week14_5day_test',
            'period': {
                'start_date': TEST_START_DATE,
                'end_date': (pd.to_datetime(TEST_START_DATE) + timedelta(days=NUM_DAYS)).strftime('%Y-%m-%d'),
                'num_days': NUM_DAYS,
                'num_intervals': num_intervals
            },
            'country': COUNTRY,
            'scenario': SCENARIO,
            'solver': {
                'timeout_sec': SOLVER_TIMEOUT,
                'status': solution['status'],
                'solve_time_sec': solution['solve_time'],
                'objective_value': solution['objective_value']
            },
            'model': {
                'num_variables': model.nvariables(),
                'num_constraints': model.nconstraints(),
                'build_time_sec': build_time
            },
            'violations': violations,
            'total_violations': total_violations,
            'timestamp': datetime.now().isoformat()
        }

        results_file = output_dir / "test_results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)
        logger.info(f"Detailed results saved to: {results_file}")

        # Print summary
        logger.info("\n" + "="*80)
        logger.info("TEST COMPLETE!")
        logger.info("="*80)
        logger.info(f"Status: {solution['status']}")
        logger.info(f"Solve time: {solution['solve_time']:.2f} seconds (limit: {SOLVER_TIMEOUT}s)")
        logger.info(f"Total violations: {total_violations:,}")
        logger.info(f"\nOutput files:")
        logger.info(f"  - Results: {results_file}")
        logger.info(f"  - Variables: {vars_file}")
        logger.info(f"  - Violation table: {table_path}")
        logger.info("="*80)

        return result

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return None


if __name__ == "__main__":
    main()
