#!/usr/bin/env python3
"""
Solver Performance Prediction Calculator
=========================================

This script calculates estimated solve times for different problem sizes
based on scaling assumptions for BESS optimization problems.
"""

import math

def main():
    print("BESS Optimization Solver Performance Predictions")
    print("=" * 60)
    
    # Base performance (2-day problem, 192 timesteps)
    base_timesteps = 192
    base_times = {
        'CPLEX': 0.5,      # seconds
        'Gurobi': 0.5,     # seconds  
        'HiGHS': 2.0,      # estimated
        'SCIP': 5.0        # estimated
    }
    
    # Problem sizes
    problems = [
        ("2 days", 192),
        ("10 days", 960), 
        ("1 month", 2880),
        ("1 year", 34560)
    ]
    
    # Scaling exponent (between 1.0 and 2.0 for MILP)
    scaling_exponent = 1.5
    
    print("Scaling Assumptions:")
    print(f"- Base problem: {base_timesteps} timesteps")
    print(f"- Scaling factor: O(n^{scaling_exponent})")
    print(f"- Conservative estimate for MILP complexity")
    print()
    
    # Calculate predictions
    print("Individual Problem Predictions:")
    print("=" * 60)
    print(f"{'Problem':<12} {'Timesteps':<12} {'CPLEX':<10} {'Gurobi':<10} {'HiGHS':<10} {'SCIP':<10}")
    print("-" * 60)
    
    yearly_times = {}
    
    for problem_name, timesteps in problems:
        scale_factor = (timesteps / base_timesteps) ** scaling_exponent
        
        times = {}
        for solver, base_time in base_times.items():
            predicted_time = base_time * scale_factor
            times[solver] = predicted_time
        
        if problem_name == "1 year":
            yearly_times = times.copy()
        
        # Format times
        def format_time(seconds):
            if seconds < 60:
                return f"{seconds:.1f}s"
            elif seconds < 3600:
                return f"{seconds/60:.1f}m"
            else:
                return f"{seconds/3600:.1f}h"
        
        print(f"{problem_name:<12} {timesteps:<12} {format_time(times['CPLEX']):<10} "
              f"{format_time(times['Gurobi']):<10} {format_time(times['HiGHS']):<10} "
              f"{format_time(times['SCIP']):<10}")
    
    print()
    print("Full Challenge Predictions (45 scenarios):")
    print("=" * 60)
    
    # Challenge scenarios
    scenarios = 45  # 5 countries × 3 C-rates × 3 cycle limits
    
    print(f"Total scenarios: {scenarios}")
    print(f"Each scenario: 1 year ({34560} timesteps)")
    print()
    
    print(f"{'Solver':<12} {'Per Scenario':<15} {'Total (45x)':<15} {'Total Hours':<15}")
    print("-" * 60)
    
    for solver, yearly_time in yearly_times.items():
        total_time = yearly_time * scenarios
        total_hours = total_time / 3600
        
        def format_time_detail(seconds):
            if seconds < 60:
                return f"{seconds:.1f}s"
            elif seconds < 3600:
                return f"{seconds/60:.1f}min"
            else:
                return f"{seconds/3600:.1f}h"
        
        print(f"{solver:<12} {format_time_detail(yearly_time):<15} "
              f"{format_time_detail(total_time):<15} {total_hours:.1f}h")
    
    print()
    print("Parallel Execution Potential:")
    print("=" * 60)
    print("Assuming 4 CPU cores available for parallel scenario execution:")
    print()
    
    for solver, yearly_time in yearly_times.items():
        serial_time = yearly_time * scenarios
        parallel_time = yearly_time * math.ceil(scenarios / 4)  # 4 parallel
        speedup = serial_time / parallel_time
        
        print(f"{solver}:")
        print(f"  Serial execution:   {serial_time/3600:.1f} hours")
        print(f"  Parallel (4 cores): {parallel_time/3600:.1f} hours")
        print(f"  Speedup factor:     {speedup:.1f}x")
        print()
    
    print("Recommendations:")
    print("=" * 60)
    print("1. CPLEX/Gurobi: Fast enough for full challenge (~6-15 hours)")
    print("2. HiGHS: Feasible but slow (~30-90 hours)")  
    print("3. SCIP: Too slow for practical use (~60-180 hours)")
    print("4. Use parallel execution to reduce wall-clock time")
    print("5. Commercial solvers strongly recommended")

if __name__ == "__main__":
    main()