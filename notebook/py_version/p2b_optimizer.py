# -*- coding: utf-8 -*-
"""
Phase 2 BESS Optimizer Test Script

This script provides a flexible testing and validation harness for the BESS optimization framework.

Purpose: Run single-pass optimization scenarios (no MPC/Meta-Opt) and validate results.

Usage:
    python p2b_optimizer.py --country DE_LU --hours 24 --c_rate 0.5 --alpha 1.0 --model III
    python p2b_optimizer.py --country AT --hours 48 --epsilon 0 --sequential  # Test strict LIFO
    python p2b_optimizer.py --help  # Show all options
"""

import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Data processing
import pandas as pd
import numpy as np

# Optimization models
from py_script.core.optimizer import (
    BESSOptimizerModelI,
    BESSOptimizerModelII,
    BESSOptimizerModelIII
)

# Visualization utilities
from py_script.visualization.optimization_analysis import (
    extract_detailed_solution,
    plot_da_market_price_bid,
    plot_afrr_energy_market_price_bid,
    plot_capacity_markets_price_bid,
    plot_soc_and_power_bids
)

# Results export
from py_script.validation.results_exporter import save_optimization_results

# Aging analysis plots
from py_script.visualization.aging_analysis import (
    plot_stacked_cyclic_soc,
    plot_calendar_aging_curve,
)

# Data loading
from py_script.data.load_process_market_data import load_preprocessed_country_data


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Phase 2 BESS Optimizer Test Script',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # Market and time parameters
    parser.add_argument('--country', type=str, default='DE_LU',
                        choices=['DE_LU', 'AT', 'CH', 'HU', 'CZ'],
                        help='Country/market to optimize')
    parser.add_argument('--hours', type=int, default=24,
                        help='Time horizon in hours')
    parser.add_argument('--start_step', type=int, default=0,
                        help='Starting time step (15-min intervals)')

    # Battery configuration
    parser.add_argument('--c_rate', type=float, default=0.5,
                        choices=[0.25, 0.33, 0.5],
                        help='C-rate for battery power limits')
    parser.add_argument('--max_as_ratio', type=float, default=0.8,
                        help='Max ancillary service ratio (0-1)')
    parser.add_argument('--max_soc', type=float, default=1.0,
                        help='Max state of charge (0-1)')
    parser.add_argument('--min_soc', type=float, default=0.0,
                        help='Min state of charge (0-1)')

    # Model selection and degradation
    parser.add_argument('--model', type=str, default='III',
                        choices=['I', 'II', 'III'],
                        help='Optimizer model (I=base, II=+cyclic, III=+calendar)')
    parser.add_argument('--alpha', type=float, default=1.0,
                        help='Degradation weight parameter (Model II/III)')
    parser.add_argument('--epsilon', type=float, default=5.0,
                        help='LIFO tolerance in kWh (0=perfect LIFO)')
    parser.add_argument('--sequential', action='store_true',
                        help='Enforce strict sequential segment activation (slower but more accurate)')

    # Other options
    parser.add_argument('--ev_weighting', action='store_true',
                        help='Enable aFRR expected value weighting')
    parser.add_argument('--daily_cycle_limit', type=float, default=None,
                        help='Daily cycle limit (Model I only)')
    parser.add_argument('--no_save', action='store_true',
                        help='Do not save results to disk')
    parser.add_argument('--no_plots', action='store_true',
                        help='Do not generate plots')
    parser.add_argument('--run_name', type=str, default=None,
                        help='Custom run name for output directory')

    return parser.parse_args()


def load_market_data(country, project_root):
    """Load market data using fastest available method."""
    print("=" * 80)
    print("[DATA] LOADING MARKET DATA")
    print("=" * 80)

    # Option 1: Try loading preprocessed country-specific parquet (FASTEST)
    preprocessed_dir = project_root / "data" / "parquet" / "preprocessed"
    preprocessed_path = preprocessed_dir / f"{country.lower()}.parquet"

    if preprocessed_path.exists():
        print(f"[FAST PATH] Loading preprocessed data: {preprocessed_path.name}")
        country_data = load_preprocessed_country_data(country, data_dir=preprocessed_dir)
        print(f"[OK] Loaded {len(country_data)} time steps for {country} (preprocessed)")

    else:
        # Option 2: Load from Excel using optimizer's Phase 2 pipeline (SUBMISSION PATH)
        excel_path = project_root / "data" / "TechArena2025_Phase2_data.xlsx"

        if excel_path.exists():
            print(f"[SUBMISSION PATH] Loading from Excel: {excel_path.name}")
            print("   This matches Huawei submission requirements...")

            # Create temporary optimizer for data loading
            temp_opt = BESSOptimizerModelI()

            # Load using new Phase 2 Excel loader
            print("   Loading Phase 2 market tables from Excel...")
            full_data = temp_opt.load_and_preprocess_data(str(excel_path))

            # Extract country-specific data
            print(f"   Extracting country data for {country}...")
            country_data = temp_opt.extract_country_data(full_data, country)
            print(f"[OK] Loaded {len(country_data)} time steps for {country} (Excel)")
        else:
            raise FileNotFoundError(
                f"No data source found!\n"
                f"Please ensure ONE of the following exists:\n"
                f"  1. Preprocessed parquet (fast): {preprocessed_path}\n"
                f"  2. Phase 2 Excel (submission): {excel_path}\n"
                f"To generate preprocessed files, run:\n"
                f"  python py_script/data/generate_preprocessed_country_data.py"
            )

    return country_data


def extract_time_window(country_data, start_step, hours):
    """Extract time window from market data."""
    horizon_steps = hours * 4  # 15-min intervals
    end_step = start_step + horizon_steps

    if end_step > len(country_data):
        raise ValueError(f"Requested end step {end_step} exceeds available data {len(country_data)}")

    data_slice = country_data.iloc[start_step:end_step].copy()
    data_slice.reset_index(drop=True, inplace=True)

    print(f"\n[OK] Extracted time window: steps {start_step} to {end_step} ({hours} hours)")
    print(f"   Time steps: {len(data_slice)}")

    # Display data summary
    print(f"\nMarket Data Summary:")
    print(f"   DA Price:           {data_slice['price_day_ahead'].min():.2f} - {data_slice['price_day_ahead'].max():.2f} EUR/MWh")
    print(f"   FCR Price:          {data_slice['price_fcr'].min():.2f} - {data_slice['price_fcr'].max():.2f} EUR/MW")
    print(f"   aFRR+ Price:        {data_slice['price_afrr_pos'].min():.2f} - {data_slice['price_afrr_pos'].max():.2f} EUR/MW")
    print(f"   aFRR- Price:        {data_slice['price_afrr_neg'].min():.2f} - {data_slice['price_afrr_neg'].max():.2f} EUR/MW")
    print(f"   aFRR Energy+ Price: {data_slice['price_afrr_energy_pos'].min():.2f} - {data_slice['price_afrr_energy_pos'].max():.2f} EUR/MWh")
    print(f"   aFRR Energy- Price: {data_slice['price_afrr_energy_neg'].min():.2f} - {data_slice['price_afrr_energy_neg'].max():.2f} EUR/MWh")

    return data_slice


def initialize_optimizer(args):
    """Initialize the appropriate optimizer model."""
    print("\n" + "=" * 80)
    print("=' INITIALIZING OPTIMIZER")
    print("=" * 80)

    # Select and instantiate the appropriate model
    if args.model == "I":
        optimizer = BESSOptimizerModelI()
        print(f"[GOOD!] Initialized Model I (Base 4-market optimization)")

    elif args.model == "II":
        optimizer = BESSOptimizerModelII(
            alpha=args.alpha,
            require_sequential_segment_activation=args.sequential,
            use_afrr_ev_weighting=args.ev_weighting
        )
        # Override LIFO epsilon from command-line parameter
        optimizer.degradation_params['lifo_epsilon_kwh'] = args.epsilon

        print(f"[GOOD!] Initialized Model II (Base + Cyclic Aging)")
        print(f"   Alpha: {args.alpha}")
        print(f"   LIFO Epsilon: {args.epsilon} kWh ({args.epsilon/447.2*100:.1f}% of segment capacity)")
        print(f"   Sequential Activation: {args.sequential}")

    elif args.model == "III":
        optimizer = BESSOptimizerModelIII(
            alpha=args.alpha,
            require_sequential_segment_activation=args.sequential,
            use_afrr_ev_weighting=args.ev_weighting
        )
        # Override LIFO epsilon from command-line parameter
        optimizer.degradation_params['lifo_epsilon_kwh'] = args.epsilon

        print(f"[GOOD!] Initialized Model III (Base + Cyclic + Calendar Aging)")
        print(f"   Alpha: {args.alpha}")
        print(f"   LIFO Epsilon: {args.epsilon} kWh ({args.epsilon/447.2*100:.1f}% of segment capacity)")
        print(f"   Sequential Activation: {args.sequential}")
    else:
        raise ValueError(f"Invalid model: {args.model}. Choose 'I', 'II', or 'III'")

    # Configure optimizer
    optimizer.max_as_ratio = args.max_as_ratio
    optimizer.battery_params['soc_min'] = args.min_soc
    optimizer.battery_params['soc_max'] = args.max_soc

    print(f"\n[CONFIG] Optimizer Configuration:")
    print(f"   Battery Capacity: {optimizer.battery_params['capacity_kwh']} kWh")
    print(f"   Round-trip Eff:   {optimizer.battery_params['efficiency'] * 100:.1f}%")
    print(f"   Max AS Ratio:     {optimizer.max_as_ratio * 100:.0f}%")
    print(f"   Max SOC:          {args.max_soc * 100:.0f}%")
    print(f"   Min SOC:          {args.min_soc * 100:.0f}%")
    print(f"   EV Weighting:     {args.ev_weighting}")

    return optimizer


def build_model(optimizer, data_slice, args):
    """Build optimization model."""
    print("\n" + "=" * 80)
    print("<[!]  BUILDING OPTIMIZATION MODEL")
    print("=" * 80)

    build_start = time.time()

    # Build model with appropriate parameters
    if args.model == "I" and args.daily_cycle_limit is not None:
        model = optimizer.build_optimization_model(
            data_slice,
            c_rate=args.c_rate,
            daily_cycle_limit=args.daily_cycle_limit
        )
        print(f"[GOOD!] Model I built with daily_cycle_limit={args.daily_cycle_limit}")
    else:
        model = optimizer.build_optimization_model(
            data_slice,
            c_rate=args.c_rate
        )

    build_time = time.time() - build_start

    print(f"[GOOD!] Model built in {build_time:.2f} seconds")
    print(f"\n[STATS] Model Statistics:")
    print(f"   Variables:   {model.nvariables()}")
    print(f"   Constraints: {model.nconstraints()}")
    print(f"   Time Steps:  {len(data_slice)}")
    print(f"   Blocks:      {len(data_slice) // 16}")  # 4-hour blocks

    return model, build_time


def solve_model(optimizer, model):
    """Solve optimization model."""
    print("\n" + "=" * 80)
    print("[SOLVE] SOLVING OPTIMIZATION MODEL")
    print("=" * 80)

    solve_start = time.time()

    # Solve the model (auto-detect solver)
    solved_model, solver_results = optimizer.solve_model(model)

    solve_time = time.time() - solve_start

    print(f"[GOOD!] Model solved in {solve_time:.2f} seconds")
    print(f"\n[RESULT] Solver Results:")
    print(f"   Status:      {solver_results.solver.status}")
    print(f"   Termination: {solver_results.solver.termination_condition}")

    return solved_model, solver_results, solve_time


def extract_solution(optimizer, solved_model, solver_results, data_slice, args, build_time, solve_time):
    """Extract and display solution."""
    print("\n" + "=" * 80)
    print("[EXTRACT] EXTRACTING SOLUTION")
    print("=" * 80)

    # Extract solution dictionary
    solution_dict = optimizer.extract_solution(solved_model, solver_results)

    print(f"[GOOD!] Solution extracted")
    print(f"\n[PROFIT] Objective Value: {solution_dict['objective_value']:.2f} EUR")

    # Display profit components if available
    if 'profit_components' in solution_dict:
        print(f"\n[BREAKDOWN] Profit Components:")
        pc = solution_dict['profit_components']
        for key, value in pc.items():
            print(f"   {key:30s}: {value:10.2f} EUR")

    # Display degradation metrics if available (Model II/III)
    if 'degradation_metrics' in solution_dict:
        print(f"\n=[Info] Degradation Metrics:")
        dm = solution_dict['degradation_metrics']
        for key, value in dm.items():
            if isinstance(value, (int, float)):
                print(f"   {key:30s}: {value:10.4f}")

    print(f"\n[!]  Timing:")
    print(f"   Build Time:  {build_time:.2f}s")
    print(f"   Solve Time:  {solve_time:.2f}s")
    print(f"   Total Time:  {build_time + solve_time:.2f}s")

    # Create solution DataFrame for visualization and export
    solution_df = extract_detailed_solution(solution_dict, data_slice, args.hours)

    print(f"\n=[Done] Solution DataFrame created: {solution_df.shape}")

    return solution_dict, solution_df


def save_results(solution_df, solution_dict, model, args, build_time, solve_time, project_root):
    """Save optimization results."""
    # Calculate revenue breakdown
    revenue_da = solution_df['revenue_da_eur'].sum() if 'revenue_da_eur' in solution_df.columns else 0
    revenue_fcr = solution_df['revenue_fcr_eur'].sum() if 'revenue_fcr_eur' in solution_df.columns else 0
    revenue_afrr_cap = solution_df['revenue_afrr_capacity_eur'].sum() if 'revenue_afrr_capacity_eur' in solution_df.columns else 0
    revenue_afrr_energy = solution_df['revenue_afrr_energy_eur'].sum() if 'revenue_afrr_energy_eur' in solution_df.columns else 0
    total_revenue = revenue_da + revenue_fcr + revenue_afrr_cap + revenue_afrr_energy

    # Build summary metrics dictionary
    summary_metrics = {
        'model': args.model,
        'country': args.country,
        'time_horizon_hours': args.hours,
        'start_step': args.start_step,
        'c_rate': args.c_rate,
        'max_as_ratio': args.max_as_ratio,
        'use_ev_weighting': args.ev_weighting,
        'total_profit_eur': solution_dict['objective_value'],
        'total_revenue_eur': total_revenue,
        'revenue_da_eur': revenue_da,
        'revenue_fcr_eur': revenue_fcr,
        'revenue_afrr_capacity_eur': revenue_afrr_cap,
        'revenue_afrr_energy_eur': revenue_afrr_energy,
        'solver_status': solution_dict['status'],
        'solver_name': solution_dict.get('solver', 'unknown'),
        'solve_time_sec': solve_time,
        'build_time_sec': build_time,
        'total_time_sec': build_time + solve_time,
        'n_variables': model.nvariables(),
        'n_constraints': model.nconstraints()
    }

    # Add model-specific parameters
    if args.model in ['II', 'III']:
        summary_metrics['alpha'] = args.alpha
        summary_metrics['lifo_epsilon_kwh'] = args.epsilon
        summary_metrics['require_sequential_segment_activation'] = args.sequential
    if args.model == 'I' and args.daily_cycle_limit is not None:
        summary_metrics['daily_cycle_limit'] = args.daily_cycle_limit

    # Add degradation metrics if available
    if 'degradation_metrics' in solution_dict:
        summary_metrics['degradation_metrics'] = solution_dict['degradation_metrics']

    # Generate descriptive run name
    if args.run_name:
        run_name = args.run_name
    else:
        run_name = f"p2b_model{args.model}_{args.country}_{args.hours}h"
        if args.model in ['II', 'III']:
            run_name += f"_alpha{args.alpha}_eps{args.epsilon}"
            if args.sequential:
                run_name += "_seq"

    # Save using results_exporter
    output_directory = save_optimization_results(
        solution_df,
        summary_metrics,
        run_name,
        base_output_dir=str(project_root / "validation_results" / "optimizer_validation")
    )

    print("\n" + "=" * 80)
    print("=📁 RESULTS SAVED SUCCESSFULLY")
    print("=" * 80)
    print(f"=📁 Output directory: {output_directory}")
    print(f"   =📁 solution_timeseries.csv")
    print(f"   =📁 performance_summary.json")
    print(f"   =📁 plots/ (subdirectory)")
    print("=" * 80)

    return output_directory, summary_metrics


def generate_plots(solution_df, solution_dict, output_directory, args, aging_config_path):
    """Generate all validation plots."""
    plots_dir = output_directory / "plots"
    title_suffix = f"{args.country} - {args.hours}h - Model {args.model}"

    print("\n" + "=" * 80)
    print("= GENERATING VALIDATION PLOTS")
    print("=" * 80)

    # Standard market participation plots
    print("\n[1/4] Day-Ahead Market...")
    fig_da = plot_da_market_price_bid(solution_df, title_suffix=title_suffix, use_timestamp=False)
    fig_da.write_html(str(plots_dir / "da_market_price_bid.html"))
    print("   [GOOD!] Saved: da_market_price_bid.html")

    print("\n[2/4] aFRR Energy Market...")
    fig_afrr_e = plot_afrr_energy_market_price_bid(solution_df, title_suffix=title_suffix, use_timestamp=False)
    fig_afrr_e.write_html(str(plots_dir / "afrr_energy_market_price_bid.html"))
    print("   [GOOD!] Saved: afrr_energy_market_price_bid.html")

    print("\n[3/4] Capacity Markets...")
    fig_cap = plot_capacity_markets_price_bid(solution_df, title_suffix=title_suffix, use_timestamp=False)
    fig_cap.write_html(str(plots_dir / "capacity_markets_price_bid.html"))
    print("   [GOOD!] Saved: capacity_markets_price_bid.html")

    print("\n[4/4] SOC & Power Bids...")
    fig_soc = plot_soc_and_power_bids(solution_df, title_suffix=title_suffix, use_timestamp=False)
    fig_soc.write_html(str(plots_dir / "soc_and_power_bids.html"))
    print("   [GOOD!] Saved: soc_and_power_bids.html")

    # Aging validation plots (Model II/III only)
    if args.model in ['II', 'III']:
        print("\n" + "-" * 80)
        print("Aging Validation Plots")
        print("-" * 80)

        # Plot 5: Stacked Cyclic SOC (Model II/III)
        if 'e_soc_j' in solution_dict and solution_dict['e_soc_j']:
            print("\n[5/6] Cyclic SOC Stacked Segments...")
            try:
                fig_cyclic = plot_stacked_cyclic_soc(
                    solution_dict,
                    title_suffix=title_suffix,
                    save_path=str(plots_dir / "cyclic_soc_stacked.html")
                )
                print("   [GOOD!] Saved: cyclic_soc_stacked.html")
            except Exception as e:
                print(f"   L Error: {e}")
        else:
            print("\n[5/6] Cyclic SOC plot skipped (no segment data)")

        # Plot 6: Calendar Aging Curve (Model III only)
        if args.model == 'III' and 'c_cal_cost' in solution_dict and solution_dict['c_cal_cost']:
            print("\n[6/6] Calendar Aging Cost Curve...")
            try:
                # Load aging config for breakpoints
                with open(aging_config_path, 'r') as f:
                    aging_config = json.load(f)

                fig_calendar = plot_calendar_aging_curve(
                    solution_dict,
                    aging_config=aging_config,
                    title_suffix=title_suffix,
                    save_path=str(plots_dir / "calendar_aging_curve.html")
                )
                print("   [GOOD!] Saved: calendar_aging_curve.html")
            except Exception as e:
                print(f"   L Error: {e}")
        else:
            print("\n[6/6] Calendar aging plot skipped (Model III required)")

    print("\n" + "=" * 80)
    print("[GOOD!] All plots generated successfully!")
    print("=" * 80)


def main():
    """Main execution function."""
    # Parse arguments
    args = parse_arguments()

    # Display scenario configuration
    print("=" * 80)
    print("=[Check] SCENARIO CONFIGURATION")
    print("=" * 80)
    print(f"Model:              {args.model}")
    print(f"Country:            {args.country}")
    print(f"Time Horizon:       {args.hours} hours")
    print(f"Start Step:         {args.start_step}")
    print(f"C-Rate:             {args.c_rate}")
    print(f"Max AS Ratio:       {args.max_as_ratio * 100:.0f}%")
    if args.model in ["II", "III"]:
        print(f"Alpha (degradation):{args.alpha}")
        print(f"LIFO Epsilon:       {args.epsilon} kWh ({args.epsilon/447.2*100:.1f}% of segment capacity)")
        print(f"Sequential Activation: {args.sequential}")
    if args.model == "I" and args.daily_cycle_limit is not None:
        print(f"Daily Cycle Limit:  {args.daily_cycle_limit}")
    print(f"EV Weighting:       {args.ev_weighting}")
    print("=" * 80)

    # Load configuration files
    config_dir = project_root / "data" / "p2_config"
    aging_config_path = config_dir / "aging_config.json"

    # Load market data
    country_data = load_market_data(args.country, project_root)

    # Extract time window
    data_slice = extract_time_window(country_data, args.start_step, args.hours)

    # Initialize optimizer
    optimizer = initialize_optimizer(args)

    # Build model
    model, build_time = build_model(optimizer, data_slice, args)

    # Solve model
    solved_model, solver_results, solve_time = solve_model(optimizer, model)

    # Extract solution
    solution_dict, solution_df = extract_solution(
        optimizer, solved_model, solver_results, data_slice, args, build_time, solve_time
    )

    # Save results
    if not args.no_save:
        output_directory, summary_metrics = save_results(
            solution_df, solution_dict, model, args, build_time, solve_time, project_root
        )

        # Generate plots
        if not args.no_plots:
            generate_plots(solution_df, solution_dict, output_directory, args, aging_config_path)
    else:
        print("\n" + "=" * 80)
        print("[!]  RESULTS NOT SAVED (--no_save flag)")
        print("=" * 80)

    print("\n" + "=" * 80)
    print("<[Yeah!] OPTIMIZATION COMPLETE!")
    print("=" * 80)
    print(f"[GOOD!] Total Profit: {solution_dict['objective_value']:.2f} EUR")
    print(f"[!]  Total Time:  {build_time + solve_time:.2f}s")
    print("=" * 80)


if __name__ == "__main__":
    main()
