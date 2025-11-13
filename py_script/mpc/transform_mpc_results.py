"""
Utilities for transforming MPC simulation results for visualization and analysis.

This module provides functions to convert MPC annual_bids_df from internal format
(MW units, minimal columns) to the format expected by visualization functions
(kW units, all required columns with standardized names).
"""

import pandas as pd
from typing import Optional


def transform_mpc_results_for_viz(
    annual_bids_df: pd.DataFrame,
    country_data: pd.DataFrame,
    battery_capacity_kwh: float = 4472.0
) -> pd.DataFrame:
    """
    Transform MPC annual_bids_df to format expected by visualization functions.

    Handles:
    - MW → kW conversion for power variables
    - Adding timestamp and price columns from country_data
    - Adding derived columns (hour, soc_pct, etc.)
    - Renaming columns to match visualization function expectations
    - Ensuring all required columns exist

    Parameters
    ----------
    annual_bids_df : pd.DataFrame
        MPC simulation output with columns:
        - timestep: int
        - e_soc: float (kWh)
        - p_ch, p_dis: float (MW)
        - p_afrr_pos_e, p_afrr_neg_e: float (MW)
        - c_fcr, c_afrr_pos, c_afrr_neg: float (MW)

    country_data : pd.DataFrame
        Original market data with columns:
        - timestamp: datetime
        - price_day_ahead: float (EUR/MWh)
        - price_fcr: float (EUR/MW)
        - price_afrr_pos, price_afrr_neg: float (EUR/MW)
        - price_afrr_energy_pos, price_afrr_energy_neg: float (EUR/MWh)

    battery_capacity_kwh : float, optional
        Total battery capacity in kWh (default: 4472)

    Returns
    -------
    pd.DataFrame
        Transformed DataFrame with all columns required for visualization:
        - Original MPC columns (timestep, e_soc, bids)
        - Timestamp from country_data
        - Price columns from country_data
        - Derived columns (hour, soc_pct)
        - Power columns in kW (p_ch_kw, p_dis_kw, etc.)
        - Renamed price columns for viz functions

    Examples
    --------
    >>> from py_script.mpc.mpc_simulator import MPCSimulator
    >>> from py_script.data.load_process_market_data import load_preprocessed_country_data
    >>>
    >>> # Run MPC simulation
    >>> country_data = load_preprocessed_country_data('CH')
    >>> simulator = MPCSimulator(optimizer, country_data, 32, 24, 0.5)
    >>> results = simulator.run_full_simulation(0.5)
    >>>
    >>> # Transform for visualization
    >>> viz_df = transform_mpc_results_for_viz(
    ...     results['annual_bids_df'],
    ...     country_data
    ... )
    >>>
    >>> # Now can use with visualization functions
    >>> from py_script.visualization.optimization_analysis import plot_soc_and_power_bids
    >>> fig = plot_soc_and_power_bids(viz_df)

    Notes
    -----
    - MPC outputs are in MW, but visualization functions expect kW for power
    - Capacity bids (c_fcr, c_afrr_pos, c_afrr_neg) remain in MW as expected
    - Price columns are aligned by slicing country_data to match annual_bids_df length
    - SOC percentage is calculated as: soc_pct = e_soc / battery_capacity_kwh * 100
    """
    # Create a copy to avoid modifying original
    viz_df = annual_bids_df.copy()

    # Verify we have the expected number of rows
    if len(viz_df) > len(country_data):
        raise ValueError(
            f"annual_bids_df has {len(viz_df)} rows but country_data only has "
            f"{len(country_data)} rows. Cannot align data."
        )

    # Add timestamp column from country_data
    viz_df['timestamp'] = country_data['timestamp'].iloc[:len(viz_df)].values

    # Add market prices for visualization (align by length)
    viz_df['price_day_ahead'] = country_data['price_day_ahead'].iloc[:len(viz_df)].values
    viz_df['price_fcr'] = country_data['price_fcr'].iloc[:len(viz_df)].values
    viz_df['price_afrr_pos'] = country_data['price_afrr_pos'].iloc[:len(viz_df)].values
    viz_df['price_afrr_neg'] = country_data['price_afrr_neg'].iloc[:len(viz_df)].values
    viz_df['price_afrr_energy_pos'] = country_data['price_afrr_energy_pos'].iloc[:len(viz_df)].values
    viz_df['price_afrr_energy_neg'] = country_data['price_afrr_energy_neg'].iloc[:len(viz_df)].values

    # NOTE: Capacity bids (c_fcr, c_afrr_pos, c_afrr_neg) are already in annual_bids_df from MPC
    # DO NOT overwrite them here!

    # Add derived columns required by visualization functions
    viz_df['hour'] = viz_df['timestep'] * 0.25  # 15-min intervals → hours
    viz_df['soc_kwh'] = viz_df['e_soc']  # Already in kWh
    viz_df['soc_pct'] = viz_df['e_soc'] / battery_capacity_kwh * 100

    # Convert power columns from MW to kW for visualization
    viz_df['p_ch_kw'] = viz_df['p_ch'] * 1000
    viz_df['p_dis_kw'] = viz_df['p_dis'] * 1000
    viz_df['p_afrr_pos_e_kw'] = viz_df['p_afrr_pos_e'] * 1000
    viz_df['p_afrr_neg_e_kw'] = viz_df['p_afrr_neg_e'] * 1000

    # Capacity bids stay in MW (as expected by viz functions)
    viz_df['c_fcr_mw'] = viz_df['c_fcr']
    viz_df['c_afrr_pos_mw'] = viz_df['c_afrr_pos']
    viz_df['c_afrr_neg_mw'] = viz_df['c_afrr_neg']

    # Rename price columns to match visualization function expectations
    viz_df['price_da_eur_mwh'] = viz_df['price_day_ahead']
    viz_df['price_fcr_eur_mw'] = viz_df['price_fcr']
    viz_df['price_afrr_cap_pos_eur_mw'] = viz_df['price_afrr_pos']
    viz_df['price_afrr_cap_neg_eur_mw'] = viz_df['price_afrr_neg']
    viz_df['price_afrr_energy_pos_eur_mwh'] = viz_df['price_afrr_energy_pos']
    viz_df['price_afrr_energy_neg_eur_mwh'] = viz_df['price_afrr_energy_neg']

    return viz_df


def extract_iteration_summary(
    mpc_results: dict,
    include_soc_trajectory: bool = True
) -> pd.DataFrame:
    """
    Extract summary statistics for each MPC iteration.

    Useful for analyzing MPC performance over time and creating
    iteration-level visualizations.

    Parameters
    ----------
    mpc_results : dict
        Results dictionary from MPCSimulator.run_full_simulation()
        Expected keys:
        - iteration_results: list of dict with per-iteration metrics
        - soc_trajectory: list of SOC values at iteration boundaries

    include_soc_trajectory : bool, optional
        If True, include initial and final SOC for each iteration (default: True)

    Returns
    -------
    pd.DataFrame
        DataFrame with one row per MPC iteration, columns:
        - iteration: int (0-indexed)
        - start_timestep: int
        - end_timestep: int
        - revenue: float (EUR)
        - degradation_cost: float (EUR)
        - profit: float (EUR)
        - initial_soc: float (kWh) - if include_soc_trajectory=True
        - final_soc: float (kWh) - if include_soc_trajectory=True
        - solve_time: float (seconds) - if available
        - solver_status: str - if available

    Examples
    --------
    >>> results = simulator.run_full_simulation(0.5)
    >>> iteration_df = extract_iteration_summary(results)
    >>> print(iteration_df[['iteration', 'profit', 'final_soc']])
    """
    iteration_data = []

    for i, iter_result in enumerate(mpc_results['iteration_results']):
        row = {
            'iteration': i,
            'start_timestep': iter_result.get('start_timestep', i * 96),  # Assume 24h = 96 timesteps
            'end_timestep': iter_result.get('end_timestep', (i + 1) * 96),
            'revenue': iter_result.get('revenue', 0.0),
            'degradation_cost': iter_result.get('degradation_cost', 0.0),
            'profit': iter_result.get('profit', 0.0),
        }

        # Add SOC trajectory if requested
        if include_soc_trajectory and 'soc_trajectory' in mpc_results:
            soc_traj = mpc_results['soc_trajectory']
            if i < len(soc_traj):
                row['initial_soc'] = soc_traj[i]
            if i + 1 < len(soc_traj):
                row['final_soc'] = soc_traj[i + 1]

        # Add solver metrics if available
        if 'solve_time' in iter_result:
            row['solve_time'] = iter_result['solve_time']
        if 'solver_status' in iter_result:
            row['solver_status'] = iter_result['solver_status']

        iteration_data.append(row)

    return pd.DataFrame(iteration_data)
