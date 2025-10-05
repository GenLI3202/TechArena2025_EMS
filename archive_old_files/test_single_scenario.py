#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'py_script'))

from validation_test_october import TechArena2025ValidationTest

# Initialize test runner
validator = TechArena2025ValidationTest()

# Run single scenario
try:
    print("=== Testing Single Scenario: DE_LU, C-rate=0.25, Cycles=1.0 ===")
    result = validator.run_single_scenario('DE_LU', 0.25, 1.0)
    
    print("\n=== Results ===")
    print(f"Status: {result.get('optimization_status', 'unknown')}")
    print(f"October Revenue: €{result.get('october_revenue', 0):,.2f}")
    print(f"Annual Estimate: €{result.get('annual_revenue_estimate', 0):,.2f}")
    print(f"Solve Time: {result.get('solve_time', 0):.2f} seconds")
    print(f"Optimization Time: {result.get('optimization_time', 0):.2f} seconds")
    print(f"Data Points (October): {result.get('data_points_october', 0)}")
    
    if result.get('error'):
        print(f"Error: {result['error']}")
    
    # Show some variables if available
    if 'optimization_variables' in result:
        opt_vars = result['optimization_variables']
        print(f"Variables: p_ch={len(opt_vars.get('p_ch', {}))}, p_dis={len(opt_vars.get('p_dis', {}))}, e_soc={len(opt_vars.get('e_soc', {}))}")
        
    print(f"\nTotal scenarios in memory: {len(validator.results)}")
    
except Exception as e:
    print(f"Test failed with error: {e}")
    import traceback
    traceback.print_exc()