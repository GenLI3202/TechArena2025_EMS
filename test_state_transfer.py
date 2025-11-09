"""
Test SOC state transfer across MPC iterations
Expected: SOC should change each day, NOT stay at 2236 kWh
"""

from py_script.rolling_horizon import MPCSimulator
from py_script.core.optimizer import BESSOptimizerModelIII
import time

def main():
    print("=" * 80)
    print("MPC STATE TRANSFER TEST")
    print("=" * 80)

    # Initialize
    optimizer = BESSOptimizerModelIII(alpha=1.0)

    # Load 3 days of data
    full_data = optimizer.load_and_preprocess_data('data/archive/phase_1_data_TechArena2025_data_tidy.jsonl')
    data = optimizer.extract_country_data(full_data, 'CH')
    data = data.iloc[:3*96].reset_index(drop=True)  # 3 days

    print(f"Data loaded: {len(data)} timesteps (3 days)\n")

    # Run MPC with 24h/24h (no overlap for clarity)
    simulator = MPCSimulator(
        optimizer_model=optimizer,
        full_data=data,
        horizon_hours=24,
        execution_hours=24,
        c_rate=0.5,
        validate_constraints=False
    )

    print("Running MPC simulation...")
    print("-" * 80)
    start = time.time()
    results = simulator.run_full_simulation(initial_soc_fraction=0.5)
    elapsed = time.time() - start

    print("\n" + "=" * 80)
    print("STATE TRANSFER VERIFICATION")
    print("=" * 80)

    soc_traj = results['soc_trajectory']
    print(f"\nSOC at iteration boundaries:")
    for i, soc in enumerate(soc_traj):
        print(f"  Iteration {i}: {soc:.2f} kWh ({100*soc/4472:.1f}%)")

    # Check if SOC is changing
    soc_changes = [abs(soc_traj[i+1] - soc_traj[i]) for i in range(len(soc_traj)-1)]
    max_change = max(soc_changes)

    print(f"\nSOC changes between iterations:")
    for i, change in enumerate(soc_changes):
        print(f"  Day {i} -> Day {i+1}: {change:.2f} kWh change")

    print(f"\n" + "=" * 80)
    if max_change > 10:  # Expect significant changes (> 10 kWh)
        print("RESULT: PASS - SOC is changing (state transfer working!)")
        print(f"Max SOC change: {max_change:.2f} kWh")
    else:
        print("RESULT: FAIL - SOC not changing (state transfer broken!)")
        print(f"Max SOC change: {max_change:.2f} kWh (expected > 10 kWh)")

    print(f"Runtime: {elapsed:.2f} seconds")
    print("=" * 80)

if __name__ == '__main__':
    main()
