#!/usr/bin/env python3
"""
Performance test script for comparing BESS optimization solvers.
"""

import sys
import os
import time
import json
from model import BESSOptimizer
import pyomo.environ as pyo

def main():
    print("BESS Optimization Solver Performance Test")
    print("=" * 50)
    
    # Create test dataset
    print("Creating 10-day test dataset...")
    with open('../data/TechArena2025_data_tidy.jsonl', 'r') as f:
        all_data = [json.loads(line) for line in f]

    # Get Austria first 10 days (96 timesteps/day * 10 days = 960)
    austria_10days = [d for d in all_data if d['country'] == 'AT'][:960]
    print(f"Created subset with {len(austria_10days)} records")

    # Save subset
    subset_file = 'test_10days.jsonl'
    with open(subset_file, 'w') as f:
        for record in austria_10days:
            f.write(json.dumps(record) + '\n')

    # Initialize optimizer and load data
    print("Loading and preprocessing data...")
    optimizer = BESSOptimizer()
    df = optimizer.load_and_preprocess_data(subset_file)

    # Build model
    country_columns = [col for col in df.columns if col[0] == 'AT']
    country_data = df[country_columns].copy()
    country_data['day_id'] = df['day_id']
    country_data['block_id'] = df['block_id']

    print("Building optimization model...")
    model = optimizer.build_optimization_model(country_data, 0.5, 1.0)
    print(f"Model built: {len(model.T)} timesteps, {len(model.D)} days, {len(model.B)} blocks")

    # Count variables and constraints
    print(f"Problem size: ~{sum(len(v) for v in model.component_objects(pyo.Var))} variables")

    print("\nTesting solvers...")
    print("=" * 60)

    # Test each solver
    results = []
    solvers_to_test = [
        ('cplex', 'CPLEX (Commercial)'),
        ('gurobi', 'Gurobi (Commercial)'),
        ('scip', 'SCIP (Open Source)'),
        ('appsi_highs', 'HiGHS (Open Source)')
    ]

    for solver_name, description in solvers_to_test:
        print(f"\nTesting {description}...")
        
        try:
            solver = pyo.SolverFactory(solver_name)
            if not solver.available():
                print(f"  NOT AVAILABLE")
                continue
            
            # Solve the model
            start_time = time.time()
            result = solver.solve(model, tee=False)
            solve_time = time.time() - start_time
            
            # Check results
            if result.solver.termination_condition == pyo.TerminationCondition.optimal:
                objective_value = pyo.value(model.objective)
                print(f"  OPTIMAL: {solve_time:.3f}s, Objective: {objective_value:,.0f} EUR")
                results.append((description, solve_time, objective_value, 'optimal'))
            elif result.solver.termination_condition == pyo.TerminationCondition.feasible:
                objective_value = pyo.value(model.objective)
                print(f"  FEASIBLE: {solve_time:.3f}s, Objective: {objective_value:,.0f} EUR")
                results.append((description, solve_time, objective_value, 'feasible'))
            else:
                print(f"  FAILED: {result.solver.termination_condition}")
                
        except Exception as e:
            print(f"  ERROR: {str(e)}")

    print("\n" + "=" * 60)
    print("PERFORMANCE SUMMARY (10 days, 960 timesteps)")
    print("=" * 60)

    if results:
        print(f"{'Solver':<25} {'Time (s)':<10} {'Objective (EUR)':<15} {'Status'}")
        print("-" * 60)
        
        for desc, time_taken, obj, status in results:
            print(f"{desc:<25} {time_taken:<10.3f} {obj:<15,.0f} {status}")
        
        # Find fastest solver
        optimal_results = [r for r in results if r[3] == 'optimal']
        if optimal_results:
            fastest = min(optimal_results, key=lambda x: x[1])
            print(f"\nFastest optimal solver: {fastest[0]} ({fastest[1]:.3f}s)")
            
            # Check consistency
            objectives = [r[2] for r in optimal_results]
            if len(set(round(obj, 0) for obj in objectives)) == 1:
                print("All solvers found the same optimal solution!")
            else:
                print("WARNING: Different objective values found!")
                for desc, _, obj, _ in optimal_results:
                    print(f"  {desc}: {obj:,.0f} EUR")
                    
            # Time predictions
            print("\n" + "=" * 60)
            print("TIME PREDICTIONS")
            print("=" * 60)
            
            # Assume quadratic scaling for problem size
            scale_factor_year = (365 * 96) / 960  # 365 days vs 10 days
            scale_factor_scenario = scale_factor_year * 45  # 45 scenarios
            
            print(f"Scaling assumptions:")
            print(f"  - 10 days (960 timesteps) -> 1 year (34,560 timesteps): {scale_factor_year:.1f}x")
            print(f"  - Linear/quadratic complexity scaling")
            print(f"  - 45 total scenarios")
            
            print(f"\nPredicted solve times:")
            for desc, time_10days, _, _ in optimal_results:
                # Assume quadratic scaling (conservative estimate)
                time_year = time_10days * (scale_factor_year ** 1.5)
                time_45_scenarios = time_year * 45
                
                print(f"{desc}:")
                print(f"  1 year:        {time_year:8.1f}s ({time_year/60:6.1f} min)")
                print(f"  45 scenarios:  {time_45_scenarios:8.0f}s ({time_45_scenarios/3600:6.1f} hours)")
        else:
            print("No optimal solutions found!")
            
    else:
        print("No solvers completed successfully!")

    # Clean up
    if os.path.exists(subset_file):
        os.remove(subset_file)

    print(f"\nTest completed!")

if __name__ == "__main__":
    main()