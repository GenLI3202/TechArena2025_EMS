#!/usr/bin/env python3
"""
TechArena 2025 Validation Test Script - October 2024 Only

This script runs optimization for all 45 scenarios using ONLY October 2024 data
and scales results by 12 to estimate annual performance. This provides a quick
validation test before running the full year scenarios.

Scenarios:
- Countries: DE_LU, AT, CH, HU, CZ
- Configurations: 3 C-rates (0.5, 1.0, 2.0) × 3 cycle limits (0.5, 1.0, 2.0)
- Data: October 2024 only (scaled by 12 for annual estimates)
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime
import time
import logging
from typing import Dict, List, Tuple, Optional

# Add the parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from model import ImprovedBESSOptimizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('validation_test_october.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TechArena2025ValidationTest:
    """Manages the validation test using October 2024 data only."""
    
    def __init__(self):
        self.countries = ['DE_LU', 'AT', 'CH', 'HU', 'CZ']
        self.c_rates = [0.25, 0.33, 0.5]
        self.cycle_limits = [1.0, 1.5, 2.0]
        
        # Results storage
        self.results = {}
        self.progress_file = 'validation_test_progress.json'
        self.output_dir = 'validation_test_csvs'
        
        # Scaling factor for annual estimation
        self.annual_scale_factor = 12  # Scale October results by 12 for annual estimate
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Load existing progress if available
        self.load_progress()
        
    def load_progress(self):
        """Load existing progress from file to enable resuming."""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    self.results = json.load(f)
                logger.info(f"Loaded existing progress: {len(self.results)} scenarios completed")
            except Exception as e:
                logger.warning(f"Could not load progress file: {e}")
                self.results = {}
        else:
            self.results = {}
    
    def save_progress(self):
        """Save current progress to file."""
        try:
            # Convert numpy types to native Python types for JSON serialization
            serializable_results = {}
            for key, value in self.results.items():
                if isinstance(value, dict):
                    serializable_value = {}
                    for k, v in value.items():
                        if k == 'optimization_variables' and isinstance(v, dict):
                            # Convert optimization variable keys from numpy types to int
                            serializable_opt_vars = {}
                            for var_name, var_dict in v.items():
                                if isinstance(var_dict, dict):
                                    serializable_opt_vars[var_name] = {int(vk): vv for vk, vv in var_dict.items()}
                                else:
                                    serializable_opt_vars[var_name] = var_dict
                            serializable_value[k] = serializable_opt_vars
                        else:
                            serializable_value[k] = v
                    serializable_results[key] = serializable_value
                else:
                    serializable_results[key] = value
            
            with open(self.progress_file, 'w') as f:
                json.dump(serializable_results, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save progress: {e}")
    
    def filter_october_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Filter data to include only October 2024."""
        try:
            # Check if data has timestamp column or datetime index
            if 'timestamp' in data.columns:
                # Convert timestamp to datetime if it's not already
                if not pd.api.types.is_datetime64_any_dtype(data['timestamp']):
                    data['timestamp'] = pd.to_datetime(data['timestamp'])
                
                # Filter for October 2024
                october_data = data[
                    (data['timestamp'].dt.year == 2024) & 
                    (data['timestamp'].dt.month == 10)
                ].copy()
            elif hasattr(data.index, 'year'):
                # Data has datetime index after preprocessing
                october_data = data[
                    (data.index.year == 2024) & 
                    (data.index.month == 10)
                ].copy()
            else:
                # Fallback: assume data is already October 2024
                logger.warning("Cannot identify timestamp column or datetime index, using all data")
                october_data = data.copy()
            
            if len(october_data) == 0:
                logger.warning("No October 2024 data found")
                if 'timestamp' in data.columns:
                    # Fallback: use first month of available data
                    first_month = data['timestamp'].dt.month.iloc[0]
                    first_year = data['timestamp'].dt.year.iloc[0]
                    october_data = data[
                        (data['timestamp'].dt.year == first_year) & 
                        (data['timestamp'].dt.month == first_month)
                    ].copy()
                    logger.info(f"Using fallback month {first_month}/{first_year}: {len(october_data)} records")
                elif hasattr(data.index, 'month'):
                    # Use first month from datetime index
                    first_month = data.index.month[0]
                    first_year = data.index.year[0]
                    october_data = data[
                        (data.index.year == first_year) & 
                        (data.index.month == first_month)
                    ].copy()
                    logger.info(f"Using fallback month {first_month}/{first_year}: {len(october_data)} records")
                else:
                    # Last resort: use all data
                    october_data = data.copy()
                    logger.warning(f"Using all available data: {len(october_data)} records")
            
            logger.info(f"Filtered to October 2024: {len(october_data)} records")
            return october_data
            
        except Exception as e:
            logger.error(f"Error filtering October data: {e}")
            # Return first ~744 records (approximately 1 month)
            return data.head(744).copy()
    
    def get_scenario_key(self, country: str, c_rate: float, cycle_limit: float) -> str:
        """Generate a unique key for each scenario."""
        return f"{country}_C{c_rate}_Cyc{cycle_limit}"
    
    def generate_all_scenarios(self) -> List[Tuple[str, float, float]]:
        """Generate all 45 scenario combinations."""
        scenarios = []
        for country in self.countries:
            for c_rate in self.c_rates:
                for cycle_limit in self.cycle_limits:
                    scenarios.append((country, c_rate, cycle_limit))
        return scenarios
    
    def run_single_scenario(self, country: str, c_rate: float, cycle_limit: float) -> Dict:
        """Run optimization for a single scenario using October data only."""
        scenario_key = self.get_scenario_key(country, c_rate, cycle_limit)
        
        # Check if already completed
        if scenario_key in self.results:
            logger.info(f"Skipping {scenario_key} - already completed")
            return self.results[scenario_key]
        
        logger.info(f"Running validation scenario: {scenario_key}")
        start_time = time.time()
        
        try:
            # Initialize optimizer
            optimizer = ImprovedBESSOptimizer()
            
            # Set battery parameters for this scenario
            optimizer.battery_params['capacity_kwh'] = 4472  # Correct nominal capacity
            optimizer.battery_params['daily_cycle_limit'] = cycle_limit
            
            # Calculate C-rate constraint (max power based on capacity and C-rate)
            max_power_kw = 4472 * c_rate  # kW
            optimizer.market_params['max_power_kw'] = max_power_kw
            
            # Load and preprocess data
            full_data = optimizer.load_and_preprocess_data('data/TechArena2025_data_tidy.jsonl')
            
            if full_data is None or len(full_data) == 0:
                raise ValueError("No data available")
            
            # Extract country-specific data first
            country_full_data = optimizer.extract_country_data(full_data, country)
            
            if country_full_data is None or len(country_full_data) == 0:
                raise ValueError(f"No data available for country {country}")
            
            # Filter to October 2024 only
            october_data = self.filter_october_data(country_full_data)
            
            if len(october_data) == 0:
                raise ValueError(f"No October data available for country {country}")
            
            # Run optimization on October data
            result = optimizer.optimize(october_data)
            
            if result is None:
                raise ValueError("Optimization failed")
            
            # Scale results by 12 for annual estimate
            monthly_revenue = result['total_revenue']
            annual_revenue_estimate = monthly_revenue * self.annual_scale_factor
            
            # Extract key metrics
            detailed_results = result.get('detailed_results', result)
            
            scenario_result = {
                'country': country,
                'c_rate': c_rate,
                'cycle_limit': cycle_limit,
                'scenario_key': scenario_key,
                'optimization_time': time.time() - start_time,
                'monthly_revenue': monthly_revenue,
                'october_revenue': monthly_revenue,  # Add this for easier access
                'annual_revenue_estimate': annual_revenue_estimate,
                'data_points_october': len(october_data),
                'data_points_full_year': len(full_data),
                'scale_factor': self.annual_scale_factor,
                'optimization_status': result.get('solver_status', 'unknown'),
                'solve_time': result.get('solve_time', 0),
                'optimization_variables': {
                    'p_ch': detailed_results.get('p_ch', {}),
                    'p_dis': detailed_results.get('p_dis', {}), 
                    'e_soc': detailed_results.get('e_soc', {}),
                    'c_fcr': detailed_results.get('c_fcr', {}),
                    'c_afrr_pos': detailed_results.get('c_afrr_pos', {}),
                    'c_afrr_neg': detailed_results.get('c_afrr_neg', {})
                },
                'timestamps': october_data['timestamp'].tolist() if 'timestamp' in october_data.columns else []
            }
            
            # Store result
            self.results[scenario_key] = scenario_result
            self.save_progress()
            
            logger.info(f"Completed {scenario_key}: "
                       f"October Revenue = €{monthly_revenue:,.0f}, "
                       f"Annual Estimate = €{annual_revenue_estimate:,.0f}, "
                       f"Time = {scenario_result['optimization_time']:.1f}s")
            
            return scenario_result
            
        except Exception as e:
            logger.error(f"Failed scenario {scenario_key}: {e}")
            # Store failure for tracking
            self.results[scenario_key] = {
                'country': country,
                'c_rate': c_rate,
                'cycle_limit': cycle_limit,
                'scenario_key': scenario_key,
                'optimization_time': time.time() - start_time,
                'optimization_status': 'failed',
                'error': str(e)
            }
            self.save_progress()
            return self.results[scenario_key]
    
    def run_all_scenarios(self):
        """Run validation test for all 45 scenarios using October data."""
        scenarios = self.generate_all_scenarios()
        total_scenarios = len(scenarios)
        
        logger.info(f"Starting VALIDATION TEST: {total_scenarios} scenarios (October 2024 only)")
        logger.info(f"Results will be scaled by {self.annual_scale_factor} for annual estimates")
        start_time = time.time()
        
        for i, (country, c_rate, cycle_limit) in enumerate(scenarios, 1):
            scenario_key = self.get_scenario_key(country, c_rate, cycle_limit)
            
            logger.info(f"\n{'='*50}")
            logger.info(f"Validation Scenario {i}/{total_scenarios}: {scenario_key}")
            logger.info(f"{'='*50}")
            
            self.run_single_scenario(country, c_rate, cycle_limit)
            
            # Progress update
            completed = len([r for r in self.results.values() if 'optimization_status' in r])
            elapsed = time.time() - start_time
            avg_time = elapsed / completed if completed > 0 else 0
            remaining = total_scenarios - completed
            eta = avg_time * remaining
            
            logger.info(f"Progress: {completed}/{total_scenarios} completed")
            logger.info(f"Elapsed: {elapsed/60:.1f} min, ETA: {eta/60:.1f} min")
        
        total_time = time.time() - start_time
        logger.info(f"\nValidation test completed in {total_time/60:.1f} minutes")
        
        # Generate summary
        self.generate_summary()
    
    def generate_csv_files(self):
        """Generate CSV files with validation results."""
        logger.info("Generating validation test CSV files...")
        
        # Collect all successful results
        successful_results = {k: v for k, v in self.results.items() 
                            if v.get('optimization_status') == 'optimal'}
        
        if not successful_results:
            logger.error("No successful optimizations to generate CSV files")
            return
        
        # Configuration file - summary of all scenarios
        config_data = []
        operation_data = []
        
        for scenario_key, result in successful_results.items():
            # Configuration entry with both monthly and annual estimates
            config_data.append({
                'Country': result['country'],
                'Configuration': f"C{result['c_rate']}_Cyc{result['cycle_limit']}",
                'C_Rate': result['c_rate'],
                'Cycle_Limit': result['cycle_limit'],
                'Monthly_Revenue_EUR': result['monthly_revenue'],
                'Annual_Revenue_Estimate_EUR': result['annual_revenue_estimate'],
                'Scale_Factor': result['scale_factor'],
                'Optimization_Time_s': result['optimization_time'],
                'Data_Points_October': result['data_points_october'],
                'Data_Points_Full_Year': result['data_points_full_year']
            })
            
            # Operation data for October time steps
            variables = result['optimization_variables']
            timestamps = result['timestamps']
            
            for i, ts in enumerate(timestamps):
                operation_data.append({
                    'Country': result['country'],
                    'Configuration': f"C{result['c_rate']}_Cyc{result['cycle_limit']}",
                    'Timestamp': ts,
                    'P_Charge_MW': variables['p_ch'][i] if i < len(variables['p_ch']) else 0,
                    'P_Discharge_MW': variables['p_dis'][i] if i < len(variables['p_dis']) else 0,
                    'E_SOC_MWh': variables['e_soc'][i] if i < len(variables['e_soc']) else 0,
                    'C_FCR_MW': variables['c_fcr'][i] if i < len(variables['c_fcr']) else 0,
                    'C_AFRR_Pos_MW': variables['c_afrr_pos'][i] if i < len(variables['c_afrr_pos']) else 0,
                    'C_AFRR_Neg_MW': variables['c_afrr_neg'][i] if i < len(variables['c_afrr_neg']) else 0
                })
        
        # Save configuration summary
        config_df = pd.DataFrame(config_data)
        config_file = os.path.join(self.output_dir, 'validation_configuration_summary.csv')
        config_df.to_csv(config_file, index=False)
        logger.info(f"Saved validation configuration summary: {config_file}")
        
        # Save operation data
        operation_df = pd.DataFrame(operation_data)
        operation_file = os.path.join(self.output_dir, 'validation_operation_results.csv')
        operation_df.to_csv(operation_file, index=False)
        logger.info(f"Saved validation operation results: {operation_file}")
        
        # Generate individual country files
        for country in self.countries:
            country_data = operation_df[operation_df['Country'] == country]
            if not country_data.empty:
                country_file = os.path.join(self.output_dir, f'validation_{country}_operation_results.csv')
                country_data.to_csv(country_file, index=False)
                logger.info(f"Saved validation country-specific file: {country_file}")
        
        logger.info(f"All validation CSV files saved to: {self.output_dir}")
    
    def generate_summary(self):
        """Generate a comprehensive summary of the validation test."""
        logger.info("Generating validation summary report...")
        
        successful = [r for r in self.results.values() if r.get('optimization_status') == 'optimal']
        failed = [r for r in self.results.values() if r.get('optimization_status') == 'failed']
        
        summary = {
            'validation_test': True,
            'data_period': 'October 2024',
            'scale_factor': self.annual_scale_factor,
            'total_scenarios': len(self.results),
            'successful': len(successful),
            'failed': len(failed),
            'success_rate': len(successful) / len(self.results) * 100 if self.results else 0,
            'total_monthly_revenue': sum(r['monthly_revenue'] for r in successful),
            'total_annual_revenue_estimate': sum(r['annual_revenue_estimate'] for r in successful),
            'avg_monthly_revenue_per_scenario': np.mean([r['monthly_revenue'] for r in successful]) if successful else 0,
            'avg_annual_revenue_estimate_per_scenario': np.mean([r['annual_revenue_estimate'] for r in successful]) if successful else 0,
            'total_optimization_time': sum(r.get('optimization_time', 0) for r in self.results.values()),
            'avg_optimization_time': np.mean([r.get('optimization_time', 0) for r in self.results.values()]) if self.results else 0,
            'by_country': {},
            'by_configuration': {}
        }
        
        # Summary by country
        for country in self.countries:
            country_results = [r for r in successful if r['country'] == country]
            summary['by_country'][country] = {
                'scenarios': len(country_results),
                'total_monthly_revenue': sum(r['monthly_revenue'] for r in country_results),
                'total_annual_revenue_estimate': sum(r['annual_revenue_estimate'] for r in country_results),
                'avg_monthly_revenue': np.mean([r['monthly_revenue'] for r in country_results]) if country_results else 0,
                'avg_annual_revenue_estimate': np.mean([r['annual_revenue_estimate'] for r in country_results]) if country_results else 0
            }
        
        # Summary by configuration
        for c_rate in self.c_rates:
            for cycle_limit in self.cycle_limits:
                config_key = f"C{c_rate}_Cyc{cycle_limit}"
                config_results = [r for r in successful 
                                if r['c_rate'] == c_rate and r['cycle_limit'] == cycle_limit]
                summary['by_configuration'][config_key] = {
                    'scenarios': len(config_results),
                    'total_monthly_revenue': sum(r['monthly_revenue'] for r in config_results),
                    'total_annual_revenue_estimate': sum(r['annual_revenue_estimate'] for r in config_results),
                    'avg_monthly_revenue': np.mean([r['monthly_revenue'] for r in config_results]) if config_results else 0,
                    'avg_annual_revenue_estimate': np.mean([r['annual_revenue_estimate'] for r in config_results]) if config_results else 0
                }
        
        # Save summary
        summary_file = 'validation_test_summary.json'
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info("VALIDATION TEST SUMMARY (October 2024 × 12)")
        logger.info("="*60)
        logger.info(f"Total scenarios: {summary['total_scenarios']}")
        logger.info(f"Successful: {summary['successful']}")
        logger.info(f"Failed: {summary['failed']}")
        logger.info(f"Success rate: {summary['success_rate']:.1f}%")
        logger.info(f"Total monthly revenue (October): €{summary['total_monthly_revenue']:,.0f}")
        logger.info(f"Total annual revenue estimate: €{summary['total_annual_revenue_estimate']:,.0f}")
        logger.info(f"Average monthly revenue per scenario: €{summary['avg_monthly_revenue_per_scenario']:,.0f}")
        logger.info(f"Average annual revenue estimate per scenario: €{summary['avg_annual_revenue_estimate_per_scenario']:,.0f}")
        logger.info(f"Total optimization time: {summary['total_optimization_time']:.1f}s")
        logger.info(f"Average optimization time: {summary['avg_optimization_time']:.1f}s")
        
        logger.info("\nAnnual Revenue Estimates by Country:")
        for country, stats in summary['by_country'].items():
            logger.info(f"  {country}: €{stats['total_annual_revenue_estimate']:,.0f} "
                       f"(avg: €{stats['avg_annual_revenue_estimate']:,.0f}, scenarios: {stats['scenarios']})")
        
        logger.info("\nAnnual Revenue Estimates by Configuration:")
        for config, stats in summary['by_configuration'].items():
            logger.info(f"  {config}: €{stats['total_annual_revenue_estimate']:,.0f} "
                       f"(avg: €{stats['avg_annual_revenue_estimate']:,.0f}, scenarios: {stats['scenarios']})")
        
        if failed:
            logger.info(f"\nFailed scenarios ({len(failed)}):")
            for failure in failed:
                logger.info(f"  {failure['scenario_key']}: {failure.get('error', 'Unknown error')}")
        
        logger.info("\nNOTE: Annual estimates are October results × 12")
        logger.info("This is a VALIDATION TEST - not actual competition submission")
        logger.info("="*60)
        
        return summary

def main():
    """Main execution function for validation test."""
    print("TechArena 2025 Validation Test - October 2024 Only")
    print("="*50)
    print("This runs 45 scenarios using ONLY October 2024 data")
    print("Results are scaled by 12 for annual revenue estimates")
    print("Use this to validate the model before running the full year")
    print("="*50)
    
    # Create runner instance
    runner = TechArena2025ValidationTest()
    
    # Run all scenarios
    runner.run_all_scenarios()
    
    # Generate CSV files
    runner.generate_csv_files()
    
    print("\nValidation test completed!")
    print(f"Results saved to: {runner.output_dir}")
    print("Check validation_test_summary.json for detailed results")
    print("This was a VALIDATION TEST using October data × 12")

if __name__ == "__main__":
    main()