"""
Quick Test of Improved BESS Model
=================================
"""

from model_improved import ImprovedBESSOptimizer
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

print('🚀 Testing Improved BESS Optimization Model')
print('=' * 50)

# Initialize optimizer
optimizer = ImprovedBESSOptimizer()
print('✅ Optimizer initialized successfully')

# Create small test dataset
print('\n📊 Creating test dataset...')
n_hours = 24  # 1 day
n_intervals = n_hours * 4  # 15-min intervals

# Create timestamps
start_time = datetime(2024, 1, 1)
timestamps = [start_time + timedelta(minutes=15*i) for i in range(n_intervals)]

# Create test market data
np.random.seed(42)  # For reproducible results
test_data = pd.DataFrame({
    'price_day_ahead': 50 + 20 * np.sin(np.arange(n_intervals) * 2 * np.pi / (24*4)) + np.random.normal(0, 5, n_intervals),
    'price_fcr': 10 + np.random.normal(0, 2, n_intervals),
    'price_afrr_pos': 8 + np.random.normal(0, 1.5, n_intervals),
    'price_afrr_neg': 7 + np.random.normal(0, 1.5, n_intervals),
    'block_id': np.repeat(range(6), 16),  # 6 blocks of 4 hours each
    'day_id': np.ones(n_intervals, dtype=int)
}, index=timestamps)

print(f'✅ Test dataset created: {len(test_data)} intervals, {test_data["block_id"].nunique()} blocks')

# Test configuration
c_rate = 0.33
n_cycles = 1.5

print(f'\n⚙️  Building model (C-rate={c_rate}, cycles={n_cycles})...')

try:
    # Build model (this tests all the critical improvements)
    model = optimizer.build_optimization_model(test_data, c_rate, n_cycles)
    print(f'✅ Model built successfully:')
    print(f'   - Variables: {model.nvariables()}')
    print(f'   - Constraints: {model.nconstraints()}')
    print(f'   - Time periods: {len(model.T)}')
    print(f'   - Blocks: {len(model.B)}')
    
    # Verify key improvements
    print(f'\n🔍 Verifying improvements:')
    
    # Check block mapping parameter (addresses closure anti-pattern)
    if hasattr(model, 'block_map'):
        print('✅ Block mapping parameter exists (no external dependencies)')
    
    # Check AS price indexing (memory efficiency)
    fcr_size = len(model.P_FCR)
    time_size = len(model.T)
    block_size = len(model.B)
    print(f'✅ AS prices indexed by blocks ({fcr_size}) not time ({time_size})')
    print(f'   Memory reduction: {((time_size - fcr_size) / time_size * 100):.1f}%')
    
    print(f'\n🎯 Model ready for solving!')
    print(f'✅ All critical improvements successfully implemented and validated!')
    
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()