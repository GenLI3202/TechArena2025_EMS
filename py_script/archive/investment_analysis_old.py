#!/usr/bin/env python3
"""
Investment Optimization Module for BESS Deployment Analysis
==========================================================

This module implements the 10-year Discounted Cash Flow (DCF) analysis
as specified in the investment_opt.tex document to evaluate the financial
viability of BESS deployments across different countries and configurations.

Key Features:
- 10-year DCF analysis with country-specific WACC and inflation rates
- Net Present Value (NPV) and Levelized ROI calculations
- Scalable testing from 2-day to full year scenarios
- Multi-country and multi-configuration analysis
"""

from pathlib import Path
import sys
import json
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging

# repo_root = Path(r"H:\TUM-PC\TUM_CEM_PhD\a_tech_arena_hw\TechArena2025_EMS")
# if str(repo_root) not in sys.path:
#     sys.path.append(str(repo_root))
# sys.path.append('py_script')


# Import our optimization model
from model import BESSOptimizer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CountryParameters:
    """Country-specific financial parameters for DCF analysis"""
    name: str
    code: str
    wacc: float  # Weighted Average Cost of Capital (%)
    inflation: float  # Annual inflation rate (%)

@dataclass
class BESSConfiguration:
    """BESS technical configuration parameters"""
    c_rate: float
    cycle_limit: float
    nominal_capacity_mwh: float  # Fixed at 4.472 MWh per project specification

    @property
    def name(self):
        return f"C{self.c_rate}_Cyc{self.cycle_limit}"

@dataclass
class DCFResult:
    """Results from DCF analysis"""
    country: str
    config: str
    annual_profit_2024: float
    npv: float
    levelized_roi: float
    capex: float
    pv_total_profits: float
    is_profitable: bool

class InvestmentAnalyzer:
    """
    Investment optimization analyzer implementing 10-year DCF analysis
    """
    
    def __init__(self):
        self.optimizer = BESSOptimizer()
        
        # Country parameters from investment_opt.tex Table
        self.countries = {
            'DE': CountryParameters('Germany', 'DE', 8.3, 2.0),
            'AT': CountryParameters('Austria', 'AT', 8.3, 3.30),
            'CH': CountryParameters('Switzerland', 'CH', 8.3, 0.10),
            'CZ': CountryParameters('Czech Republic', 'CZ', 12.0, 2.90),
            'HU': CountryParameters('Hungary', 'HU', 15.0, 4.60)
        }
        
        # BESS configurations per project specification
        # Fixed parameters: E_nom = 4472 kWh (4.472 MWh), P_rated = 2236 kW
        # C-rate scenarios: 0.25C, 0.33C, 0.50C
        # Cycle limit scenarios: 1.0, 1.5, 2.0 cycles/day
        # Total: 3 × 3 = 9 configurations
        fixed_capacity_mwh = 4.472  # MWh - constant for all configurations

        self.configurations = [
            # C-rate 0.25C (P_max = 1118 kW)
            BESSConfiguration(0.25, 1.0, fixed_capacity_mwh),
            BESSConfiguration(0.25, 1.5, fixed_capacity_mwh),
            BESSConfiguration(0.25, 2.0, fixed_capacity_mwh),
            # C-rate 0.33C (P_max = 1476 kW)
            BESSConfiguration(0.33, 1.0, fixed_capacity_mwh),
            BESSConfiguration(0.33, 1.5, fixed_capacity_mwh),
            BESSConfiguration(0.33, 2.0, fixed_capacity_mwh),
            # C-rate 0.50C (P_max = 2236 kW)
            BESSConfiguration(0.50, 1.0, fixed_capacity_mwh),
            BESSConfiguration(0.50, 1.5, fixed_capacity_mwh),
            BESSConfiguration(0.50, 2.0, fixed_capacity_mwh),
        ]
        
        # Financial constants
        self.capex_per_kwh = 200  # EUR/kWh as specified
        self.project_lifetime = 10  # years
        
    def calculate_capex(self, nominal_capacity_mwh: float) -> float:
        """Calculate CAPEX for given nominal capacity"""
        return self.capex_per_kwh * nominal_capacity_mwh * 1000  # Convert MWh to kWh
    
    def project_nominal_profits(self, initial_profit: float, inflation_rate: float) -> List[float]:
        """
        Project nominal profits over 10-year horizon
        Formula: Π_y = Π_2024 * (1 + π)^(y-1)
        """
        profits = []
        for year in range(1, self.project_lifetime + 1):
            nominal_profit = initial_profit * ((1 + inflation_rate / 100) ** (year - 1))
            profits.append(nominal_profit)
        return profits
    
    def calculate_dcf_metrics(self, initial_profit: float, country_params: CountryParameters, 
                            nominal_capacity_mwh: float) -> Tuple[float, float, float]:
        """
        Calculate DCF metrics: NPV and Levelized ROI
        
        Returns:
            Tuple of (NPV, Levelized ROI, PV of total profits)
        """
        # Step 1: Project nominal profits
        nominal_profits = self.project_nominal_profits(initial_profit, country_params.inflation)
        
        # Step 2: Calculate present values
        wacc = country_params.wacc / 100  # Convert percentage to decimal
        present_values = []
        
        for year, profit in enumerate(nominal_profits, 1):
            discount_factor = 1 / ((1 + wacc) ** year)
            pv = profit * discount_factor
            present_values.append(pv)
        
        pv_total_profits = sum(present_values)
        
        # Step 3: Calculate CAPEX and NPV
        capex = self.calculate_capex(nominal_capacity_mwh)
        npv = pv_total_profits - capex
        
        # Step 4: Calculate Levelized ROI
        # Formula: PV(Total Profits) / (CAPEX × Lifetime) × 100
        levelized_roi = (pv_total_profits / (capex * self.project_lifetime)) * 100
        
        return npv, levelized_roi, pv_total_profits
    
    def run_operational_optimization(self, data_file: str, country_code: str, 
                                   config: BESSConfiguration, 
                                   scale_factor: float = 1.0) -> Optional[float]:
        """
        Run operational optimization for given scenario
        
        Args:
            data_file: Path to market data file
            country_code: Country code for analysis
            config: BESS configuration
            scale_factor: Scaling factor for annual projection (e.g., 365/2 for 2-day test)
        
        Returns:
            Scaled annual profit or None if optimization failed
        """
        try:
            result = self.optimizer.optimize_bess(
                data_file=data_file,
                c_rate=config.c_rate,
                cycle_limit=config.cycle_limit
            )
            
            if result['success']:
                # Scale the profit to annual equivalent
                annual_profit = result['objective_value'] * scale_factor
                return annual_profit
            else:
                logger.warning(f"Optimization failed for {country_code}-{config.name}: {result.get('error', 'Unknown')}")
                return None
                
        except Exception as e:
            logger.error(f"Error in optimization for {country_code}-{config.name}: {str(e)}")
            return None
    
    def analyze_single_scenario(self, data_file: str, country_code: str, 
                              config: BESSConfiguration, scale_factor: float = 1.0) -> Optional[DCFResult]:
        """
        Perform complete DCF analysis for a single scenario
        """
        logger.info(f"Analyzing {country_code}-{config.name}...")
        
        # Get country parameters
        if country_code not in self.countries:
            logger.error(f"Unknown country code: {country_code}")
            return None
        
        country_params = self.countries[country_code]
        
        # Run operational optimization
        annual_profit = self.run_operational_optimization(data_file, country_code, config, scale_factor)
        if annual_profit is None:
            return None
        
        # Calculate DCF metrics
        npv, levelized_roi, pv_total_profits = self.calculate_dcf_metrics(
            annual_profit, country_params, config.nominal_capacity_mwh
        )
        
        capex = self.calculate_capex(config.nominal_capacity_mwh)
        
        return DCFResult(
            country=country_params.name,
            config=config.name,
            annual_profit_2024=annual_profit,
            npv=npv,
            levelized_roi=levelized_roi,
            capex=capex,
            pv_total_profits=pv_total_profits,
            is_profitable=(npv > 0)
        )
    
    def create_test_dataset(self, source_file: str, country_code: str, 
                          test_days: int = 2) -> str:
        """
        Create test dataset for smaller scale analysis
        """
        output_file = f"test_{country_code}_{test_days}days.jsonl"
        
        with open(source_file, 'r') as f:
            all_data = [json.loads(line) for line in f]
        
        # Filter for specific country and time period
        country_data = [d for d in all_data if d['country'] == country_code]
        test_data = country_data[:test_days * 96]  # 96 timesteps per day
        
        with open(output_file, 'w') as f:
            for record in test_data:
                f.write(json.dumps(record) + '\n')
        
        logger.info(f"Created test dataset: {output_file} with {len(test_data)} records")
        return output_file
    
    def run_investment_analysis(self, source_data_file: str, test_days: int = 2, 
                              countries: List[str] = None, 
                              configurations: List[int] = None) -> pd.DataFrame:
        """
        Run comprehensive investment analysis
        
        Args:
            source_data_file: Path to full market data file
            test_days: Number of days for testing (will be scaled to annual)
            countries: List of country codes to analyze (default: all)
            configurations: List of configuration indices to test (default: all)
        
        Returns:
            DataFrame with analysis results
        """
        if countries is None:
            countries = list(self.countries.keys())
        
        if configurations is None:
            configurations = list(range(len(self.configurations)))
        
        # Calculate scaling factor
        scale_factor = 365 / test_days
        
        results = []
        
        for country_code in countries:
            # Create test dataset for this country
            test_file = self.create_test_dataset(source_data_file, country_code, test_days)
            
            try:
                for config_idx in configurations:
                    config = self.configurations[config_idx]
                    
                    result = self.analyze_single_scenario(
                        test_file, country_code, config, scale_factor
                    )
                    
                    if result:
                        results.append({
                            'Country': result.country,
                            'Country_Code': country_code,
                            'Configuration': result.config,
                            'C_Rate': config.c_rate,
                            'Cycle_Limit': config.cycle_limit,
                            'Nominal_Capacity_MWh': config.nominal_capacity_mwh,
                            'CAPEX_EUR': result.capex,
                            'Annual_Profit_2024_EUR': result.annual_profit_2024,
                            'NPV_EUR': result.npv,
                            'Levelized_ROI_Percent': result.levelized_roi,
                            'PV_Total_Profits_EUR': result.pv_total_profits,
                            'Is_Profitable': result.is_profitable,
                            'WACC_Percent': self.countries[country_code].wacc,
                            'Inflation_Percent': self.countries[country_code].inflation
                        })
            
            finally:
                # Clean up test file
                import os
                if os.path.exists(test_file):
                    os.remove(test_file)
        
        return pd.DataFrame(results)
    
    def generate_investment_report(self, results_df: pd.DataFrame) -> str:
        """
        Generate comprehensive investment analysis report
        """
        report = []
        report.append("BESS Investment Analysis Report")
        report.append("=" * 50)
        report.append("")
        
        # Summary statistics
        total_scenarios = len(results_df)
        profitable_scenarios = len(results_df[results_df['Is_Profitable']])
        
        report.append(f"Total scenarios analyzed: {total_scenarios}")
        report.append(f"Profitable scenarios: {profitable_scenarios} ({profitable_scenarios/total_scenarios*100:.1f}%)")
        report.append("")
        
        # Best investment opportunities
        if profitable_scenarios > 0:
            best_npv = results_df.loc[results_df['NPV_EUR'].idxmax()]
            best_roi = results_df.loc[results_df['Levelized_ROI_Percent'].idxmax()]
            
            report.append("BEST INVESTMENT OPPORTUNITIES")
            report.append("-" * 30)
            report.append(f"Highest NPV: {best_npv['Country']} - {best_npv['Configuration']}")
            report.append(f"  NPV: {best_npv['NPV_EUR']:,.0f} EUR")
            report.append(f"  ROI: {best_npv['Levelized_ROI_Percent']:.2f}%")
            report.append("")
            
            report.append(f"Highest ROI: {best_roi['Country']} - {best_roi['Configuration']}")
            report.append(f"  ROI: {best_roi['Levelized_ROI_Percent']:.2f}%")
            report.append(f"  NPV: {best_roi['NPV_EUR']:,.0f} EUR")
            report.append("")
        
        # Country ranking
        country_summary = results_df.groupby('Country').agg({
            'NPV_EUR': 'mean',
            'Levelized_ROI_Percent': 'mean',
            'Is_Profitable': 'sum'
        }).round(2)
        country_summary['Profitable_Count'] = country_summary['Is_Profitable']
        country_summary = country_summary.sort_values('NPV_EUR', ascending=False)
        
        report.append("COUNTRY RANKING (by average NPV)")
        report.append("-" * 40)
        for country, row in country_summary.iterrows():
            report.append(f"{country:<15} NPV: {row['NPV_EUR']:>10,.0f} EUR, "
                         f"ROI: {row['Levelized_ROI_Percent']:>6.2f}%, "
                         f"Profitable: {int(row['Profitable_Count'])}/9")
        
        report.append("")
        
        # Configuration analysis
        config_summary = results_df.groupby('Configuration').agg({
            'NPV_EUR': 'mean',
            'Levelized_ROI_Percent': 'mean',
            'Is_Profitable': 'sum'
        }).round(2)
        config_summary = config_summary.sort_values('NPV_EUR', ascending=False)
        
        report.append("CONFIGURATION RANKING (by average NPV)")
        report.append("-" * 45)
        for config, row in config_summary.iterrows():
            report.append(f"{config:<12} NPV: {row['NPV_EUR']:>10,.0f} EUR, "
                         f"ROI: {row['Levelized_ROI_Percent']:>6.2f}%, "
                         f"Profitable: {int(row['Is_Profitable'])}/9")
        
        return "\n".join(report)

def main():
    """
    Main function for running investment analysis
    """
    print("BESS Investment Optimization Analysis")
    print("=" * 50)
    
    # Initialize analyzer
    analyzer = InvestmentAnalyzer()
    
    # Configuration for dummy test
    test_days = 2  # Start with 2-day test (scalable to 365)
    source_data = '../data/TechArena2025_data_tidy.jsonl'
    
    # Run analysis on subset for testing (first 3 countries, first 3 configurations)
    test_countries = ['AT', 'DE', 'CH']  # Start with these for testing
    test_configs = [0, 1, 2]  # First 3 configs: 0.25C with cycles 1.0, 1.5, 2.0
    
    print(f"Running {test_days}-day test analysis...")
    print(f"Countries: {test_countries}")
    print(f"Configurations: {[analyzer.configurations[i].name for i in test_configs]}")
    print(f"Scale factor: {365/test_days:.1f}x (to annual)")
    print()
    
    # Run analysis
    results_df = analyzer.run_investment_analysis(
        source_data_file=source_data,
        test_days=test_days,
        countries=test_countries,
        configurations=test_configs
    )
    
    if not results_df.empty:
        # Generate report
        report = analyzer.generate_investment_report(results_df)
        print(report)
        
        # Save detailed results
        output_file = f'investment_analysis_results_{test_days}days.csv'
        results_df.to_csv(output_file, index=False)
        print(f"\nDetailed results saved to: {output_file}")
        
        # Save report
        report_file = f'investment_analysis_report_{test_days}days.txt'
        with open(report_file, 'w') as f:
            f.write(report)
        print(f"Report saved to: {report_file}")
        
    else:
        print("No successful results obtained!")

if __name__ == "__main__":
    main()