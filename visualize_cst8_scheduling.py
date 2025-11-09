"""
Visualize Cst-8 Fix Scheduling Behavior
========================================

Creates comprehensive visualizations of battery scheduling decisions with
energy and capacity market data to verify optimal bidding behavior after
Cst-8 constraint re-enablement.

Visualizations:
1. Power scheduling overview (charge/discharge/reserves with SOC)
2. Market participation timeline (binary decisions + capacity bids)
3. Price-action correlation (market prices vs battery decisions)
4. Revenue breakdown by market and time
5. Cst-8 constraint validation visualization

Usage:
    python visualize_cst8_scheduling.py --horizon 24
    python visualize_cst8_scheduling.py --horizon 48 --country CH
"""

import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import json
from typing import Optional, Dict, Tuple
import argparse
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import McKinsey styling
sys.path.append(str(Path(__file__).parent / 'py_script'))
from visualization.config import MCKINSEY_COLORS, COUNTRY_COLORS, MCKINSEY_FONTS

class Cst8SchedulingVisualizer:
    """Visualize battery scheduling with market data after Cst-8 fix."""

    def __init__(self, horizon_hours: int, country: str = 'CH'):
        """Initialize visualizer.

        Args:
            horizon_hours: Planning horizon (24, 36, or 48)
            country: Country code (CH, DE, AT, etc.)
        """
        self.horizon_hours = horizon_hours
        self.country = country
        self.results_dir = Path("results/model_iii_detailed_solutions")

        # Load decision variables CSV
        self.csv_file = self.results_dir / f"solution_{horizon_hours}h_cst8_enabled.csv"
        self.json_file = self.results_dir / f"summary_{horizon_hours}h_cst8_enabled.json"

        if not self.csv_file.exists():
            raise FileNotFoundError(f"Solution file not found: {self.csv_file}")

        self.df = pd.read_csv(self.csv_file)

        with open(self.json_file, 'r') as f:
            self.summary = json.load(f)

        logger.info(f"Loaded {len(self.df)} time steps for {horizon_hours}h horizon")

        # Create output directory for plots
        self.plot_dir = Path("results/model_iii_validation/cst8_scheduling_plots")
        self.plot_dir.mkdir(exist_ok=True, parents=True)

    def plot_power_scheduling_overview(self, save: bool = True) -> plt.Figure:
        """
        Plot 1: Power scheduling overview with SOC profile.

        Shows:
        - Top panel: Charge/discharge power + aFRR energy activation
        - Middle panel: Capacity reservations (FCR, aFRR+, aFRR-)
        - Bottom panel: SOC trajectory
        """
        fig = plt.figure(figsize=(16, 10))
        gs = gridspec.GridSpec(3, 1, height_ratios=[1.2, 1, 1], hspace=0.3)

        # Prepare time axis (hours)
        hours = self.df['hour'].values

        # ========== Panel 1: Power Profile ==========
        ax1 = fig.add_subplot(gs[0])

        # Plot charge (positive) and discharge (negative) with aFRR energy overlaid
        p_ch = self.df['p_ch_kw'].values / 1000  # Convert to MW
        p_dis = -self.df['p_dis_kw'].values / 1000  # Negative for discharge
        p_afrr_pos_e = self.df['p_afrr_pos_e_kw'].values / 1000
        p_afrr_neg_e = -self.df['p_afrr_neg_e_kw'].values / 1000

        # Stack the power components
        ax1.fill_between(hours, 0, p_ch, step='post', alpha=0.6,
                        color=MCKINSEY_COLORS['positive'], label='Charge (DA)')
        ax1.fill_between(hours, 0, p_dis, step='post', alpha=0.6,
                        color=MCKINSEY_COLORS['negative'], label='Discharge (DA)')
        ax1.fill_between(hours, 0, p_afrr_pos_e, step='post', alpha=0.4,
                        color='#4ECDC4', label='aFRR+ Energy')
        ax1.fill_between(hours, 0, p_afrr_neg_e, step='post', alpha=0.4,
                        color='#FF6B6B', label='aFRR- Energy')

        ax1.axhline(y=0, color='black', linewidth=1, alpha=0.5)
        ax1.set_ylabel('Power (MW)', fontsize=MCKINSEY_FONTS['axis_label_size'],
                      color=MCKINSEY_COLORS['gray_dark'])
        ax1.set_title(f'Battery Power Scheduling - {self.horizon_hours}h Horizon (Cst-8 Enabled)',
                     fontsize=MCKINSEY_FONTS['title_size'], fontweight='bold',
                     color=MCKINSEY_COLORS['navy'])
        ax1.grid(True, alpha=0.3, color=MCKINSEY_COLORS['gray_light'])
        ax1.legend(loc='upper right', fontsize=MCKINSEY_FONTS['legend_size'])
        ax1.set_xlim(0, self.horizon_hours)

        # ========== Panel 2: Capacity Reservations ==========
        ax2 = fig.add_subplot(gs[1], sharex=ax1)

        c_fcr = self.df['c_fcr_mw'].values
        c_afrr_pos = self.df['c_afrr_pos_mw'].values
        c_afrr_neg = self.df['c_afrr_neg_mw'].values

        # Stacked area chart for capacity bids
        ax2.fill_between(hours, 0, c_fcr, step='post', alpha=0.7,
                        color='#FFD700', label='FCR Capacity')
        ax2.fill_between(hours, c_fcr, c_fcr + c_afrr_pos, step='post', alpha=0.7,
                        color='#4ECDC4', label='aFRR+ Capacity')
        ax2.fill_between(hours, c_fcr + c_afrr_pos, c_fcr + c_afrr_pos + c_afrr_neg,
                        step='post', alpha=0.7, color='#FF6B6B', label='aFRR- Capacity')

        ax2.set_ylabel('Capacity (MW)', fontsize=MCKINSEY_FONTS['axis_label_size'],
                      color=MCKINSEY_COLORS['gray_dark'])
        ax2.set_title('Ancillary Service Capacity Reservations',
                     fontsize=MCKINSEY_FONTS['subtitle_size'], fontweight='bold',
                     color=MCKINSEY_COLORS['dark_blue'])
        ax2.grid(True, alpha=0.3, color=MCKINSEY_COLORS['gray_light'])
        ax2.legend(loc='upper right', fontsize=MCKINSEY_FONTS['legend_size'])

        # ========== Panel 3: SOC Profile ==========
        ax3 = fig.add_subplot(gs[2], sharex=ax1)

        soc_pct = self.df['soc_pct'].values
        ax3.plot(hours, soc_pct, linewidth=2.5, color=MCKINSEY_COLORS['navy'],
                label='SOC')
        ax3.fill_between(hours, 0, soc_pct, alpha=0.2, color=MCKINSEY_COLORS['navy'])

        # Add SOC limits
        ax3.axhline(y=0, color='red', linestyle='--', linewidth=1, alpha=0.7, label='Min SOC')
        ax3.axhline(y=100, color='red', linestyle='--', linewidth=1, alpha=0.7, label='Max SOC')

        ax3.set_xlabel('Time (hours)', fontsize=MCKINSEY_FONTS['axis_label_size'],
                      color=MCKINSEY_COLORS['gray_dark'])
        ax3.set_ylabel('SOC (%)', fontsize=MCKINSEY_FONTS['axis_label_size'],
                      color=MCKINSEY_COLORS['gray_dark'])
        ax3.set_title('State of Charge Trajectory',
                     fontsize=MCKINSEY_FONTS['subtitle_size'], fontweight='bold',
                     color=MCKINSEY_COLORS['dark_blue'])
        ax3.grid(True, alpha=0.3, color=MCKINSEY_COLORS['gray_light'])
        ax3.legend(loc='upper right', fontsize=MCKINSEY_FONTS['legend_size'])
        ax3.set_ylim(-5, 105)
        ax3.set_xlim(0, self.horizon_hours)

        plt.tight_layout()

        if save:
            filename = self.plot_dir / f"{self.horizon_hours}h_power_scheduling_overview.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            logger.info(f"Saved power scheduling overview: {filename}")

        return fig

    def plot_market_participation_timeline(self, save: bool = True) -> plt.Figure:
        """
        Plot 2: Market participation timeline with binary decisions.

        Shows binary decision variables (y_ch, y_dis, y_fcr, y_afrr_pos, y_afrr_neg)
        as heatmap to visualize when battery participates in each market.
        """
        fig, ax = plt.subplots(figsize=(16, 6))

        # Prepare binary decision matrix
        binary_vars = pd.DataFrame({
            'DA Charge': self.df['y_ch'].values,
            'DA Discharge': self.df['y_dis'].values,
            'FCR Reserve': self.df['y_fcr'].values,
            'aFRR+ Reserve': self.df['y_afrr_pos'].values,
            'aFRR- Reserve': self.df['y_afrr_neg'].values,
        })

        # Create heatmap
        im = ax.imshow(binary_vars.T, aspect='auto', cmap='YlGn',
                      interpolation='nearest', vmin=0, vmax=1,
                      extent=[0, self.horizon_hours, -0.5, 4.5])

        # Set ticks and labels
        ax.set_yticks(range(5))
        ax.set_yticklabels(binary_vars.columns, fontsize=MCKINSEY_FONTS['axis_label_size'])
        ax.set_xlabel('Time (hours)', fontsize=MCKINSEY_FONTS['axis_label_size'],
                     color=MCKINSEY_COLORS['gray_dark'])
        ax.set_title(f'Market Participation Timeline - {self.horizon_hours}h Horizon\n'
                    f'Binary Decision Variables (0 = Inactive, 1 = Active)',
                    fontsize=MCKINSEY_FONTS['title_size'], fontweight='bold',
                    color=MCKINSEY_COLORS['navy'])

        # Add colorbar
        cbar = plt.colorbar(im, ax=ax, orientation='vertical', pad=0.02)
        cbar.set_label('Decision Value', fontsize=MCKINSEY_FONTS['axis_label_size'])

        # Add grid lines
        ax.set_xticks(np.arange(0, self.horizon_hours + 1, 6))
        ax.grid(True, which='major', axis='x', alpha=0.3, color='white', linewidth=1)

        plt.tight_layout()

        if save:
            filename = self.plot_dir / f"{self.horizon_hours}h_market_participation_timeline.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            logger.info(f"Saved market participation timeline: {filename}")

        return fig

    def plot_price_action_correlation(self, save: bool = True) -> plt.Figure:
        """
        Plot 3: Price-action correlation analysis.

        Shows market prices overlaid with battery actions to verify
        optimal bidding behavior (charge when prices low, discharge when high, etc.)
        """
        fig = plt.figure(figsize=(16, 10))
        gs = gridspec.GridSpec(3, 1, height_ratios=[1, 1, 1], hspace=0.3)

        hours = self.df['hour'].values

        # ========== Panel 1: Day-Ahead Market ==========
        ax1 = fig.add_subplot(gs[0])

        # Plot DA price
        ax1_price = ax1.twinx()
        price_da = self.df['price_da_eur_mwh'].values
        ax1_price.plot(hours, price_da, linewidth=2, color=MCKINSEY_COLORS['navy'],
                      label='DA Price', alpha=0.7)
        ax1_price.set_ylabel('DA Price (EUR/MWh)', fontsize=MCKINSEY_FONTS['axis_label_size'],
                            color=MCKINSEY_COLORS['navy'])
        ax1_price.tick_params(axis='y', labelcolor=MCKINSEY_COLORS['navy'])

        # Plot charge/discharge decisions as bars
        p_net = (self.df['p_dis_kw'].values - self.df['p_ch_kw'].values) / 1000
        colors = ['green' if p >= 0 else 'red' for p in p_net]
        ax1.bar(hours, p_net, width=0.25, color=colors, alpha=0.5, label='Net Power (MW)')
        ax1.axhline(y=0, color='black', linewidth=1, alpha=0.5)
        ax1.set_ylabel('Net Power (MW)', fontsize=MCKINSEY_FONTS['axis_label_size'])
        ax1.set_title('Day-Ahead Market: Price vs Battery Action',
                     fontsize=MCKINSEY_FONTS['title_size'], fontweight='bold',
                     color=MCKINSEY_COLORS['navy'])
        ax1.grid(True, alpha=0.3, axis='y')
        ax1.set_xlim(0, self.horizon_hours)

        # Combined legend
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax1_price.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left',
                  fontsize=MCKINSEY_FONTS['legend_size'])

        # ========== Panel 2: FCR Capacity Market ==========
        ax2 = fig.add_subplot(gs[1], sharex=ax1)

        # Plot FCR capacity price
        ax2_price = ax2.twinx()
        price_fcr = self.df['price_fcr_eur_mw'].values
        ax2_price.plot(hours, price_fcr, linewidth=2, color='#FFD700',
                      label='FCR Price', alpha=0.7)
        ax2_price.set_ylabel('FCR Price (EUR/MW)', fontsize=MCKINSEY_FONTS['axis_label_size'],
                            color='#FFD700')
        ax2_price.tick_params(axis='y', labelcolor='#FFD700')

        # Plot FCR capacity bids as bars
        c_fcr = self.df['c_fcr_mw'].values
        ax2.bar(hours, c_fcr, width=0.25, color='#FFD700', alpha=0.5, label='FCR Bid (MW)')
        ax2.set_ylabel('FCR Capacity (MW)', fontsize=MCKINSEY_FONTS['axis_label_size'])
        ax2.set_title('FCR Market: Price vs Capacity Bid',
                     fontsize=MCKINSEY_FONTS['subtitle_size'], fontweight='bold',
                     color=MCKINSEY_COLORS['dark_blue'])
        ax2.grid(True, alpha=0.3, axis='y')

        lines1, labels1 = ax2.get_legend_handles_labels()
        lines2, labels2 = ax2_price.get_legend_handles_labels()
        ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper left',
                  fontsize=MCKINSEY_FONTS['legend_size'])

        # ========== Panel 3: aFRR Capacity Markets ==========
        ax3 = fig.add_subplot(gs[2], sharex=ax1)

        # Plot aFRR prices
        ax3_price = ax3.twinx()
        price_afrr_pos = self.df['price_afrr_cap_pos_eur_mw'].values
        price_afrr_neg = self.df['price_afrr_cap_neg_eur_mw'].values
        ax3_price.plot(hours, price_afrr_pos, linewidth=2, color='#4ECDC4',
                      label='aFRR+ Price', alpha=0.7, linestyle='--')
        ax3_price.plot(hours, price_afrr_neg, linewidth=2, color='#FF6B6B',
                      label='aFRR- Price', alpha=0.7, linestyle='--')
        ax3_price.set_ylabel('aFRR Price (EUR/MW)', fontsize=MCKINSEY_FONTS['axis_label_size'])

        # Plot aFRR capacity bids as bars
        c_afrr_pos = self.df['c_afrr_pos_mw'].values
        c_afrr_neg = self.df['c_afrr_neg_mw'].values
        width = 0.12
        ax3.bar(hours - width/2, c_afrr_pos, width=width, color='#4ECDC4',
               alpha=0.5, label='aFRR+ Bid')
        ax3.bar(hours + width/2, c_afrr_neg, width=width, color='#FF6B6B',
               alpha=0.5, label='aFRR- Bid')
        ax3.set_ylabel('aFRR Capacity (MW)', fontsize=MCKINSEY_FONTS['axis_label_size'])
        ax3.set_xlabel('Time (hours)', fontsize=MCKINSEY_FONTS['axis_label_size'])
        ax3.set_title('aFRR Markets: Price vs Capacity Bids',
                     fontsize=MCKINSEY_FONTS['subtitle_size'], fontweight='bold',
                     color=MCKINSEY_COLORS['dark_blue'])
        ax3.grid(True, alpha=0.3, axis='y')
        ax3.set_xlim(0, self.horizon_hours)

        lines1, labels1 = ax3.get_legend_handles_labels()
        lines2, labels2 = ax3_price.get_legend_handles_labels()
        ax3.legend(lines1 + lines2, labels1 + labels2, loc='upper left',
                  fontsize=MCKINSEY_FONTS['legend_size'])

        plt.tight_layout()

        if save:
            filename = self.plot_dir / f"{self.horizon_hours}h_price_action_correlation.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            logger.info(f"Saved price-action correlation: {filename}")

        return fig

    def plot_revenue_breakdown(self, save: bool = True) -> plt.Figure:
        """
        Plot 4: Revenue breakdown by market and time.

        Shows instantaneous and cumulative revenue from each market.
        """
        fig = plt.figure(figsize=(16, 8))
        gs = gridspec.GridSpec(2, 2, height_ratios=[1, 1], width_ratios=[2, 1],
                              hspace=0.3, wspace=0.3)

        hours = self.df['hour'].values

        # ========== Panel 1: Instantaneous Revenue by Market ==========
        ax1 = fig.add_subplot(gs[0, 0])

        rev_da = self.df['revenue_da_eur'].values
        rev_afrr_e = self.df['revenue_afrr_energy_eur'].values
        rev_as_cap = self.df['revenue_as_capacity_eur'].values

        # Stacked area chart
        ax1.fill_between(hours, 0, rev_da, step='post', alpha=0.6,
                        color=MCKINSEY_COLORS['navy'], label='DA Energy')
        ax1.fill_between(hours, rev_da, rev_da + rev_afrr_e, step='post', alpha=0.6,
                        color='#4ECDC4', label='aFRR Energy')
        ax1.fill_between(hours, rev_da + rev_afrr_e,
                        rev_da + rev_afrr_e + rev_as_cap,
                        step='post', alpha=0.6, color='#FFD700', label='AS Capacity')

        ax1.set_ylabel('Revenue (EUR/interval)', fontsize=MCKINSEY_FONTS['axis_label_size'])
        ax1.set_title('Instantaneous Revenue by Market',
                     fontsize=MCKINSEY_FONTS['subtitle_size'], fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper left', fontsize=MCKINSEY_FONTS['legend_size'])
        ax1.set_xlim(0, self.horizon_hours)

        # ========== Panel 2: Cumulative Revenue ==========
        ax2 = fig.add_subplot(gs[1, 0], sharex=ax1)

        cum_da = np.cumsum(rev_da)
        cum_afrr_e = np.cumsum(rev_afrr_e)
        cum_as_cap = np.cumsum(rev_as_cap)
        cum_total = cum_da + cum_afrr_e + cum_as_cap

        ax2.plot(hours, cum_da, linewidth=2.5, color=MCKINSEY_COLORS['navy'],
                label='DA Energy')
        ax2.plot(hours, cum_afrr_e, linewidth=2.5, color='#4ECDC4',
                label='aFRR Energy')
        ax2.plot(hours, cum_as_cap, linewidth=2.5, color='#FFD700',
                label='AS Capacity')
        ax2.plot(hours, cum_total, linewidth=3, color='black', linestyle='--',
                label='Total', alpha=0.7)

        ax2.set_xlabel('Time (hours)', fontsize=MCKINSEY_FONTS['axis_label_size'])
        ax2.set_ylabel('Cumulative Revenue (EUR)', fontsize=MCKINSEY_FONTS['axis_label_size'])
        ax2.set_title('Cumulative Revenue Over Time',
                     fontsize=MCKINSEY_FONTS['subtitle_size'], fontweight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc='upper left', fontsize=MCKINSEY_FONTS['legend_size'])
        ax2.set_xlim(0, self.horizon_hours)

        # ========== Panel 3: Total Revenue Pie Chart ==========
        ax3 = fig.add_subplot(gs[0, 1])

        total_da = self.summary['total_revenue_da']
        total_afrr_e = self.summary['total_revenue_afrr_e']
        total_as_cap = self.summary['total_revenue_as_cap']

        revenues = [total_da, total_afrr_e, total_as_cap]
        labels = ['DA Energy', 'aFRR Energy', 'AS Capacity']
        colors = [MCKINSEY_COLORS['navy'], '#4ECDC4', '#FFD700']

        # Filter out near-zero revenues
        filtered_data = [(r, l, c) for r, l, c in zip(revenues, labels, colors) if abs(r) > 0.01]
        if filtered_data:
            revenues_f, labels_f, colors_f = zip(*filtered_data)
            wedges, texts, autotexts = ax3.pie(revenues_f, labels=labels_f, colors=colors_f,
                                               autopct='%1.1f%%', startangle=90,
                                               textprops={'fontsize': MCKINSEY_FONTS['legend_size']})
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')

        ax3.set_title(f'Total Revenue\n{sum(revenues):.2f} EUR',
                     fontsize=MCKINSEY_FONTS['subtitle_size'], fontweight='bold')

        # ========== Panel 4: Summary Statistics ==========
        ax4 = fig.add_subplot(gs[1, 1])
        ax4.axis('off')

        stats_text = f"""
        REVENUE SUMMARY
        {'=' * 30}

        Total Revenue: {sum(revenues):.2f} EUR

        By Market:
        • DA Energy:    {total_da:>10.2f} EUR
        • aFRR Energy:  {total_afrr_e:>10.2f} EUR
        • AS Capacity:  {total_as_cap:>10.2f} EUR

        Objective Value: {self.summary['objective_value']:.2f} EUR

        Degradation Costs:
        • Cyclic:   {self.summary['degradation']['total_cyclic_cost_eur']:>10.2f} EUR
        • Calendar: {self.summary['degradation']['total_calendar_cost_eur']:>10.2f} EUR
        """

        ax4.text(0.1, 0.5, stats_text, fontsize=10, family='monospace',
                verticalalignment='center',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

        plt.suptitle(f'Revenue Analysis - {self.horizon_hours}h Horizon',
                    fontsize=MCKINSEY_FONTS['title_size'], fontweight='bold',
                    color=MCKINSEY_COLORS['navy'])

        plt.tight_layout()

        if save:
            filename = self.plot_dir / f"{self.horizon_hours}h_revenue_breakdown.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            logger.info(f"Saved revenue breakdown: {filename}")

        return fig

    def plot_cst8_validation(self, save: bool = True) -> plt.Figure:
        """
        Plot 5: Cst-8 constraint validation visualization.

        Shows the binary sums to verify they don't exceed 1.0.
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 8), sharex=True)

        hours = self.df['hour'].values

        # Discharge constraint: y_total_dis + y_fcr + y_afrr_neg ≤ 1
        sum_discharge = self.df['cst8_discharge_sum'].values

        ax1.plot(hours, sum_discharge, linewidth=2, color=MCKINSEY_COLORS['negative'],
                label='Discharge Binary Sum', marker='o', markersize=3)
        ax1.axhline(y=1.0, color='red', linestyle='--', linewidth=2, alpha=0.7,
                   label='Constraint Limit (≤ 1.0)')
        ax1.fill_between(hours, 0, sum_discharge, alpha=0.3,
                        color=MCKINSEY_COLORS['negative'])

        ax1.set_ylabel('Binary Sum', fontsize=MCKINSEY_FONTS['axis_label_size'])
        ax1.set_title('Cst-8a: Discharge + AS Reserves Binary Sum\n'
                     '(y_total_dis + y_fcr + y_afrr_neg ≤ 1.0)',
                     fontsize=MCKINSEY_FONTS['subtitle_size'], fontweight='bold',
                     color=MCKINSEY_COLORS['navy'])
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper right', fontsize=MCKINSEY_FONTS['legend_size'])
        ax1.set_ylim(-0.05, 1.15)

        # Add violation markers
        violations_dis = sum_discharge > 1.000001
        if violations_dis.any():
            viol_hours = hours[violations_dis]
            viol_values = sum_discharge[violations_dis]
            ax1.scatter(viol_hours, viol_values, color='red', s=100, marker='X',
                       label=f'Violations: {violations_dis.sum()}', zorder=10)

        # Charge constraint: y_total_ch + y_fcr + y_afrr_pos ≤ 1
        sum_charge = self.df['cst8_charge_sum'].values

        ax2.plot(hours, sum_charge, linewidth=2, color=MCKINSEY_COLORS['positive'],
                label='Charge Binary Sum', marker='o', markersize=3)
        ax2.axhline(y=1.0, color='red', linestyle='--', linewidth=2, alpha=0.7,
                   label='Constraint Limit (≤ 1.0)')
        ax2.fill_between(hours, 0, sum_charge, alpha=0.3,
                        color=MCKINSEY_COLORS['positive'])

        ax2.set_xlabel('Time (hours)', fontsize=MCKINSEY_FONTS['axis_label_size'])
        ax2.set_ylabel('Binary Sum', fontsize=MCKINSEY_FONTS['axis_label_size'])
        ax2.set_title('Cst-8b: Charge + AS Reserves Binary Sum\n'
                     '(y_total_ch + y_fcr + y_afrr_pos ≤ 1.0)',
                     fontsize=MCKINSEY_FONTS['subtitle_size'], fontweight='bold',
                     color=MCKINSEY_COLORS['navy'])
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc='upper right', fontsize=MCKINSEY_FONTS['legend_size'])
        ax2.set_ylim(-0.05, 1.15)
        ax2.set_xlim(0, self.horizon_hours)

        # Add violation markers
        violations_ch = sum_charge > 1.000001
        if violations_ch.any():
            viol_hours = hours[violations_ch]
            viol_values = sum_charge[violations_ch]
            ax2.scatter(viol_hours, viol_values, color='red', s=100, marker='X',
                       label=f'Violations: {violations_ch.sum()}', zorder=10)

        # Overall status
        total_violations = violations_dis.sum() + violations_ch.sum()
        status_text = 'PASS' if total_violations == 0 else f'FAIL ({total_violations} violations)'
        status_color = 'green' if total_violations == 0 else 'red'

        fig.suptitle(f'Cst-8 Constraint Validation - {self.horizon_hours}h Horizon\n'
                    f'Status: {status_text}',
                    fontsize=MCKINSEY_FONTS['title_size'], fontweight='bold',
                    color=status_color)

        plt.tight_layout()

        if save:
            filename = self.plot_dir / f"{self.horizon_hours}h_cst8_validation.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            logger.info(f"Saved Cst-8 validation plot: {filename}")

        return fig

    def generate_all_plots(self):
        """Generate all visualization plots."""
        logger.info(f"Generating all plots for {self.horizon_hours}h horizon...")

        logger.info("1/5 - Power scheduling overview...")
        self.plot_power_scheduling_overview()

        logger.info("2/5 - Market participation timeline...")
        self.plot_market_participation_timeline()

        logger.info("3/5 - Price-action correlation...")
        self.plot_price_action_correlation()

        logger.info("4/5 - Revenue breakdown...")
        self.plot_revenue_breakdown()

        logger.info("5/5 - Cst-8 validation...")
        self.plot_cst8_validation()

        logger.info(f"All plots saved to: {self.plot_dir}")

        return self.plot_dir


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Visualize battery scheduling after Cst-8 fix'
    )
    parser.add_argument('--horizon', type=int, choices=[24, 36, 48], default=24,
                       help='Planning horizon in hours (default: 24)')
    parser.add_argument('--country', type=str, default='CH',
                       help='Country code (default: CH)')

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("CST-8 FIX SCHEDULING VISUALIZATION")
    logger.info("=" * 80)
    logger.info(f"Horizon: {args.horizon}h")
    logger.info(f"Country: {args.country}")
    logger.info("=" * 80)

    try:
        visualizer = Cst8SchedulingVisualizer(
            horizon_hours=args.horizon,
            country=args.country
        )

        plot_dir = visualizer.generate_all_plots()

        logger.info("\n" + "=" * 80)
        logger.info("VISUALIZATION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Plots saved to: {plot_dir}")
        logger.info("\nGenerated plots:")
        logger.info(f"  1. {args.horizon}h_power_scheduling_overview.png")
        logger.info(f"  2. {args.horizon}h_market_participation_timeline.png")
        logger.info(f"  3. {args.horizon}h_price_action_correlation.png")
        logger.info(f"  4. {args.horizon}h_revenue_breakdown.png")
        logger.info(f"  5. {args.horizon}h_cst8_validation.png")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Visualization failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
