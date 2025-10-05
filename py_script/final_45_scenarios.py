#!/usr/bin/env python3
"""
TechArena 2025 Final 45-Scenario Competition Script

This script runs optimization for all 45 scenarios (5 countries × 9 configurations)
and generates CSV submission files in the correct format.

Scenarios:
- Countries: DE_LU, AT, CH, HU, CZ
- Configurations: 3 C-rates (0.5, 1.0, 2.0) × 3 cycle limits (0.5, 1.0, 2.0)
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
        logging.FileHandler('final_45_scenarios.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TechArena2025FinalRun:
    """Manages the final 45-scenario competition run with CSV generation."""
    
    def __init__(self):
        self.countries = ['DE_LU', 'AT', 'CH', 'HU', 'CZ']
        self.c_rates = [0.25, 0.33, 0.5]
        self.cycle_limits = [1.0, 1.5, 2.0]
        
        # Results storage
        self.results = {}
        self.progress_file = 'final_45_scenarios_progress.json'
        self.output_dir = 'final_submission_csvs'
        
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
            with open(self.progress_file, 'w') as f:
                json.dump(self.results, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save progress: {e}")
    
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
        """Run optimization for a single scenario."""
        scenario_key = self.get_scenario_key(country, c_rate, cycle_limit)
        
        # Check if already completed
        if scenario_key in self.results:
            logger.info(f"Skipping {scenario_key} - already completed")
            return self.results[scenario_key]
        
        logger.info(f"Running scenario: {scenario_key}")
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
            
            # Load and preprocess data for the specific country
            data = optimizer.load_and_preprocess_data(
                'data/TechArena2025_data_tidy.jsonl',
                country=country
            )
            
            if data is None or len(data) == 0:
                raise ValueError(f"No data available for country {country}")
            
            # Run optimization
            result = optimizer.optimize()
            
            if result is None:
                raise ValueError("Optimization failed")
            
            # Extract key metrics
            scenario_result = {
                'country': country,
                'c_rate': c_rate,
                'cycle_limit': cycle_limit,
                'scenario_key': scenario_key,
                'optimization_time': time.time() - start_time,
                'total_revenue': result['total_revenue'],
                'data_points': len(data),
                'optimization_status': 'optimal',
                'optimization_variables': {
                    'p_ch': result['p_ch'],
                    'p_dis': result['p_dis'], 
                    'e_soc': result['e_soc'],
                    'c_fcr': result['c_fcr'],
                    'c_afrr_pos': result['c_afrr_pos'],
                    'c_afrr_neg': result['c_afrr_neg']
                },
                'timestamps': data['timestamp'].tolist()
            }
            
            # Store result
            self.results[scenario_key] = scenario_result
            self.save_progress()
            
            logger.info(f"Completed {scenario_key}: Revenue = €{result['total_revenue']:,.0f}, "
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
        """Run optimization for all 45 scenarios."""
        scenarios = self.generate_all_scenarios()
        total_scenarios = len(scenarios)
        
        logger.info(f"Starting final competition run: {total_scenarios} scenarios")
        start_time = time.time()
        
        for i, (country, c_rate, cycle_limit) in enumerate(scenarios, 1):
            scenario_key = self.get_scenario_key(country, c_rate, cycle_limit)
            
            logger.info(f"\n{'='*50}")
            logger.info(f"Scenario {i}/{total_scenarios}: {scenario_key}")
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
        logger.info(f"\nFinal run completed in {total_time/60:.1f} minutes")
        
        # Generate summary
        self.generate_summary()
    
    def generate_csv_files(self):
        """Generate CSV submission files in the correct format."""
        logger.info("Generating CSV submission files...")
        
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
            # Configuration entry
            config_data.append({
                'Country': result['country'],
                'Configuration': f"C{result['c_rate']}_Cyc{result['cycle_limit']}",
                'C_Rate': result['c_rate'],
                'Cycle_Limit': result['cycle_limit'],
                'Total_Revenue_EUR': result['total_revenue'],
                'Optimization_Time_s': result['optimization_time'],
                'Data_Points': result['data_points']
            })
            
            # Operation data for each time step
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
        config_file = os.path.join(self.output_dir, 'configuration_summary.csv')
        config_df.to_csv(config_file, index=False)
        logger.info(f"Saved configuration summary: {config_file}")
        
        # Save operation data
        operation_df = pd.DataFrame(operation_data)
        operation_file = os.path.join(self.output_dir, 'operation_results.csv')
        operation_df.to_csv(operation_file, index=False)
        logger.info(f"Saved operation results: {operation_file}")
        
        # Generate individual country files if needed
        for country in self.countries:
            country_data = operation_df[operation_df['Country'] == country]
            if not country_data.empty:
                country_file = os.path.join(self.output_dir, f'{country}_operation_results.csv')
                country_data.to_csv(country_file, index=False)
                logger.info(f"Saved country-specific file: {country_file}")
        
        logger.info(f"All CSV files saved to: {self.output_dir}")
    
    def generate_summary(self):
        """Generate a comprehensive summary of the final run."""
        logger.info("Generating summary report...")
        
        successful = [r for r in self.results.values() if r.get('optimization_status') == 'optimal']
        failed = [r for r in self.results.values() if r.get('optimization_status') == 'failed']
        
        summary = {
            'total_scenarios': len(self.results),
            'successful': len(successful),
            'failed': len(failed),
            'success_rate': len(successful) / len(self.results) * 100 if self.results else 0,
            'total_revenue': sum(r['total_revenue'] for r in successful),
            'avg_revenue_per_scenario': np.mean([r['total_revenue'] for r in successful]) if successful else 0,
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
                'total_revenue': sum(r['total_revenue'] for r in country_results),
                'avg_revenue': np.mean([r['total_revenue'] for r in country_results]) if country_results else 0
            }
        
        # Summary by configuration
        for c_rate in self.c_rates:
            for cycle_limit in self.cycle_limits:
                config_key = f"C{c_rate}_Cyc{cycle_limit}"
                config_results = [r for r in successful 
                                if r['c_rate'] == c_rate and r['cycle_limit'] == cycle_limit]
                summary['by_configuration'][config_key] = {
                    'scenarios': len(config_results),
                    'total_revenue': sum(r['total_revenue'] for r in config_results),
                    'avg_revenue': np.mean([r['total_revenue'] for r in config_results]) if config_results else 0
                }
        
        # Save summary
        summary_file = 'final_45_scenarios_summary.json'
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info("FINAL COMPETITION RUN SUMMARY")
        logger.info("="*60)
        logger.info(f"Total scenarios: {summary['total_scenarios']}")
        logger.info(f"Successful: {summary['successful']}")
        logger.info(f"Failed: {summary['failed']}")
        logger.info(f"Success rate: {summary['success_rate']:.1f}%")
        logger.info(f"Total revenue: €{summary['total_revenue']:,.0f}")
        logger.info(f"Average revenue per scenario: €{summary['avg_revenue_per_scenario']:,.0f}")
        logger.info(f"Total optimization time: {summary['total_optimization_time']:.1f}s")
        logger.info(f"Average optimization time: {summary['avg_optimization_time']:.1f}s")
        
        logger.info("\nRevenue by Country:")
        for country, stats in summary['by_country'].items():
            logger.info(f"  {country}: €{stats['total_revenue']:,.0f} "
                       f"(avg: €{stats['avg_revenue']:,.0f}, scenarios: {stats['scenarios']})")
        
        logger.info("\nRevenue by Configuration:")
        for config, stats in summary['by_configuration'].items():
            logger.info(f"  {config}: €{stats['total_revenue']:,.0f} "
                       f"(avg: €{stats['avg_revenue']:,.0f}, scenarios: {stats['scenarios']})")
        
        if failed:
            logger.info(f"\nFailed scenarios ({len(failed)}):")
            for failure in failed:
                logger.info(f"  {failure['scenario_key']}: {failure.get('error', 'Unknown error')}")
        
        logger.info("="*60)
        
        return summary

def main():
    """Main execution function."""
    print("TechArena 2025 Final 45-Scenario Competition Run")
    print("="*50)
    
    # Create runner instance
    runner = TechArena2025FinalRun()
    
    # Run all scenarios
    runner.run_all_scenarios()
    
    # Generate CSV files
    runner.generate_csv_files()
    
    print("\nFinal competition run completed!")
    print(f"Results saved to: {runner.output_dir}")
    print("Check the log file for detailed information.")

if __name__ == "__main__":
    main()