# Import the generation functions from the main script
print("📁 Importing Excel generation functions...")

# Import required libraries
import openpyxl
from openpyxl import Workbook

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

# Define generation functions inline (compatible with notebook environment)
def generate_configuration_xlsx(results, output_dir, optimizer):
    """Generate Configuration Excel file with country-specific sheets"""
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
    
    print(f"   ✅ Saved: {config_file}")
    return config_file

def generate_investment_xlsx(results, output_dir):
    """Generate Investment Excel file using InvestmentAnalyzer"""
    # Find best scenario for each country (using Excel country codes)
    best_by_country = {}
    for scenario_name, result in results.items():
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
    return investment_file

def generate_operation_xlsx(results, output_dir, optimizer, market_data):
    """Generate Operation Excel file with country-specific sheets - FULL YEAR DATA"""
    # Find best scenario for each country (using Excel country codes)
    best_by_country = {}
    for scenario_name, result in results.items():
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
    return operation_file

print("✅ Generation functions defined and ready to use")
print("📝 Country mapping: DE_LU (optimization) -> DE (Excel sheets)")
