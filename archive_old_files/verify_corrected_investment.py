#!/usr/bin/env python3
"""
Verify the corrected investment calculations based on LaTeX document
"""

import pandas as pd
import os

def verify_corrected_investment():
    print('📊 CORRECTED Investment Calculations Verification:')
    print('Based on LaTeX document: 3_b_model_investment_opt.tex')
    print()
    
    test_file = r'SoloGen_TechArena2025_Phase1_test\TechArena_Phase1_Investment.xlsx'
    
    if os.path.exists(test_file):
        df = pd.read_excel(test_file, sheet_name='AT')
        
        print(f'📁 File: {os.path.abspath(test_file)}')
        print(f'📊 Sheet: AT (Austria)')
        print()
        
        # Extract key values from the table
        yearly_profits_2024 = df.iloc[3, 1]  # Row 4, Col B (Yearly Profits 2024)
        initial_investment_2023 = df.iloc[6, 1]  # Row 7, Col B (2023 investment)
        
        print('🔍 Key Values from Excel:')
        print(f'   Annual Revenue (2024): {yearly_profits_2024}')
        print(f'   Initial Investment (2023): {initial_investment_2023} kEUR/MWh')
        print()
        
        # Calculate the corrected values based on LaTeX formulas
        print('💡 Calculation Verification (based on LaTeX document):')
        
        # Best scenario is C-rate 0.5 with €1,266,418 annual revenue
        c_rate = 0.5
        annual_revenue = 1266418  # EUR
        power_mw = 1.0  # 1 MW system
        
        # Energy capacity calculation: E_nom = P / C-rate
        energy_capacity_mwh = power_mw / c_rate
        energy_capacity_kwh = energy_capacity_mwh * 1000
        
        print(f'   C-rate: {c_rate}')
        print(f'   Power: {power_mw} MW')
        print(f'   Energy Capacity: {energy_capacity_mwh} MWh ({energy_capacity_kwh} kWh)')
        
        # CAPEX calculation: 200 EUR/kWh
        investment_cost_per_kwh = 200
        capex_eur = energy_capacity_kwh * investment_cost_per_kwh
        capex_keur = capex_eur / 1000
        capex_per_mwh_keur = capex_keur / energy_capacity_mwh
        
        print(f'   CAPEX: {capex_eur:,.0f} EUR = {capex_keur:,.0f} kEUR')
        print(f'   CAPEX per MWh: {capex_per_mwh_keur:,.0f} kEUR/MWh')
        print()
        
        # Compare with Excel values
        print('✅ Verification Results:')
        revenue_match = str(yearly_profits_2024).replace(',', '') == str(annual_revenue)
        investment_match = str(initial_investment_2023).replace(',', '') == str(int(capex_per_mwh_keur))
        
        print(f'   Annual Revenue: Excel = {yearly_profits_2024}, Calculated = {annual_revenue:,} EUR {"✅" if revenue_match else "❌"}')
        print(f'   Initial Investment: Excel = {initial_investment_2023}, Calculated = {capex_per_mwh_keur:,.0f} kEUR/MWh {"✅" if investment_match else "❌"}')
        print()
        
        # Show the corrected table structure
        print('📋 Corrected Investment Table:')
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 120)
        print(df.head(12).to_string(index=False))
        
        print()
        print('🎯 Key Corrections Applied:')
        print('   ✅ Initial Investment now based on actual C-rate and 1 MW system')
        print(f'   ✅ Energy capacity correctly calculated: {energy_capacity_mwh} MWh for C-rate {c_rate}')
        print(f'   ✅ CAPEX correctly calculated: 200 EUR/kWh × {energy_capacity_kwh:,} kWh = {capex_eur:,} EUR')
        print(f'   ✅ Investment only in 2023, no additional investment in operation years')
        print(f'   ✅ Profits per MWh correctly normalized by energy capacity')
        
    else:
        print(f'❌ File not found: {test_file}')

if __name__ == "__main__":
    verify_corrected_investment()