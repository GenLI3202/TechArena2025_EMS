from py_script.rolling_horizon import MPCSimulator
from py_script.core.optimizer import BESSOptimizerModelIII
import pandas as pd

# Test MPC bid extraction
optimizer = BESSOptimizerModelIII(alpha=1.0)
full_data = optimizer.load_and_preprocess_data('data/archive/phase_1_data_TechArena2025_data_tidy.jsonl')
country_data = optimizer.extract_country_data(full_data, 'CH')

# Take first 128 timesteps (32h)
test_data = country_data.iloc[:128].reset_index(drop=True)

# Build and solve
model = optimizer.build_optimization_model(test_data, c_rate=0.5)
solution = optimizer.solve_model(model)

print("Solution c_fcr:")
print(solution['c_fcr'])

print("\nblock_id mapping (first 20 rows):")
print(test_data[['timestamp', 'block_id']].head(20))

print("\nTesting bid extraction logic:")
# Simulate what MPC does
for t_exec in range(5):  # Just first 5 timesteps
    block_id = int(test_data['block_id'].iloc[t_exec])
    c_fcr_val = solution['c_fcr'].get(block_id, 0.0)
    print(f"  t_exec={t_exec}, block_id={block_id}, c_fcr={c_fcr_val:.4f}")
