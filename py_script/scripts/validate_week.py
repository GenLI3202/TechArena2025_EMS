"""
BESS Model Week-Long Validation Script
======================================

Validates the refined BESS optimization model (model.py) using first week of 2024 data.

Validation Focus:
1. Model Correctness: Objective function, variable values, solver performance
2. Constraint Satisfaction: All 9 constraints verified per scenario
3. Configuration Comparison: Optimal C-rate and daily cycle per country

Outputs:
- Detailed logs in validation_week_results/logs/
- CSV results in validation_week_results/results/
- Diagnostic plots in validation_week_results/plots/
- Markdown validation report

Usage:
    python validate_model_week.py [--resume] [--solver SOLVER]

Author: BESS Optimization Team
Date: October 2025
"""

import pandas as pd
import numpy as np
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Any
import sys
import os
import argparse

# Import the BESS optimizer V2
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import BESSOptimizerV2

# Set up comprehensive logging
def setup_logging(output_dir: Path):
    """Setup dual logging to file and console."""
    log_dir = output_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Master log file
    log_file = log_dir / f"validation_master_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    logger = logging.getLogger(__name__)
    logger.info(f"Validation logging initialized: {log_file}")
    return logger

class BESSModelValidator:
    """
    Comprehensive validator for BESS optimization model.

    Validates both model correctness and constraint satisfaction across
    all configuration scenarios using minimal time window (1 week).
    """

    def __init__(self, output_dir: str = "validation_week_results"):
        """Initialize validator with output directory."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Create subdirectories
        (self.output_dir / "logs").mkdir(exist_ok=True)
        (self.output_dir / "results").mkdir(exist_ok=True)
        (self.output_dir / "plots").mkdir(exist_ok=True)

        self.logger = setup_logging(self.output_dir)

        # Initialize optimizer
        self.optimizer = BESSOptimizerV2()

        # Test configurations (matching competition scenarios)
        self.countries = ['DE_LU', 'AT', 'CH', 'HU', 'CZ']  # 5 countries
        self.c_rates = [0.25, 0.33, 0.5]  # 3 C-rates
        self.daily_cycles = [1.0, 1.5, 2.0]  # 3 daily cycles

        # Progress tracking
        self.progress_file = self.output_dir / "validation_progress.json"
        self.completed_scenarios = self._load_progress()

        self.logger.info("="*80)
        self.logger.info("BESS MODEL WEEK-LONG VALIDATION")
        self.logger.info("="*80)
        self.logger.info(f"Countries: {self.countries}")
        self.logger.info(f"C-rates: {self.c_rates}")
        self.logger.info(f"Daily cycles: {self.daily_cycles}")
        self.logger.info(f"Total scenarios: {len(self.countries) * len(self.c_rates) * len(self.daily_cycles)}")
        self.logger.info(f"Already completed: {len(self.completed_scenarios)}")
        self.logger.info("="*80)

    def _load_progress(self) -> List[str]:
        """Load progress from previous run."""
        if self.progress_file.exists():
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        return []

    def _save_progress(self, scenario_name: str):
        """Save progress after each scenario."""
        if scenario_name not in self.completed_scenarios:
            self.completed_scenarios.append(scenario_name)
        with open(self.progress_file, 'w') as f:
            json.dump(self.completed_scenarios, f, indent=2)

    def load_week_data(self, data_file: str, week_start: str = "2024-01-01") -> pd.DataFrame:
        """
        Load first week of data for validation.

        Args:
            data_file: Path to full year JSONL data
            week_start: Start date for week (default: Jan 1, 2024)

        Returns:
            DataFrame with one week of preprocessed data
        """
        self.logger.info(f"Loading week of data starting {week_start}...")

        # Load full data
        full_data = self.optimizer.load_and_preprocess_data(data_file)

        # Extract first week
        week_start_dt = pd.to_datetime(week_start)
        week_end_dt = week_start_dt + timedelta(days=7)

        week_data = full_data[(full_data.index >= week_start_dt) &
                              (full_data.index < week_end_dt)]

        self.logger.info(f"Week data loaded: {len(week_data)} timesteps")
        self.logger.info(f"Date range: {week_data.index.min()} to {week_data.index.max()}")

        return week_data

    def validate_constraint_satisfaction(self, model, solution: Dict) -> Dict[str, Any]:
        """
        Validate that all constraints are satisfied in the solution.

        Returns dict with constraint validation results (pass/fail per constraint).
        """
        validation_results = {
            'all_constraints_satisfied': True,
            'constraint_details': {}
        }

        # Extract solution values
        p_ch = solution.get('p_ch', {})
        p_dis = solution.get('p_dis', {})
        e_soc = solution.get('e_soc', {})
        c_fcr = solution.get('c_fcr', {})
        c_afrr_pos = solution.get('c_afrr_pos', {})
        c_afrr_neg = solution.get('c_afrr_neg', {})
        y_ch = solution.get('y_ch', {})
        y_dis = solution.get('y_dis', {})
        y_fcr = solution.get('y_fcr', {})
        y_afrr_pos = solution.get('y_afrr_pos', {})
        y_afrr_neg = solution.get('y_afrr_neg', {})

        # Get model parameters
        E_nom = model.E_nom.value
        P_max = model.P_max_config.value
        SOC_min = model.SOC_min.value
        SOC_max = model.SOC_max.value
        eta_ch = model.eta_ch.value
        eta_dis = model.eta_dis.value
        dt = model.dt.value
        tau = model.tau.value
        N_cycles = model.N_cycles.value

        # Get block mapping
        block_map = {t: int(model.block_map[t]) for t in model.T}

        # Cst-1: SOC Dynamics (verify energy balance)
        soc_errors = []
        T_list = sorted(list(model.T))
        for i, t in enumerate(T_list):
            if i == 0:
                expected_soc = model.E_soc_init.value + (eta_ch * p_ch[t] - p_dis[t] / eta_dis) * dt
            else:
                t_prev = T_list[i-1]
                expected_soc = e_soc[t_prev] + (eta_ch * p_ch[t] - p_dis[t] / eta_dis) * dt

            actual_soc = e_soc[t]
            error = abs(actual_soc - expected_soc)
            if error > 0.01:  # 10 Wh tolerance
                soc_errors.append((t, error))

        validation_results['constraint_details']['Cst1_SOC_Dynamics'] = {
            'pass': len(soc_errors) == 0,
            'violations': len(soc_errors),
            'max_error': max([e[1] for e in soc_errors]) if soc_errors else 0
        }

        # Cst-2: SOC Limits
        soc_violations = []
        for t in model.T:
            if e_soc[t] < SOC_min * E_nom - 0.01 or e_soc[t] > SOC_max * E_nom + 0.01:
                soc_violations.append((t, e_soc[t]))

        validation_results['constraint_details']['Cst2_SOC_Limits'] = {
            'pass': len(soc_violations) == 0,
            'violations': len(soc_violations),
            'min_soc': min(e_soc.values()) / E_nom,
            'max_soc': max(e_soc.values()) / E_nom
        }

        # Cst-3: No Simultaneous Charge/Discharge
        simultaneous_violations = []
        for t in model.T:
            if y_ch.get(t, 0) + y_dis.get(t, 0) > 1.01:  # tolerance for numerical issues
                simultaneous_violations.append(t)

        validation_results['constraint_details']['Cst3_No_Simultaneous'] = {
            'pass': len(simultaneous_violations) == 0,
            'violations': len(simultaneous_violations)
        }

        # Cst-4: Power Limits (co-optimization constraints)
        power_dis_violations = []
        power_ch_violations = []
        for t in model.T:
            block = block_map[t]

            # Discharge + upward reserves <= P_max
            total_dis = p_dis[t] + 1000 * c_fcr.get(block, 0) + 1000 * c_afrr_pos.get(block, 0)
            if total_dis > P_max + 0.1:  # 0.1 kW tolerance
                power_dis_violations.append((t, total_dis - P_max))

            # Charge + downward reserves <= P_max
            total_ch = p_ch[t] + 1000 * c_fcr.get(block, 0) + 1000 * c_afrr_neg.get(block, 0)
            if total_ch > P_max + 0.1:
                power_ch_violations.append((t, total_ch - P_max))

        validation_results['constraint_details']['Cst4_Power_Limits'] = {
            'pass': len(power_dis_violations) == 0 and len(power_ch_violations) == 0,
            'discharge_violations': len(power_dis_violations),
            'charge_violations': len(power_ch_violations)
        }

        # Cst-5: Daily Cycle Limits
        # For week validation, check weekly total <= 7 * N_cycles * E_nom
        total_discharge_energy = sum(p_dis[t] / eta_dis * dt for t in model.T)
        cycle_limit = 7 * N_cycles * E_nom  # 7 days
        cycle_violation = total_discharge_energy > cycle_limit + 0.01

        validation_results['constraint_details']['Cst5_Daily_Cycles'] = {
            'pass': not cycle_violation,
            'total_discharge_kwh': total_discharge_energy,
            'limit_kwh': cycle_limit,
            'actual_cycles': total_discharge_energy / E_nom
        }

        # Cst-6: Energy Reserves
        energy_reserve_pos_violations = []
        energy_reserve_neg_violations = []
        for t in model.T:
            block = block_map[t]

            # Upward reserve check
            required_energy_pos = (1000 * c_fcr.get(block, 0) + 1000 * c_afrr_pos.get(block, 0)) * tau / eta_dis
            available_energy_pos = e_soc[t] - SOC_min * E_nom
            if required_energy_pos > available_energy_pos + 0.01:
                energy_reserve_pos_violations.append((t, required_energy_pos - available_energy_pos))

            # Downward reserve check
            required_storage_neg = (1000 * c_fcr.get(block, 0) + 1000 * c_afrr_neg.get(block, 0)) * tau * eta_ch
            available_storage_neg = SOC_max * E_nom - e_soc[t]
            if required_storage_neg > available_storage_neg + 0.01:
                energy_reserve_neg_violations.append((t, required_storage_neg - available_storage_neg))

        validation_results['constraint_details']['Cst6_Energy_Reserves'] = {
            'pass': len(energy_reserve_pos_violations) == 0 and len(energy_reserve_neg_violations) == 0,
            'upward_violations': len(energy_reserve_pos_violations),
            'downward_violations': len(energy_reserve_neg_violations)
        }

        # Cst-7: AS Market Exclusivity
        as_exclusivity_violations = []
        for b in model.B:
            if y_fcr.get(b, 0) + y_afrr_pos.get(b, 0) + y_afrr_neg.get(b, 0) > 1.01:
                as_exclusivity_violations.append(b)

        validation_results['constraint_details']['Cst7_AS_Exclusivity'] = {
            'pass': len(as_exclusivity_violations) == 0,
            'violations': len(as_exclusivity_violations)
        }

        # Cst-8: Cross-Market Exclusivity
        cross_market_violations_1 = []
        cross_market_violations_2 = []
        for t in model.T:
            block = block_map[t]

            # No discharge with charging AS
            if y_dis.get(t, 0) + y_fcr.get(block, 0) + y_afrr_neg.get(block, 0) > 1.01:
                cross_market_violations_1.append(t)

            # No charge with discharging AS
            if y_ch.get(t, 0) + y_fcr.get(block, 0) + y_afrr_pos.get(block, 0) > 1.01:
                cross_market_violations_2.append(t)

        validation_results['constraint_details']['Cst8_Cross_Market_Exclusivity'] = {
            'pass': len(cross_market_violations_1) == 0 and len(cross_market_violations_2) == 0,
            'violations_type1': len(cross_market_violations_1),
            'violations_type2': len(cross_market_violations_2)
        }

        # Cst-9: Minimum Bid Sizes (already enforced by model, just verify)
        min_bid_violations = 0
        min_bid_da = model.min_bid_da.value * 1000  # Convert MW to kW
        min_bid_fcr = model.min_bid_fcr.value
        min_bid_afrr = model.min_bid_afrr.value

        for t in model.T:
            if y_ch.get(t, 0) > 0.5 and p_ch[t] < min_bid_da - 0.1:
                min_bid_violations += 1
            if y_dis.get(t, 0) > 0.5 and p_dis[t] < min_bid_da - 0.1:
                min_bid_violations += 1

        for b in model.B:
            if y_fcr.get(b, 0) > 0.5 and c_fcr.get(b, 0) < min_bid_fcr - 0.01:
                min_bid_violations += 1
            if y_afrr_pos.get(b, 0) > 0.5 and c_afrr_pos.get(b, 0) < min_bid_afrr - 0.01:
                min_bid_violations += 1
            if y_afrr_neg.get(b, 0) > 0.5 and c_afrr_neg.get(b, 0) < min_bid_afrr - 0.01:
                min_bid_violations += 1

        validation_results['constraint_details']['Cst9_Min_Bid_Sizes'] = {
            'pass': min_bid_violations == 0,
            'violations': min_bid_violations
        }

        # Check if all constraints passed
        validation_results['all_constraints_satisfied'] = all(
            details['pass'] for details in validation_results['constraint_details'].values()
        )

        return validation_results

    def validate_model_correctness(self, model, solution: Dict, country_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate model correctness: objective function, variable values, etc.
        """
        correctness_results = {}

        # Get model parameters
        E_nom = model.E_nom.value
        P_max = model.P_max_config.value
        dt = model.dt.value

        # Manually calculate objective components
        p_ch = solution.get('p_ch', {})
        p_dis = solution.get('p_dis', {})
        c_fcr = solution.get('c_fcr', {})
        c_afrr_pos = solution.get('c_afrr_pos', {})
        c_afrr_neg = solution.get('c_afrr_neg', {})

        # Calculate DA profit manually
        da_profit_manual = 0
        for t in model.T:
            price_da = model.P_DA[t]
            da_profit_manual += (price_da / 1000 * p_dis[t] - price_da / 1000 * p_ch[t]) * dt

        # Calculate AS profit manually
        as_profit_manual = 0
        fcr_revenue = 0
        afrr_pos_revenue = 0
        afrr_neg_revenue = 0
        for b in model.B:
            fcr_revenue += model.P_FCR[b] * c_fcr.get(b, 0)
            afrr_pos_revenue += model.P_aFRR_pos[b] * c_afrr_pos.get(b, 0)
            afrr_neg_revenue += model.P_aFRR_neg[b] * c_afrr_neg.get(b, 0)

        as_profit_manual = fcr_revenue + afrr_pos_revenue + afrr_neg_revenue

        total_profit_manual = da_profit_manual + as_profit_manual
        total_profit_model = solution.get('objective_value', 0)

        # Check if they match
        profit_error = abs(total_profit_manual - total_profit_model)

        correctness_results['objective_validation'] = {
            'model_objective': total_profit_model,
            'manual_calculation': total_profit_manual,
            'error': profit_error,
            'match': profit_error < 0.01,  # 1 cent tolerance
            'da_profit': da_profit_manual,
            'as_profit': as_profit_manual,
            'fcr_revenue': fcr_revenue,
            'afrr_pos_revenue': afrr_pos_revenue,
            'afrr_neg_revenue': afrr_neg_revenue
        }

        # Validate variable value ranges
        e_soc = solution.get('e_soc', {})
        correctness_results['variable_ranges'] = {
            'soc_min_pct': min(e_soc.values()) / E_nom * 100,
            'soc_max_pct': max(e_soc.values()) / E_nom * 100,
            'soc_avg_pct': np.mean(list(e_soc.values())) / E_nom * 100,
            'max_charge_kw': max(p_ch.values()) if p_ch else 0,
            'max_discharge_kw': max(p_dis.values()) if p_dis else 0,
            'max_fcr_mw': max(c_fcr.values()) if c_fcr else 0,
            'max_afrr_pos_mw': max(c_afrr_pos.values()) if c_afrr_pos else 0,
            'max_afrr_neg_mw': max(c_afrr_neg.values()) if c_afrr_neg else 0
        }

        # Model statistics
        correctness_results['model_stats'] = {
            'num_variables': model.nvariables(),
            'num_constraints': model.nconstraints(),
            'solver_status': solution.get('status', 'unknown'),
            'solve_time_sec': solution.get('solve_time', 0),
            'termination_condition': solution.get('termination_condition', 'unknown')
        }

        # Calculate operational metrics
        total_charge = sum(p_ch.values()) * dt
        total_discharge = sum(p_dis.values()) * dt

        correctness_results['operational_metrics'] = {
            'total_charge_kwh': total_charge,
            'total_discharge_kwh': total_discharge,
            'actual_cycles': total_discharge / E_nom if E_nom > 0 else 0,
            'round_trip_efficiency': total_discharge / total_charge if total_charge > 0 else 0
        }

        return correctness_results

    def run_single_scenario(self, week_data: pd.DataFrame, country: str,
                          c_rate: float, daily_cycle: float,
                          solver_name: str = None) -> Dict[str, Any]:
        """
        Run optimization and validation for a single scenario.

        Returns comprehensive results including validation outcomes.
        """
        scenario_name = f"{country}_C{c_rate}_N{daily_cycle}"
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"Running scenario: {scenario_name}")
        self.logger.info(f"{'='*80}")

        try:
            # Extract country data
            country_data = self.optimizer.extract_country_data(week_data, country)

            # Build model
            self.logger.info("Building optimization model...")
            model = self.optimizer.build_optimization_model(country_data, c_rate, daily_cycle)

            # Solve model
            self.logger.info("Solving optimization model...")
            solution = self.optimizer.solve_model(model, solver_name)

            if solution['status'] not in ['optimal', 'feasible']:
                self.logger.error(f"Scenario {scenario_name} failed to solve: {solution.get('status')}")
                return {
                    'scenario': scenario_name,
                    'country': country,
                    'c_rate': c_rate,
                    'n_cycles': daily_cycle,
                    'status': 'FAILED',
                    'error': solution.get('error', 'Unknown error')
                }

            # Validate constraints
            self.logger.info("Validating constraint satisfaction...")
            constraint_validation = self.validate_constraint_satisfaction(model, solution)

            # Validate model correctness
            self.logger.info("Validating model correctness...")
            correctness_validation = self.validate_model_correctness(model, solution, country_data)

            # Compile results
            result = {
                'scenario': scenario_name,
                'country': country,
                'c_rate': c_rate,
                'n_cycles': daily_cycle,
                'status': 'PASS' if constraint_validation['all_constraints_satisfied'] else 'FAIL',
                'solver_status': solution.get('status'),
                'solve_time': solution.get('solve_time'),

                # Revenue breakdown
                'total_revenue': correctness_validation['objective_validation']['model_objective'],
                'da_revenue': correctness_validation['objective_validation']['da_profit'],
                'as_revenue': correctness_validation['objective_validation']['as_profit'],
                'fcr_revenue': correctness_validation['objective_validation']['fcr_revenue'],
                'afrr_pos_revenue': correctness_validation['objective_validation']['afrr_pos_revenue'],
                'afrr_neg_revenue': correctness_validation['objective_validation']['afrr_neg_revenue'],

                # Operational metrics
                'avg_soc_pct': correctness_validation['variable_ranges']['soc_avg_pct'],
                'min_soc_pct': correctness_validation['variable_ranges']['soc_min_pct'],
                'max_soc_pct': correctness_validation['variable_ranges']['soc_max_pct'],
                'total_charge_kwh': correctness_validation['operational_metrics']['total_charge_kwh'],
                'total_discharge_kwh': correctness_validation['operational_metrics']['total_discharge_kwh'],
                'actual_cycles': correctness_validation['operational_metrics']['actual_cycles'],

                # Model stats
                'num_variables': correctness_validation['model_stats']['num_variables'],
                'num_constraints': correctness_validation['model_stats']['num_constraints'],

                # Constraint validation (pass/fail for each)
                'all_constraints_pass': constraint_validation['all_constraints_satisfied']
            }

            # Add detailed constraint results
            for cst_name, cst_details in constraint_validation['constraint_details'].items():
                result[f'{cst_name}_pass'] = cst_details['pass']
                result[f'{cst_name}_violations'] = cst_details.get('violations', 0)

            # Log summary
            self.logger.info(f"Scenario {scenario_name} - Status: {result['status']}")
            self.logger.info(f"  Total Revenue: €{result['total_revenue']:.2f}")
            self.logger.info(f"  Solve Time: {result['solve_time']:.2f}s")
            self.logger.info(f"  All Constraints Pass: {result['all_constraints_pass']}")

            if not result['all_constraints_pass']:
                self.logger.warning(f"  CONSTRAINT VIOLATIONS DETECTED!")
                for cst_name, cst_details in constraint_validation['constraint_details'].items():
                    if not cst_details['pass']:
                        self.logger.warning(f"    - {cst_name}: {cst_details.get('violations', 0)} violations")

            # Save scenario-specific detailed results
            detailed_result = {
                'scenario_info': result,
                'constraint_validation': constraint_validation,
                'correctness_validation': correctness_validation,
                'solution': solution
            }

            # Convert numpy types in nested dict structure for JSON serialization
            def convert_numpy_types(obj):
                """Recursively convert numpy types to native Python types."""
                if isinstance(obj, dict):
                    return {str(k) if isinstance(k, (np.integer, np.floating)) else k: convert_numpy_types(v)
                           for k, v in obj.items()}
                elif isinstance(obj, (list, tuple)):
                    return [convert_numpy_types(item) for item in obj]
                elif isinstance(obj, np.integer):
                    return int(obj)
                elif isinstance(obj, np.floating):
                    return float(obj)
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
                else:
                    return obj

            result_file = self.output_dir / "results" / f"{scenario_name}_detailed.json"
            with open(result_file, 'w') as f:
                # Convert numpy types before JSON serialization
                json.dump(convert_numpy_types(detailed_result), f, indent=2)

            # Save progress
            self._save_progress(scenario_name)

            return result

        except Exception as e:
            self.logger.error(f"Error in scenario {scenario_name}: {str(e)}", exc_info=True)
            return {
                'scenario': scenario_name,
                'country': country,
                'c_rate': c_rate,
                'n_cycles': daily_cycle,
                'status': 'ERROR',
                'error': str(e)
            }

    def run_all_scenarios(self, data_file: str, solver_name: str = None, resume: bool = True):
        """
        Run validation on all 45 scenarios.

        Args:
            data_file: Path to full year JSONL data
            solver_name: Solver to use (None = auto-detect)
            resume: Whether to resume from previous progress
        """
        self.logger.info("\n" + "="*80)
        self.logger.info("STARTING VALIDATION OF ALL 45 SCENARIOS")
        self.logger.info("="*80 + "\n")

        # Load week data
        week_data = self.load_week_data(data_file)

        # Run all scenarios
        results = []
        total_scenarios = len(self.countries) * len(self.c_rates) * len(self.daily_cycles)
        completed = 0

        for country in self.countries:
            for c_rate in self.c_rates:
                for daily_cycle in self.daily_cycles:
                    scenario_name = f"{country}_C{c_rate}_N{daily_cycle}"

                    # Skip if already completed and resume is enabled
                    if resume and scenario_name in self.completed_scenarios:
                        self.logger.info(f"Skipping {scenario_name} (already completed)")
                        completed += 1
                        continue

                    result = self.run_single_scenario(week_data, country, c_rate, daily_cycle, solver_name)
                    results.append(result)

                    completed += 1
                    self.logger.info(f"\nProgress: {completed}/{total_scenarios} scenarios completed ({completed/total_scenarios*100:.1f}%)\n")

        # Save summary results
        self.logger.info("\n" + "="*80)
        self.logger.info("ALL SCENARIOS COMPLETED - SAVING RESULTS")
        self.logger.info("="*80 + "\n")

        # Load previously completed scenarios if resuming
        if resume and self.completed_scenarios:
            self.logger.info("Loading previous results for complete summary...")
            for scenario_name in self.completed_scenarios:
                if scenario_name not in [r['scenario'] for r in results]:
                    result_file = self.output_dir / "results" / f"{scenario_name}_detailed.json"
                    if result_file.exists():
                        with open(result_file, 'r') as f:
                            detailed = json.load(f)
                            results.append(detailed['scenario_info'])

        results_df = pd.DataFrame(results)

        # Save to CSV
        csv_file = self.output_dir / "results" / "validation_summary.csv"
        results_df.to_csv(csv_file, index=False)
        self.logger.info(f"Summary results saved to: {csv_file}")

        # Generate summary statistics
        self._generate_summary_stats(results_df)

        return results_df

    def _generate_summary_stats(self, results_df: pd.DataFrame):
        """Generate and log summary statistics."""
        self.logger.info("\n" + "="*80)
        self.logger.info("VALIDATION SUMMARY STATISTICS")
        self.logger.info("="*80)

        # Overall pass rate
        total = len(results_df)
        passed = len(results_df[results_df['status'] == 'PASS'])
        failed = len(results_df[results_df['status'] == 'FAIL'])
        errors = len(results_df[results_df['status'] == 'ERROR'])

        self.logger.info(f"\nOverall Results:")
        self.logger.info(f"  Total scenarios: {total}")
        self.logger.info(f"  Passed: {passed} ({passed/total*100:.1f}%)")
        self.logger.info(f"  Failed: {failed} ({failed/total*100:.1f}%)")
        self.logger.info(f"  Errors: {errors} ({errors/total*100:.1f}%)")

        # Revenue statistics (only for successful scenarios)
        successful = results_df[results_df['status'].isin(['PASS', 'FAIL'])]
        if not successful.empty:
            self.logger.info(f"\nRevenue Statistics (€, Week-long):")
            self.logger.info(f"  Mean: €{successful['total_revenue'].mean():.2f}")
            self.logger.info(f"  Median: €{successful['total_revenue'].median():.2f}")
            self.logger.info(f"  Min: €{successful['total_revenue'].min():.2f}")
            self.logger.info(f"  Max: €{successful['total_revenue'].max():.2f}")
            self.logger.info(f"  Std Dev: €{successful['total_revenue'].std():.2f}")

            # Revenue breakdown
            if 'da_revenue' in successful.columns:
                total_da = successful['da_revenue'].sum()
                total_as = successful['as_revenue'].sum()
                total_all = total_da + total_as
                self.logger.info(f"\nRevenue Breakdown:")
                self.logger.info(f"  Day-Ahead: €{total_da:.2f} ({total_da/total_all*100:.1f}%)")
                self.logger.info(f"  Ancillary Services: €{total_as:.2f} ({total_as/total_all*100:.1f}%)")

        # Solve time statistics
        if 'solve_time' in successful.columns:
            self.logger.info(f"\nSolve Time Statistics (seconds):")
            self.logger.info(f"  Mean: {successful['solve_time'].mean():.2f}s")
            self.logger.info(f"  Median: {successful['solve_time'].median():.2f}s")
            self.logger.info(f"  Max: {successful['solve_time'].max():.2f}s")

        # Best configuration per country
        self.logger.info(f"\nBest Configuration per Country:")
        for country in self.countries:
            country_results = successful[successful['country'] == country]
            if not country_results.empty:
                best = country_results.loc[country_results['total_revenue'].idxmax()]
                self.logger.info(f"  {country}: C-rate={best['c_rate']}, N_cycles={best['n_cycles']}, Revenue=€{best['total_revenue']:.2f}")

        # Constraint violation summary
        constraint_cols = [col for col in results_df.columns if col.endswith('_pass')]
        if constraint_cols:
            self.logger.info(f"\nConstraint Validation Summary:")
            for col in constraint_cols:
                constraint_name = col.replace('_pass', '')
                pass_count = results_df[col].sum()
                pass_rate = pass_count / len(results_df) * 100
                self.logger.info(f"  {constraint_name}: {pass_count}/{len(results_df)} passed ({pass_rate:.1f}%)")

        self.logger.info("\n" + "="*80 + "\n")

def main():
    """Main entry point for validation script."""
    parser = argparse.ArgumentParser(description='BESS Model Week-Long Validation')
    parser.add_argument('--data', type=str,
                       default='../data/TechArena2025_data_tidy.jsonl',
                       help='Path to data file')
    parser.add_argument('--solver', type=str, default=None,
                       help='Solver to use (cplex, gurobi, highs, etc.)')
    parser.add_argument('--resume', action='store_true', default=True,
                       help='Resume from previous progress')
    parser.add_argument('--output', type=str, default='validation_week_results',
                       help='Output directory for results')

    args = parser.parse_args()

    # Create validator
    validator = BESSModelValidator(output_dir=args.output)

    # Run validation
    results_df = validator.run_all_scenarios(
        data_file=args.data,
        solver_name=args.solver,
        resume=args.resume
    )

    print("\n" + "="*80)
    print("VALIDATION COMPLETE!")
    print(f"Results saved to: {validator.output_dir}")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
