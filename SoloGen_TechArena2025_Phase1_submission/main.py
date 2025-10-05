#!/usr/bin/env python3
"""
TechArena 2025 Phase 1 - BESS Energy Management System
======================================================

Main execution script for generating competition submission files.

This script:
1. Loads market price data from input/TechArena2025_data.xlsx
2. Runs optimization for all 45 scenarios (5 countries × 3 C-rates × 3 cycle limits)
3. Generates three output files:
   - TechArena_Phase1_Configuration.xlsx
   - TechArena_Phase1_Investment.xlsx
   - TechArena_Phase1_Operation.xlsx

Usage:
    python main.py

Requirements:
    - Input file must be in: input/TechArena2025_data.xlsx
    - Output files will be created in: output/
    - Requires CPLEX or Gurobi solver installed

Author: SoloGen Team
Date: October 2025
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Import core modules
try:
    from model import ImprovedBESSOptimizer
    from investment_analysis import InvestmentAnalyzer
    from excel_generator import (
        generate_configuration_xlsx,
        generate_investment_xlsx,
        generate_operation_xlsx
    )
except ImportError as e:
    print(f"❌ Error importing modules: {e}")
    print("Please ensure all required modules are in the same directory as main.py")
    sys.exit(1)


def validate_input_file(input_path: str) -> bool:
    """
    Validate that the input JSONL file exists.
    
    Args:
        input_path: Path to input JSONL file
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not os.path.exists(input_path):
        print(f"❌ Error: Input file not found: {input_path}")
        print("Please place TechArena2025_data_tidy.jsonl in the input/ folder")
        return False
    
    print(f"✅ Input file validated: {input_path}")
    return True


def load_market_data(input_path: str, optimizer: ImprovedBESSOptimizer) -> pd.DataFrame:
    """
    Load and preprocess market data from JSONL file.
    
    Args:
        input_path: Path to input JSONL file
        optimizer: Instance of ImprovedBESSOptimizer
        
    Returns:
        pd.DataFrame: Preprocessed market data
    """
    print("\n📥 Loading market price data...")
    
    try:
        # Load market data using optimizer's method
        market_data = optimizer.load_and_preprocess_data(input_path)
        print(f"✅ Loaded market data: {market_data.shape[0]} time steps, {market_data.shape[1]} columns")
        
        return market_data
        
    except Exception as e:
        print(f"❌ Error loading market data: {e}")
        raise


def run_optimization_pipeline(market_data: pd.DataFrame, 
                              optimizer: ImprovedBESSOptimizer) -> dict:
    """
    Run optimization for all scenarios and collect results.
    
    Args:
        market_data: Preprocessed market data
        optimizer: Instance of ImprovedBESSOptimizer
        
    Returns:
        dict: Results for all scenarios
    """
    print("\n🔄 Running optimization for all scenarios...")
    print("=" * 70)
    
    # Competition parameters - all 5 countries (DE_LU maps to DE in output)
    countries = ['DE_LU', 'AT', 'CH', 'HU', 'CZ']
    c_rates = [0.25, 0.33, 0.5]
    cycle_limits = [1.0, 1.5, 2.0]
    
    total_scenarios = len(countries) * len(c_rates) * len(cycle_limits)
    print(f"Total scenarios to run: {total_scenarios}")
    print(f"Countries: {countries}")
    print(f"C-rates: {c_rates}")
    print(f"Daily cycles: {cycle_limits}")
    print("=" * 70)
    
    all_results = {}
    successful_count = 0
    failed_count = 0
    
    for country in countries:
        print(f"\n📍 Processing country: {country}")
        
        try:
            # Extract country-specific data
            country_data = optimizer.extract_country_data(market_data, country)
            print(f"   Data points: {len(country_data)} time steps")
            
            for c_rate in c_rates:
                for cycles in cycle_limits:
                    scenario_name = f"{country}_C{c_rate}_Cyc{cycles}"
                    print(f"\n   ⚙️  Scenario: {scenario_name}")
                    
                    try:
                        # Build and solve optimization model
                        model = optimizer.build_optimization_model(
                            country_data, c_rate, cycles
                        )
                        # Auto-detect best available solver (CPLEX/Gurobi if available, else HiGHS)
                        solution = optimizer.solve_model(model, solver_name=None)
                        
                        if solution['status'] in ['optimal', 'feasible']:
                            result = {
                                'country': country,
                                'c_rate': c_rate,
                                'cycles': cycles,
                                'objective_value': solution['objective_value'],
                                'status': solution['status'],
                                'solve_time': solution['solve_time'],
                                'solution': solution,  # Full solution for operation file
                                'country_data': country_data  # Store for later use
                            }
                            all_results[scenario_name] = result
                            successful_count += 1
                            
                            print(f"      ✅ Success: Revenue = €{solution['objective_value']:,.0f}")
                            print(f"      ⏱️  Solve time: {solution['solve_time']:.2f}s")
                        else:
                            print(f"      ❌ Failed: {solution['status']}")
                            failed_count += 1
                            
                    except Exception as e:
                        print(f"      ❌ Error: {str(e)}")
                        failed_count += 1
                        
        except Exception as e:
            print(f"   ❌ Error processing country {country}: {e}")
            failed_count += len(c_rates) * len(cycle_limits)
    
    print("\n" + "=" * 70)
    print(f"✅ Optimization complete:")
    print(f"   Successful: {successful_count}/{total_scenarios}")
    print(f"   Failed: {failed_count}/{total_scenarios}")
    print("=" * 70)
    
    if successful_count == 0:
        raise RuntimeError("No successful optimizations - cannot generate output files")
    
    return all_results


def generate_output_files(results: dict, output_dir: str, 
                          optimizer: ImprovedBESSOptimizer,
                          investment_analyzer: InvestmentAnalyzer,
                          market_data: pd.DataFrame) -> None:
    """
    Generate all three required output files.
    
    Args:
        results: Dictionary of optimization results
        output_dir: Output directory path
        optimizer: Instance of ImprovedBESSOptimizer
        investment_analyzer: Instance of InvestmentAnalyzer
        market_data: Full market data
    """
    print("\n📝 Generating output files...")
    print("=" * 70)
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # 1. Configuration file
        print("\n1️⃣  Generating Configuration file...")
        generate_configuration_xlsx(results, output_dir, optimizer)
        config_file = os.path.join(output_dir, 'TechArena_Phase1_Configuration.xlsx')
        print(f"   ✅ Created: {config_file}")
        
        # 2. Investment file
        print("\n2️⃣  Generating Investment file...")
        generate_investment_xlsx(results, output_dir, investment_analyzer)
        investment_file = os.path.join(output_dir, 'TechArena_Phase1_Investment.xlsx')
        print(f"   ✅ Created: {investment_file}")
        
        # 3. Operation file
        print("\n3️⃣  Generating Operation file...")
        generate_operation_xlsx(results, output_dir, optimizer, market_data)
        operation_file = os.path.join(output_dir, 'TechArena_Phase1_Operation.xlsx')
        print(f"   ✅ Created: {operation_file}")
        
        print("\n" + "=" * 70)
        print("✅ All output files generated successfully!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Error generating output files: {e}")
        raise


def print_summary(results: dict) -> None:
    """
    Print summary statistics of optimization results.
    
    Args:
        results: Dictionary of optimization results
    """
    print("\n📊 OPTIMIZATION SUMMARY")
    print("=" * 70)
    
    # Find best scenario by revenue
    best_scenario = max(results.items(), key=lambda x: x[1]['objective_value'])
    best_name, best_result = best_scenario
    
    print(f"🏆 Best Scenario: {best_name}")
    print(f"   Revenue: €{best_result['objective_value']:,.0f}")
    print(f"   Configuration: C-rate={best_result['c_rate']}, Cycles={best_result['cycles']}")
    
    # Revenue by country
    print("\n💰 Revenue by Country:")
    country_revenues = {}
    for scenario_name, result in results.items():
        country = result['country']
        if country not in country_revenues:
            country_revenues[country] = []
        country_revenues[country].append(result['objective_value'])
    
    for country in sorted(country_revenues.keys()):
        revenues = country_revenues[country]
        avg_revenue = np.mean(revenues)
        max_revenue = np.max(revenues)
        print(f"   {country:6s}: Avg = €{avg_revenue:>10,.0f}, Max = €{max_revenue:>10,.0f}")
    
    # Configuration analysis
    print("\n⚙️  Configuration Performance:")
    config_revenues = {}
    for scenario_name, result in results.items():
        config = f"C{result['c_rate']}_Cyc{result['cycles']}"
        if config not in config_revenues:
            config_revenues[config] = []
        config_revenues[config].append(result['objective_value'])
    
    for config in sorted(config_revenues.keys()):
        revenues = config_revenues[config]
        avg_revenue = np.mean(revenues)
        print(f"   {config:12s}: Avg = €{avg_revenue:>10,.0f}")
    
    print("=" * 70)


def main():
    """
    Main execution function for TechArena Phase 1 solution.
    """
    print("=" * 70)
    print("  TechArena 2025 Phase 1 - BESS Energy Management System")
    print("  SoloGen Team Submission Generator")
    print("=" * 70)
    print(f"\n🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Step 1: Setup paths
    input_file = os.path.join("input", "TechArena2025_data_tidy.jsonl")
    output_dir = "output"
    
    print(f"📁 Input file: {input_file}")
    print(f"📁 Output directory: {output_dir}")
    
    # Step 2: Validate input
    if not validate_input_file(input_file):
        print("\n❌ Validation failed. Please check the input file and try again.")
        sys.exit(1)
    
    # Step 3: Initialize components
    print("\n🔧 Initializing optimization components...")
    try:
        optimizer = ImprovedBESSOptimizer()
        investment_analyzer = InvestmentAnalyzer()
        print("✅ Components initialized")
    except Exception as e:
        print(f"❌ Error initializing components: {e}")
        sys.exit(1)
    
    # Step 4: Load market data
    try:
        market_data = load_market_data(input_file, optimizer)
    except Exception as e:
        print(f"\n❌ Failed to load market data: {e}")
        sys.exit(1)
    
    # Step 5: Run optimization pipeline
    try:
        results = run_optimization_pipeline(market_data, optimizer)
    except Exception as e:
        print(f"\n❌ Optimization pipeline failed: {e}")
        sys.exit(1)
    
    # Step 6: Generate output files
    try:
        generate_output_files(results, output_dir, optimizer, investment_analyzer, market_data)
    except Exception as e:
        print(f"\n❌ Failed to generate output files: {e}")
        sys.exit(1)
    
    # Step 7: Print summary
    print_summary(results)
    
    # Success!
    print(f"\n🕐 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n" + "=" * 70)
    print("  🎉 SUCCESS! All files generated successfully!")
    print("=" * 70)
    print(f"\n📦 Output files location: {output_dir}/")
    print("   1. TechArena_Phase1_Configuration.xlsx")
    print("   2. TechArena_Phase1_Investment.xlsx")
    print("   3. TechArena_Phase1_Operation.xlsx")
    print("\n✨ Your submission is ready for packaging!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
