#!/usr/bin/env python3
"""
Generate TechArena 2025 Phase 1 Competition Excel Files from Real Optimization Results
=====================================================================================

This script orchestrates the complete competition file generation process:
1. Runs optimization models to get real revenue data
2. Uses InvestmentAnalyzer for proper DCF calculations  
3. Generates Excel files with country-specific sheets

The script separates business logic (investment analysis) from data formatting.

Key differences from dummy file generators:
- Actually runs Pyomo optimization models
- Uses dedicated InvestmentAnalyzer for DCF calculations
- Extracts real decision variables (p_ch, p_dis, e_soc, etc.)
- Uses real objective values for revenue calculations
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
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

# Country mapping: optimization uses 'DE_LU', but Excel sheets need 'DE'
def map_country_for_excel(country):
    """Map optimization country codes to Excel sheet names"""
    if country == 'DE_LU':
        return 'DE'
    return country

def map_country_from_excel(excel_country):
    """Map Excel sheet names back to optimization country codes"""
    if excel_country == 'DE':
        return 'DE_LU'
    return excel_country

def main():
    print("=== Generating TechArena 2025 Phase 1 Excel Files from Real Optimization Results ===")
    print("This will run actual optimization models and extract real solution data")
    
    # Create output directory
    output_dir = 'SoloGen_TechArena2025_Phase1'
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output directory: {output_dir}")
    
    # Initialize optimizer and investment analyzer
    optimizer = ImprovedBESSOptimizer()
    investment_analyzer = InvestmentAnalyzer()
    
    # Load market data
    data_file = 'data/TechArena2025_data_tidy.jsonl'
    if not os.path.exists(data_file):
        print(f"❌ Error: Data file not found: {data_file}")
        return
    
    print(f"Loading market data from: {data_file}")
    try:
        market_data = optimizer.load_and_preprocess_data(data_file)
        print(f"✅ Loaded market data: {market_data.shape}")
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return
    
    # Competition parameters - ALL 5 countries as required
    # Note: Use 'DE_LU' for optimization (matches data), will be mapped to 'DE' for Excel output
    countries = ['DE_LU', 'AT', 'CH', 'HU', 'CZ']
    c_rates = [0.25, 0.33, 0.5]
    cycle_limits = [1.0, 1.5, 2.0]
    
    # Step 1: Run optimization for all scenarios to get real results
    print("\n1. Running optimization for all scenarios...")
    all_results = {}
    best_scenario = None
    best_revenue = 0
    
    for country in countries:
        print(f"\n  Processing country: {country}")
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
                            result = {
                                'country': country,
                                'c_rate': c_rate,
                                'cycles': cycles,
                                'objective_value': solution['objective_value'],
                                'status': solution['status'],
                                'solve_time': solution['solve_time'],
                                'solution': solution  # Store full solution for operation CSV
                            }
                            all_results[scenario_name] = result
                            
                            # Track best scenario for operation CSV
                            if solution['objective_value'] > best_revenue:
                                best_revenue = solution['objective_value']
                                best_scenario = result
                                
                            print(f"      ✅ Success: Revenue = €{solution['objective_value']:,.0f}")
                        else:
                            print(f"      ❌ Failed: {solution['status']}")
                            
                    except Exception as e:
                        print(f"      ❌ Error: {str(e)}")
                        
        except Exception as e:
            print(f"  ❌ Error processing country {country}: {e}")
    
    if not all_results:
        print("❌ No successful optimizations found. Cannot generate Excel files.")
        return
    
    print(f"\n✅ Completed optimization: {len(all_results)} successful scenarios")
    print(f"Best scenario: {best_scenario['country']}_C{best_scenario['c_rate']}_Cyc{best_scenario['cycles']} "
          f"with revenue €{best_scenario['objective_value']:,.0f}")
    
    # Step 2: Generate Excel files using calculated results
    print("\n2. Generating Configuration Excel file...")
    generate_configuration_xlsx(all_results, output_dir, optimizer)
    
    print("\n3. Generating Investment Excel file...")
    generate_investment_xlsx(all_results, output_dir, investment_analyzer)
    
    print("\n4. Generating Operation Excel file...")
    generate_operation_xlsx(all_results, output_dir, optimizer, market_data)
    
    print(f"\n🎉 SUCCESS: All TechArena 2025 Phase 1 Excel files generated with real optimization results!")
    print(f"\nOutput Directory: {output_dir}/")
    print("📁 Generated Files (Excel format with country sheets):")
    print("   1. TechArena_Phase1_Configuration.xlsx")
    print("   2. TechArena_Phase1_Investment.xlsx") 
    print("   3. TechArena_Phase1_Operation.xlsx")

def generate_configuration_xlsx(results, output_dir, optimizer):
    """Generate Configuration Excel file with country-specific sheets as required"""
    # Group results by country (using Excel country codes)
    results_by_country = {}
    for scenario_name, result in results.items():
        country = result['country']
        excel_country = map_country_for_excel(country)  # Convert DE_LU -> DE
        
        if excel_country not in results_by_country:
            results_by_country[excel_country] = []
        results_by_country[excel_country].append(result)
    
    # Create Excel file with country sheets
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
    
    print(f"   ✅ Saved: {config_file} (Excel file with {len(results_by_country)} country sheets)")
    print(f"📝 Country mapping: DE_LU (optimization) -> DE (Excel sheets)")

def generate_investment_xlsx(all_results, output_dir, investment_analyzer):
    """Generate Investment Excel file using InvestmentAnalyzer"""
    # Find best scenario for each country (using Excel country codes)
    best_by_country = {}
    for scenario_name, result in all_results.items():
        country = result['country']
        excel_country = map_country_for_excel(country)  # Convert DE_LU -> DE
        
        if excel_country not in best_by_country or result['objective_value'] > best_by_country[excel_country]['objective_value']:
            best_by_country[excel_country] = result
    
    investment_file = os.path.join(output_dir, 'TechArena_Phase1_Investment.xlsx')
    
    with pd.ExcelWriter(investment_file, engine='openpyxl') as writer:
        for country in ['DE', 'AT', 'CH', 'HU', 'CZ']:
            if country not in best_by_country:
                empty_df = pd.DataFrame({'Note': [f'No optimization results available for {country}']})
                empty_df.to_excel(writer, sheet_name=country, index=False)
                continue
            
            best_scenario = best_by_country[country]
            annual_revenue = best_scenario['objective_value']
            c_rate = best_scenario['c_rate']
            
            # Use InvestmentAnalyzer (pass Excel country code)
            analysis_result = investment_analyzer.analyze_investment(
                country=country,
                c_rate=c_rate,
                annual_revenue_2024=annual_revenue
            )
            
            # Format for Excel
            investment_df = investment_analyzer.format_for_excel(analysis_result)
            investment_df.to_excel(writer, sheet_name=country, index=False)
            print(f"   Created investment sheet for {country}: NPV = €{analysis_result['npv']:,.0f}")
    
    print(f"   ✅ Saved: {investment_file}")

def generate_operation_xlsx(all_results, output_dir, optimizer, market_data):
    """Generate Operation Excel file with country-specific sheets - FULL YEAR DATA"""
    # Find best scenario for each country (using Excel country codes)
    best_by_country = {}
    for scenario_name, result in all_results.items():
        country = result['country']
        excel_country = map_country_for_excel(country)  # Convert DE_LU -> DE
        
        # Compare objective values properly
        if excel_country not in best_by_country or result['objective_value'] > best_by_country[excel_country]['result']['objective_value']:
            best_by_country[excel_country] = {
                'result': result,
                'optimization_country': country  # Keep original country for data extraction
            }
    
    operation_file = os.path.join(output_dir, 'TechArena_Phase1_Operation.xlsx')
    
    with pd.ExcelWriter(operation_file, engine='openpyxl') as writer:
        for country in ['DE', 'AT', 'CH', 'HU', 'CZ']:  # Required order
            if country not in best_by_country:
                # Create empty sheet if no results for this country
                empty_df = pd.DataFrame({'Note': [f'No optimization results available for {country}']})
                empty_df.to_excel(writer, sheet_name=country, index=False)
                continue
            
            best_info = best_by_country[country]
            best_scenario = best_info['result']
            optimization_country = best_info['optimization_country']  # Use original country code
            
            print(f"   Extracting operation schedule for {country} (using data from {optimization_country})...")
            
            # Get the optimization solution
            solution = best_scenario['solution']
            
            # Extract real operational data from solution using ORIGINAL country code
            country_data = optimizer.extract_country_data(market_data, optimization_country)
            
            operation_data = []
            
            # *** FIXED: Use FULL YEAR data (all time steps) ***
            # Full year = 35136 intervals for 2024 (leap year: 366 days * 96 intervals/day)
            end_idx = len(country_data)  # Use ALL data points
            timestamps = pd.date_range('2024-01-01 00:00:00', periods=end_idx, freq='15min')
            
            print(f"      Processing {end_idx} time steps (full year)...")
            
            # Battery parameters
            battery_capacity_kwh = optimizer.battery_params['capacity_kwh']
            
            for i, ts in enumerate(timestamps):
                if i < len(country_data):
                    t = i
                    
                    # *** CRITICAL FIX: Solution indices are stored as STRINGS, not integers ***
                    t_str = str(t)  # Convert index to string for dictionary lookup
                    
                    # Extract real values from optimization solution
                    charge_kw = solution['p_ch'].get(t_str, 0) if 'p_ch' in solution else 0
                    discharge_kw = solution['p_dis'].get(t_str, 0) if 'p_dis' in solution else 0
                    soc_energy_kwh = solution['e_soc'].get(t_str, battery_capacity_kwh * 0.5) if 'e_soc' in solution else battery_capacity_kwh * 0.5
                    
                    # Convert to required units
                    charge_mwh = (charge_kw * 0.25) / 1000  # kW to MWh for 15-min interval
                    discharge_mwh = (discharge_kw * 0.25) / 1000
                    stored_energy_mwh = soc_energy_kwh / 1000
                    soc_fraction = soc_energy_kwh / battery_capacity_kwh
                    
                    # Day-ahead market activities
                    da_buy_mwh = charge_mwh
                    da_sell_mwh = discharge_mwh
                    
                    # *** FIXED: Extract bid information from solution (ancillary services) ***
                    # Get block ID for this time step and convert to string
                    block_id = country_data['block_id'].iloc[t] if t < len(country_data) else 0
                    block_id_str = str(int(block_id))  # Convert to string for dictionary lookup
                    
                    # Extract capacity bids (these ARE the bid variables)
                    fcr_capacity_mw = solution['c_fcr'].get(block_id_str, 0) if 'c_fcr' in solution else 0
                    afrr_pos_capacity_mw = solution['c_afrr_pos'].get(block_id_str, 0) if 'c_afrr_pos' in solution else 0
                    afrr_neg_capacity_mw = solution['c_afrr_neg'].get(block_id_str, 0) if 'c_afrr_neg' in solution else 0
                    
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
                    
                    # Progress indicator for large datasets
                    if (i + 1) % 10000 == 0:
                        print(f"      Progress: {i + 1}/{end_idx} time steps processed...")
            
            operation_df = pd.DataFrame(operation_data)
            operation_df.to_excel(writer, sheet_name=country, index=False)
            
            # Summary statistics
            total_energy_charged = operation_df['Charge [MWh]'].sum()
            total_energy_discharged = operation_df['Discharge [MWh]'].sum()
            total_fcr_capacity = operation_df['FCR Capacity [MW]'].sum()
            total_afrr_pos = operation_df['aFRR Capacity POS [MW]'].sum()
            total_afrr_neg = operation_df['aFRR Capacity NEG [MW]'].sum()
            
            print(f"   Created operation sheet for {country}: {len(operation_df)} time steps (full year)")
            print(f"      - Charged: {total_energy_charged:.2f} MWh, Discharged: {total_energy_discharged:.2f} MWh")
            print(f"      - Total FCR: {total_fcr_capacity:.2f} MW·h, aFRR+: {total_afrr_pos:.2f} MW·h, aFRR-: {total_afrr_neg:.2f} MW·h")
    
    print(f"   ✅ Saved: {operation_file}")

def generate_sample_operation_csv(best_scenario, output_dir, optimizer):
    """Fallback: Generate sample operation CSV if real data is unavailable"""
    print("   Generating sample operation data...")
    
    # Generate sample data based on best scenario parameters
    c_rate = best_scenario['c_rate']
    battery_capacity_kwh = optimizer.battery_params['capacity_kwh']
    battery_capacity_mwh = battery_capacity_kwh / 1000
    max_power_mw = (c_rate * battery_capacity_kwh) / 1000
    
    # Generate 1 month of sample data
    timestamps = pd.date_range('2024-01-01 00:00:00', '2024-01-31 23:45:00', freq='15min')
    operation_data = []
    
    current_soc = 0.5  # Start at 50%
    np.random.seed(42)  # For reproducible results
    
    for ts in timestamps:
        hour = ts.hour
        
        # Simple operation pattern
        if 2 <= hour <= 6:  # Night charging
            charge_mwh = min(max_power_mw * 0.25, (0.8 - current_soc) * battery_capacity_mwh) * 0.25
            discharge_mwh = 0
        elif 17 <= hour <= 20:  # Evening discharge
            charge_mwh = 0
            discharge_mwh = min(max_power_mw * 0.25, (current_soc - 0.2) * battery_capacity_mwh) * 0.25
        else:
            charge_mwh = 0
            discharge_mwh = 0
        
        # Update SoC
        soc_change = (charge_mwh - discharge_mwh) / battery_capacity_mwh
        current_soc = np.clip(current_soc + soc_change, 0.1, 0.9)
        stored_energy_mwh = current_soc * battery_capacity_mwh
        
        operation_data.append({
            'Timestamp': ts.strftime('%Y-%m-%d %H:%M:%S'),
            'Stored energy [MWh]': round(stored_energy_mwh, 4),
            'SoC [-]': round(current_soc, 4),
            'Charge [MWh]': round(charge_mwh, 4),
            'Discharge [MWh]': round(discharge_mwh, 4),
            'Day-ahead buy [MWh]': round(charge_mwh, 4),
            'Day-ahead sell [MWh]': round(discharge_mwh, 4),
            'FCR Capacity [MW]': 0,
            'aFRR Capacity POS [MW]': 0,
            'aFRR Capacity NEG [MW]': 0
        })
    
    operation_df = pd.DataFrame(operation_data)
    operation_file = os.path.join(output_dir, 'TechArena_Phase1_Operation.csv')
    operation_df.to_csv(operation_file, index=False)
    print(f"   ✅ Saved: {operation_file} ({len(operation_df)} sample time steps)")

if __name__ == "__main__":
    main()