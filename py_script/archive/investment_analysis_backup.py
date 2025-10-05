#!/usr/bin/env python3
"""
Investment Analysis Module for TechArena 2025 Phase 1
=====================================================

Investment Optimization Module for BESS Deployment Analysis

This module provides the InvestmentAnalyzer class for performing detailed
Discounted Cash Flow (DCF) analysis for Battery Energy Storage System (BESS)
investments according to TechArena 2025 competition specifications.

Key Features:
- Fixed BESS capacity (4,472 kWh) with configurable C-rates
- Country-specific financial parameters (WACC, inflation)
- 10-year DCF analysis with nominal cash flows
- NPV and levelized ROI calculations
- Excel-compatible output formatting

Competition Specifications:
- BESS Capacity: 4,472 kWh (fixed)
- BESS Power: 2,236 kW (rated)
- Investment Cost: 200 EUR/kWh
- C-rate Options: 0.25C, 0.33C, 0.50C
- Analysis Period: 2024-2033 (10 years operation)
- Investment Year: 2023
"""



This module handles all investment optimization calculations based on the LaTeX documentThis module implements the 10-year Discounted Cash Flow (DCF) analysis

specifications and competition requirements. It separates business logic from data output.as specified in the investment_opt.tex document to evaluate the financial

viability of BESS deployments across different countries and configurations.

Key Features:

- DCF analysis with nominal cash flows and nominal discount ratesKey Features:

- Country-specific WACC and inflation rates- 10-year DCF analysis with country-specific WACC and inflation rates

- Proper BESS configuration parameters (fixed 4,472 kWh capacity)- Net Present Value (NPV) and Levelized ROI calculations

- Levelized ROI calculations as per competition guidelines- Scalable testing from 2-day to full year scenarios

- Multi-country and multi-configuration analysis

Author: Gen's BESS Optimization Team"""

Date: October 2025

"""from pathlib import Path

import sys

import pandas as pdimport json

import numpy as npimport pandas as pd

from typing import Dict, List, Tuple, Anyimport numpy as np

import loggingfrom typing import Dict, List, Tuple, Optional

from dataclasses import dataclass

class InvestmentAnalyzer:import logging

    """

    Investment Analysis Engine for BESS deployment decisions.# repo_root = Path(r"H:\TUM-PC\TUM_CEM_PhD\a_tech_arena_hw\TechArena2025_EMS")

    # if str(repo_root) not in sys.path:

    Implements DCF methodology with proper nominal cash flow / nominal discount rate alignment.#     sys.path.append(str(repo_root))

    """# sys.path.append('py_script')

    

    def __init__(self):

        """Initialize the investment analyzer with competition specifications."""# Import our optimization model

        from model import BESSOptimizer

        # BESS Technical Specifications (from competition rules)

        self.bess_specs = {# Configure logging

            'nominal_energy_kwh': 4472,  # Fixed capacity from competitionlogging.basicConfig(level=logging.INFO)

            'rated_power_kw': 2236,      # Fixed rated power from competition  logger = logging.getLogger(__name__)

            'investment_cost_per_kwh': 200,  # EUR/kWh from competition

            'efficiency': 0.85,         # Round-trip efficiency@dataclass

            'max_lifetime_cycles': 4500  # Maximum lifetime cyclesclass CountryParameters:

        }    """Country-specific financial parameters for DCF analysis"""

            name: str

        # C-rate Configuration Matrix (from competition specifications)    code: str

        self.c_rate_configs = {    wacc: float  # Weighted Average Cost of Capital (%)

            0.25: {'max_power_kw': 1118, 'cycles_per_day': 1.0, 'max_daily_discharge_kwh': 4472},    inflation: float  # Annual inflation rate (%)

            0.33: {'max_power_kw': 1476, 'cycles_per_day': 1.5, 'max_daily_discharge_kwh': 6708},

            0.50: {'max_power_kw': 2236, 'cycles_per_day': 2.0, 'max_daily_discharge_kwh': 8944}@dataclass

        }class BESSConfiguration:

            """BESS technical configuration parameters"""

        # Country-specific Financial Parameters (from competition specifications)    c_rate: float

        self.financial_params = {    cycle_limit: float

            'DE': {'wacc': 8.3, 'inflation': 2.0},    nominal_capacity_mwh: float  # Fixed at 4.472 MWh per project specification

            'AT': {'wacc': 8.3, 'inflation': 3.3},

            'CH': {'wacc': 8.3, 'inflation': 0.1},    @property

            'CZ': {'wacc': 12.0, 'inflation': 2.9},    def name(self):

            'HU': {'wacc': 15.0, 'inflation': 4.6}        return f"C{self.c_rate}_Cyc{self.cycle_limit}"

        }

        @dataclass

        # Analysis Parametersclass DCFResult:

        self.analysis_years = 10  # 2024-2033 operation period    """Results from DCF analysis"""

        self.investment_year = 2023  # Investment happens in 2023    country: str

            config: str

        # Setup logging    annual_profit_2024: float

        self.logger = logging.getLogger(__name__)    npv: float

        levelized_roi: float

    def calculate_investment_metrics(self, optimization_results: Dict[str, Any]) -> Dict[str, Any]:    capex: float

        """    pv_total_profits: float

        Calculate comprehensive investment metrics for all scenarios.    is_profitable: bool

        

        Args:class InvestmentAnalyzer:

            optimization_results: Dict containing optimization results with structure:    """

                {scenario_name: {'country': str, 'c_rate': float, 'cycles': float,     Investment optimization analyzer implementing 10-year DCF analysis

                                'objective_value': float, 'status': str, ...}}    """

            

        Returns:    def __init__(self):

            Dict containing investment analysis results for each country        self.optimizer = BESSOptimizer()

        """        

        investment_results = {}        # Country parameters from investment_opt.tex Table

                self.countries = {

        # Find best scenario for each country            'DE': CountryParameters('Germany', 'DE', 8.3, 2.0),

        best_by_country = self._find_best_scenarios(optimization_results)            'AT': CountryParameters('Austria', 'AT', 8.3, 3.30),

                    'CH': CountryParameters('Switzerland', 'CH', 8.3, 0.10),

        for country in ['DE', 'AT', 'CH', 'HU', 'CZ']:            'CZ': CountryParameters('Czech Republic', 'CZ', 12.0, 2.90),

            if country not in best_by_country:            'HU': CountryParameters('Hungary', 'HU', 15.0, 4.60)

                investment_results[country] = self._create_empty_analysis(country)        }

                continue        

                    # BESS configurations per project specification

            best_scenario = best_by_country[country]        # Fixed parameters: E_nom = 4472 kWh (4.472 MWh), P_rated = 2236 kW

            analysis = self._perform_dcf_analysis(country, best_scenario)        # C-rate scenarios: 0.25C, 0.33C, 0.50C

            investment_results[country] = analysis        # Cycle limit scenarios: 1.0, 1.5, 2.0 cycles/day

                # Total: 3 × 3 = 9 configurations

        return investment_results        fixed_capacity_mwh = 4.472  # MWh - constant for all configurations

    

    def _find_best_scenarios(self, optimization_results: Dict[str, Any]) -> Dict[str, Any]:        self.configurations = [

        """Find the best scenario (highest revenue) for each country."""            # C-rate 0.25C (P_max = 1118 kW)

        best_by_country = {}            BESSConfiguration(0.25, 1.0, fixed_capacity_mwh),

                    BESSConfiguration(0.25, 1.5, fixed_capacity_mwh),

        for scenario_name, result in optimization_results.items():            BESSConfiguration(0.25, 2.0, fixed_capacity_mwh),

            country = result['country']            # C-rate 0.33C (P_max = 1476 kW)

            if country not in best_by_country or result['objective_value'] > best_by_country[country]['objective_value']:            BESSConfiguration(0.33, 1.0, fixed_capacity_mwh),

                best_by_country[country] = result            BESSConfiguration(0.33, 1.5, fixed_capacity_mwh),

                    BESSConfiguration(0.33, 2.0, fixed_capacity_mwh),

        return best_by_country            # C-rate 0.50C (P_max = 2236 kW)

                BESSConfiguration(0.50, 1.0, fixed_capacity_mwh),

    def _perform_dcf_analysis(self, country: str, scenario: Dict[str, Any]) -> Dict[str, Any]:            BESSConfiguration(0.50, 1.5, fixed_capacity_mwh),

        """Perform DCF analysis for a specific country and scenario."""            BESSConfiguration(0.50, 2.0, fixed_capacity_mwh),

                ]

        # Extract scenario parameters        

        c_rate = scenario['c_rate']        # Financial constants

        annual_revenue = scenario['objective_value']  # EUR/year        self.capex_per_kwh = 200  # EUR/kWh as specified

                self.project_lifetime = 10  # years

        # Get financial parameters for this country        

        wacc = self.financial_params[country]['wacc'] / 100  # Convert to decimal    def calculate_capex(self, nominal_capacity_mwh: float) -> float:

        inflation = self.financial_params[country]['inflation'] / 100  # Convert to decimal        """Calculate CAPEX for given nominal capacity"""

                return self.capex_per_kwh * nominal_capacity_mwh * 1000  # Convert MWh to kWh

        # Calculate CAPEX based on fixed BESS specifications    

        capex_eur = self.bess_specs['nominal_energy_kwh'] * self.bess_specs['investment_cost_per_kwh']    def project_nominal_profits(self, initial_profit: float, inflation_rate: float) -> List[float]:

        capex_keur = capex_eur / 1000        """

                Project nominal profits over 10-year horizon

        # Energy capacity in MWh (fixed specification)        Formula: Π_y = Π_2024 * (1 + π)^(y-1)

        energy_capacity_mwh = self.bess_specs['nominal_energy_kwh'] / 1000        """

                profits = []

        # Calculate per-MWh metrics for table display        for year in range(1, self.project_lifetime + 1):

        capex_per_mwh_keur = capex_keur / energy_capacity_mwh            nominal_profit = initial_profit * ((1 + inflation_rate / 100) ** (year - 1))

                    profits.append(nominal_profit)

        # Project nominal cash flows with inflation growth        return profits

        # Formula from LaTeX: Π_y = Π_2024 * (1 + π)^(y-1)    

        cash_flows = []    def calculate_dcf_metrics(self, initial_profit: float, country_params: CountryParameters, 

        for year_offset in range(self.analysis_years):                            nominal_capacity_mwh: float) -> Tuple[float, float, float]:

            nominal_profit = annual_revenue * ((1 + inflation) ** year_offset)        """

            cash_flows.append(nominal_profit)        Calculate DCF metrics: NPV and Levelized ROI

                

        # Calculate present value of all cash flows        Returns:

        # NPV = Σ(CF_t / (1 + WACC)^t) - CAPEX            Tuple of (NPV, Levelized ROI, PV of total profits)

        pv_cash_flows = []        """

        for year, cash_flow in enumerate(cash_flows, start=1):        # Step 1: Project nominal profits

            pv = cash_flow / ((1 + wacc) ** year)        nominal_profits = self.project_nominal_profits(initial_profit, country_params.inflation)

            pv_cash_flows.append(pv)        

                # Step 2: Calculate present values

        total_pv = sum(pv_cash_flows)        wacc = country_params.wacc / 100  # Convert percentage to decimal

        npv = total_pv - capex_eur        present_values = []

                

        # Calculate Levelized ROI as per competition specifications        for year, profit in enumerate(nominal_profits, 1):

        # Levelized ROI = PV(Total Profits) / (CAPEX × Lifetime) × 100            discount_factor = 1 / ((1 + wacc) ** year)

        levelized_roi = (total_pv / (capex_eur * self.analysis_years)) * 100            pv = profit * discount_factor

                    present_values.append(pv)

        # Prepare year-by-year data for Excel table        

        yearly_data = []        pv_total_profits = sum(present_values)

                

        # Investment year (2023)        # Step 3: Calculate CAPEX and NPV

        yearly_data.append({        capex = self.calculate_capex(nominal_capacity_mwh)

            'year': 2023,        npv = pv_total_profits - capex

            'investment_keur_per_mwh': capex_per_mwh_keur,        

            'profit_keur_per_mwh': 0,        # Step 4: Calculate Levelized ROI

            'cash_flow_eur': -capex_eur,        # Formula: PV(Total Profits) / (CAPEX × Lifetime) × 100

            'pv_eur': -capex_eur        levelized_roi = (pv_total_profits / (capex * self.project_lifetime)) * 100

        })        

                return npv, levelized_roi, pv_total_profits

        # Operation years (2024-2033)    

        for year_offset in range(self.analysis_years):    def run_operational_optimization(self, data_file: str, country_code: str, 

            year = 2024 + year_offset                                   config: BESSConfiguration, 

            nominal_profit = cash_flows[year_offset]                                   scale_factor: float = 1.0) -> Optional[float]:

            profit_per_mwh_keur = (nominal_profit / 1000) / energy_capacity_mwh        """

            pv = pv_cash_flows[year_offset]        Run operational optimization for given scenario

                    

            yearly_data.append({        Args:

                'year': year,            data_file: Path to market data file

                'investment_keur_per_mwh': 0,  # No additional investment in operation years            country_code: Country code for analysis

                'profit_keur_per_mwh': profit_per_mwh_keur,            config: BESS configuration

                'cash_flow_eur': nominal_profit,            scale_factor: Scaling factor for annual projection (e.g., 365/2 for 2-day test)

                'pv_eur': pv        

            })        Returns:

                    Scaled annual profit or None if optimization failed

        # Compile comprehensive analysis        """

        analysis = {        try:

            'country': country,            result = self.optimizer.optimize_bess(

            'scenario': scenario,                data_file=data_file,

            'financial_params': {                c_rate=config.c_rate,

                'wacc_percent': self.financial_params[country]['wacc'],                cycle_limit=config.cycle_limit

                'inflation_percent': self.financial_params[country]['inflation'],            )

                'discount_rate_percent': self.financial_params[country]['wacc']  # Same as WACC for nominal approach            

            },            if result['success']:

            'bess_config': {                # Scale the profit to annual equivalent

                'c_rate': c_rate,                annual_profit = result['objective_value'] * scale_factor

                'energy_capacity_kwh': self.bess_specs['nominal_energy_kwh'],                return annual_profit

                'energy_capacity_mwh': energy_capacity_mwh,            else:

                'max_power_kw': self.c_rate_configs[c_rate]['max_power_kw']                logger.warning(f"Optimization failed for {country_code}-{config.name}: {result.get('error', 'Unknown')}")

            },                return None

            'investment_metrics': {                

                'capex_eur': capex_eur,        except Exception as e:

                'capex_keur': capex_keur,            logger.error(f"Error in optimization for {country_code}-{config.name}: {str(e)}")

                'capex_per_mwh_keur': capex_per_mwh_keur,            return None

                'annual_revenue_eur': annual_revenue,    

                'total_pv_eur': total_pv,    def analyze_single_scenario(self, data_file: str, country_code: str, 

                'npv_eur': npv,                              config: BESSConfiguration, scale_factor: float = 1.0) -> Optional[DCFResult]:

                'levelized_roi_percent': levelized_roi        """

            },        Perform complete DCF analysis for a single scenario

            'yearly_data': yearly_data        """

        }        logger.info(f"Analyzing {country_code}-{config.name}...")

                

        self.logger.info(f"Investment analysis completed for {country}: "        # Get country parameters

                        f"NPV = €{npv:,.0f}, Levelized ROI = {levelized_roi:.2f}%")        if country_code not in self.countries:

                    logger.error(f"Unknown country code: {country_code}")

        return analysis            return None

            

    def _create_empty_analysis(self, country: str) -> Dict[str, Any]:        country_params = self.countries[country_code]

        """Create empty analysis structure for countries with no optimization results."""        

        return {        # Run operational optimization

            'country': country,        annual_profit = self.run_operational_optimization(data_file, country_code, config, scale_factor)

            'scenario': None,        if annual_profit is None:

            'financial_params': self.financial_params.get(country, {}),            return None

            'bess_config': {},        

            'investment_metrics': {},        # Calculate DCF metrics

            'yearly_data': [],        npv, levelized_roi, pv_total_profits = self.calculate_dcf_metrics(

            'note': f'No optimization results available for {country}'            annual_profit, country_params, config.nominal_capacity_mwh

        }        )

            

    def get_country_rankings(self, investment_results: Dict[str, Any]) -> List[Tuple[str, float]]:        capex = self.calculate_capex(config.nominal_capacity_mwh)

        """Rank countries by Levelized ROI in descending order."""        

        rankings = []        return DCFResult(

                    country=country_params.name,

        for country, analysis in investment_results.items():            config=config.name,

            if 'investment_metrics' in analysis and analysis['investment_metrics']:            annual_profit_2024=annual_profit,

                roi = analysis['investment_metrics'].get('levelized_roi_percent', 0)            npv=npv,

                rankings.append((country, roi))            levelized_roi=levelized_roi,

                    capex=capex,

        # Sort by ROI descending            pv_total_profits=pv_total_profits,

        rankings.sort(key=lambda x: x[1], reverse=True)            is_profitable=(npv > 0)

                )

        return rankings    

        def create_test_dataset(self, source_file: str, country_code: str, 

    def validate_bess_configuration(self, c_rate: float) -> bool:                          test_days: int = 2) -> str:

        """Validate that C-rate matches competition specifications."""        """

        if c_rate not in self.c_rate_configs:        Create test dataset for smaller scale analysis

            self.logger.error(f"Invalid C-rate {c_rate}. Must be one of {list(self.c_rate_configs.keys())}")        """

            return False        output_file = f"test_{country_code}_{test_days}days.jsonl"

                

        # Verify power calculation consistency        with open(source_file, 'r') as f:

        expected_power = c_rate * self.bess_specs['nominal_energy_kwh']            all_data = [json.loads(line) for line in f]

        config_power = self.c_rate_configs[c_rate]['max_power_kw']        

                # Filter for specific country and time period

        if abs(expected_power - config_power) > 1:  # Allow 1 kW tolerance        country_data = [d for d in all_data if d['country'] == country_code]

            self.logger.warning(f"Power calculation mismatch for C-rate {c_rate}: "        test_data = country_data[:test_days * 96]  # 96 timesteps per day

                              f"Expected {expected_power} kW, Config {config_power} kW")        

                with open(output_file, 'w') as f:

        return True            for record in test_data:

                f.write(json.dumps(record) + '\n')

if __name__ == "__main__":        

    # Example usage and testing        logger.info(f"Created test dataset: {output_file} with {len(test_data)} records")

    analyzer = InvestmentAnalyzer()        return output_file

        

    # Test with sample optimization results    def run_investment_analysis(self, source_data_file: str, test_days: int = 2, 

    sample_results = {                              countries: List[str] = None, 

        'AT_C0.5_Cyc1.0': {                              configurations: List[int] = None) -> pd.DataFrame:

            'country': 'AT',        """

            'c_rate': 0.5,        Run comprehensive investment analysis

            'cycles': 1.0,        

            'objective_value': 1266418,  # EUR/year        Args:

            'status': 'optimal'            source_data_file: Path to full market data file

        }            test_days: Number of days for testing (will be scaled to annual)

    }            countries: List of country codes to analyze (default: all)

                configurations: List of configuration indices to test (default: all)

    investment_analysis = analyzer.calculate_investment_metrics(sample_results)        

    rankings = analyzer.get_country_rankings(investment_analysis)        Returns:

                DataFrame with analysis results

    print("Investment Analysis Test Results:")        """

    for country, analysis in investment_analysis.items():        if countries is None:

        if analysis.get('investment_metrics'):            countries = list(self.countries.keys())

            metrics = analysis['investment_metrics']        

            print(f"{country}: NPV = €{metrics['npv_eur']:,.0f}, ROI = {metrics['levelized_roi_percent']:.2f}%")        if configurations is None:
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