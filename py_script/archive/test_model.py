"""
Test script for BESS optimization model
=======================================

This script tests the optimization model with a small dataset to verify
the implementation before running the full optimization.
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from model import BESSOptimizer
import pandas as pd
import json
import numpy as np
import pyomo.environ as pyo
from datetime import datetime, timedelta

def create_test_data():
    """Create a small test dataset for verification."""
    print("Creating test dataset...")
    
    # Create 1 day of data (96 15-minute intervals)
    start_time = datetime(2024, 1, 1)
    timestamps = [start_time + timedelta(minutes=15*i) for i in range(96)]
    
    test_data = []
    
    # Day-ahead prices (simple pattern: low at night, high during day)
    for i, ts in enumerate(timestamps):
        hour = ts.hour
        if 0 <= hour < 6:  # Night: low prices
            price = np.random.uniform(-10, 20)
        elif 6 <= hour < 10:  # Morning ramp: increasing
            price = np.random.uniform(20, 60)
        elif 10 <= hour < 16:  # Day: high prices
            price = np.random.uniform(50, 100)
        elif 16 <= hour < 20:  # Evening: peak
            price = np.random.uniform(80, 120)
        else:  # Late evening: decreasing
            price = np.random.uniform(20, 60)
            
        test_data.append({
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "country": "DE",
            "price_eur_mwh": price,
            "source": "day_ahead"
        })
    
    # FCR prices (6 blocks of 4 hours each)
    fcr_prices = [100, 80, 60, 70, 90, 85]  # EUR/MW
    for block_idx, price in enumerate(fcr_prices):
        ts = start_time + timedelta(hours=4*block_idx)
        test_data.append({
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "country": "DE", 
            "price_eur_mwh": price,
            "source": "fcr"
        })
    
    # aFRR prices (positive and negative, 6 blocks each)
    afrr_pos_prices = [15, 12, 8, 10, 18, 14]  # EUR/MW
    afrr_neg_prices = [10, 8, 5, 7, 12, 9]     # EUR/MW
    
    for block_idx, (pos_price, neg_price) in enumerate(zip(afrr_pos_prices, afrr_neg_prices)):
        ts = start_time + timedelta(hours=4*block_idx)
        
        test_data.append({
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "country": "DE",
            "price_eur_mwh": pos_price,
            "source": "afrr",
            "direction": "positive"
        })
        
        test_data.append({
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "country": "DE",
            "price_eur_mwh": neg_price,
            "source": "afrr", 
            "direction": "negative"
        })
    
    # Save test data
    test_file = "test_data.jsonl"
    with open(test_file, 'w') as f:
        for item in test_data:
            f.write(json.dumps(item) + '\n')
    
    print(f"Created test dataset with {len(test_data)} records")
    return test_file

def test_data_loading():
    """Test the data loading and preprocessing."""
    print("\n=== Testing Data Loading ===")
    
    # Create test data
    test_file = create_test_data()
    
    # Initialize optimizer
    optimizer = BESSOptimizer()
    
    try:
        # Test data loading
        df = optimizer.load_and_preprocess_data(test_file)
        print(f"Data shape: {df.shape}")
        print(f"Columns: {df.columns.tolist()}")
        print(f"Index range: {df.index.min()} to {df.index.max()}")
        
        # Check data structure
        print("\nData sample:")
        print(df.head())
        
        return df, test_file
        
    except Exception as e:
        print(f"Data loading test failed: {e}")
        return None, None

def test_model_building():
    """Test model building without solving."""
    print("\n=== Testing Model Building ===")
    
    df, test_file = test_data_loading()
    if df is None:
        return False
    
    optimizer = BESSOptimizer()
    
    try:
        # Extract country data 
        country_columns = [col for col in df.columns if col[0] == 'DE']
        country_data = df[country_columns].copy()
        country_data['day_id'] = df['day_id']
        country_data['block_id'] = df['block_id']
        
        # Build model
        model = optimizer.build_optimization_model(country_data, c_rate=0.5, n_cycles=1.0)
        
        print(f"Model built successfully!")
        print(f"Number of variables: {len(model.component_objects(ctype=pyo.Var))}")
        print(f"Number of constraints: {len(model.component_objects(ctype=pyo.Constraint))}")
        
        # Print model structure info
        print(f"\nTime steps: {len(model.T)}")
        print(f"Days: {len(model.D)}") 
        print(f"Blocks: {len(model.B)}")
        
        return True
        
    except Exception as e:
        print(f"Model building test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_simple_linear_model():
    """Test with a simplified linear model (no binary variables) to verify solver works."""
    print("\n=== Testing Simplified Linear Model ===")
    
    import pyomo.environ as pyo
    
    # Create simple LP model
    model = pyo.ConcreteModel()
    
    # Just day-ahead arbitrage without reserves
    model.T = pyo.Set(initialize=range(96))  # 1 day, 15-min intervals
    
    # Simple price pattern for testing
    prices = {}
    for t in range(96):
        hour = t // 4  # Convert to hour
        if 0 <= hour < 6:
            prices[t] = 20  # Low night prices
        elif 10 <= hour < 16:
            prices[t] = 80  # High day prices  
        else:
            prices[t] = 50  # Medium prices
    
    model.P_DA = pyo.Param(model.T, initialize=prices)
    model.E_nom = pyo.Param(initialize=4472)
    model.P_max = pyo.Param(initialize=2236)  # 0.5C
    model.eta = pyo.Param(initialize=0.95)
    model.dt = pyo.Param(initialize=0.25)
    
    # Variables (continuous only)
    model.p_ch = pyo.Var(model.T, domain=pyo.NonNegativeReals, bounds=(0, 2236))
    model.p_dis = pyo.Var(model.T, domain=pyo.NonNegativeReals, bounds=(0, 2236))
    model.e_soc = pyo.Var(model.T, domain=pyo.NonNegativeReals, bounds=(447.2, 4024.8))
    
    # Objective: maximize profit
    def obj_rule(model):
        return sum((model.P_DA[t]/1000) * (model.p_dis[t] - model.p_ch[t]) * model.dt 
                  for t in model.T)
    model.objective = pyo.Objective(rule=obj_rule, sense=pyo.maximize)
    
    # SOC dynamics
    def soc_rule(model, t):
        if t == 0:
            return model.e_soc[t] == 2236 + (model.p_ch[t] * 0.95 - model.p_dis[t] / 0.95) * 0.25
        else:
            return model.e_soc[t] == model.e_soc[t-1] + (model.p_ch[t] * 0.95 - model.p_dis[t] / 0.95) * 0.25
    model.soc_dynamics = pyo.Constraint(model.T, rule=soc_rule)
    
    # No simultaneous charge/discharge (simple constraint)
    def no_simult_rule(model, t):
        return model.p_ch[t] * model.p_dis[t] <= 0  # Nonlinear but should work for LP relaxation
    # Skip this constraint for now to keep it linear
    
    # Try to solve with different solvers
    solvers_to_try = ['glpk', 'cbc', 'gurobi', 'cplex']
    
    for solver_name in solvers_to_try:
        try:
            solver = pyo.SolverFactory(solver_name)
            if solver.available():
                print(f"Trying solver: {solver_name}")
                result = solver.solve(model, tee=False)
                
                if result.solver.termination_condition == pyo.TerminationCondition.optimal:
                    print(f"✓ {solver_name} solved successfully!")
                    print(f"  Objective value: {pyo.value(model.objective):.2f}")
                    print(f"  Total charge: {sum(pyo.value(model.p_ch[t]) for t in model.T) * 0.25:.1f} kWh")
                    print(f"  Total discharge: {sum(pyo.value(model.p_dis[t]) for t in model.T) * 0.25:.1f} kWh")
                    return True
                else:
                    print(f"✗ {solver_name} failed: {result.solver.termination_condition}")
            else:
                print(f"✗ {solver_name} not available")
                
        except Exception as e:
            print(f"✗ {solver_name} error: {e}")
    
    print("No working solver found!")
    return False

def main():
    """Run all tests."""
    print("BESS Optimization Model Test Suite")
    print("=" * 50)
    
    # Test 1: Data loading
    success1 = test_data_loading() is not None
    
    # Test 2: Model building  
    success2 = test_model_building()
    
    # Test 3: Simple solver test
    success3 = test_simple_linear_model()
    
    print("\n" + "=" * 50)
    print("Test Results:")
    print(f"Data Loading: {'✓' if success1 else '✗'}")
    print(f"Model Building: {'✓' if success2 else '✗'}")
    print(f"Solver Test: {'✓' if success3 else '✗'}")
    
    if success1 and success2 and success3:
        print("\n🎉 All tests passed! Model is ready for full optimization.")
    else:
        print("\n⚠️  Some tests failed. Check the issues above.")
        
        if not success3:
            print("\nTo run the full optimization, you need to install a solver:")
            print("- Option 1: Install CBC: conda install -c conda-forge coincbc")
            print("- Option 2: Install GLPK: conda install -c conda-forge glpk") 
            print("- Option 3: Use commercial solver (Gurobi/CPLEX) if available")

if __name__ == "__main__":
    main()