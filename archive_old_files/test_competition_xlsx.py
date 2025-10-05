#!/usr/bin/env python3
"""
TEST: Generate TechArena 2025 Excel Files from Real Optimization Results
========================================================================

This is a test version that runs optimization on a smaller dataset (1 week)
to demonstrate the proper architecture with separated business logic and data formatting.

Key improvements:
- Uses InvestmentAnalyzer for proper DCF calculations
- Separates investment analysis from Excel generation
- Follows correct BESS specifications (4,472 kWh fixed capacity)
- Proper file naming (xlsx instead of csv)
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from py_script.investment_analysis import InvestmentAnalyzer
from typing import Dict, Any
import warnings
warnings.filterwarnings('ignore')

# Add py_script directory to path for model imports
script_dir = os.path.dirname(os.path.abspath(__file__))
py_script_dir = os.path.join(script_dir, 'py_script')
if py_script_dir not in sys.path:
    sys.path.insert(0, py_script_dir)

# Import the optimization model and investment analyzer
try:
    from model import ImprovedBESSOptimizer
    from investment_analysis import InvestmentAnalyzer
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure py_script/model.py and py_script/investment_analysis.py exist and are accessible")
    sys.exit(1)

def main():
    print("=== TEST: Generating Excel Files from Real Optimization Results (1 week) ===")
    
    # Create output directory
    output_dir = 'SoloGen_TechArena2025_Phase1_test'
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output directory: {output_dir}")
    
    # Initialize optimizer
    optimizer = ImprovedBESSOptimizer()
    
    # Load market data
    data_file = 'data/TechArena2025_data_tidy.jsonl'
    if not os.path.exists(data_file):
        print(f"❌ Error: Data file not found: {data_file}")
        return
    
    print(f"Loading market data from: {data_file}")
    try:
        market_data = optimizer.load_and_preprocess_data(data_file)
        print(f"✅ Loaded market data: {market_data.shape}")
        
        # Limit to 1 week for testing (672 intervals = 7 days * 96 intervals/day)
        market_data = market_data.iloc[:672]
        print(f"Limited to 1 week: {market_data.shape}")
        
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return
    
    # Test parameters (subset for quick testing)
    countries = ['AT']  # Start with AT since it worked
    c_rates = [0.25, 0.5]  # Just 2 C-rates
    cycle_limits = [1.0, 1.5]  # Just 2 cycle limits
    
    print(f"\\n1. Running optimization for {len(countries) * len(c_rates) * len(cycle_limits)} test scenarios...")
    all_results = {}
    best_scenario = None
    best_revenue = 0
    
    for country in countries:
        print(f"\\n  Processing country: {country}")
        try:
            country_data = optimizer.extract_country_data(market_data, country)
            
            for c_rate in c_rates:
                for cycles in cycle_limits:
                    scenario_name = f"{country}_C{c_rate}_Cyc{cycles}"
                    print(f"    Running scenario: {scenario_name}")
                    
                    try:
                        # Build and solve optimization model
                        model = optimizer.build_optimization_model(country_data, c_rate, cycles)
                        solution = optimizer.solve_model(model, 'cplex')
                        
                        if solution['status'] in ['optimal', 'feasible']:
                            # Scale to annual estimate
                            weekly_revenue = solution['objective_value']
                            annual_estimate = weekly_revenue * 52  # Scale to annual
                            
                            result = {
                                'country': country,
                                'c_rate': c_rate,
                                'cycles': cycles,
                                'objective_value': annual_estimate,  # Use annual estimate
                                'weekly_revenue': weekly_revenue,
                                'status': solution['status'],
                                'solve_time': solution['solve_time'],
                                'solution': solution  # Store full solution for operation CSV
                            }
                            all_results[scenario_name] = result
                            
                            # Track best scenario for operation CSV
                            if annual_estimate > best_revenue:
                                best_revenue = annual_estimate
                                best_scenario = result
                                
                            print(f"      ✅ Success: Weekly = €{weekly_revenue:,.0f}, Annual Est. = €{annual_estimate:,.0f}")
                        else:
                            print(f"      ❌ Failed: {solution['status']}")
                            
                    except Exception as e:
                        print(f"      ❌ Error: {str(e)}")
                        
        except Exception as e:
            print(f"  ❌ Error processing country {country}: {e}")
    
    if not all_results:
        print("❌ No successful optimizations found. Cannot generate Excel files.")
        return
    
    print(f"\\n✅ Completed optimization: {len(all_results)} successful scenarios")
    print(f"Best scenario: {best_scenario['country']}_C{best_scenario['c_rate']}_Cyc{best_scenario['cycles']} "
          f"with annual estimate €{best_scenario['objective_value']:,.0f}")
    
    # Perform investment analysis using dedicated analyzer
    print("\\n2. Performing investment analysis...")
    # Note: Investment analysis is now performed within generate_investment_xlsx
    
    # Generate test Excel files
    print("\\n3. Generating Configuration Excel file...")
    generate_configuration_xlsx(all_results, output_dir, optimizer)
    
    print("\\n4. Generating Investment Excel file...")
    generate_investment_xlsx(all_results, output_dir)
    
    print("\\n5. Generating Operation Excel file...")
    generate_operation_xlsx(all_results, output_dir, optimizer, market_data)
    
    print(f"\\n🎉 SUCCESS: Test Excel files generated with real optimization results!")

def generate_configuration_xlsx(results, output_dir, optimizer):
    """Generate Configuration Excel file with country-specific sheets"""
    # Group results by country
    results_by_country = {}
    for scenario_name, result in results.items():
        country = result['country']
        if country not in results_by_country:
            results_by_country[country] = []
        results_by_country[country].append(result)
    
    config_file = os.path.join(output_dir, 'TechArena_Phase1_Configuration.xlsx')
    
    with pd.ExcelWriter(config_file, engine='openpyxl') as writer:
        for country in ['DE', 'AT', 'CH', 'HU', 'CZ']:  # Required order
            config_data = []
            
            if country in results_by_country:
                for result in results_by_country[country]:
                    c_rate = result['c_rate']
                    cycles = result['cycles']
                    annual_revenue = result['objective_value']
                    
                    # Calculate real metrics using optimization results
                    battery_capacity_kwh = optimizer.battery_params['capacity_kwh']
                    max_power_kw = c_rate * battery_capacity_kwh
                    max_power_mw = max_power_kw / 1000
                    
                    # Yearly profits per MW (normalized)
                    yearly_profits_keur_per_mw = (annual_revenue / 1000) / max_power_mw
                    
                    # Investment cost and ROI calculation
                    investment_cost_per_kwh = 200  # EUR/kWh
                    total_investment = battery_capacity_kwh * investment_cost_per_kwh
                    levelized_roi = (annual_revenue / total_investment) * 100
                    
                    config_data.append({
                        'C-rate': c_rate,
                        'number of cycles': cycles,
                        'yearly profits [kEUR/MW]': round(yearly_profits_keur_per_mw, 2),
                        'levelized ROI [%]': round(levelized_roi, 2)
                    })
            
            # Create sheet for this country (even if empty)
            config_df = pd.DataFrame(config_data)
            config_df.to_excel(writer, sheet_name=country, index=False)
            print(f"   Created configuration sheet for {country}: {len(config_df)} scenarios")
    
    print(f"   ✅ Saved: {config_file} (Excel file with country sheets)")
    if results_by_country:
        print("   📊 Configuration Results:")
        for country, results in results_by_country.items():
            print(f"      {country}: {len(results)} scenarios")

def generate_investment_xlsx(all_results, output_dir):
    """Generate Investment Excel file with country-specific sheets using InvestmentAnalyzer"""
    
    # Initialize the investment analyzer
    analyzer = InvestmentAnalyzer()
    
    # Find best scenario for each country
    best_by_country = {}
    for scenario_name, result in all_results.items():
        country = result['country']
        if country not in best_by_country or result['objective_value'] > best_by_country[country]['objective_value']:
            best_by_country[country] = result
    
    investment_file = os.path.join(output_dir, 'TechArena_Phase1_Investment.xlsx')
    
    with pd.ExcelWriter(investment_file, engine='openpyxl') as writer:
        for country in ['DE', 'AT', 'CH', 'HU', 'CZ']:  # Required order
            if country not in best_by_country:
                # Create empty sheet if no results for this country
                empty_df = pd.DataFrame({'Note': [f'No optimization results available for {country}']})
                empty_df.to_excel(writer, sheet_name=country, index=False)
                continue
            
            best_scenario = best_by_country[country]
            annual_revenue = best_scenario['objective_value']
            c_rate = best_scenario['c_rate']  # Get the C-rate from best scenario
            
            # Perform investment analysis using the dedicated analyzer
            analysis_result = analyzer.analyze_investment(
                country=country,
                c_rate=c_rate,
                annual_revenue_2024=annual_revenue
            )
            
            # Format results for Excel output using analyzer's format method
            investment_df = analyzer.format_for_excel(analysis_result)
            investment_df.to_excel(writer, sheet_name=country, index=False)
            
            print(f"   Created investment sheet for {country}: Revenue = €{annual_revenue:,.0f}, NPV = €{analysis_result['npv']:,.0f}")
    
    print(f"   ✅ Saved: {investment_file} (Excel file with country investment analysis)")

def generate_operation_xlsx(all_results, output_dir, optimizer, market_data):
    """Generate Operation Excel file with country-specific sheets"""
    # Find best scenario for each country
    best_by_country = {}
    for scenario_name, result in all_results.items():
        country = result['country']
        if country not in best_by_country or result['objective_value'] > best_by_country[country]['objective_value']:
            best_by_country[country] = result
    
    operation_file = os.path.join(output_dir, 'TechArena_Phase1_Operation.xlsx')
    
    with pd.ExcelWriter(operation_file, engine='openpyxl') as writer:
        for country in ['DE', 'AT', 'CH', 'HU', 'CZ']:  # Required order
            if country not in best_by_country:
                # Create empty sheet if no results for this country
                empty_df = pd.DataFrame({'Note': [f'No optimization results available for {country}']})
                empty_df.to_excel(writer, sheet_name=country, index=False)
                continue
            
            best_scenario = best_by_country[country]
            print(f"   Extracting operation schedule for {country}...")
            
            # Get the optimization solution
            solution = best_scenario['solution']
            
            # Extract real operational data from solution
            country_data = optimizer.extract_country_data(market_data, country)
            
            operation_data = []
            
            # Use the available data (1 week for test)
            end_idx = min(len(country_data), 168)  # 1 week for test
            timestamps = pd.date_range('2024-01-01 00:00:00', periods=end_idx, freq='15min')
            
            # Battery parameters
            battery_capacity_kwh = optimizer.battery_params['capacity_kwh']
            
            for i, ts in enumerate(timestamps):
                if i < len(country_data):
                    t = i
                    
                    # Extract real values from optimization solution
                    charge_kw = solution['p_ch'].get(t, 0) if 'p_ch' in solution else 0
                    discharge_kw = solution['p_dis'].get(t, 0) if 'p_dis' in solution else 0
                    soc_energy_kwh = solution['e_soc'].get(t, battery_capacity_kwh * 0.5) if 'e_soc' in solution else battery_capacity_kwh * 0.5
                    
                    # Convert to required units
                    charge_mwh = (charge_kw * 0.25) / 1000  # kW to MWh for 15-min interval
                    discharge_mwh = (discharge_kw * 0.25) / 1000
                    stored_energy_mwh = soc_energy_kwh / 1000
                    soc_fraction = soc_energy_kwh / battery_capacity_kwh
                    
                    # Day-ahead market activities
                    da_buy_mwh = charge_mwh
                    da_sell_mwh = discharge_mwh
                    
                    # Ancillary services
                    block_id = country_data['block_id'].iloc[t] if t < len(country_data) else 0
                    fcr_capacity_mw = solution['c_fcr'].get(block_id, 0) if 'c_fcr' in solution else 0
                    afrr_pos_capacity_mw = solution['c_afrr_pos'].get(block_id, 0) if 'c_afrr_pos' in solution else 0
                    afrr_neg_capacity_mw = solution['c_afrr_neg'].get(block_id, 0) if 'c_afrr_neg' in solution else 0
                    
                    operation_data.append({
                        'Timestamp': ts.strftime('%Y-%m-%d %H:%M:%S'),
                        'Stored energy [MWh]': round(stored_energy_mwh, 4),
                        'SoC [-]': round(soc_fraction, 4),
                        'Charge [MWh]': round(charge_mwh, 4),
                        'Discharge [MWh]': round(discharge_mwh, 4),
                        'Day-ahead buy [MWh]': round(da_buy_mwh, 4),
                        'Day-ahead sell [MWh]': round(da_sell_mwh, 4),
                        'FCR Capacity [MW]': round(fcr_capacity_mw, 3),
                        'aFRR Capacity POS [MW]': round(afrr_pos_capacity_mw, 3),
                        'aFRR Capacity NEG [MW]': round(afrr_neg_capacity_mw, 3)
                    })
            
            operation_df = pd.DataFrame(operation_data)
            operation_df.to_excel(writer, sheet_name=country, index=False)
            
            # Summary statistics
            total_energy_charged = operation_df['Charge [MWh]'].sum()
            total_energy_discharged = operation_df['Discharge [MWh]'].sum()
            avg_soc = operation_df['SoC [-]'].mean()
            
            print(f"   Created operation sheet for {country}: {len(operation_df)} time steps")
    
    print(f"   ✅ Saved: {operation_file} (Excel file with country operation schedules)")

if __name__ == "__main__":
    main()