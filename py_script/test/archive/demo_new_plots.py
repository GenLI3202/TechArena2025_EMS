#!/usr/bin/env python3
"""
Demo script to test the new energy and capacity market visualization functions.
"""

import sys
from pathlib import Path
import pandas as pd

sys.path.append(str(Path(__file__).parent / 'py_script'))

from py_script.visualization.optimization_analysis import (
    plot_da_market_price_bid,
    plot_afrr_energy_market_price_bid,
    plot_capacity_markets_price_bid,
    plot_soc_and_power_bids
)

def main():
    """Test the new plotting functions with the balanced 24h solution."""

    # Load the balanced 24h solution
    solution_file = Path("results/model_iii_detailed_solutions/solution_24h_balanced.csv")

    if not solution_file.exists():
        print(f"Error: Solution file not found at {solution_file}")
        print("Please run test_24h_balanced.py first to generate the solution.")
        return

    print(f"Loading solution from {solution_file}...")
    df = pd.read_csv(solution_file)

    print(f"Loaded {len(df)} time steps")
    print(f"Columns: {df.columns.tolist()}")

    # Create output directory
    output_dir = Path("results/model_iii_validation/new_plots")
    output_dir.mkdir(exist_ok=True, parents=True)

    # ========================================================================
    # Plot 1: Day-Ahead Market
    # ========================================================================
    print("\nGenerating Day-Ahead Market plot...")
    try:
        fig_da = plot_da_market_price_bid(
            df,
            title_suffix="(Balanced Configuration, 24h)",
            use_timestamp=False
        )

        # Save as HTML for interactive viewing
        html_file = output_dir / "da_market_price_bid.html"
        fig_da.write_html(str(html_file))
        print(f"[OK] Saved to: {html_file}")

        # Try to save as static image (requires kaleido)
        try:
            png_file = output_dir / "da_market_price_bid.png"
            fig_da.write_image(str(png_file), width=1200, height=600, scale=2)
            print(f"[OK] Saved to: {png_file}")
        except Exception:
            print(f"[INFO] PNG export skipped (kaleido not installed)")

    except Exception as e:
        print(f"[ERROR] Error creating DA market plot: {e}")
        import traceback
        traceback.print_exc()

    # ========================================================================
    # Plot 2: aFRR Energy Market
    # ========================================================================
    print("\nGenerating aFRR Energy Market plot...")
    try:
        fig_afrr_e = plot_afrr_energy_market_price_bid(
            df,
            title_suffix="(Balanced Configuration, 24h)",
            use_timestamp=False
        )

        # Save as HTML for interactive viewing
        html_file = output_dir / "afrr_energy_market_price_bid.html"
        fig_afrr_e.write_html(str(html_file))
        print(f"[OK] Saved to: {html_file}")

        # Try to save as static image (requires kaleido)
        try:
            png_file = output_dir / "afrr_energy_market_price_bid.png"
            fig_afrr_e.write_image(str(png_file), width=1200, height=600, scale=2)
            print(f"[OK] Saved to: {png_file}")
        except Exception:
            print(f"[INFO] PNG export skipped (kaleido not installed)")

    except Exception as e:
        print(f"[ERROR] Error creating aFRR energy market plot: {e}")
        import traceback
        traceback.print_exc()

    # ========================================================================
    # Plot 3: Capacity Markets (FCR + aFRR capacity)
    # ========================================================================
    print("\nGenerating Capacity Markets plot...")
    try:
        fig_capacity = plot_capacity_markets_price_bid(
            df,
            title_suffix="(Balanced Configuration, 24h)",
            use_timestamp=False
        )

        # Save as HTML for interactive viewing
        html_file = output_dir / "capacity_markets_price_bid.html"
        fig_capacity.write_html(str(html_file))
        print(f"[OK] Saved to: {html_file}")

        # Try to save as static image (requires kaleido)
        try:
            png_file = output_dir / "capacity_markets_price_bid.png"
            fig_capacity.write_image(str(png_file), width=1200, height=600, scale=2)
            print(f"[OK] Saved to: {png_file}")
        except Exception:
            print(f"[INFO] PNG export skipped (kaleido not installed)")

    except Exception as e:
        print(f"[ERROR] Error creating capacity markets plot: {e}")
        import traceback
        traceback.print_exc()

    # ========================================================================
    # Plot 4: SOC & Power Bids Combined
    # ========================================================================
    print("\nGenerating SOC & Power Bids plot...")
    try:
        fig_soc = plot_soc_and_power_bids(
            df,
            title_suffix="(Balanced Configuration, 24h)",
            use_timestamp=False
        )

        # Save as HTML for interactive viewing
        html_file = output_dir / "soc_and_power_bids.html"
        fig_soc.write_html(str(html_file))
        print(f"[OK] Saved to: {html_file}")

        # Try to save as static image (requires kaleido)
        try:
            png_file = output_dir / "soc_and_power_bids.png"
            fig_soc.write_image(str(png_file), width=1200, height=600, scale=2)
            print(f"[OK] Saved to: {png_file}")
        except Exception:
            print(f"[INFO] PNG export skipped (kaleido not installed)")

    except Exception as e:
        print(f"[ERROR] Error creating SOC & power bids plot: {e}")
        import traceback
        traceback.print_exc()

    print(f"\n{'='*60}")
    print("Demo complete! Check the output directory:")
    print(f"  {output_dir}")
    print("="*60)

    # Show quick statistics
    print("\nSolution Statistics:")
    print(f"  DA Charge: {df['p_ch_kw'].sum()/1000:.2f} MWh")
    print(f"  DA Discharge: {df['p_dis_kw'].sum()/1000:.2f} MWh")
    print(f"  aFRR+ Energy: {df['p_afrr_pos_e_kw'].sum()/1000:.2f} MWh")
    print(f"  aFRR- Energy: {df['p_afrr_neg_e_kw'].sum()/1000:.2f} MWh")
    print(f"  Max FCR: {df['c_fcr_mw'].max():.3f} MW")
    print(f"  Max aFRR+ Cap: {df['c_afrr_pos_mw'].max():.3f} MW")
    print(f"  Max aFRR- Cap: {df['c_afrr_neg_mw'].max():.3f} MW")

if __name__ == "__main__":
    main()
