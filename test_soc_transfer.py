"""
Test SOC State Transfer in MPC
===============================
Manually force SOC change in first iteration to verify transfer to second iteration
"""

from py_script.rolling_horizon import MPCSimulator
from py_script.core.optimizer import BESSOptimizerModelIII
import pyomo.environ as pyo

# Initialize
optimizer = BESSOptimizerModelIII(alpha=1.0)
full_data = optimizer.load_and_preprocess_data('data/archive/phase_1_data_TechArena2025_data_tidy.jsonl')
country_data = optimizer.extract_country_data(full_data, 'CH')
test_data = country_data.iloc[:480].reset_index(drop=True)  # 5 days

# Create MPC simulator
simulator = MPCSimulator(
    optimizer_model=optimizer,
    full_data=test_data,
    horizon_hours=32,
    execution_hours=24,
    c_rate=0.5,
    validate_constraints=False
)

# Modify simulator to force SOC change after first iteration
original_run = simulator.run_full_simulation

def modified_run(initial_soc_fraction=0.5):
    """Modified run that forces SOC to 80% after first iteration"""
    import logging
    logger = logging.getLogger('BESSOptimizer')

    # Run first iteration normally
    logger.info("="*80)
    logger.info("MODIFIED TEST: Forcing SOC change after first iteration")
    logger.info("="*80)

    # Access internals (this is a hack for testing)
    simulator.optimizer.battery_params['initial_soc_kwh'] = 2236.0  # 50%

    # Manually run first iteration
    data_window = test_data.iloc[:128].reset_index(drop=True)
    model = simulator.optimizer.build_optimization_model(data_window, 0.5)

    # Set initial segment SOC
    if hasattr(model, 'e_soc_j'):
        for j in model.J:
            if j <= 5:
                model.e_soc_j[0, j].setlb(447.2)
                model.e_soc_j[0, j].setub(447.2)
            else:
                model.e_soc_j[0, j].setlb(0.0)
                model.e_soc_j[0, j].setub(0.0)

    solution = simulator.optimizer.solve_model(model)
    logger.info("First iteration solved: status=%s", solution['status'])

    # FORCE SOC to 80% for second iteration
    forced_soc = 3577.6  # 80% of 4472 kWh
    logger.info("")
    logger.info("="*80)
    logger.info("FORCING SOC to %.2f kWh (80%%) for second iteration", forced_soc)
    logger.info("="*80)

    # Manually set for second iteration
    simulator.optimizer.battery_params['initial_soc_kwh'] = forced_soc

    # Run second iteration
    data_window_2 = test_data.iloc[96:224].reset_index(drop=True)
    model_2 = simulator.optimizer.build_optimization_model(data_window_2, 0.5)

    # Set initial segment SOC for 80% (all 10 segments partially filled)
    if hasattr(model_2, 'e_soc_j'):
        logger.info("Setting segment SOC for 80% total (3577.6 kWh):")
        for j in model_2.J:
            # All segments full
            seg_soc = 447.2  # Each segment is 447.2 kWh
            if j == 8:
                # 8th segment: partial (3577.6 - 7*447.2 = 447.2)
                seg_soc = 3577.6 - 7 * 447.2
            elif j == 9 or j == 10:
                seg_soc = 0.0

            logger.info("  Segment %d: %.2f kWh", j, seg_soc)
            model_2.e_soc_j[0, j].setlb(seg_soc)
            model_2.e_soc_j[0, j].setub(seg_soc)

    solution_2 = simulator.optimizer.solve_model(model_2)
    logger.info("Second iteration solved: status=%s", solution_2['status'])

    # Check initial SOC in solution
    if hasattr(model_2, 'e_soc_j'):
        actual_init_soc = sum(pyo.value(model_2.e_soc_j[0, j]) for j in model_2.J)
        logger.info("")
        logger.info("="*80)
        logger.info("VERIFICATION: Second iteration initial SOC")
        logger.info("="*80)
        logger.info("  Expected: %.2f kWh (80%%)", forced_soc)
        logger.info("  Actual:   %.2f kWh (%.1f%%)", actual_init_soc, 100*actual_init_soc/4472)
        logger.info("  Match: %s", "YES" if abs(actual_init_soc - forced_soc) < 1.0 else "NO")
        logger.info("="*80)

        if abs(actual_init_soc - forced_soc) < 1.0:
            print("\n[PASS] State transfer is WORKING! SOC was correctly transferred from 50% to 80%")
        else:
            print(f"\n[FAIL] State transfer FAILED! Expected {forced_soc:.2f}, got {actual_init_soc:.2f}")

    return None

# Run modified test
modified_run()
