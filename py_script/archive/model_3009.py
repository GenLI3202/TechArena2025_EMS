"""
BESS Optimization Model for Huawei TechArena 2025
=================================================

This module implements a comprehensive Battery Energy Storage System (BESS) optimization model
for participating in European electricity markets including day-ahead energy trading and 
ancillary services (FCR and aFRR).

Author: Gen's BESS Optimization Team
Date: September 2025
"""

import pandas as pd
import numpy as np
import pyomo.environ as pyo
from datetime import datetime, timedelta
import json
import logging
from typing import Dict, List, Tuple, Optional
import warnings

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BESSOptimizer:
    """
    Battery Energy Storage System optimization model implementation using Pyomo.
    
    This class handles the complete optimization pipeline including:
    - Data preprocessing and alignment
    - Model construction with all constraints
    - Solving optimization problems
    - Result extraction and formatting
    """
    
    def __init__(self):
        """Initialize the BESS optimizer with default parameters."""
        # Fixed BESS parameters
        self.E_nom = 4472  # kWh, nominal energy capacity
        self.eta_ch = 0.95  # charging efficiency
        self.eta_dis = 0.95  # discharging efficiency
        self.SOC_min = 0.1  # minimum SOC (10%)
        self.SOC_max = 0.9  # maximum SOC (90%)
        self.dt = 0.25  # time step in hours (15 minutes)
        self.db = 4.0   # ancillary service block duration in hours
        
        # Market parameters
        self.min_bid_fcr = 1.0   # MW, minimum FCR bid size
        self.min_bid_afrr = 1.0  # MW, minimum aFRR bid size
        
        # Configuration scenarios
        self.countries = ['DE', 'AT', 'CH', 'HU', 'CZ']
        self.c_rates = [0.25, 0.33, 0.5]  # C-rates
        self.daily_cycles = [1.0, 1.5, 2.0]  # daily cycle limits
        
        logger.info("BESS Optimizer initialized with default parameters")
    
    def load_and_preprocess_data(self, data_file: str) -> pd.DataFrame:
        """
        Load and preprocess the market data from JSONL file.
        
        Args:
            data_file: Path to the JSONL data file
            
        Returns:
            pd.DataFrame: Preprocessed data with multi-level columns and proper indexing
        """
        logger.info(f"Loading data from {data_file}")
        
        # Read JSONL file
        data_list = []
        with open(data_file, 'r') as f:
            for line in f:
                data_list.append(json.loads(line.strip()))
        
        df = pd.DataFrame(data_list)
        logger.info(f"Loaded {len(df)} data points")
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed')
        
        # Create multi-level structure based on data source
        processed_dfs = []
        
        # Process day-ahead data (15-min intervals)
        da_data = df[df['source'] == 'day_ahead'].copy()
        if not da_data.empty:
            da_pivot = da_data.pivot_table(
                index='timestamp', 
                columns='country', 
                values='price_eur_mwh', 
                aggfunc='first'
            )
            da_pivot.columns = pd.MultiIndex.from_product([da_pivot.columns, ['day_ahead'], ['']])
            processed_dfs.append(da_pivot)
        
        # Process FCR data (4-hour blocks)
        fcr_data = df[df['source'] == 'fcr'].copy()
        if not fcr_data.empty:
            fcr_pivot = fcr_data.pivot_table(
                index='timestamp',
                columns='country',
                values='price_eur_mwh',
                aggfunc='first'
            )
            fcr_pivot.columns = pd.MultiIndex.from_product([fcr_pivot.columns, ['fcr'], ['']])
            processed_dfs.append(fcr_pivot)
        
        # Process aFRR data (4-hour blocks, positive and negative)
        afrr_data = df[df['source'] == 'afrr'].copy()
        if not afrr_data.empty:
            afrr_pivot = afrr_data.pivot_table(
                index='timestamp',
                columns=['country', 'direction'],
                values='price_eur_mwh',
                aggfunc='first'
            )
            # Restructure to match expected format: (country, source, direction)
            afrr_columns = []
            for (country, direction) in afrr_pivot.columns:
                afrr_columns.append((country, 'afrr', direction))
            afrr_pivot.columns = pd.MultiIndex.from_tuples(afrr_columns)
            processed_dfs.append(afrr_pivot)
        
        # Combine all data
        if processed_dfs:
            combined_df = pd.concat(processed_dfs, axis=1, sort=True)
        else:
            raise ValueError("No valid data found in input file")
        
        # Resample to 15-minute frequency and forward fill
        combined_df = combined_df.resample('15min').ffill()
        
        # Add helper columns for day and block identification
        combined_df['day_id'] = combined_df.index.day_of_year
        combined_df['hour'] = combined_df.index.hour
        combined_df['block_id'] = (combined_df.index.day_of_year - 1) * 6 + combined_df['hour'] // 4
        
        # Sort by timestamp
        combined_df = combined_df.sort_index()
        
        logger.info(f"Data preprocessed. Shape: {combined_df.shape}")
        logger.info(f"Date range: {combined_df.index.min()} to {combined_df.index.max()}")
        
        return combined_df
    
    def build_optimization_model(self, country_data: pd.DataFrame, 
                               c_rate: float, n_cycles: float) -> pyo.ConcreteModel:
        """
        Build the complete Pyomo optimization model.
        
        Args:
            country_data: Market data for specific country
            c_rate: C-rate configuration (power to energy ratio)
            n_cycles: Daily cycle limit
            
        Returns:
            pyo.ConcreteModel: Complete optimization model
        """
        logger.info(f"Building optimization model for C-rate={c_rate}, cycles={n_cycles}")
        
        # Calculate configuration-specific parameters
        P_max_config = c_rate * self.E_nom  # kW, maximum charge/discharge power
        E_soc_init = 0.5 * self.E_nom  # kWh, initial SOC at 50%
        
        # Create model
        model = pyo.ConcreteModel(name="BESS_Optimization")
        
        # Define sets
        T_data = list(range(len(country_data)))
        model.T = pyo.Set(initialize=T_data, doc="Time intervals (15-min)")
        
        # Get unique days and blocks
        days = sorted(country_data['day_id'].unique())
        blocks = sorted(country_data['block_id'].unique())
        model.D = pyo.Set(initialize=days, doc="Days")
        model.B = pyo.Set(initialize=blocks, doc="4-hour blocks")
        
        # Parameters
        model.E_nom = pyo.Param(initialize=self.E_nom, doc="Nominal energy capacity (kWh)")
        model.P_max_config = pyo.Param(initialize=P_max_config, doc="Max charge/discharge power (kW)")
        model.eta_ch = pyo.Param(initialize=self.eta_ch, doc="Charging efficiency")
        model.eta_dis = pyo.Param(initialize=self.eta_dis, doc="Discharging efficiency")
        model.SOC_min = pyo.Param(initialize=self.SOC_min, doc="Minimum SOC fraction")
        model.SOC_max = pyo.Param(initialize=self.SOC_max, doc="Maximum SOC fraction")
        model.N_cycles = pyo.Param(initialize=n_cycles, doc="Daily cycle limit")
        model.dt = pyo.Param(initialize=self.dt, doc="Time step duration (h)")
        model.db = pyo.Param(initialize=self.db, doc="Block duration (h)")
        model.E_soc_init = pyo.Param(initialize=E_soc_init, doc="Initial SOC (kWh)")
        model.min_bid_fcr = pyo.Param(initialize=self.min_bid_fcr, doc="Min FCR bid (MW)")
        model.min_bid_afrr = pyo.Param(initialize=self.min_bid_afrr, doc="Min aFRR bid (MW)")
        
        # Price parameters - extract from country_data
        country = country_data.columns.levels[0][0]  # Get country name
        
        # Day-ahead prices (EUR/MWh)
        da_prices = {}
        if (country, 'day_ahead', '') in country_data.columns:
            da_series = country_data[(country, 'day_ahead', '')].fillna(0)
            da_prices = {t: float(da_series.iloc[t]) for t in model.T}
        else:
            # Default to zero if no day-ahead data
            da_prices = {t: 0.0 for t in model.T}
        model.P_DA = pyo.Param(model.T, initialize=da_prices, default=0.0, doc="Day-ahead prices (EUR/MWh)")
        
        # FCR prices (EUR/MW)
        fcr_prices = {}
        if (country, 'fcr', '') in country_data.columns:
            fcr_series = country_data[(country, 'fcr', '')].fillna(0)
            # Map time intervals to blocks and get block prices
            for t in model.T:
                block_id = country_data['block_id'].iloc[t]
                if block_id in blocks:
                    # Find first timestamp of this block to get price
                    block_timestamps = country_data[country_data['block_id'] == block_id].index
                    if len(block_timestamps) > 0:
                        fcr_prices[t] = float(fcr_series.loc[block_timestamps[0]])
                    else:
                        fcr_prices[t] = 0.0
                else:
                    fcr_prices[t] = 0.0
        else:
            fcr_prices = {t: 0.0 for t in model.T}
        model.P_FCR = pyo.Param(model.T, initialize=fcr_prices, default=0.0, doc="FCR prices (EUR/MW)")
        
        # aFRR positive prices (EUR/MW)
        afrr_pos_prices = {}
        if (country, 'afrr', 'positive') in country_data.columns:
            afrr_pos_series = country_data[(country, 'afrr', 'positive')].fillna(0)
            for t in model.T:
                block_id = country_data['block_id'].iloc[t]
                if block_id in blocks:
                    block_timestamps = country_data[country_data['block_id'] == block_id].index
                    if len(block_timestamps) > 0:
                        afrr_pos_prices[t] = float(afrr_pos_series.loc[block_timestamps[0]])
                    else:
                        afrr_pos_prices[t] = 0.0
                else:
                    afrr_pos_prices[t] = 0.0
        else:
            afrr_pos_prices = {t: 0.0 for t in model.T}
        model.P_aFRR_pos = pyo.Param(model.T, initialize=afrr_pos_prices, default=0.0, doc="aFRR positive prices (EUR/MW)")
        
        # aFRR negative prices (EUR/MW)
        afrr_neg_prices = {}
        if (country, 'afrr', 'negative') in country_data.columns:
            afrr_neg_series = country_data[(country, 'afrr', 'negative')].fillna(0)
            for t in model.T:
                block_id = country_data['block_id'].iloc[t]
                if block_id in blocks:
                    block_timestamps = country_data[country_data['block_id'] == block_id].index
                    if len(block_timestamps) > 0:
                        afrr_neg_prices[t] = float(afrr_neg_series.loc[block_timestamps[0]])
                    else:
                        afrr_neg_prices[t] = 0.0
                else:
                    afrr_neg_prices[t] = 0.0
        else:
            afrr_neg_prices = {t: 0.0 for t in model.T}
        model.P_aFRR_neg = pyo.Param(model.T, initialize=afrr_neg_prices, default=0.0, doc="aFRR negative prices (EUR/MW)")
        
        # Decision variables
        model.p_ch = pyo.Var(model.T, domain=pyo.NonNegativeReals, doc="Charging power (kW)")
        model.p_dis = pyo.Var(model.T, domain=pyo.NonNegativeReals, doc="Discharging power (kW)")
        model.e_soc = pyo.Var(model.T, domain=pyo.NonNegativeReals, doc="State of charge (kWh)")
        
        model.c_fcr = pyo.Var(model.B, domain=pyo.NonNegativeReals, doc="FCR capacity bid (MW)")
        model.c_afrr_pos = pyo.Var(model.B, domain=pyo.NonNegativeReals, doc="aFRR positive bid (MW)")
        model.c_afrr_neg = pyo.Var(model.B, domain=pyo.NonNegativeReals, doc="aFRR negative bid (MW)")
        
        model.y_ch = pyo.Var(model.T, domain=pyo.Binary, doc="Charging binary")
        model.y_dis = pyo.Var(model.T, domain=pyo.Binary, doc="Discharging binary")
        model.y_fcr = pyo.Var(model.B, domain=pyo.Binary, doc="FCR bidding binary")
        model.y_afrr_pos = pyo.Var(model.B, domain=pyo.Binary, doc="aFRR positive bidding binary")
        model.y_afrr_neg = pyo.Var(model.B, domain=pyo.Binary, doc="aFRR negative bidding binary")
        
        # Objective function: Maximize total profit
        def objective_rule(model):
            # Day-ahead energy arbitrage revenue (EUR)
            da_revenue = sum(
                (model.P_DA[t] / 1000) * model.p_dis[t] * model.dt - 
                (model.P_DA[t] / 1000) * model.p_ch[t] * model.dt 
                for t in model.T
            )
            
            # Ancillary service capacity revenue (EUR)
            # Group time intervals by blocks for pricing
            as_revenue = 0
            for b in model.B:
                # Find representative time step for this block
                block_times = [t for t in model.T if country_data['block_id'].iloc[t] == b]
                if block_times:
                    t_rep = block_times[0]  # Use first time step of block
                    as_revenue += (
                        model.P_FCR[t_rep] * model.c_fcr[b] * model.db +
                        model.P_aFRR_pos[t_rep] * model.c_afrr_pos[b] * model.db +
                        model.P_aFRR_neg[t_rep] * model.c_afrr_neg[b] * model.db
                    )
            
            return da_revenue + as_revenue
        
        model.objective = pyo.Objective(rule=objective_rule, sense=pyo.maximize)
        
        # Constraints
        
        # 1. SOC dynamics
        def soc_dynamics_rule(model, t):
            if t == model.T.first():
                return model.e_soc[t] == (
                    model.E_soc_init + 
                    (model.p_ch[t] * model.eta_ch - model.p_dis[t] / model.eta_dis) * model.dt
                )
            else:
                t_prev = model.T.prev(t)
                return model.e_soc[t] == (
                    model.e_soc[t_prev] + 
                    (model.p_ch[t] * model.eta_ch - model.p_dis[t] / model.eta_dis) * model.dt
                )
        model.soc_dynamics = pyo.Constraint(model.T, rule=soc_dynamics_rule)
        
        # 2. SOC limits
        def soc_min_rule(model, t):
            return model.e_soc[t] >= model.SOC_min * model.E_nom
        model.soc_min_limit = pyo.Constraint(model.T, rule=soc_min_rule)
        
        def soc_max_rule(model, t):
            return model.e_soc[t] <= model.SOC_max * model.E_nom
        model.soc_max_limit = pyo.Constraint(model.T, rule=soc_max_rule)
        
        # 3. Power limits with binary linking
        def power_ch_limit_rule(model, t):
            return model.p_ch[t] <= model.y_ch[t] * model.P_max_config
        model.power_ch_limit = pyo.Constraint(model.T, rule=power_ch_limit_rule)
        
        def power_dis_limit_rule(model, t):
            return model.p_dis[t] <= model.y_dis[t] * model.P_max_config
        model.power_dis_limit = pyo.Constraint(model.T, rule=power_dis_limit_rule)
        
        # 4. Simultaneous operation prevention
        def no_simultaneous_rule(model, t):
            return model.y_ch[t] + model.y_dis[t] <= 1
        model.no_simultaneous = pyo.Constraint(model.T, rule=no_simultaneous_rule)
        
        # 5. Market co-optimization power limits
        def power_ch_reserve_limit_rule(model, t):
            # Find which block this time step belongs to
            block_id = country_data['block_id'].iloc[t]
            if block_id in model.B:
                return (model.p_ch[t] + 1000 * model.c_fcr[block_id] + 
                       1000 * model.c_afrr_pos[block_id] <= model.P_max_config)
            else:
                return pyo.Constraint.Skip
        model.power_ch_reserve_limit = pyo.Constraint(model.T, rule=power_ch_reserve_limit_rule)
        
        def power_dis_reserve_limit_rule(model, t):
            block_id = country_data['block_id'].iloc[t]
            if block_id in model.B:
                return (model.p_dis[t] + 1000 * model.c_fcr[block_id] + 
                       1000 * model.c_afrr_neg[block_id] <= model.P_max_config)
            else:
                return pyo.Constraint.Skip
        model.power_dis_reserve_limit = pyo.Constraint(model.T, rule=power_dis_reserve_limit_rule)
        
        # 6. Daily cycle limit
        def daily_cycle_rule(model, d):
            # Get time steps for this day
            day_times = [t for t in model.T if country_data['day_id'].iloc[t] == d]
            if day_times:
                return sum(model.p_dis[t] * model.dt for t in day_times) <= model.N_cycles * model.E_nom
            else:
                return pyo.Constraint.Skip
        model.daily_cycle_limit = pyo.Constraint(model.D, rule=daily_cycle_rule)
        
        # 7. Ancillary service energy reserve constraints
        def energy_reserve_pos_rule(model, t):
            block_id = country_data['block_id'].iloc[t]
            if block_id in model.B:
                return (model.e_soc[t] >= 
                       model.SOC_min * model.E_nom + 
                       (1000 * model.c_fcr[block_id] + 1000 * model.c_afrr_pos[block_id]) * model.dt)
            else:
                return pyo.Constraint.Skip
        model.energy_reserve_pos = pyo.Constraint(model.T, rule=energy_reserve_pos_rule)
        
        def energy_reserve_neg_rule(model, t):
            block_id = country_data['block_id'].iloc[t]
            if block_id in model.B:
                return (model.e_soc[t] <= 
                       model.SOC_max * model.E_nom - 
                       (1000 * model.c_fcr[block_id] + 1000 * model.c_afrr_neg[block_id]) * model.dt)
            else:
                return pyo.Constraint.Skip
        model.energy_reserve_neg = pyo.Constraint(model.T, rule=energy_reserve_neg_rule)
        
        # 8. Minimum bid size constraints
        def fcr_min_bid_rule(model, b):
            return model.c_fcr[b] >= model.y_fcr[b] * model.min_bid_fcr
        model.fcr_min_bid = pyo.Constraint(model.B, rule=fcr_min_bid_rule)
        
        def fcr_max_bid_rule(model, b):
            return model.c_fcr[b] <= model.y_fcr[b] * (model.P_max_config / 1000)
        model.fcr_max_bid = pyo.Constraint(model.B, rule=fcr_max_bid_rule)
        
        def afrr_pos_min_bid_rule(model, b):
            return model.c_afrr_pos[b] >= model.y_afrr_pos[b] * model.min_bid_afrr
        model.afrr_pos_min_bid = pyo.Constraint(model.B, rule=afrr_pos_min_bid_rule)
        
        def afrr_pos_max_bid_rule(model, b):
            return model.c_afrr_pos[b] <= model.y_afrr_pos[b] * (model.P_max_config / 1000)
        model.afrr_pos_max_bid = pyo.Constraint(model.B, rule=afrr_pos_max_bid_rule)
        
        def afrr_neg_min_bid_rule(model, b):
            return model.c_afrr_neg[b] >= model.y_afrr_neg[b] * model.min_bid_afrr
        model.afrr_neg_min_bid = pyo.Constraint(model.B, rule=afrr_neg_min_bid_rule)
        
        def afrr_neg_max_bid_rule(model, b):
            return model.c_afrr_neg[b] <= model.y_afrr_neg[b] * (model.P_max_config / 1000)
        model.afrr_neg_max_bid = pyo.Constraint(model.B, rule=afrr_neg_max_bid_rule)
        
        logger.info(f"Model built successfully with {len(model.T)} time steps, "
                   f"{len(model.D)} days, and {len(model.B)} blocks")
        
        return model
    
    def solve_model(self, model: pyo.ConcreteModel, solver_name: str = 'cplex') -> Dict:
        """
        Solve the optimization model and extract results.
        
        Args:
            model: Built Pyomo model
            solver_name: Solver to use (default: 'cbc')
            
        Returns:
            Dict: Solution results including objective value and key variables
        """
        logger.info(f"Solving model with {solver_name} solver")
        
        try:
            # Create solver
            solver = pyo.SolverFactory(solver_name)
            if not solver.available():
                # Try alternative solvers (prioritize commercial solvers)
                alternative_solvers = ['cplex', 'gurobi', 'cbc', 'glpk']
                solver_found = False
                
                for alt_solver in alternative_solvers:
                    if alt_solver != solver_name:
                        alt_solver_obj = pyo.SolverFactory(alt_solver)
                        if alt_solver_obj.available():
                            logger.info(f"{solver_name} not available, using {alt_solver} instead")
                            solver = alt_solver_obj
                            solver_name = alt_solver
                            solver_found = True
                            break
                
                if not solver_found:
                    error_msg = (f"No suitable solver found. Tried: {solver_name}, {alternative_solvers}. "
                               "Please install a solver (CBC, GLPK, Gurobi, or CPLEX).")
                    logger.error(error_msg)
                    return {"status": "no_solver", "error": error_msg}
            
            # Set solver options for better performance on large problems
            if solver_name.lower() == 'cplex':
                solver.options['mip_tolerances_mipgap'] = 0.01  # 1% optimality gap
                solver.options['timelimit'] = 600  # 10 minute time limit
                solver.options['threads'] = 0  # Use all available cores
            elif solver_name.lower() == 'gurobi':
                solver.options['MIPGap'] = 0.01  # 1% optimality gap
                solver.options['TimeLimit'] = 600  # 10 minute time limit
                solver.options['Threads'] = 0  # Use all available cores
            elif solver_name.lower() == 'cbc':
                solver.options['seconds'] = 300  # 5 minute time limit
                solver.options['ratio'] = 0.01   # 1% optimality gap
            elif solver_name.lower() == 'glpk':
                solver.options['tmlim'] = 300    # 5 minute time limit
            
            # Solve
            logger.info("Starting optimization solve...")
            results = solver.solve(model, tee=False)
            
            # Check solution status
            if results.solver.termination_condition != pyo.TerminationCondition.optimal:
                if results.solver.termination_condition == pyo.TerminationCondition.feasible:
                    logger.warning("Solver found feasible but not optimal solution")
                elif results.solver.termination_condition == pyo.TerminationCondition.maxTimeLimit:
                    logger.warning("Solver hit time limit - may not be optimal")
                else:
                    logger.error(f"Solver failed: {results.solver.termination_condition}")
                    return {"status": "failed", "termination_condition": str(results.solver.termination_condition)}
            
            # Extract solution
            solution = {
                "status": "optimal" if results.solver.termination_condition == pyo.TerminationCondition.optimal else "feasible",
                "objective_value": pyo.value(model.objective),
                "solve_time": results.solver.time if hasattr(results.solver, 'time') else None,
                "termination_condition": str(results.solver.termination_condition),
                "solver_used": solver_name,
            }
            
            # Extract key variables (time series)
            solution["p_ch"] = {t: pyo.value(model.p_ch[t]) for t in model.T}
            solution["p_dis"] = {t: pyo.value(model.p_dis[t]) for t in model.T}
            solution["e_soc"] = {t: pyo.value(model.e_soc[t]) for t in model.T}
            
            # Extract ancillary service bids (by block)
            solution["c_fcr"] = {b: pyo.value(model.c_fcr[b]) for b in model.B}
            solution["c_afrr_pos"] = {b: pyo.value(model.c_afrr_pos[b]) for b in model.B}
            solution["c_afrr_neg"] = {b: pyo.value(model.c_afrr_neg[b]) for b in model.B}
            
            # Calculate summary statistics
            total_energy_charged = sum(solution["p_ch"][t] * 0.25 for t in model.T)  # kWh
            total_energy_discharged = sum(solution["p_dis"][t] * 0.25 for t in model.T)  # kWh
            avg_fcr_bid = np.mean(list(solution["c_fcr"].values()))
            avg_afrr_pos_bid = np.mean(list(solution["c_afrr_pos"].values()))
            avg_afrr_neg_bid = np.mean(list(solution["c_afrr_neg"].values()))
            
            solution["summary"] = {
                "total_energy_charged_kwh": total_energy_charged,
                "total_energy_discharged_kwh": total_energy_discharged,
                "avg_fcr_bid_mw": avg_fcr_bid,
                "avg_afrr_pos_bid_mw": avg_afrr_pos_bid,
                "avg_afrr_neg_bid_mw": avg_afrr_neg_bid,
                "annual_profit_eur": solution["objective_value"]
            }
            
            logger.info(f"Optimization completed successfully. Objective value: {solution['objective_value']:.2f} EUR")
            
            return solution
            
        except Exception as e:
            logger.error(f"Error during optimization: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    def run_optimization(self, data_file: str, country: str, c_rate: float, n_cycles: float) -> Dict:
        """
        Run complete optimization for a single scenario.
        
        Args:
            data_file: Path to market data file
            country: Country to optimize for
            c_rate: C-rate configuration
            n_cycles: Daily cycle limit
            
        Returns:
            Dict: Complete optimization results
        """
        logger.info(f"Running optimization for {country}, C-rate={c_rate}, cycles={n_cycles}")
        
        try:
            # Load and preprocess data
            full_data = self.load_and_preprocess_data(data_file)
            
            # Extract country-specific data
            country_columns = [col for col in full_data.columns if col[0] == country]
            if not country_columns:
                raise ValueError(f"No data found for country {country}")
            
            # Create country dataset with helper columns
            country_data = full_data[country_columns].copy()
            country_data['day_id'] = full_data['day_id']
            country_data['block_id'] = full_data['block_id']
            
            # Build and solve model
            model = self.build_optimization_model(country_data, c_rate, n_cycles)
            solution = self.solve_model(model)
            
            # Add scenario information to solution
            solution["scenario"] = {
                "country": country,
                "c_rate": c_rate,
                "n_cycles": n_cycles,
                "P_max_config_kw": c_rate * self.E_nom,
                "E_nom_kwh": self.E_nom
            }
            
            return solution
            
        except Exception as e:
            logger.error(f"Error in optimization pipeline: {str(e)}")
            return {
                "status": "error", 
                "error": str(e),
                "scenario": {"country": country, "c_rate": c_rate, "n_cycles": n_cycles}
            }
    
    def run_all_scenarios(self, data_file: str) -> List[Dict]:
        """
        Run optimization for all country/configuration scenarios.
        
        Args:
            data_file: Path to market data file
            
        Returns:
            List[Dict]: Results for all scenarios
        """
        logger.info("Starting optimization for all scenarios")
        
        all_results = []
        total_scenarios = len(self.countries) * len(self.c_rates) * len(self.daily_cycles)
        scenario_count = 0
        
        for country in self.countries:
            for c_rate in self.c_rates:
                for n_cycles in self.daily_cycles:
                    scenario_count += 1
                    logger.info(f"Running scenario {scenario_count}/{total_scenarios}")
                    
                    result = self.run_optimization(data_file, country, c_rate, n_cycles)
                    all_results.append(result)
                    
                    # Log progress
                    if result["status"] in ["optimal", "feasible"]:
                        profit = result.get("objective_value", 0)
                        logger.info(f"Scenario completed: {country} C{c_rate} Cyc{n_cycles} "
                                  f"-> {profit:.0f} EUR")
                    else:
                        logger.warning(f"Scenario failed: {country} C{c_rate} Cyc{n_cycles} "
                                     f"-> {result['status']}")
        
        logger.info(f"All {total_scenarios} scenarios completed")
        return all_results


def main():
    """Main function to run the complete optimization pipeline."""
    # Initialize optimizer
    optimizer = BESSOptimizer()
    
    # Data file path
    data_file = "../data/TechArena2025_data_tidy.jsonl"
    
    # Run single test scenario first
    logger.info("Running test scenario: Germany, C-rate=0.5, cycles=1.0")
    test_result = optimizer.run_optimization(data_file, "DE", 0.5, 1.0)
    
    if test_result["status"] in ["optimal", "feasible"]:
        logger.info(f"Test successful! Profit: {test_result['objective_value']:.2f} EUR")
        
        # Run all scenarios
        all_results = optimizer.run_all_scenarios(data_file)
        
        # Save results
        results_file = "../output/optimization_results.json"
        with open(results_file, 'w') as f:
            json.dump(all_results, f, indent=2, default=str)
        
        logger.info(f"Results saved to {results_file}")
        
        # Print summary
        successful_scenarios = [r for r in all_results if r["status"] in ["optimal", "feasible"]]
        logger.info(f"Successfully solved {len(successful_scenarios)}/{len(all_results)} scenarios")
        
        if successful_scenarios:
            best_result = max(successful_scenarios, key=lambda x: x["objective_value"])
            best_scenario = best_result["scenario"]
            logger.info(f"Best scenario: {best_scenario['country']} C{best_scenario['c_rate']} "
                       f"Cyc{best_scenario['n_cycles']} -> {best_result['objective_value']:.0f} EUR")
    
    else:
        logger.error(f"Test scenario failed: {test_result}")


if __name__ == "__main__":
    main()