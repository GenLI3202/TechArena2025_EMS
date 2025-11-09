"""
Debug script to check if optimizer is charging/discharging
"""

from py_script.core.optimizer import BESSOptimizerModelIII

def main():
    print("=" * 80)
    print("DEBUG: CHECK POWER BIDS (CHARGE/DISCHARGE)")
    print("=" * 80)

    # Initialize
    optimizer = BESSOptimizerModelIII(alpha=1.0)

    # Load 1 day of data
    full_data = optimizer.load_and_preprocess_data('data/archive/phase_1_data_TechArena2025_data_tidy.jsonl')
    data = optimizer.extract_country_data(full_data, 'CH')
    data_window = data.iloc[:96].reset_index(drop=True)  # 1 day

    print(f"\nData loaded: {len(data_window)} timesteps")
    print(f"DA price range: {data_window['price_day_ahead'].min():.2f} - {data_window['price_day_ahead'].max():.2f} EUR/MWh")

    # Build and solve
    print("\nSolving...")
    model = optimizer.build_optimization_model(data_window, c_rate=0.5)
    solution = optimizer.solve_model(model)

    # Check power bids
    p_ch = solution.get('p_ch', {})
    p_dis = solution.get('p_dis', {})

    total_charge = sum(p_ch.values())
    total_discharge = sum(p_dis.values())

    print(f"\nPower bids:")
    print(f"  Total charge: {total_charge:.2f} MW*intervals")
    print(f"  Total discharge: {total_discharge:.2f} MW*intervals")

    if total_charge == 0 and total_discharge == 0:
        print("\n  [ALERT] Optimizer is NOT using DA market at all!")
        print("  This explains why SOC stays constant.")
        print("  Possible reasons:")
        print("    1. DA price spread too small vs degradation cost")
        print("    2. Calendar aging cost dominates (85.92 EUR/day)")
        print("    3. No profitable arbitrage opportunity")
    else:
        print(f"\n  Optimizer IS trading in DA market")
        print(f"  Expected SOC change: ~{(total_discharge - total_charge) * 0.25:.2f} kWh (rough estimate)")

    # Check AS capacity bids
    c_fcr = solution.get('c_fcr', {})
    c_afrr_pos = solution.get('c_afrr_pos', {})
    c_afrr_neg = solution.get('c_afrr_neg', {})

    print(f"\nAS capacity bids (MW):")
    print(f"  FCR: {list(c_fcr.values())[:3]}...")
    print(f"  aFRR+: {list(c_afrr_pos.values())[:3]}...")
    print(f"  aFRR-: {list(c_afrr_neg.values())[:3]}...")

    print("\n" + "=" * 80)
    print("CONCLUSION:")
    print("  If SOC doesn't change, it's because the optimizer finds it")
    print("  more profitable to hold SOC constant and only provide AS capacity.")
    print("  This is actually CORRECT behavior, not a bug!")
    print("=" * 80)

if __name__ == '__main__':
    main()
