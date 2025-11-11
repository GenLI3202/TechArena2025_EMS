#!/usr/bin/env python3
"""
Test script to verify if Cst-6 (Energy Reserve) constraints are broken in Model II/III.
If the bug exists, FCR should have zero "energy cost" in the optimizer's view.
"""

import sys
from pathlib import Path
import pyomo.environ as pyo
import logging

sys.path.append(str(Path(__file__).parent / 'py_script'))
from core.optimizer import BESSOptimizerModelIII

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def test_cst6_integrity():
    """Test if Cst-6 constraints properly reference the e_soc Expression."""

    # Initialize Model III
    optimizer = BESSOptimizerModelIII(alpha=1.5)

    # Load test data (just need structure)
    data_file = "data/phase_1_data_TechArena2025_data_tidy.jsonl"
    full_data = optimizer.load_and_preprocess_data(data_file)
    country_data = optimizer.extract_country_data(full_data, "CH")
    test_data = country_data.iloc[:4].copy().reset_index(drop=True)  # Just 1 hour

    # Build model
    model = optimizer.build_optimization_model(test_data, c_rate=0.5)

    logger.info("\n" + "="*60)
    logger.info("TESTING CST-6 INTEGRITY IN MODEL III")
    logger.info("="*60)

    # Check 1: Does e_soc exist?
    if hasattr(model, 'e_soc'):
        logger.info("✓ model.e_soc exists")
        logger.info(f"  Type: {type(model.e_soc)}")
        logger.info(f"  Is Variable? {isinstance(model.e_soc, pyo.Var)}")
        logger.info(f"  Is Expression? {isinstance(model.e_soc, pyo.Expression)}")
    else:
        logger.error("✗ model.e_soc does NOT exist!")

    # Check 2: Do energy reserve constraints exist?
    if hasattr(model, 'energy_reserve_pos'):
        logger.info("✓ energy_reserve_pos constraint exists")

        # Try to evaluate the constraint for t=0
        try:
            # Get the constraint expression
            t = 0
            block = int(pyo.value(model.block_map[t]))

            # Try to access e_soc in the constraint
            constraint = model.energy_reserve_pos[t]
            logger.info(f"  Constraint body type: {type(constraint.body)}")

            # Check if the constraint can "see" the e_soc value
            if isinstance(model.e_soc, pyo.Expression):
                # For Expression, we need segment values
                logger.info("  e_soc is an Expression (sum of segments)")

                # Check if segments exist
                if hasattr(model, 'e_soc_j'):
                    logger.info(f"  ✓ Segments (e_soc_j) exist")

                    # Initialize a test value
                    for j in model.J:
                        model.e_soc_j[t, j].set_value(100.0)  # Test value

                    # Now try to evaluate e_soc Expression
                    try:
                        soc_value = pyo.value(model.e_soc[t])
                        logger.info(f"  ✓ e_soc[{t}] evaluates to: {soc_value}")
                    except Exception as e:
                        logger.error(f"  ✗ Cannot evaluate e_soc[{t}]: {e}")
                else:
                    logger.error("  ✗ Segments (e_soc_j) do NOT exist!")

            # Check if the constraint references the correct e_soc
            constraint_str = str(constraint.body)
            logger.info(f"  Constraint body: {constraint_str[:100]}...")

            # Look for references to e_soc in the constraint
            if 'e_soc' in constraint_str:
                logger.info("  ✓ Constraint references 'e_soc'")
            else:
                logger.warning("  ⚠ Constraint may not reference e_soc properly")

        except Exception as e:
            logger.error(f"  ✗ Error evaluating constraint: {e}")
    else:
        logger.error("✗ energy_reserve_pos constraint does NOT exist!")

    # Check 3: Test if FCR can be bid without energy cost
    logger.info("\n" + "-"*60)
    logger.info("TESTING FCR BIDDING BEHAVIOR:")

    # Set FCR to maximum
    for b in model.B:
        model.c_fcr[b].set_value(model.P_max_config / 1000)  # Max MW (P_max_config is a parameter)
        model.y_fcr[b].set_value(1)

    # Check if this violates energy reserve
    t = 0
    block = 0
    required_energy_up = (1000 * model.c_fcr[block].value) * model.tau / model.eta_dis
    required_energy_down = (1000 * model.c_fcr[block].value) * model.tau * model.eta_ch

    logger.info(f"FCR bid: {model.c_fcr[block].value:.3f} MW")
    logger.info(f"Required energy for upward: {required_energy_up:.1f} kWh")
    logger.info(f"Required energy for downward: {required_energy_down:.1f} kWh")

    # Check if constraint is satisfied
    try:
        # Initialize SOC to 50%
        for j in model.J:
            for t in model.T:
                if j == 5:  # Middle segment
                    model.e_soc_j[t, j].set_value(model.E_seg)
                else:
                    model.e_soc_j[t, j].set_value(0)

        soc_value = pyo.value(model.e_soc[0])
        available_up = soc_value - model.SOC_min * model.E_nom
        available_down = model.SOC_max * model.E_nom - soc_value

        logger.info(f"SOC at t=0: {soc_value:.1f} kWh")
        logger.info(f"Available for upward: {available_up:.1f} kWh")
        logger.info(f"Available for downward: {available_down:.1f} kWh")

        if required_energy_up <= available_up:
            logger.info("✓ Upward reserve constraint satisfied")
        else:
            logger.warning(f"✗ Upward reserve violated by {required_energy_up - available_up:.1f} kWh")

        if required_energy_down <= available_down:
            logger.info("✓ Downward reserve constraint satisfied")
        else:
            logger.warning(f"✗ Downward reserve violated by {required_energy_down - available_down:.1f} kWh")

    except Exception as e:
        logger.error(f"✗ Cannot check constraint satisfaction: {e}")

    logger.info("\n" + "="*60)
    logger.info("DIAGNOSIS:")
    logger.info("="*60)

    # Final diagnosis
    if isinstance(model.e_soc, pyo.Expression):
        logger.warning("⚠ POTENTIAL BUG CONFIRMED:")
        logger.warning("  - e_soc is an Expression (not Variable)")
        logger.warning("  - Cst-6 constraints inherited from Model I may be broken")
        logger.warning("  - They likely reference the deleted Variable, not the Expression")
        logger.warning("  - This makes FCR appear to have zero energy cost!")
    else:
        logger.info("✓ No obvious bug detected (but needs deeper investigation)")

    return model

if __name__ == "__main__":
    model = test_cst6_integrity()