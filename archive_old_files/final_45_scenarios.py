#!/usr/bin/env python3
"""
TechArena 2025 Final 45-Scenario Competition Run
===============================================

This script executes the final optimization for all 45 scenarios required for
the TechArena 2025 Phase 1 submission. It tests all countries with all
configuration combinations and generates the official submission files.

Scenarios:
- 5 Countries: DE_LU, AT, CH, HU, CZ
- 9 Configurations: 3 C-rates × 3 cycle limits = 9 combinations per country
- Total: 5 × 9 = 45 scenarios

Configuration Matrix:
- C-rates: 0.25, 0.33, 0.50
- Cycle limits: 1.0, 1.5, 2.0 cycles/day

Output:
- Detailed results for each scenario
- Performance benchmarks
- Official submission CSV files
- Comprehensive final report

Usage:
    python final_45_scenarios.py [--output-dir OUTPUT_DIR] [--parallel] [--resume]

Arguments:
    --output-dir: Directory for output files (default: final_results_YYYYMMDD_HHMMSS)
    --parallel: Enable parallel processing where possible (experimental)
    --resume: Resume from previous incomplete run

Estimated Runtime: 2-8 hours depending on system performance
"""

import sys
import time
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import warnings
warnings.filterwarnings('ignore')

# Add project root to path
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))

class CompetitionRunner:
    """Main class for running the final 45-scenario competition"""
    
    def __init__(self, output_dir: str = None, resume: bool = False):
        """Initialize competition runner"""
        
        # Setup output directory
        if output_dir is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = f"final_results_{timestamp}"
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Setup logging
        self.log_file = self.output_dir / "competition_log.txt"
        
        # Configuration matrix
        self.countries = ['DE_LU', 'AT', 'CH', 'HU', 'CZ']
        self.c_rates = [0.25, 0.33, 0.50]
        self.cycle_limits = [1.0, 1.5, 2.0]
        
        # Generate all scenarios
        self.scenarios = []
        scenario_id = 1
        for country in self.countries:
            for c_rate in self.c_rates:
                for cycle_limit in self.cycle_limits:
                    self.scenarios.append({
                        'id': scenario_id,
                        'country': country,
                        'c_rate': c_rate,
                        'cycle_limit': cycle_limit
                    })
                    scenario_id += 1
        
        # Results storage
        self.results = []
        self.summary_stats = {}
        
        # Resume capability
        self.resume = resume
        self.completed_scenarios = set()
        
        if resume:
            self._load_existing_results()
    
    def log(self, message: str, print_also: bool = True):
        """Log message to file and optionally print"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry + "\n")
        
        if print_also:
            print(message)
    
    def _load_existing_results(self):
        """Load existing results for resume capability"""
        results_file = self.output_dir / "interim_results.json"
        
        if results_file.exists():
            try:
                with open(results_file, 'r') as f:
                    data = json.load(f)
                    self.results = data.get('results', [])
                    self.completed_scenarios = set(r['scenario'] for r in self.results)
                
                self.log(f"📁 Resumed: {len(self.completed_scenarios)} scenarios already completed")
            except Exception as e:
                self.log(f"⚠️  Could not load existing results: {str(e)}")
    
    def _save_interim_results(self):
        """Save interim results for resume capability"""
        results_file = self.output_dir / "interim_results.json"
        
        try:
            data = {
                'results': self.results,
                'summary_stats': self.summary_stats,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(results_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            self.log(f"⚠️  Could not save interim results: {str(e)}")
    
    def run_single_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Run optimization for a single scenario"""
        
        scenario_id = scenario['id']
        country = scenario['country']
        c_rate = scenario['c_rate']
        cycle_limit = scenario['cycle_limit']
        
        self.log(f"🧮 Scenario {scenario_id:2d}: {country} | C-rate: {c_rate} | Cycles: {cycle_limit}")
        
        try:
            # Initialize optimizer
            from py_script.model import ImprovedBESSOptimizer
            
            optimizer = ImprovedBESSOptimizer()
            
            # Configure optimizer
            optimizer.max_cycles_per_day = cycle_limit
            optimizer.c_rate = c_rate
            
            # Load and extract country data
            data = optimizer.load_and_preprocess_data(str(repo_root / 'data/TechArena2025_data_tidy.jsonl'))
            country_data = optimizer.extract_country_data(data, country)
            
            # Run optimization
            start_time = time.time()
            result = optimizer.optimize(country_data)
            runtime = time.time() - start_time
            
            # Format results
            scenario_result = {
                'scenario': scenario_id,
                'country': country,
                'c_rate': c_rate,
                'cycle_limit': cycle_limit,
                'revenue': result.get('total_revenue', 0),
                'runtime_seconds': runtime,
                'runtime_minutes': runtime / 60,
                'status': 'SUCCESS',
                'timestamp': datetime.now().isoformat(),
                'detailed_results': result
            }
            
            self.log(f"   ✅ Revenue: €{scenario_result['revenue']:,.0f} | Runtime: {runtime/60:.1f}min")
            
            return scenario_result
            
        except Exception as e:
            self.log(f"   ❌ FAILED: {str(e)}")
            
            return {
                'scenario': scenario_id,
                'country': country,
                'c_rate': c_rate,
                'cycle_limit': cycle_limit,
                'revenue': 0,
                'runtime_seconds': 0,
                'runtime_minutes': 0,
                'status': 'FAILED',
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'detailed_results': {}
            }
    
    def run_all_scenarios(self):
        """Run all 45 scenarios"""
        
        self.log("🚀 Starting TechArena 2025 Final 45-Scenario Run")
        self.log("=" * 60)
        self.log(f"📊 Total scenarios: {len(self.scenarios)}")
        self.log(f"🌍 Countries: {', '.join(self.countries)}")
        self.log(f"⚙️  C-rates: {self.c_rates}")
        self.log(f"🔄 Cycle limits: {self.cycle_limits}")
        self.log(f"📁 Output directory: {self.output_dir}")
        
        if self.resume and self.completed_scenarios:
            self.log(f"🔄 Resuming: {len(self.completed_scenarios)} scenarios already completed")
        
        self.log("=" * 60)
        
        overall_start_time = time.time()
        
        # Process each scenario
        for i, scenario in enumerate(self.scenarios, 1):
            
            # Skip if already completed (resume mode)
            if scenario['id'] in self.completed_scenarios:
                self.log(f"⏭️  Scenario {scenario['id']:2d}: Already completed (resume mode)")
                continue
            
            # Progress indicator
            remaining = len(self.scenarios) - i + 1
            elapsed_hours = (time.time() - overall_start_time) / 3600
            
            if i > 1:  # After first scenario
                avg_time_per_scenario = elapsed_hours / (i - 1 - len(self.completed_scenarios))
                estimated_remaining_hours = avg_time_per_scenario * remaining
                self.log(f"📈 Progress: {i-1}/{len(self.scenarios)} | "
                        f"Elapsed: {elapsed_hours:.1f}h | "
                        f"Estimated remaining: {estimated_remaining_hours:.1f}h")
            
            # Run scenario
            result = self.run_single_scenario(scenario)
            self.results.append(result)
            
            # Save interim results every 5 scenarios
            if len(self.results) % 5 == 0:
                self._save_interim_results()
                self.log("💾 Interim results saved")
        
        # Final statistics
        overall_runtime = time.time() - overall_start_time
        self.summary_stats = {
            'total_scenarios': len(self.scenarios),
            'successful_scenarios': len([r for r in self.results if r['status'] == 'SUCCESS']),
            'failed_scenarios': len([r for r in self.results if r['status'] == 'FAILED']),
            'total_runtime_hours': overall_runtime / 3600,
            'total_revenue': sum(r['revenue'] for r in self.results),
            'average_runtime_per_scenario': overall_runtime / len(self.scenarios)
        }
        
        self.log("=" * 60)
        self.log("🏁 All scenarios completed!")
        self.log(f"⏱️  Total runtime: {overall_runtime/3600:.1f} hours")
        self.log(f"✅ Successful: {self.summary_stats['successful_scenarios']}")
        self.log(f"❌ Failed: {self.summary_stats['failed_scenarios']}")
        self.log(f"💰 Total revenue: €{self.summary_stats['total_revenue']:,.0f}")
        self.log("=" * 60)
    
    def generate_summary_analysis(self):
        """Generate detailed summary analysis"""
        
        self.log("\n📊 Generating summary analysis...")
        
        # Results by country
        country_analysis = {}
        for country in self.countries:
            country_results = [r for r in self.results if r['country'] == country]
            successful_results = [r for r in country_results if r['status'] == 'SUCCESS']
            
            if successful_results:
                revenues = [r['revenue'] for r in successful_results]
                runtimes = [r['runtime_minutes'] for r in successful_results]
                
                country_analysis[country] = {
                    'total_scenarios': len(country_results),
                    'successful_scenarios': len(successful_results),
                    'total_revenue': sum(revenues),
                    'avg_revenue': sum(revenues) / len(revenues),
                    'max_revenue': max(revenues),
                    'min_revenue': min(revenues),
                    'avg_runtime_minutes': sum(runtimes) / len(runtimes),
                    'best_scenario': max(successful_results, key=lambda x: x['revenue'])
                }
        
        # Results by configuration
        config_analysis = {}
        for c_rate in self.c_rates:
            for cycle_limit in self.cycle_limits:
                config_key = f"C{c_rate}_Cyc{cycle_limit}"
                config_results = [r for r in self.results 
                                if r['c_rate'] == c_rate and r['cycle_limit'] == cycle_limit
                                and r['status'] == 'SUCCESS']
                
                if config_results:
                    revenues = [r['revenue'] for r in config_results]
                    config_analysis[config_key] = {
                        'scenarios': len(config_results),
                        'total_revenue': sum(revenues),
                        'avg_revenue': sum(revenues) / len(revenues)
                    }
        
        # Find best overall scenario
        successful_results = [r for r in self.results if r['status'] == 'SUCCESS']
        if successful_results:
            best_scenario = max(successful_results, key=lambda x: x['revenue'])
        else:
            best_scenario = None
        
        # Save analysis
        analysis = {
            'overall_summary': self.summary_stats,
            'country_analysis': country_analysis,
            'configuration_analysis': config_analysis,
            'best_scenario': best_scenario,
            'all_results': self.results
        }
        
        analysis_file = self.output_dir / "competition_analysis.json"
        with open(analysis_file, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        
        self.log(f"💾 Analysis saved to: {analysis_file}")
        
        return analysis
    
    def generate_submission_files(self):
        """Generate official submission CSV files"""
        
        self.log("\n📁 Generating submission files...")
        
        try:
            # Prepare data for submission generator
            submission_data = {
                'results': self.results,
                'summary': self.summary_stats,
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            # Create submission subdirectory
            submission_dir = self.output_dir / "submission_files"
            submission_dir.mkdir(exist_ok=True)
            
            # Generate CSV files using the submission generator
            # Note: This would need to be adapted based on the actual submission format requirements
            
            # For now, create a basic CSV with results
            import pandas as pd
            
            # Configuration CSV
            config_data = []
            for result in self.results:
                if result['status'] == 'SUCCESS':
                    config_data.append({
                        'Country': result['country'],
                        'C_Rate': result['c_rate'],
                        'Max_Cycles_Per_Day': result['cycle_limit'],
                        'Revenue_EUR': result['revenue'],
                        'Runtime_Minutes': result['runtime_minutes']
                    })
            
            config_df = pd.DataFrame(config_data)
            config_file = submission_dir / "TechArena_Phase1_Configuration.csv"
            config_df.to_csv(config_file, index=False)
            
            self.log(f"✅ Configuration file: {config_file}")
            
            # Best configurations summary
            best_configs = {}
            for country in self.countries:
                country_results = [r for r in self.results 
                                 if r['country'] == country and r['status'] == 'SUCCESS']
                if country_results:
                    best_result = max(country_results, key=lambda x: x['revenue'])
                    best_configs[country] = best_result
            
            best_config_data = []
            for country, result in best_configs.items():
                best_config_data.append({
                    'Country': country,
                    'Best_C_Rate': result['c_rate'],
                    'Best_Cycle_Limit': result['cycle_limit'],
                    'Max_Revenue_EUR': result['revenue']
                })
            
            best_df = pd.DataFrame(best_config_data)
            best_file = submission_dir / "TechArena_Phase1_Best_Configurations.csv"
            best_df.to_csv(best_file, index=False)
            
            self.log(f"✅ Best configurations: {best_file}")
            
            # Competition summary
            summary_data = [{
                'Total_Scenarios': self.summary_stats['total_scenarios'],
                'Successful_Scenarios': self.summary_stats['successful_scenarios'],
                'Total_Revenue_EUR': self.summary_stats['total_revenue'],
                'Runtime_Hours': self.summary_stats['total_runtime_hours'],
                'Timestamp': datetime.now().isoformat()
            }]
            
            summary_df = pd.DataFrame(summary_data)
            summary_file = submission_dir / "TechArena_Phase1_Summary.csv"
            summary_df.to_csv(summary_file, index=False)
            
            self.log(f"✅ Summary file: {summary_file}")
            
            return submission_dir
            
        except Exception as e:
            self.log(f"❌ Submission file generation failed: {str(e)}")
            return None
    
    def generate_final_report(self):
        """Generate comprehensive final report"""
        
        self.log("\n📋 Generating final report...")
        
        # Create detailed text report
        report_file = self.output_dir / "FINAL_REPORT.txt"
        
        with open(report_file, 'w') as f:
            f.write("TechArena 2025 Phase 1 - Final Competition Results\n")
            f.write("=" * 60 + "\n\n")
            
            # Executive summary
            f.write("EXECUTIVE SUMMARY\n")
            f.write("-" * 20 + "\n")
            f.write(f"Total Scenarios: {self.summary_stats['total_scenarios']}\n")
            f.write(f"Successful: {self.summary_stats['successful_scenarios']}\n")
            f.write(f"Failed: {self.summary_stats['failed_scenarios']}\n")
            f.write(f"Success Rate: {self.summary_stats['successful_scenarios']/self.summary_stats['total_scenarios']*100:.1f}%\n")
            f.write(f"Total Revenue: €{self.summary_stats['total_revenue']:,.0f}\n")
            f.write(f"Runtime: {self.summary_stats['total_runtime_hours']:.1f} hours\n\n")
            
            # Best results by country
            f.write("BEST RESULTS BY COUNTRY\n")
            f.write("-" * 25 + "\n")
            
            for country in self.countries:
                country_results = [r for r in self.results 
                                 if r['country'] == country and r['status'] == 'SUCCESS']
                if country_results:
                    best = max(country_results, key=lambda x: x['revenue'])
                    f.write(f"{country}: €{best['revenue']:,.0f} "
                           f"(C-rate: {best['c_rate']}, Cycles: {best['cycle_limit']})\n")
                else:
                    f.write(f"{country}: No successful scenarios\n")
            
            f.write("\n")
            
            # Detailed results
            f.write("DETAILED RESULTS\n")
            f.write("-" * 16 + "\n")
            
            for result in self.results:
                status_icon = "✅" if result['status'] == 'SUCCESS' else "❌"
                f.write(f"Scenario {result['scenario']:2d}: {status_icon} {result['country']} | "
                       f"C{result['c_rate']} | Cyc{result['cycle_limit']} | "
                       f"€{result['revenue']:,.0f} | {result['runtime_minutes']:.1f}min\n")
            
            # Configuration analysis
            f.write("\n\nCONFIGURATION ANALYSIS\n")
            f.write("-" * 22 + "\n")
            
            # Best C-rate
            c_rate_revenues = {}
            for c_rate in self.c_rates:
                c_rate_results = [r['revenue'] for r in self.results 
                                if r['c_rate'] == c_rate and r['status'] == 'SUCCESS']
                if c_rate_results:
                    c_rate_revenues[c_rate] = sum(c_rate_results) / len(c_rate_results)
            
            if c_rate_revenues:
                best_c_rate = max(c_rate_revenues.keys(), key=lambda x: c_rate_revenues[x])
                f.write(f"Best C-rate: {best_c_rate} (avg revenue: €{c_rate_revenues[best_c_rate]:,.0f})\n")
            
            # Best cycle limit
            cycle_revenues = {}
            for cycle_limit in self.cycle_limits:
                cycle_results = [r['revenue'] for r in self.results 
                               if r['cycle_limit'] == cycle_limit and r['status'] == 'SUCCESS']
                if cycle_results:
                    cycle_revenues[cycle_limit] = sum(cycle_results) / len(cycle_results)
            
            if cycle_revenues:
                best_cycle = max(cycle_revenues.keys(), key=lambda x: cycle_revenues[x])
                f.write(f"Best Cycle Limit: {best_cycle} (avg revenue: €{cycle_revenues[best_cycle]:,.0f})\n")
        
        self.log(f"📋 Final report: {report_file}")
        
        return report_file

def main():
    """Main execution function"""
    
    parser = argparse.ArgumentParser(description='TechArena 2025 Final 45-Scenario Run')
    parser.add_argument('--output-dir', type=str, help='Output directory')
    parser.add_argument('--resume', action='store_true', help='Resume from previous run')
    parser.add_argument('--parallel', action='store_true', help='Enable parallel processing (experimental)')
    
    args = parser.parse_args()
    
    print("🏆 TechArena 2025 Final 45-Scenario Competition Run")
    print("=" * 60)
    
    try:
        # Initialize runner
        runner = CompetitionRunner(
            output_dir=args.output_dir,
            resume=args.resume
        )
        
        # Run all scenarios
        runner.run_all_scenarios()
        
        # Generate analysis
        analysis = runner.generate_summary_analysis()
        
        # Generate submission files
        submission_dir = runner.generate_submission_files()
        
        # Generate final report
        report_file = runner.generate_final_report()
        
        # Final summary
        print("\n🎉 COMPETITION RUN COMPLETED!")
        print("=" * 40)
        print(f"📊 Results: {runner.summary_stats['successful_scenarios']}/{runner.summary_stats['total_scenarios']} scenarios successful")
        print(f"💰 Total Revenue: €{runner.summary_stats['total_revenue']:,.0f}")
        print(f"⏱️  Runtime: {runner.summary_stats['total_runtime_hours']:.1f} hours")
        print(f"📁 Output Directory: {runner.output_dir}")
        print(f"📋 Final Report: {report_file}")
        if submission_dir:
            print(f"📤 Submission Files: {submission_dir}")
        print("=" * 40)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)