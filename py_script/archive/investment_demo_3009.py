#!/usr/bin/env python3
"""
Investment Analysis Test Script
==============================

This script demonstrates the investment optimization functionality
using a simplified approach that can work without the full Pyomo environment.
"""

import json
import pandas as pd
import numpy as np
from typing import Dict, List

class InvestmentAnalysisDemo:
    """
    Simplified investment analysis for demonstration
    """
    
    def __init__(self):
        # Country parameters from investment_opt.tex
        self.countries = {
            'DE': {'name': 'Germany', 'wacc': 8.3, 'inflation': 2.0},
            'AT': {'name': 'Austria', 'wacc': 8.3, 'inflation': 3.30},
            'CH': {'name': 'Switzerland', 'wacc': 8.3, 'inflation': 0.10},
            'CZ': {'name': 'Czech Republic', 'wacc': 12.0, 'inflation': 2.90},
            'HU': {'name': 'Hungary', 'wacc': 15.0, 'inflation': 4.60}
        }
        
        # BESS configurations (C-rate determines nominal capacity)
        self.configurations = [
            {'c_rate': 0.5, 'cycle_limit': 1.0, 'capacity_mwh': 2.0},
            {'c_rate': 1.0, 'cycle_limit': 1.0, 'capacity_mwh': 1.0},
            {'c_rate': 2.0, 'cycle_limit': 1.0, 'capacity_mwh': 0.5}
        ]
        
        # Financial constants
        self.capex_per_kwh = 200  # EUR/kWh
        self.project_lifetime = 10  # years
    
    def calculate_capex(self, capacity_mwh: float) -> float:
        """Calculate CAPEX for given capacity"""
        return self.capex_per_kwh * capacity_mwh * 1000
    
    def project_nominal_profits(self, initial_profit: float, inflation_rate: float) -> List[float]:
        """Project profits over 10 years with inflation"""
        profits = []
        for year in range(1, self.project_lifetime + 1):
            nominal_profit = initial_profit * ((1 + inflation_rate / 100) ** (year - 1))
            profits.append(nominal_profit)
        return profits
    
    def calculate_dcf_metrics(self, initial_profit: float, wacc: float, 
                            inflation: float, capacity_mwh: float) -> Dict:
        """Calculate NPV and Levelized ROI"""
        
        # Project nominal profits
        nominal_profits = self.project_nominal_profits(initial_profit, inflation)
        
        # Calculate present values
        wacc_decimal = wacc / 100
        present_values = []
        
        for year, profit in enumerate(nominal_profits, 1):
            discount_factor = 1 / ((1 + wacc_decimal) ** year)
            pv = profit * discount_factor
            present_values.append(pv)
        
        pv_total_profits = sum(present_values)
        capex = self.calculate_capex(capacity_mwh)
        npv = pv_total_profits - capex
        
        # Levelized ROI calculation
        levelized_roi = (pv_total_profits / (capex * self.project_lifetime)) * 100
        
        return {
            'npv': npv,
            'levelized_roi': levelized_roi,
            'pv_total_profits': pv_total_profits,
            'capex': capex,
            'nominal_profits': nominal_profits,
            'present_values': present_values
        }
    
    def simulate_profits(self, country_code: str, c_rate: float) -> float:
        """
        Simulate annual profits based on our previous analysis
        This replaces the actual optimization for demonstration
        """
        # Base profits from our previous revenue analysis (scaled from 2-day Austria result)
        base_profits = {
            'AT': {'0.5': 472310, '1.0': 650000, '2.0': 950000},  # EUR/year
            'DE': {'0.5': 520000, '1.0': 720000, '2.0': 1050000},  # Higher prices
            'CH': {'0.5': 450000, '1.0': 620000, '2.0': 900000},   # Lower volatility
            'CZ': {'0.5': 580000, '1.0': 800000, '2.0': 1200000},  # Higher volatility
            'HU': {'0.5': 600000, '1.0': 850000, '2.0': 1300000}   # Highest volatility
        }
        
        c_rate_str = str(c_rate)
        if country_code in base_profits and c_rate_str in base_profits[country_code]:
            return base_profits[country_code][c_rate_str]
        else:
            # Default estimation
            return 500000 * c_rate  # Rough scaling
    
    def run_analysis(self) -> pd.DataFrame:
        """Run investment analysis for all scenarios"""
        
        results = []
        
        print("Investment Analysis Results")
        print("=" * 80)
        print(f"{'Country':<12} {'Config':<8} {'Annual Profit':<15} {'NPV':<15} {'ROI %':<10} {'Profitable'}")
        print("-" * 80)
        
        for country_code, country_data in self.countries.items():
            for config in self.configurations:
                # Simulate annual profit
                annual_profit = self.simulate_profits(country_code, config['c_rate'])
                
                # Calculate DCF metrics
                dcf_result = self.calculate_dcf_metrics(
                    annual_profit,
                    country_data['wacc'],
                    country_data['inflation'],
                    config['capacity_mwh']
                )
                
                is_profitable = dcf_result['npv'] > 0
                
                print(f"{country_data['name']:<12} "
                      f"C{config['c_rate']:<7} "
                      f"{annual_profit:<15,.0f} "
                      f"{dcf_result['npv']:<15,.0f} "
                      f"{dcf_result['levelized_roi']:<10.2f} "
                      f"{'YES' if is_profitable else 'NO'}")
                
                results.append({
                    'Country': country_data['name'],
                    'Country_Code': country_code,
                    'C_Rate': config['c_rate'],
                    'Capacity_MWh': config['capacity_mwh'],
                    'WACC_%': country_data['wacc'],
                    'Inflation_%': country_data['inflation'],
                    'Annual_Profit_EUR': annual_profit,
                    'CAPEX_EUR': dcf_result['capex'],
                    'NPV_EUR': dcf_result['npv'],
                    'Levelized_ROI_%': dcf_result['levelized_roi'],
                    'PV_Total_Profits_EUR': dcf_result['pv_total_profits'],
                    'Is_Profitable': is_profitable
                })
        
        return pd.DataFrame(results)
    
    def generate_detailed_example(self, country_code: str = 'AT', c_rate: float = 0.5):
        """Generate detailed DCF table example like in the tex document"""
        
        country_data = self.countries[country_code]
        config = next(c for c in self.configurations if c['c_rate'] == c_rate)
        
        annual_profit = self.simulate_profits(country_code, c_rate)
        
        print(f"\nDetailed DCF Analysis Example: {country_data['name']} - C-rate {c_rate}")
        print("=" * 70)
        print(f"BESS Configuration: C-rate = {c_rate} C => E_nom = {config['capacity_mwh']} MWh")
        print(f"Initial CAPEX: €{self.calculate_capex(config['capacity_mwh']):,.0f}")
        print(f"Country Parameters: WACC = {country_data['wacc']}%, Inflation = {country_data['inflation']}%")
        print(f"Simulated Annual Profit (2024): €{annual_profit:,.0f}")
        print()
        
        # Calculate year-by-year breakdown
        dcf_result = self.calculate_dcf_metrics(
            annual_profit, country_data['wacc'], country_data['inflation'], config['capacity_mwh']
        )
        
        print(f"{'Year':<6} {'Nominal Profit':<15} {'Discount Factor':<15} {'Present Value':<15}")
        print("-" * 60)
        
        wacc_decimal = country_data['wacc'] / 100
        for year in range(1, self.project_lifetime + 1):
            nominal_profit = dcf_result['nominal_profits'][year-1]
            discount_factor = 1 / ((1 + wacc_decimal) ** year)
            present_value = dcf_result['present_values'][year-1]
            
            print(f"{year:<6} €{nominal_profit:<14,.0f} {discount_factor:<15.4f} €{present_value:<14,.0f}")
        
        print("-" * 60)
        print(f"{'Total':<6} {'PV(Profits)':<15} {'CAPEX':<15} {'NPV':<15}")
        print(f"{'Result':<6} €{dcf_result['pv_total_profits']:<14,.0f} €{dcf_result['capex']:<14,.0f} €{dcf_result['npv']:<14,.0f}")
        print()
        print(f"Levelized ROI = {dcf_result['pv_total_profits']:,.0f} / ({dcf_result['capex']:,.0f} × 10) × 100 = {dcf_result['levelized_roi']:.2f}%")
        
        return dcf_result

def main():
    """Main analysis function"""
    analyzer = InvestmentAnalysisDemo()
    
    # Run full analysis
    results_df = analyzer.run_analysis()
    
    print("\n")
    print("INVESTMENT SUMMARY")
    print("=" * 50)
    
    # Find best opportunities
    profitable = results_df[results_df['Is_Profitable']]
    
    if len(profitable) > 0:
        best_npv = profitable.loc[profitable['NPV_EUR'].idxmax()]
        best_roi = profitable.loc[profitable['Levelized_ROI_%'].idxmax()]
        
        print(f"Best NPV: {best_npv['Country']} C{best_npv['C_Rate']} - €{best_npv['NPV_EUR']:,.0f}")
        print(f"Best ROI: {best_roi['Country']} C{best_roi['C_Rate']} - {best_roi['Levelized_ROI_%']:.2f}%")
        print(f"Profitable scenarios: {len(profitable)} out of {len(results_df)}")
    else:
        print("No profitable scenarios found!")
    
    # Country ranking
    print("\nCountry Rankings (by average NPV):")
    country_avg = results_df.groupby('Country')['NPV_EUR'].mean().sort_values(ascending=False)
    for i, (country, avg_npv) in enumerate(country_avg.items(), 1):
        print(f"{i}. {country}: €{avg_npv:,.0f}")
    
    # Generate detailed example
    analyzer.generate_detailed_example('AT', 0.5)
    
    # Save results
    results_df.to_csv('investment_analysis_demo_results.csv', index=False)
    print(f"\nDetailed results saved to: investment_analysis_demo_results.csv")

if __name__ == "__main__":
    main()