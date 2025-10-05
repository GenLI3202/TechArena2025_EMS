"""
Excel File Generator for TechArena 2025 Phase 1 Submission
==========================================================

This module contains functions to generate the three required output Excel files:
1. Configuration.xlsx - Analysis of all C-rate and cycle combinations
2. Investment.xlsx - DCF analysis for best scenario per country
3. Operation.xlsx - Full year operational schedule for best scenario per country

All functions use real optimization results and handle the DE_LU -> DE country mapping.

Author: SoloGen Team
Date: October 2025
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any


def map_country_for_excel(country: str) -> str:
    """
    Map optimization country codes to Excel sheet names.
    
    Args:
        country: Optimization country code (e.g., 'DE_LU')
        
    Returns:
        str: Excel sheet name (e.g., 'DE')
    """
    if country == 'DE_LU':
        return 'DE'
    return country


def map_country_from_excel(excel_country: str) -> str:
    """
    Map Excel sheet names back to optimization country codes.
    
    Args:
        excel_country: Excel sheet name (e.g., 'DE')
        
    Returns:
        str: Optimization country code (e.g., 'DE_LU')
    """
    if excel_country == 'DE':
        return 'DE_LU'
    return excel_country


def generate_configuration_xlsx(results: Dict[str, Any], output_dir: str, 
                                optimizer) -> None:
    """
    Generate Configuration Excel file with country-specific sheets.
    
    Required columns per sheet:
    - C-rate: Configuration C-rate (0.25, 0.33, 0.50)
    - number of cycles: Daily cycle limit (1.0, 1.5, 2.0)
    - yearly profits [kEUR/MW]: Normalized yearly profits per MW
    - levelized ROI [%]: Return on investment percentage
    
    Args:
        results: Dictionary containing all scenario results
        output_dir: Output directory for Excel file
        optimizer: ImprovedBESSOptimizer instance for battery parameters
    """
    print("   Grouping results by country...")
    
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
            
            if config_data:
                print(f"      {country}: {len(config_df)} scenarios")
    
    print(f"   ✅ Configuration file created with {len(results_by_country)} country sheets")


def generate_investment_xlsx(all_results: Dict[str, Any], output_dir: str, 
                             investment_analyzer) -> None:
    """
    Generate Investment Excel file using InvestmentAnalyzer for DCF calculations.
    
    Each country sheet contains:
    - Financial parameters (WACC, inflation rate, discount rate)
    - 10-year cash flow projection
    - Levelized ROI calculation
    
    Args:
        all_results: Dictionary containing all scenario results
        output_dir: Output directory for Excel file
        investment_analyzer: InvestmentAnalyzer instance for DCF calculations
    """
    print("   Finding best scenario per country...")
    
    # Find best scenario for each country (using Excel country codes)
    best_by_country = {}
    for scenario_name, result in all_results.items():
        country = result['country']
        excel_country = map_country_for_excel(country)  # Convert DE_LU -> DE
        
        if excel_country not in best_by_country or \
           result['objective_value'] > best_by_country[excel_country]['objective_value']:
            best_by_country[excel_country] = result
    
    investment_file = os.path.join(output_dir, 'TechArena_Phase1_Investment.xlsx')
    
    with pd.ExcelWriter(investment_file, engine='openpyxl') as writer:
        for country in ['DE', 'AT', 'CH', 'HU', 'CZ']:
            if country not in best_by_country:
                # Create empty sheet if no results
                empty_df = pd.DataFrame({
                    'Note': [f'No optimization results available for {country}']
                })
                empty_df.to_excel(writer, sheet_name=country, index=False)
                continue
            
            best_scenario = best_by_country[country]
            annual_revenue = best_scenario['objective_value']
            c_rate = best_scenario['c_rate']
            
            # Use InvestmentAnalyzer for proper DCF calculation
            analysis_result = investment_analyzer.analyze_investment(
                country=country,
                c_rate=c_rate,
                annual_revenue_2024=annual_revenue
            )
            
            # Format for Excel output
            investment_df = investment_analyzer.format_for_excel(analysis_result)
            investment_df.to_excel(writer, sheet_name=country, index=False)
            
            npv = analysis_result['npv']
            levelized_roi = analysis_result['levelized_roi']
            print(f"      {country}: NPV = €{npv:,.0f}, ROI = {levelized_roi:.2f}%")
    
    print(f"   ✅ Investment file created with DCF analysis")


def generate_operation_xlsx(all_results: Dict[str, Any], output_dir: str, 
                            optimizer, market_data: pd.DataFrame) -> None:
    """
    Generate Operation Excel file with full year operational schedule.
    
    Each country sheet contains 35,136 time steps (366 days × 96 intervals/day for 2024):
    - Timestamp
    - Stored energy [MWh]
    - SoC [-]
    - Charge [MWh]
    - Discharge [MWh]
    - Day-ahead buy [MWh]
    - Day-ahead sell [MWh]
    - FCR Capacity [MW]
    - aFRR Capacity POS [MW]
    - aFRR Capacity NEG [MW]
    
    Args:
        all_results: Dictionary containing all scenario results
        output_dir: Output directory for Excel file
        optimizer: ImprovedBESSOptimizer instance
        market_data: Full market data DataFrame
    """
    print("   Extracting operational schedules...")
    
    # Find best scenario for each country
    best_by_country = {}
    for scenario_name, result in all_results.items():
        country = result['country']
        excel_country = map_country_for_excel(country)
        
        if excel_country not in best_by_country or \
           result['objective_value'] > best_by_country[excel_country]['result']['objective_value']:
            best_by_country[excel_country] = {
                'result': result,
                'optimization_country': country  # Keep original for data extraction
            }
    
    operation_file = os.path.join(output_dir, 'TechArena_Phase1_Operation.xlsx')
    
    with pd.ExcelWriter(operation_file, engine='openpyxl') as writer:
        for country in ['DE', 'AT', 'CH', 'HU', 'CZ']:
            if country not in best_by_country:
                # Create empty sheet if no results
                empty_df = pd.DataFrame({
                    'Note': [f'No optimization results available for {country}']
                })
                empty_df.to_excel(writer, sheet_name=country, index=False)
                continue
            
            best_info = best_by_country[country]
            best_scenario = best_info['result']
            optimization_country = best_info['optimization_country']
            
            print(f"      {country}: Processing full year data...")
            
            # Get the optimization solution
            solution = best_scenario['solution']
            
            # Extract country-specific data using ORIGINAL country code
            country_data = optimizer.extract_country_data(market_data, optimization_country)
            
            operation_data = []
            
            # *** CRITICAL: Use FULL YEAR data (all time steps) ***
            # 2024 is a leap year: 366 days × 96 intervals/day = 35,136 intervals
            end_idx = len(country_data)
            timestamps = pd.date_range('2024-01-01 00:00:00', periods=end_idx, freq='15min')
            
            # Battery parameters
            battery_capacity_kwh = optimizer.battery_params['capacity_kwh']
            
            # Process all time steps
            for i, ts in enumerate(timestamps):
                if i < len(country_data):
                    t = i
                    
                    # *** CRITICAL FIX: Solution indices stored as STRINGS ***
                    t_str = str(t)
                    
                    # Extract real values from optimization solution
                    charge_kw = solution['p_ch'].get(t_str, 0) if 'p_ch' in solution else 0
                    discharge_kw = solution['p_dis'].get(t_str, 0) if 'p_dis' in solution else 0
                    soc_energy_kwh = solution['e_soc'].get(t_str, battery_capacity_kwh * 0.5) \
                                     if 'e_soc' in solution else battery_capacity_kwh * 0.5
                    
                    # Convert to required units
                    charge_mwh = (charge_kw * 0.25) / 1000  # kW to MWh for 15-min
                    discharge_mwh = (discharge_kw * 0.25) / 1000
                    stored_energy_mwh = soc_energy_kwh / 1000
                    soc_fraction = soc_energy_kwh / battery_capacity_kwh
                    
                    # Day-ahead market activities
                    da_buy_mwh = charge_mwh
                    da_sell_mwh = discharge_mwh
                    
                    # *** CRITICAL FIX: Extract bid information with string keys ***
                    block_id = country_data['block_id'].iloc[t] if t < len(country_data) else 0
                    block_id_str = str(int(block_id))
                    
                    # Extract capacity bids from solution
                    fcr_capacity_mw = solution['c_fcr'].get(block_id_str, 0) \
                                     if 'c_fcr' in solution else 0
                    afrr_pos_capacity_mw = solution['c_afrr_pos'].get(block_id_str, 0) \
                                          if 'c_afrr_pos' in solution else 0
                    afrr_neg_capacity_mw = solution['c_afrr_neg'].get(block_id_str, 0) \
                                          if 'c_afrr_neg' in solution else 0
                    
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
                        print(f"         Progress: {i + 1}/{end_idx} time steps...")
            
            # Create DataFrame and save
            operation_df = pd.DataFrame(operation_data)
            operation_df.to_excel(writer, sheet_name=country, index=False)
            
            # Calculate summary statistics
            total_charged = operation_df['Charge [MWh]'].sum()
            total_discharged = operation_df['Discharge [MWh]'].sum()
            total_fcr = operation_df['FCR Capacity [MW]'].sum()
            total_afrr_pos = operation_df['aFRR Capacity POS [MW]'].sum()
            total_afrr_neg = operation_df['aFRR Capacity NEG [MW]'].sum()
            
            print(f"      {country}: {len(operation_df)} time steps")
            print(f"         Charged: {total_charged:.1f} MWh, "
                  f"Discharged: {total_discharged:.1f} MWh")
            print(f"         FCR: {total_fcr:.1f} MW·h, "
                  f"aFRR+: {total_afrr_pos:.1f} MW·h, "
                  f"aFRR-: {total_afrr_neg:.1f} MW·h")
    
    print(f"   ✅ Operation file created with full year schedules")
