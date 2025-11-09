"""
Debug script to check SOC extraction from model
"""

from py_script.rolling_horizon import MPCSimulator
from py_script.core.optimizer import BESSOptimizerModelIII
import pyomo.environ as pyo

def main():
    print("=" * 80)
    print("DEBUG: SOC EXTRACTION FROM OPTIMIZER")
    print("=" * 80)

    # Initialize
    optimizer = BESSOptimizerModelIII(alpha=1.0)

    # Load 1 day of data
    full_data = optimizer.load_and_preprocess_data('data/archive/phase_1_data_TechArena2025_data_tidy.jsonl')
    data = optimizer.extract_country_data(full_data, 'CH')
    data_window = data.iloc[:96].reset_index(drop=True)  # 1 day

    print(f"\nData loaded: {len(data_window)} timesteps (1 day)")

    # Build model directly (not through MPC)
    print("\nBuilding Model III for 1 day...")
    model = optimizer.build_optimization_model(
        data_window,
        c_rate=0.5,
        daily_cycle_limit=None
    )

    # Check E_soc_init value
    print(f"\nE_soc_init parameter value: {pyo.value(model.E_soc_init):.2f} kWh")

    # Solve
    print("\nSolving...")
    solution = optimizer.solve_model(model)
    print(f"Status: {solution['status']}")

    # Extract SOC trajectory from SOLUTION dict
    if 'e_soc' in solution:
        print("\n[e_soc in solution dict]")
        e_soc_dict = solution['e_soc']
        print(f"  Keys: {list(e_soc_dict.keys())[:10]}...")
        print(f"  First 5 values:")
        for t in range(min(5, len(e_soc_dict))):
            print(f"    e_soc[{t}] = {e_soc_dict[t]:.2f} kWh")
        print(f"  Last 5 values:")
        for t in range(max(0, len(e_soc_dict)-5), len(e_soc_dict)):
            print(f"    e_soc[{t}] = {e_soc_dict[t]:.2f} kWh")

    # Extract from MODEL variables directly
    if hasattr(model, 'e_soc_j'):
        print("\n[e_soc_j from MODEL]")
        print(f"  Segments (J): {list(model.J)}")
        print(f"  Timesteps (T): {len(model.T)} steps")

        # Initial SOC (t=0)
        print(f"\n  Initial SOC (t=0) by segment:")
        total_initial = 0
        for j in model.J:
            val = pyo.value(model.e_soc_j[0, j])
            total_initial += val
            print(f"    Segment {j}: {val:.2f} kWh")
        print(f"    TOTAL: {total_initial:.2f} kWh")

        # Final SOC (t=95, last execution step)
        last_step = 95
        print(f"\n  Final SOC (t={last_step}) by segment:")
        total_final = 0
        for j in model.J:
            val = pyo.value(model.e_soc_j[last_step, j])
            total_final += val
            print(f"    Segment {j}: {val:.2f} kWh")
        print(f"    TOTAL: {total_final:.2f} kWh")

    # Check if SOC changed
    print("\n" + "=" * 80)
    if abs(total_final - total_initial) > 0.1:
        print(f"SOC CHANGED: {total_initial:.2f} -> {total_final:.2f} kWh (delta: {total_final - total_initial:.2f})")
        print("State transfer SHOULD work if we extract this correctly!")
    else:
        print(f"SOC DID NOT CHANGE: Stuck at {total_initial:.2f} kWh")
        print("This suggests the optimizer is not changing SOC (why?)")
    print("=" * 80)

if __name__ == '__main__':
    main()
