"""
BESS Optimizer V2 - Phase II Implementation
============================================

This module implements the Phase II Battery Energy Storage System (BESS) optimization model
for Huawei TechArena 2025 competition.

Version 2 Improvements (over Phase I archived in r1-static-battery branch):
---------------------------------------------------------------------------
Core Optimizations:
- Eliminated constraint closure anti-patterns for better performance
- Pre-computed block-to-time mappings for O(1) lookup efficiency
- AS prices indexed by block instead of time to reduce memory overhead
- Constraint functions use model parameters instead of external data closures
- Optimized objective function computation
- Enhanced memory efficiency for full-year optimizations

Phase II Enhancements:
- Added reserve duration parameter for accurate energy reserve calculations
- Refined constraints for energy reserve calculations in upward/downward regulation
- Improved representation of activation durations for aFRR and FCR services
- Comprehensive input validation and error handling
- Consistent solver time limits across different solvers

Technical Features:
- Multi-market co-optimization (day-ahead, FCR, aFRR)
- Advanced battery operation constraints (SOC dynamics, cycle limits)
- Support for multiple C-rates and daily cycle configurations
- Cross-market exclusivity and minimum bid size constraints

Author: Gen's BESS Optimization Team
Phase II Development: October-November 2025
"""

import pandas as pd
import numpy as np
import pyomo.environ as pyo
from datetime import datetime, timedelta
import json
import logging
from typing import Dict, List, Tuple, Optional, Any
import warnings

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BESSOptimizerV2:
    """
    Battery Energy Storage System Optimizer - Version 2 (Phase II)

    Phase II optimization model with enhanced constraint handling and performance.

    Key Features:
    - Multi-market co-optimization (day-ahead energy, FCR, aFRR capacity markets)
    - Advanced SOC dynamics with charging/discharging efficiency modeling
    - Reserve energy constraints with configurable activation durations
    - Daily cycle limits and power constraints based on C-rate configuration
    - Cross-market exclusivity and minimum bid size enforcement

    Version 2 Improvements:
    - Constraint closure anti-patterns eliminated for better solver performance
    - Pre-computed index mappings for O(1) lookup efficiency
    - Memory-optimized data structures for full-year horizon
    - Comprehensive input validation and error handling
    - Enhanced reserve duration modeling for Phase II requirements

    Attributes:
        battery_params (dict): Battery technical specifications
        market_params (dict): Market rules and constraints
        countries (list): Supported country markets
        c_rates (list): Available C-rate configurations
        daily_cycles (list): Available daily cycle limit options
    """
    
    def __init__(self):
        """Initialize the BESS Optimizer V2 with default Phase II parameters."""
        # Battery specifications
        self.battery_params = {
            'capacity_kwh': 4472,
            'efficiency': 0.95,
            'soc_min': 0, # the offical QnA says in this challenge free to use from 0-100%
            'soc_max': 1,
            'initial_soc': 0.5,
            'daily_cycle_limit': 1.0  # Default, will be overridden
        }
        
        # Market parameters
        self.market_params = {
            'min_bid_da': 0.1,    # MW
            'min_bid_fcr': 1.0,   # MW
            'min_bid_afrr': 1.0,  # MW
            'time_step_hours': 0.25,  # 15 minutes
            'block_duration_hours': 4.0,  # AS market blocks
            'reserve_duration_hours': 0.25, # Assumed activation duration for reserve calculation
            'solver_time_limit': 600  # seconds - consistent across all solvers
        }
        
        # Configuration scenarios
        # Include DE_LU for coupled Germany-Luxembourg day-ahead market
        self.countries = ['DE', 'DE_LU', 'AT', 'CH', 'HU', 'CZ']
        self.c_rates = [0.25, 0.33, 0.5]
        self.daily_cycles = [1.0, 1.5, 2.0]
        
        # Pre-computed mappings for efficiency
        self._block_to_times = {}
        self._time_to_block = {}
        self._day_to_times = {}
        
        logger.info("BESS Optimizer V2 (Phase II) initialized")
    
    def _validate_input_data(self, country_data: pd.DataFrame, blocks: List[int], 
                           days: List[int], T_data: List[int]) -> None:
        """
        Comprehensive input data validation.
        
        Args:
            country_data: Market data for validation
            blocks: List of block IDs
            days: List of day IDs
            T_data: List of time indices
        """
        logger.info("Validating input data...")
        
        # Check for missing data
        required_cols = ['price_day_ahead', 'price_fcr', 'price_afrr_pos', 'price_afrr_neg', 
                        'block_id', 'day_id']
        missing_cols = [col for col in required_cols if col not in country_data.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Check for null values
        null_counts = country_data[required_cols].isnull().sum()
        if null_counts.any():
            logger.warning(f"Null values found: {null_counts[null_counts > 0].to_dict()}")
        
        # Validate block_id continuity
        if not all(isinstance(b, (int, np.integer)) for b in blocks):
            raise ValueError("Block IDs must be integers")
        
        # Check negative prices (warn but don't fail - they can be valid)
        for col in ['price_day_ahead', 'price_fcr', 'price_afrr_pos', 'price_afrr_neg']:
            negative_count = (country_data[col] < 0).sum()
            if negative_count > 0:
                logger.warning(f"Found {negative_count} negative prices in {col}")
        
        # Validate block structure (each block should have ~16 time intervals)
        intervals_per_block = self.market_params['block_duration_hours'] / self.market_params['time_step_hours']
        expected_intervals = int(intervals_per_block)
        
        block_sizes = country_data.groupby('block_id').size()
        irregular_blocks = block_sizes[block_sizes != expected_intervals]
        if len(irregular_blocks) > 0:
            logger.warning(f"Found {len(irregular_blocks)} blocks with irregular size (expected {expected_intervals})")
            logger.warning(f"The irregular blocks are: {irregular_blocks.to_dict()}")
        
        # Validate time horizon
        expected_hours_per_year = 365.25 * 24
        expected_intervals_per_year = expected_hours_per_year / self.market_params['time_step_hours']
        
        if len(T_data) > expected_intervals_per_year * 1.1:  # Allow 10% margin
            logger.warning(f"Time horizon unusually large: {len(T_data)} intervals "
                          f"(expected ~{expected_intervals_per_year:.0f} for one year)")
        
        logger.info("Input validation completed")
    
    def load_and_preprocess_data(self, data_file: str) -> pd.DataFrame:
        """
        Load and preprocess the market data from JSONL file.
        Enhanced with additional validation and robustness checks.
        """
        logger.info(f"Loading data from {data_file}")
        
        # Read JSONL file
        data_list = []
        with open(data_file, 'r') as f:
            for line in f:
                data_list.append(json.loads(line.strip()))
        
        df = pd.DataFrame(data_list)
        logger.info(f"Loaded {len(df)} data points")
        
        # Convert timestamp to datetime and round to nearest 15-minute interval
        df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed')
        # CRITICAL FIX: Round timestamps to nearest 15-min to avoid misalignment
        df['timestamp'] = df['timestamp'].dt.round('15min')
        
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
                values='price_eur_mw',
                aggfunc='first'
            )
            fcr_pivot.columns = pd.MultiIndex.from_product([fcr_pivot.columns, ['fcr'], ['']])
            processed_dfs.append(fcr_pivot)
        
        # Process aFRR data (4-hour blocks)
        afrr_data = df[df['source'] == 'afrr'].copy()
        if not afrr_data.empty:
            # Pivot for both positive and negative
            afrr_pos = afrr_data[afrr_data['direction'] == 'positive'].pivot_table(
                index='timestamp',
                columns='country', 
                values='price_eur_mw',
                aggfunc='first'
            )
            afrr_neg = afrr_data[afrr_data['direction'] == 'negative'].pivot_table(
                index='timestamp',
                columns='country',
                values='price_eur_mw', 
                aggfunc='first'
            )
            
            afrr_pos.columns = pd.MultiIndex.from_product([afrr_pos.columns, ['afrr'], ['positive']])
            afrr_neg.columns = pd.MultiIndex.from_product([afrr_neg.columns, ['afrr'], ['negative']])
            
            processed_dfs.extend([afrr_pos, afrr_neg])
        
        # Combine all data
        if processed_dfs:
            combined_df = pd.concat(processed_dfs, axis=1)
        else:
            raise ValueError("No valid data found in input file")
        
        # FIXED: Since timestamps are already rounded to 15-min, just ensure complete timeline
        # Get the full time range from the data
        start_time = combined_df.index.min()
        end_time = combined_df.index.max()
        
        # Create a complete 15-minute frequency index
        full_index = pd.date_range(start=start_time, end=end_time, freq='15min')
        
        # Reindex to ensure all 15-min slots are present and forward fill
        combined_df = combined_df.reindex(full_index).ffill()
        
        # Verify the fix: ensure timestamps are aligned
        logger.info(f"Time range: {combined_df.index.min()} to {combined_df.index.max()}")
        logger.info(f"Index frequency: {pd.infer_freq(combined_df.index)}")
        
        # Sort by timestamp
        combined_df = combined_df.sort_index()
        
        logger.info(f"Data preprocessed. Shape: {combined_df.shape}")
        logger.info(f"Date range: {combined_df.index.min()} to {combined_df.index.max()}")
        
        return combined_df
    
    def build_optimization_model(self, country_data: pd.DataFrame, 
                               c_rate: float, daily_cycle_limit: float) -> pyo.ConcreteModel:
        """
        Build the improved optimization model addressing all critical issues.
        
        Key improvements:
        1. Pre-computed block mappings for O(1) lookup
        2. AS prices indexed by block instead of time
        3. Constraint functions use model parameters only
        4. Comprehensive validation
        
        Args:
            country_data: Market data for specific country
            c_rate: C-rate configuration (power to energy ratio)
            daily_cycle_limit: Daily cycle limit
            
        Returns:
            pyo.ConcreteModel: Improved optimization model
        """
        logger.info(f"Building improved optimization model for C-rate={c_rate}, cycles={daily_cycle_limit}")
        
        # Update battery parameters for this configuration
        self.battery_params['daily_cycle_limit'] = daily_cycle_limit
        P_max_config = c_rate * self.battery_params['capacity_kwh']  # kW
        
        # Extract time range for this data
        T_data = list(range(len(country_data)))
        
        # Extract unique blocks and days 
        blocks = sorted(country_data['block_id'].unique())
        days = sorted(country_data['day_id'].unique())
        
        logger.info(f"Time horizon: {len(T_data)} periods ({len(T_data) * self.market_params['time_step_hours']:.1f} hours)")
        logger.info(f"Blocks: {len(blocks)} blocks")
        logger.info(f"Days: {len(days)} days")
        
        # Input validation
        self._validate_input_data(country_data, blocks, days, T_data)
        
        # PRE-COMPUTE MAPPINGS FOR EFFICIENCY (Addresses Critical Issue #3)
        block_to_times = {}
        time_to_block = {}
        day_to_times = {}
        for t in T_data:
            block_id = int(country_data['block_id'].iloc[t])
            if block_id not in block_to_times:
                block_to_times[block_id] = []
            block_to_times[block_id].append(t)
            time_to_block[t] = block_id

            day_id = int(country_data['day_id'].iloc[t])
            if day_id not in day_to_times:
                day_to_times[day_id] = []
            day_to_times[day_id].append(t)

        # Store for objective function (eliminates O(B×T) complexity)
        self._block_to_times = block_to_times
        self._day_to_times = day_to_times
        
        # PRE-COMPUTE AS PRICES BY BLOCK (Addresses Critical Issue #4)
        fcr_prices_by_block = {}
        afrr_pos_prices_by_block = {}
        afrr_neg_prices_by_block = {}
        
        for b in blocks:
            # Take first time step in block (all should have same price)
            t_rep = block_to_times[b][0]
            fcr_prices_by_block[b] = float(country_data['price_fcr'].iloc[t_rep])
            afrr_pos_prices_by_block[b] = float(country_data['price_afrr_pos'].iloc[t_rep])
            afrr_neg_prices_by_block[b] = float(country_data['price_afrr_neg'].iloc[t_rep])
        
        # Create concrete model
        model = pyo.ConcreteModel(name="Improved_BESS_Optimization")
        
        # Sets
        model.T = pyo.Set(initialize=T_data, doc="Set of 15-minute time intervals")
        model.B = pyo.Set(initialize=blocks, doc="Set of 4-hour blocks for AS market")
        model.D = pyo.Set(initialize=days, doc="Set of days")
        
        # Parameters - Battery Configuration
        model.E_nom = pyo.Param(initialize=self.battery_params['capacity_kwh'], 
                               doc="Nominal energy capacity (kWh)")
        model.P_max_config = pyo.Param(initialize=P_max_config, 
                                      doc="Maximum power rating (kW)")
        model.eta_ch = pyo.Param(initialize=self.battery_params['efficiency'], 
                                doc="Charging efficiency")
        model.eta_dis = pyo.Param(initialize=self.battery_params['efficiency'], 
                                 doc="Discharging efficiency")
        model.SOC_min = pyo.Param(initialize=self.battery_params['soc_min'], 
                                 doc="Minimum SOC")
        model.SOC_max = pyo.Param(initialize=self.battery_params['soc_max'], 
                                 doc="Maximum SOC")
        model.E_soc_init = pyo.Param(initialize=self.battery_params['initial_soc'] * self.battery_params['capacity_kwh'], 
                                    doc="Initial SOC energy (kWh)")
        model.N_cycles = pyo.Param(initialize=daily_cycle_limit, doc="Daily cycle limit")
        
        # Parameters - Time intervals  
        model.dt = pyo.Param(initialize=self.market_params['time_step_hours'], 
                            doc="Time step duration (hours)")
        model.tau = pyo.Param(initialize=self.market_params['reserve_duration_hours'],
                             doc="Assumed reserve activation duration (hours)")
        model.db = pyo.Param(initialize=self.market_params['block_duration_hours'], 
                            doc="Block duration for AS markets (hours)")
        
        # Parameters - Minimum bid sizes
        model.min_bid_da = pyo.Param(initialize=self.market_params['min_bid_da'],
                                     doc="Minimum DA bid size (MW)")
        model.min_bid_fcr = pyo.Param(initialize=self.market_params['min_bid_fcr'], 
                                     doc="Minimum FCR bid size (MW)")
        model.min_bid_afrr = pyo.Param(initialize=self.market_params['min_bid_afrr'], 
                                      doc="Minimum aFRR bid size (MW)")
        
        # BLOCK MAPPING PARAMETER (Addresses Critical Issue #2 - No more closures!)
        model.block_map = pyo.Param(model.T, initialize=time_to_block, 
                                   doc="Mapping from time to block")
        
        # OPTIMIZED PRICE PARAMETERS
        # DA prices indexed by time (vary every 15 min)
        da_prices = {t: float(country_data['price_day_ahead'].iloc[t]) for t in T_data}
        model.P_DA = pyo.Param(model.T, initialize=da_prices, 
                              doc="Day-ahead price (EUR/MWh)")
        
        # AS prices indexed by block (constant within 4h blocks) - MEMORY OPTIMIZED
        model.P_FCR = pyo.Param(model.B, initialize=fcr_prices_by_block, 
                               doc="FCR capacity price (EUR/MW/h)")
        model.P_aFRR_pos = pyo.Param(model.B, initialize=afrr_pos_prices_by_block, 
                                    doc="aFRR positive capacity price (EUR/MW/h)")
        model.P_aFRR_neg = pyo.Param(model.B, initialize=afrr_neg_prices_by_block, 
                                    doc="aFRR negative capacity price (EUR/MW/h)")
        
        # Decision Variables
        # Continuous variables
        model.p_ch = pyo.Var(model.T, bounds=(0, P_max_config), 
                            doc="Charging power (kW)")
        model.p_dis = pyo.Var(model.T, bounds=(0, P_max_config), 
                             doc="Discharging power (kW)")
        model.e_soc = pyo.Var(model.T, bounds=(self.battery_params['soc_min'] * self.battery_params['capacity_kwh'], 
                                              self.battery_params['soc_max'] * self.battery_params['capacity_kwh']), 
                             doc="State of charge energy (kWh)")
        
        # Ancillary service capacity variables (MW)
        model.c_fcr = pyo.Var(model.B, bounds=(0, P_max_config/1000), 
                             doc="FCR capacity bid (MW)")
        model.c_afrr_pos = pyo.Var(model.B, bounds=(0, P_max_config/1000), 
                                  doc="aFRR positive capacity bid (MW)")
        model.c_afrr_neg = pyo.Var(model.B, bounds=(0, P_max_config/1000), 
                                  doc="aFRR negative capacity bid (MW)")
        
        # Binary variables for operational states
        model.y_ch = pyo.Var(model.T, domain=pyo.Binary, 
                            doc="Charging state binary")
        model.y_dis = pyo.Var(model.T, domain=pyo.Binary, 
                             doc="Discharging state binary")
        
        # Binary variables for market participation
        model.y_fcr = pyo.Var(model.B, domain=pyo.Binary, 
                             doc="FCR market participation")
        model.y_afrr_pos = pyo.Var(model.B, domain=pyo.Binary, 
                                  doc="aFRR positive market participation")
        model.y_afrr_neg = pyo.Var(model.B, domain=pyo.Binary, 
                                  doc="aFRR negative market participation")
        
        # ============================================================================
        # CONSTRAINTS (Ordered to match documentation structure)
        # ============================================================================

        # Cst-1: Energy Balance (SOC Dynamics)
        # e_soc(t) = e_soc(t-1) + (p_ch(t)*η_ch - p_dis(t)/η_dis) * Δt
        def soc_dynamics_rule(model, t):
            if t == T_data[0]:
                return model.e_soc[t] == model.E_soc_init + (model.eta_ch * model.p_ch[t] - model.p_dis[t] / model.eta_dis) * model.dt
            else:
                return model.e_soc[t] == model.e_soc[t-1] + (model.eta_ch * model.p_ch[t] - model.p_dis[t] / model.eta_dis) * model.dt
        model.soc_dynamics = pyo.Constraint(model.T, rule=soc_dynamics_rule)

        # Cst-2: SOC Limits
        # SOC_min * E_nom ≤ e_soc(t) ≤ SOC_max * E_nom
        # Note: Already enforced via variable bounds (lines 375-377)
        # No explicit constraint needed - included in model.e_soc variable definition

        # Cst-3: Simultaneous Operation Prevention
        # y_ch(t) + y_dis(t) ≤ 1
        def no_simultaneous_rule(model, t):
            return model.y_ch[t] + model.y_dis[t] <= 1
        model.no_simultaneous = pyo.Constraint(model.T, rule=no_simultaneous_rule)

        # Cst-4: Market Co-optimization Power Limits
        # Total discharge: p_dis(t) + 1000*c_fcr(b) + 1000*c_afrr_pos(b) ≤ P_max
        # Total charge: p_ch(t) + 1000*c_fcr(b) + 1000*c_afrr_neg(b) ≤ P_max
        def power_dis_reserve_limit_rule(model, t):
            block = model.block_map[t]
            return model.p_dis[t] + 1000 * model.c_fcr[block] + 1000 * model.c_afrr_pos[block] <= model.P_max_config
        model.power_dis_reserve_limit = pyo.Constraint(model.T, rule=power_dis_reserve_limit_rule)

        def power_ch_reserve_limit_rule(model, t):
            block = model.block_map[t]
            return model.p_ch[t] + 1000 * model.c_fcr[block] + 1000 * model.c_afrr_neg[block] <= model.P_max_config
        model.power_ch_reserve_limit = pyo.Constraint(model.T, rule=power_ch_reserve_limit_rule)

        # Cst-5: Daily Cycle Limits
        # Σ_{t∈d} (p_dis(t)/η_dis * Δt) ≤ N_cycles * E_nom
        def daily_cycle_rule(model, d):
            # Use pre-computed day_to_times mapping
            return sum(model.p_dis[t] / model.eta_dis * model.dt for t in self._day_to_times[d]) <= model.N_cycles * model.E_nom
        model.daily_cycle_limit = pyo.Constraint(model.D, rule=daily_cycle_rule)

        # Cst-6: Ancillary Service Energy Reserve
        # Upward regulation: (1000*c_fcr + 1000*c_afrr_pos)*τ/η_dis ≤ e_soc(t) - SOC_min*E_nom
        # Downward regulation: (1000*c_fcr + 1000*c_afrr_neg)*τ*η_ch ≤ SOC_max*E_nom - e_soc(t)
        def energy_reserve_pos_rule(model, t):
            block = model.block_map[t]
            required_energy = (1000 * model.c_fcr[block] + 1000 * model.c_afrr_pos[block]) * model.tau / model.eta_dis
            return required_energy <= model.e_soc[t] - model.SOC_min * model.E_nom
        model.energy_reserve_pos = pyo.Constraint(model.T, rule=energy_reserve_pos_rule)

        def energy_reserve_neg_rule(model, t):
            block = model.block_map[t]
            required_storage = (1000 * model.c_fcr[block] + 1000 * model.c_afrr_neg[block]) * model.tau * model.eta_ch
            return required_storage <= model.SOC_max * model.E_nom - model.e_soc[t]
        model.energy_reserve_neg = pyo.Constraint(model.T, rule=energy_reserve_neg_rule)

        # Cst-7: Ancillary Service Market Mutual Exclusivity
        # y_fcr(b) + y_afrr_pos(b) + y_afrr_neg(b) ≤ 1
        def as_market_exclusivity_rule(model, b):
            return model.y_fcr[b] + model.y_afrr_pos[b] + model.y_afrr_neg[b] <= 1
        model.as_market_exclusivity = pyo.Constraint(model.B, rule=as_market_exclusivity_rule)

        # Cst-8: Cross-Market Mutual Exclusivity
        # y_dis(t) + y_fcr(b) + y_afrr_neg(b) ≤ 1  (no discharge bid with charging AS)
        # y_ch(t) + y_fcr(b) + y_afrr_pos(b) ≤ 1   (no charge bid with discharging AS)
        def cross_market_exclusivity_rule_1(model, t):
            block = model.block_map[t]
            return model.y_dis[t] + model.y_fcr[block] + model.y_afrr_neg[block] <= 1
        model.cross_market_exclusivity1 = pyo.Constraint(model.T, rule=cross_market_exclusivity_rule_1)

        def cross_market_exclusivity_rule_2(model, t):
            block = model.block_map[t]
            return model.y_ch[t] + model.y_fcr[block] + model.y_afrr_pos[block] <= 1
        model.cross_market_exclusivity2 = pyo.Constraint(model.T, rule=cross_market_exclusivity_rule_2)

        # Cst-9: Minimum and Maximum Bid Size Constraints
        # DA Energy Bids: y(t)*MinBid*1000 ≤ p(t) ≤ y(t)*P_max_config
        def da_ch_min_bid_rule(model, t):
            return model.p_ch[t] >= model.y_ch[t] * model.min_bid_da * 1000
        model.da_ch_min_bid = pyo.Constraint(model.T, rule=da_ch_min_bid_rule)

        def da_ch_max_bid_rule(model, t):
            return model.p_ch[t] <= model.y_ch[t] * model.P_max_config
        model.da_ch_max_bid = pyo.Constraint(model.T, rule=da_ch_max_bid_rule)

        def da_dis_min_bid_rule(model, t):
            return model.p_dis[t] >= model.y_dis[t] * model.min_bid_da * 1000
        model.da_dis_min_bid = pyo.Constraint(model.T, rule=da_dis_min_bid_rule)

        def da_dis_max_bid_rule(model, t):
            return model.p_dis[t] <= model.y_dis[t] * model.P_max_config
        model.da_dis_max_bid = pyo.Constraint(model.T, rule=da_dis_max_bid_rule)

        # FCR Capacity Bids: y(b)*MinBid ≤ c(b) ≤ y(b)*P_max_config/1000
        def fcr_min_bid_rule(model, b):
            return model.c_fcr[b] >= model.y_fcr[b] * model.min_bid_fcr
        model.fcr_min_bid = pyo.Constraint(model.B, rule=fcr_min_bid_rule)

        def fcr_max_bid_rule(model, b):
            return model.c_fcr[b] <= model.y_fcr[b] * (model.P_max_config / 1000)
        model.fcr_max_bid = pyo.Constraint(model.B, rule=fcr_max_bid_rule)

        # aFRR Capacity Bids: y(b)*MinBid ≤ c(b) ≤ y(b)*P_max_config/1000
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
        
        # OPTIMIZED OBJECTIVE FUNCTION (Addresses Critical Issue #3)
        def objective_rule(model):
            # Day-ahead profit
            da_profit = sum((model.P_DA[t] / 1000 * model.p_dis[t] - 
                             model.P_DA[t] / 1000 * model.p_ch[t]) * model.dt 
                            for t in model.T)
            
            # Ancillary service profit (prices are per block, so no db multiplication)
            as_profit = sum(model.P_FCR[b] * model.c_fcr[b] +
                            model.P_aFRR_pos[b] * model.c_afrr_pos[b] +
                            model.P_aFRR_neg[b] * model.c_afrr_neg[b]
                            for b in model.B)
            
            return da_profit + as_profit
        
        model.objective = pyo.Objective(rule=objective_rule, sense=pyo.maximize)
        
        # OPTIONAL: End-of-horizon SOC constraint (mentioned in review)
        # Uncomment if required to return to initial SOC
        # def final_soc_rule(model):
        #     return model.e_soc[model.T.last()] == model.E_soc_init
        # model.final_soc = pyo.Constraint(rule=final_soc_rule)
        
        logger.info("Improved optimization model built successfully")
        logger.info(f"Variables: {model.nvariables()}")
        logger.info(f"Constraints: {model.nconstraints()}")
        
        return model
    
    def detect_available_solver(self) -> str:
        """
        Detect the best available solver with fallback logic.
        
        Priority order (per competition requirements):
        1. CPLEX (commercial) - if available in submission system
        2. Gurobi (commercial) - if available in submission system
        3. HiGHS (open-source) - REQUIRED fallback for competition submission
        
        Returns:
            str: Name of the best available solver
        """
        # Priority order: Try commercial first, fallback to open-source HiGHS
        solver_priority = [
            ('cplex', 'CPLEX (commercial)'),
            ('gurobi', 'Gurobi (commercial)'),
            ('highs', 'HiGHS (open-source, competition approved)'),
            ('cbc', 'CBC (open-source)'),
            ('glpk', 'GLPK (open-source)')
        ]
        
        logger.info("🔍 Detecting available optimization solver...")
        
        for solver_name, solver_display in solver_priority:
            try:
                solver = pyo.SolverFactory(solver_name)
                if solver.available():
                    logger.info(f"✅ Using solver: {solver_display}")
                    return solver_name
            except Exception as e:
                logger.debug(f"   Solver {solver_display} not available: {e}")
                continue
        
        # If no solver found, raise error
        raise RuntimeError(
            "❌ No compatible optimization solver found!\n"
            "Required: At least one of CPLEX, Gurobi, or HiGHS (recommended for competition).\n"
            "Install HiGHS: pip install highspy"
        )
    
    def solve_model(self, model: pyo.ConcreteModel, solver_name: str = None) -> Dict:
        """
        Solve the optimization model with automatic solver detection.
        
        Args:
            model: Pyomo model to solve
            solver_name: Solver to use. If None, auto-detect best available.
                        Options: 'cplex', 'gurobi', 'highs' (recommended for competition)
            
        Returns:
            Dict: Solution results with performance metrics
        """
        # Auto-detect solver if not specified
        if solver_name is None:
            solver_name = self.detect_available_solver()
        else:
            logger.info(f"Using specified solver: {solver_name}")
        
        try:
            # Create solver
            solver = pyo.SolverFactory(solver_name)
            
            # Verify solver is available
            if not solver.available():
                logger.warning(f"⚠️  Solver {solver_name} not available, auto-detecting...")
                solver_name = self.detect_available_solver()
                solver = pyo.SolverFactory(solver_name)
            
            # CONSISTENT SOLVER TIME LIMITS (Addresses Critical Issue #6)
            if solver_name.lower() == 'cplex':
                solver.options['timelimit'] = self.market_params['solver_time_limit']
                solver.options['mip_tolerances_mipgap'] = 0.01
                solver.options['emphasis_mip'] = 1
            elif solver_name.lower() == 'gurobi':
                solver.options['TimeLimit'] = self.market_params['solver_time_limit']
                solver.options['MIPGap'] = 0.01
                solver.options['Threads'] = 4
            elif solver_name.lower() == 'highs':
                solver.options['time_limit'] = self.market_params['solver_time_limit']
                solver.options['mip_rel_gap'] = 0.01
            elif solver_name.lower() == 'scip':
                solver.options['limits/time'] = self.market_params['solver_time_limit']
                solver.options['limits/gap'] = 0.01
            elif solver_name.lower() == 'cbc':
                solver.options['seconds'] = self.market_params['solver_time_limit']
                solver.options['ratio'] = 0.01
            
            # Solve
            start_time = datetime.now()
            results = solver.solve(model, tee=False)
            solve_time = (datetime.now() - start_time).total_seconds()
            
            # Check solution status
            if results.solver.termination_condition == pyo.TerminationCondition.optimal:
                logger.info(f"Optimal solution found in {solve_time:.2f} seconds")
                status = "optimal"
            elif results.solver.termination_condition == pyo.TerminationCondition.feasible:
                logger.info(f"Feasible solution found in {solve_time:.2f} seconds")
                status = "feasible"
            else:
                logger.error(f"Solver failed: {results.solver.termination_condition}")
                return {
                    'status': 'failed',
                    'termination_condition': str(results.solver.termination_condition),
                    'solve_time': solve_time
                }
            
            # Extract solution - OPTIMIZED (Addresses Minor Issue #9)
            solution = {
                'status': status,
                'solve_time': solve_time,
                'objective_value': pyo.value(model.objective),
                'solver': solver_name,
                'termination_condition': str(results.solver.termination_condition)
            }
            
            # Extract variable values efficiently
            solution["p_ch"] = {t: model.p_ch[t].value for t in model.T if model.p_ch[t].value is not None}
            solution["p_dis"] = {t: model.p_dis[t].value for t in model.T if model.p_dis[t].value is not None}
            solution["e_soc"] = {t: model.e_soc[t].value for t in model.T if model.e_soc[t].value is not None}
            
            solution["c_fcr"] = {b: model.c_fcr[b].value for b in model.B if model.c_fcr[b].value is not None}
            solution["c_afrr_pos"] = {b: model.c_afrr_pos[b].value for b in model.B if model.c_afrr_pos[b].value is not None}
            solution["c_afrr_neg"] = {b: model.c_afrr_neg[b].value for b in model.B if model.c_afrr_neg[b].value is not None}
            
            solution["y_ch"] = {t: model.y_ch[t].value for t in model.T if model.y_ch[t].value is not None}
            solution["y_dis"] = {t: model.y_dis[t].value for t in model.T if model.y_dis[t].value is not None}
            
            solution["y_fcr"] = {b: model.y_fcr[b].value for b in model.B if model.y_fcr[b].value is not None}
            solution["y_afrr_pos"] = {b: model.y_afrr_pos[b].value for b in model.B if model.y_afrr_pos[b].value is not None}
            solution["y_afrr_neg"] = {b: model.y_afrr_neg[b].value for b in model.B if model.y_afrr_neg[b].value is not None}
            
            return solution
            
        except Exception as e:
            logger.error(f"Error solving model: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'solve_time': 0
            }
    
    def extract_country_data(self, data: pd.DataFrame, country: str) -> pd.DataFrame:
        """
        Extract and format data for a specific country with enhanced validation.
        """
        logger.info(f"Extracting data for country: {country}")
        
        if country not in self.countries:
            raise ValueError(f"Country {country} not supported. Available: {self.countries}")
        
        try:
            # Handle special case for DE_LU coupled market
            # Day-ahead: Use DE_LU (coupled Germany-Luxembourg market)
            # Ancillary services: Use DE (German TSO responsibility)
            if country == 'DE_LU':
                day_ahead_country = 'DE_LU'
                as_country = 'DE'  # Ancillary services handled by German TSO
            else:
                day_ahead_country = country
                as_country = country
            
            # Extract country-specific data with market-aware mapping
            country_df = pd.DataFrame()
            country_df['price_day_ahead'] = data[(day_ahead_country, 'day_ahead', '')]
            country_df['price_fcr'] = data[(as_country, 'fcr', '')]
            country_df['price_afrr_pos'] = data[(as_country, 'afrr', 'positive')]
            country_df['price_afrr_neg'] = data[(as_country, 'afrr', 'negative')]
            
            # Create time-based identifiers
            timestamps = data.index
            country_df['hour'] = timestamps.hour
            country_df['day_of_year'] = timestamps.dayofyear
            country_df['month'] = timestamps.month
            country_df['year'] = timestamps.year
            
            # Create block IDs (4-hour blocks starting at midnight)
            country_df['block_of_day'] = country_df['hour'] // 4
            country_df['block_id'] = (country_df['day_of_year'] - 1) * 6 + country_df['block_of_day']
            
            # Create day IDs
            country_df['day_id'] = country_df['day_of_year']
            
            # Keep timestamp as a column for filtering
            country_df['timestamp'] = timestamps
            
            # Reset index to get integer-based indexing
            country_df = country_df.reset_index(drop=True)
            
            # Additional validation
            if country_df.isnull().any().any():
                logger.warning(f"Missing data found for country {country}")
            
            logger.info(f"Extracted {len(country_df)} data points for {country}")
            return country_df
            
        except KeyError as e:
            raise ValueError(f"Missing data for country {country}: {str(e)}")
    
    def optimize(self, country_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Simplified optimization interface for testing and single-scenario runs.
        
        Args:
            country_data: Preprocessed DataFrame with market data for a specific country
            
        Returns:
            Dictionary with optimization results including total_revenue
        """
        try:
            # Get daily cycle limit directly (NOT multiplied by num_days - that was the bug!)
            # # The constraint is applied per day, so we pass the daily limit to the model
            daily_cycle_limit = self.battery_params['daily_cycle_limit']
            
            # Calculate c_rate from max_power_kw and capacity
            max_power_kw = self.market_params.get('max_power_kw', self.battery_params['capacity_kwh'] * 0.5)
            c_rate = max_power_kw / self.battery_params['capacity_kwh']
            
            # Build and solve the optimization model
            model = self.build_optimization_model(country_data, c_rate, daily_cycle_limit)
            results = self.solve_model(model)
            
            # Return results in expected format
            return {
                'total_revenue': results.get('objective_value', 0),
                'solver_status': results.get('status', 'unknown'),
                'solve_time': results.get('solve_time', 0),
                'detailed_results': results
            }
            
        except Exception as e:
            logger.error(f"Optimization failed: {str(e)}")
            return {
                'total_revenue': 0,
                'solver_status': 'failed',
                'solve_time': 0,
                'error': str(e),
                'detailed_results': {}
            }
    
    def run_scenario_analysis(self, data_file: str, output_file: str = None, 
                            num_days: int = 10) -> pd.DataFrame:
        """
        Run comprehensive scenario analysis with improved model.
        """
        logger.info("Starting improved scenario analysis")
        
        # Load data
        data = self.load_and_preprocess_data(data_file)
        
        # Limit to specified number of days
        if num_days:
            end_time = data.index[0] + timedelta(days=num_days)
            data = data[data.index < end_time]
            logger.info(f"Limited analysis to {num_days} days")
        
        results = []
        
        for country in self.countries:
            logger.info(f"Processing country: {country}")
            
            try:
                country_data = self.extract_country_data(data, country)
                
                for c_rate in self.c_rates:
                    for daily_cycle_limit in self.daily_cycles:
                        scenario_name = f"{country}_C{c_rate}_N{daily_cycle_limit}"
                        logger.info(f"Running scenario: {scenario_name}")
                        
                        try:
                            # Build and solve model
                            model = self.build_optimization_model(country_data, c_rate, daily_cycle_limit)
                            solution = self.solve_model(model, 'cplex')
                            
                            if solution['status'] in ['optimal', 'feasible']:
                                result = {
                                    'scenario': scenario_name,
                                    'country': country,
                                    'c_rate': c_rate,
                                    'n_cycles': daily_cycle_limit,
                                    'status': solution['status'],
                                    'objective_value': solution['objective_value'],
                                    'solve_time': solution['solve_time'],
                                    'power_rating_kw': c_rate * self.battery_params['capacity_kwh'],
                                    'energy_capacity_kwh': self.battery_params['capacity_kwh']
                                }
                                results.append(result)
                                logger.info(f"Scenario {scenario_name}: Objective = {solution['objective_value']:.2f} EUR")
                            else:
                                logger.warning(f"Scenario {scenario_name} failed: {solution['status']}")
                                
                        except Exception as e:
                            logger.error(f"Error in scenario {scenario_name}: {str(e)}")
                            
            except Exception as e:
                logger.error(f"Error processing country {country}: {str(e)}")
        
        # Convert to DataFrame
        results_df = pd.DataFrame(results)
        
        if output_file:
            results_df.to_csv(output_file, index=False)
            logger.info(f"Results saved to {output_file}")
        
        logger.info("Improved scenario analysis completed")
        return results_df

# For backward compatibility (alias for old code that might use BESSOptimizer)
BESSOptimizer = BESSOptimizerV2

if __name__ == "__main__":
    # Example usage
    optimizer = BESSOptimizerV2()
    
    # Run quick test
    data_file = "../data/TechArena2025_data_tidy.jsonl"
    results = optimizer.run_scenario_analysis(data_file, num_days=3)
    print("\nImproved Model Results:")
    print(results.to_string())