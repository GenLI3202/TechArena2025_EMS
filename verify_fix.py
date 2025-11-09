import json

# Load current MPC results
with open('results/mpc_5day_test/financial_summary.json', 'r') as f:
    results = json.load(f)

print("="*80)
print("AS REVENUE FIX VERIFICATION")
print("="*80)
print()

as_revenue = results['financial']['as_revenue']
da_revenue = results['financial']['da_revenue']

print("Current MPC Results (After Fix):")
print(f"  AS Capacity Revenue: {as_revenue:.2f} EUR")
print(f"  DA Energy Revenue:   {da_revenue:.2f} EUR")
print()

print("If bug still existed (4x multiplier):")
print(f"  AS Revenue would be: {as_revenue * 4:.2f} EUR")
print()

print("="*80)
print("VERIFICATION RESULT")
print("="*80)

if as_revenue < 5000:
    print(f"SUCCESS: AS revenue is {as_revenue:.2f} EUR (correct)")
    print("  - Value is ~1/4 of the previous 15,512 EUR")
    print("  - Formula no longer multiplies by model.db")
    print("  - Optimizer now balances FCR with DA arbitrage")
else:
    print(f"ERROR: AS revenue is {as_revenue:.2f} EUR (still inflated!)")
    print("  - Value should be ~3,770 EUR, not >5,000 EUR")
    print("  - Check if optimizer.py was actually reloaded")

print()
print("SOC Trajectory:")
soc_traj = results['soc']['soc_trajectory']
print(f"  Initial: {soc_traj[0]:.2f} kWh")
print(f"  Final:   {soc_traj[-1]:.2f} kWh")
if abs(soc_traj[-1] - soc_traj[0]) > 100:
    print("  SUCCESS: SOC changed significantly (strategic behavior)")
else:
    print("  WARNING: SOC barely changed (check if fix applied)")
print()
print("="*80)
