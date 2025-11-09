"""
Test SOC state transfer with FORCED initial SOC changes
Expected: Even if optimizer doesn't change SOC within a day,
          it should maintain whatever SOC we start with
"""

from py_script.rolling_horizon import MPCSimulator
from py_script.core.optimizer import BESSOptimizerModelIII
import time

def main():
    print("=" * 80)
    print("MPC STATE TRANSFER TEST (FORCED DIFFERENT INITIAL SOC)")
    print("=" * 80)

    # Initialize
    optimizer = BESSOptimizerModelIII(alpha=1.0)

    # Load 3 days of data
    full_data = optimizer.load_and_preprocess_data('data/archive/phase_1_data_TechArena2025_data_tidy.jsonl')
    data = optimizer.extract_country_data(full_data, 'CH')
    data = data.iloc[:3*96].reset_index(drop=True)  # 3 days

    print(f"Data loaded: {len(data)} timesteps (3 days)\n")

    # Test 1: Start at 20% SOC
    print("\n" + "=" * 80)
    print("TEST 1: Initial SOC = 20% (894.4 kWh)")
    print("=" * 80)

    simulator1 = MPCSimulator(
        optimizer_model=optimizer,
        full_data=data,
        horizon_hours=24,
        execution_hours=24,
        c_rate=0.5,
        validate_constraints=False
    )

    start = time.time()
    results1 = simulator1.run_full_simulation(initial_soc_fraction=0.2)
    elapsed1 = time.time() - start

    soc_traj1 = results1['soc_trajectory']
    print(f"\nSOC trajectory (20% start):")
    for i, soc in enumerate(soc_traj1):
        print(f"  Iteration {i}: {soc:.2f} kWh ({100*soc/4472:.1f}%)")

    # Test 2: Start at 80% SOC
    print("\n" + "=" * 80)
    print("TEST 2: Initial SOC = 80% (3577.6 kWh)")
    print("=" * 80)

    # Need to re-initialize optimizer for fresh run
    optimizer2 = BESSOptimizerModelIII(alpha=1.0)
    full_data2 = optimizer2.load_and_preprocess_data('data/archive/phase_1_data_TechArena2025_data_tidy.jsonl')
    data2 = optimizer2.extract_country_data(full_data2, 'CH')
    data2 = data2.iloc[:3*96].reset_index(drop=True)

    simulator2 = MPCSimulator(
        optimizer_model=optimizer2,
        full_data=data2,
        horizon_hours=24,
        execution_hours=24,
        c_rate=0.5,
        validate_constraints=False
    )

    start = time.time()
    results2 = simulator2.run_full_simulation(initial_soc_fraction=0.8)
    elapsed2 = time.time() - start

    soc_traj2 = results2['soc_trajectory']
    print(f"\nSOC trajectory (80% start):")
    for i, soc in enumerate(soc_traj2):
        print(f"  Iteration {i}: {soc:.2f} kWh ({100*soc/4472:.1f}%)")

    # Verification
    print("\n" + "=" * 80)
    print("STATE TRANSFER VERIFICATION")
    print("=" * 80)

    # Test 1: Should stay around 894.4 kWh if optimizer doesn't trade
    test1_pass = all(abs(soc - 894.4) < 50 for soc in soc_traj1)  # Allow 50 kWh tolerance
    print(f"\nTest 1 (20% start):")
    print(f"  Expected: ~894.4 kWh maintained across iterations")
    print(f"  Actual range: {min(soc_traj1):.2f} - {max(soc_traj1):.2f} kWh")
    print(f"  Result: {'PASS' if test1_pass else 'FAIL'}")

    # Test 2: Should stay around 3577.6 kWh if optimizer doesn't trade
    test2_pass = all(abs(soc - 3577.6) < 50 for soc in soc_traj2)  # Allow 50 kWh tolerance
    print(f"\nTest 2 (80% start):")
    print(f"  Expected: ~3577.6 kWh maintained across iterations")
    print(f"  Actual range: {min(soc_traj2):.2f} - {max(soc_traj2):.2f} kWh")
    print(f"  Result: {'PASS' if test2_pass else 'FAIL'}")

    # Overall result
    print(f"\n" + "=" * 80)
    if test1_pass and test2_pass:
        print("OVERALL RESULT: PASS - State transfer working!")
        print("  The optimizer correctly maintains initial SOC across iterations")
        print("  (Even though it doesn't change SOC within each day)")
    else:
        print("OVERALL RESULT: FAIL - State transfer broken!")
        print("  The initial SOC is not being maintained across iterations")

    print(f"\nTotal runtime: {elapsed1 + elapsed2:.2f} seconds")
    print("=" * 80)

if __name__ == '__main__':
    main()
