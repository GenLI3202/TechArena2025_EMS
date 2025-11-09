"""
Market Data Analysis Visualizations
===================================

This script contains a collection of plotting functions designed to explore and
understand the market data for the TechArena 2025 challenge. These functions
are primarily focused on visualizing price distributions, trends, and patterns
in the day-ahead, FCR, and aFRR markets.

All functions are designed to work with the data loading utilities from the
`py_script.data.market_data` module and produce McKinsey-styled visualizations
using Plotly or Matplotlib.
"""

from __future__ import annotations

from typing import Dict, Iterable, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.figure_factory as ff
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt

from ..visualization.config import MCKINSEY_COLORS, COUNTRY_COLORS, apply_mckinsey_style, MCKINSEY_FONTS

# Constants from market_data
TIMESTAMP_COL = "timestamp"
COUNTRY_COL = "country"
PRICE_COL_MWH = "price_eur_mwh"
PRICE_COL_MW = "price_eur_mw"
DIRECTION_COL = "direction"

AFRR_DIRECTION_ALIASES = {
    "positive": "positive", "pos": "positive", "up": "positive", "+": "positive", "upward": "positive",
    "negative": "negative", "neg": "negative", "down": "negative", "-": "negative", "downward": "negative",
}


def _is_tidy_format(df: pd.DataFrame, expected_columns: list) -> bool:
    """Check if DataFrame is in tidy format based on expected column names."""
    return all(col in df.columns for col in expected_columns)

def wide_to_tidy_day_ahead(day_ahead_df: pd.DataFrame) -> pd.DataFrame:
    """Convert day-ahead DataFrame from wide format to tidy format."""
    country_cols = [col for col in day_ahead_df.columns if col != TIMESTAMP_COL]
    tidy_df = day_ahead_df.melt(
        id_vars=[TIMESTAMP_COL], value_vars=country_cols,
        var_name=COUNTRY_COL, value_name=PRICE_COL_MWH
    ).dropna(subset=[PRICE_COL_MWH])
    return tidy_df.sort_values([COUNTRY_COL, TIMESTAMP_COL]).reset_index(drop=True)

def plot_day_ahead_distribution(day_ahead_df: pd.DataFrame) -> go.Figure:
    """Box plot comparing Day-Ahead price distributions across countries."""
    if not _is_tidy_format(day_ahead_df, [TIMESTAMP_COL, COUNTRY_COL, PRICE_COL_MWH]):
        melted = wide_to_tidy_day_ahead(day_ahead_df.copy())
    else:
        melted = day_ahead_df.copy()
    melted = melted.rename(columns={PRICE_COL_MWH: 'price', COUNTRY_COL: 'country'})
    melted = melted.dropna(subset=['price'])
    melted['price'] = pd.to_numeric(melted['price'], errors='coerce')
    melted = melted.dropna(subset=['price'])

    if melted.empty:
        fig = go.Figure()
        fig.add_annotation(text="No valid price data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(title="Day-Ahead Price Distribution by Country")
        return fig

    fig = px.box(
        melted, x='country', y='price', color='country',
        title="Day-Ahead Price Distribution by Country", points="suspectedoutliers",
    )
    fig.update_layout(showlegend=False, xaxis_title="Country", yaxis_title="Price [EUR/MWh]")
    return fig

def plot_day_ahead_trend(day_ahead_df: pd.DataFrame, *, countries: Optional[Iterable[str]] = None) -> go.Figure:
    """Line plot of Day-Ahead prices across 2024, optionally filtered by country."""
    if _is_tidy_format(day_ahead_df, [TIMESTAMP_COL, COUNTRY_COL, PRICE_COL_MWH]):
        melted = day_ahead_df.copy()
        melted = melted.rename(columns={PRICE_COL_MWH: 'price', COUNTRY_COL: 'country'})
        if countries:
            melted = melted[melted['country'].isin(countries)]
    else:
        all_country_cols = [col for col in day_ahead_df.columns if col != TIMESTAMP_COL]
        available_countries = [col for col in all_country_cols if col in countries] if countries else all_country_cols
        melted = day_ahead_df.melt(
            id_vars=[TIMESTAMP_COL], value_vars=available_countries,
            var_name='country', value_name='price'
        )

    melted = melted.dropna(subset=['price'])
    melted['price'] = pd.to_numeric(melted['price'], errors='coerce')
    melted = melted.dropna(subset=['price'])

    if melted.empty:
        fig = go.Figure()
        fig.add_annotation(text="No valid price data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(title="Day-Ahead Price Trend (2024)")
        return fig

    fig = px.line(
        melted, x=TIMESTAMP_COL, y='price', color='country',
        title="Day-Ahead Price Trend (2024)",
    )
    fig.update_layout(xaxis_title="Timestamp", yaxis_title="Price [EUR/MWh]")
    return fig

def plot_fcr_distribution(fcr_df: pd.DataFrame) -> go.Figure:
    """Box plot comparing FCR price distributions across countries."""
    country_cols = [col for col in fcr_df.columns if col != TIMESTAMP_COL]
    melted = fcr_df.melt(
        id_vars=[TIMESTAMP_COL], value_vars=country_cols,
        var_name='country', value_name='price'
    )
    melted = melted.dropna(subset=['price'])
    melted['price'] = pd.to_numeric(melted['price'], errors='coerce')
    melted = melted.dropna(subset=['price'])

    if melted.empty:
        fig = go.Figure()
        fig.add_annotation(text="No valid price data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(title="FCR Price Distribution by Country")
        return fig

    fig = px.box(
        melted, x='country', y='price', color='country',
        title="FCR Price Distribution by Country", points="suspectedoutliers",
    )
    fig.update_layout(showlegend=False, xaxis_title="Country", yaxis_title="Price [EUR/MW]")
    return fig

def plot_afrr_distribution(afrr_df: pd.DataFrame) -> go.Figure:
    """Box plots for aFRR positive and negative capacity prices by country."""
    country_dir_cols = [col for col in afrr_df.columns if col != TIMESTAMP_COL]
    melted_data = []
    for col in country_dir_cols:
        if '_' in col:
            country, direction = col.rsplit('_', 1)
            direction = AFRR_DIRECTION_ALIASES.get(direction.lower(), direction.lower())
        else:
            country, direction = col, 'unknown'
        col_data = afrr_df[[TIMESTAMP_COL, col]].dropna()
        for _, row in col_data.iterrows():
            melted_data.append({
                TIMESTAMP_COL: row[TIMESTAMP_COL], COUNTRY_COL: country,
                DIRECTION_COL: direction, PRICE_COL_MW: row[col]
            })
    melted = pd.DataFrame(melted_data)

    if melted.empty:
        fig = go.Figure()
        fig.add_annotation(text="No valid price data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(title="aFRR Capacity Price Distribution")
        return fig

    melted = melted.dropna(subset=[PRICE_COL_MW])
    melted[PRICE_COL_MW] = pd.to_numeric(melted[PRICE_COL_MW], errors='coerce')
    melted = melted.dropna(subset=[PRICE_COL_MW])
    melted = melted[melted[DIRECTION_COL].isin(['positive', 'negative'])]

    if melted.empty:
        fig = go.Figure()
        fig.add_annotation(text="No valid price data available after cleaning", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(title="aFRR Capacity Price Distribution")
        return fig

    fig = px.box(
        melted, x=COUNTRY_COL, y=PRICE_COL_MW, color=DIRECTION_COL,
        facet_col=DIRECTION_COL, facet_col_spacing=0.07,
        category_orders={DIRECTION_COL: ['positive', 'negative']},
        title="aFRR Capacity Price Distribution (Positive vs Negative)",
    )
    fig.update_layout(xaxis_title="Country", yaxis_title="Price [EUR/MW]", showlegend=False)
    fig.update_xaxes(tickangle=45)
    return fig

def plot_day_ahead_heatmap(day_ahead_df: pd.DataFrame, country: str) -> go.Figure:
    """Hourly-by-month heatmap to reveal charging/discharging windows for a country."""
    if country not in day_ahead_df.columns:
        raise ValueError(f"No Day-Ahead data available for country '{country}'.")
    country_df = day_ahead_df[[TIMESTAMP_COL, country]].dropna()
    if country_df.empty:
        raise ValueError(f"No Day-Ahead data available for country '{country}'.")

    enriched = country_df.assign(
        hour=lambda d: d[TIMESTAMP_COL].dt.hour,
        month=lambda d: d[TIMESTAMP_COL].dt.month,
    )
    pivot = enriched.pivot_table(index="month", columns="hour", values=country, aggfunc="mean").sort_index().sort_index(axis=1)
    fig = px.imshow(
        pivot, aspect="auto", color_continuous_scale="Turbo",
        labels=dict(x="Hour of Day", y="Month", color="Avg Price [EUR/MWh]"),
        title=f"Hourly vs Monthly Day-Ahead Prices · {country}",
    )
    return fig

def _filter_by_time_range(df: pd.DataFrame, time_range: str) -> pd.DataFrame:
    """Filter DataFrame by time range string."""
    if time_range == 'full':
        return df
    elif time_range in ['Q1', 'Q2', 'Q3', 'Q4']:
        quarter_map = {'Q1': [1,2,3], 'Q2': [4,5,6], 'Q3': [7,8,9], 'Q4': [10,11,12]}
        return df[df[TIMESTAMP_COL].dt.month.isin(quarter_map[time_range])]
    else:
        return df[df[TIMESTAMP_COL].dt.strftime('%Y-%m') == time_range]

def plot_price_time_series_mckinsey(tables: Dict[str, pd.DataFrame], country: str, time_range: str = 'full', markets: list = None) -> go.Figure:
    """Plot multi-market price time series with McKinsey styling."""
    if markets is None:
        markets = ['day_ahead', 'fcr', 'afrr_capacity', 'afrr_energy']
    fig = go.Figure()

    if 'day_ahead' in markets and 'day_ahead' in tables:
        df_da = tables['day_ahead']
        country_col = 'DE_LU' if country == 'DE' else country
        if country_col in df_da.columns:
            df_filtered = _filter_by_time_range(df_da, time_range)
            fig.add_trace(go.Scatter(x=df_filtered[TIMESTAMP_COL], y=df_filtered[country_col], mode='lines', name='Day-Ahead', line=dict(color=MCKINSEY_COLORS['cat_1'], width=1.5), hovertemplate='%{y:.2f} EUR/MWh<extra></extra>'))

    if 'fcr' in markets and 'fcr' in tables:
        df_fcr = tables['fcr']
        if country in df_fcr.columns:
            df_filtered = _filter_by_time_range(df_fcr, time_range)
            fig.add_trace(go.Scatter(x=df_filtered[TIMESTAMP_COL], y=df_filtered[country], mode='lines', name='FCR Capacity', line=dict(color=MCKINSEY_COLORS['cat_2'], width=1.5, dash='dot'), hovertemplate='%{y:.2f} EUR/MW<extra></extra>', yaxis='y2'))

    if 'afrr_capacity' in markets and 'afrr_capacity' in tables:
        df_afrr_cap = tables['afrr_capacity']
        df_filtered = _filter_by_time_range(df_afrr_cap, time_range)
        if f'{country}_Pos' in df_afrr_cap.columns:
            fig.add_trace(go.Scatter(x=df_filtered[TIMESTAMP_COL], y=df_filtered[f'{country}_Pos'], mode='lines', name='aFRR Cap (Pos)', line=dict(color=MCKINSEY_COLORS['positive'], width=1.5, dash='dash'), hovertemplate='%{y:.2f} EUR/MW<extra></extra>', yaxis='y2'))
        if f'{country}_Neg' in df_afrr_cap.columns:
            fig.add_trace(go.Scatter(x=df_filtered[TIMESTAMP_COL], y=df_filtered[f'{country}_Neg'], mode='lines', name='aFRR Cap (Neg)', line=dict(color=MCKINSEY_COLORS['negative'], width=1.5, dash='dash'), hovertemplate='%{y:.2f} EUR/MW<extra></extra>', yaxis='y2'))

    if 'afrr_energy' in markets and 'afrr_energy' in tables:
        df_afrr_energy = tables['afrr_energy']
        df_filtered = _filter_by_time_range(df_afrr_energy, time_range)
        if f'{country}_Pos' in df_afrr_energy.columns:
            fig.add_trace(go.Scatter(x=df_filtered[TIMESTAMP_COL], y=df_filtered[f'{country}_Pos'], mode='lines', name='aFRR Energy (Pos)', line=dict(color=MCKINSEY_COLORS['teal'], width=1.5), hovertemplate='%{y:.2f} EUR/MWh<extra></extra>'))
        if f'{country}_Neg' in df_afrr_energy.columns:
            fig.add_trace(go.Scatter(x=df_filtered[TIMESTAMP_COL], y=df_filtered[f'{country}_Neg'], mode='lines', name='aFRR Energy (Neg)', line=dict(color=MCKINSEY_COLORS['cat_5'], width=1.5), hovertemplate='%{y:.2f} EUR/MWh<extra></extra>'))

    fig = apply_mckinsey_style(fig, title=f'Electricity Market Prices - {country} ({time_range})')
    fig.update_layout(
        xaxis_title='Time', yaxis_title='Energy Price (EUR/MWh)',
        yaxis2=dict(title='Capacity Price (EUR/MW)', overlaying='y', side='right', showgrid=False),
        hovermode='x unified', height=500,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )
    return fig

def plot_da_price_distribution_mckinsey(day_ahead_df: pd.DataFrame, country: str, bins: int = 50) -> go.Figure:
    """Plot day-ahead price distribution with McKinsey styling."""
    country_col = 'DE_LU' if country == 'DE' else country
    if country_col not in day_ahead_df.columns:
        raise ValueError(f"Country {country} not found in day-ahead data")
    prices = day_ahead_df[country_col].dropna()
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=prices, nbinsx=bins, name='Frequency', marker_color=MCKINSEY_COLORS['navy'], opacity=0.7, hovertemplate='Price: %{x:.2f} EUR/MWh<br>Count: %{y}<extra></extra>'))
    try:
        kde = stats.gaussian_kde(prices)
        x_range = np.linspace(prices.min(), prices.max(), 200)
        kde_values = kde(x_range)
        kde_scaled = kde_values * len(prices) * (prices.max() - prices.min()) / bins
        fig.add_trace(go.Scatter(x=x_range, y=kde_scaled, mode='lines', name='Density', line=dict(color=MCKINSEY_COLORS['teal'], width=2), yaxis='y2', hovertemplate='Price: %{x:.2f} EUR/MWh<extra></extra>'))
    except:
        pass
    mean_price, median_price = prices.mean(), prices.median()
    fig.add_vline(x=mean_price, line_dash="dash", line_color=MCKINSEY_COLORS['gray_dark'], annotation_text=f"Mean: {mean_price:.1f}", annotation_position="top")
    fig.add_vline(x=median_price, line_dash="dot", line_color=MCKINSEY_COLORS['gray_dark'], annotation_text=f"Median: {median_price:.1f}", annotation_position="bottom")
    fig = apply_mckinsey_style(fig, title=f'Day-Ahead Price Distribution - {country}')
    fig.update_layout(
        xaxis_title='Price (EUR/MWh)', yaxis_title='Frequency',
        yaxis2=dict(overlaying='y', side='right', showgrid=False),
        height=400, showlegend=True
    )
    return fig

def plot_da_price_distribution_multi_country_mckinsey(day_ahead_df: pd.DataFrame, countries: list = None, bins: int = 50) -> go.Figure:
    """Plot day-ahead price distribution comparison across multiple countries."""
    if countries is None:
        countries = ['DE', 'AT', 'CH', 'HU', 'CZ']
    fig = go.Figure()
    for i, country in enumerate(countries):
        country_col = 'DE_LU' if country == 'DE' else country
        if country_col not in day_ahead_df.columns:
            continue
        prices = day_ahead_df[country_col].dropna()
        color = COUNTRY_COLORS.get(country, MCKINSEY_COLORS['cat_1'])
        fig.add_trace(go.Histogram(x=prices, nbinsx=bins, name=country, marker_color=color, opacity=0.6, histnorm='probability density'))
    fig = apply_mckinsey_style(fig, title='Day-Ahead Price Distribution Comparison')
    fig.update_layout(barmode='overlay', xaxis_title='Price (EUR/MWh)', yaxis_title='Density', height=500, legend_title_text='Country')
    return fig

def plot_da_price_ridgeline_mckinsey(day_ahead_df: pd.DataFrame, countries: list = None, height_factor: float = 0.7, spacing_factor: float = 0.5) -> plt.Figure:
    """Creates a McKinsey-styled ridgeline plot for day-ahead prices."""
    if countries is None:
        countries = ['DE', 'AT', 'CH', 'HU', 'CZ']
    
    df_tidy = wide_to_tidy_day_ahead(day_ahead_df)
    df_plot = df_tidy[df_tidy['country'].isin(countries)]

    fig, axes = plt.subplots(len(countries), 1, figsize=(12, len(countries) * 1.5), sharex=True, sharey=False)
    fig.suptitle('Day-Ahead Price Distribution by Country (Ridgeline Plot)', fontsize=MCKINSEY_FONTS['title_size'], fontweight='bold', color=MCKINSEY_COLORS['navy'])

    for i, (ax, country) in enumerate(zip(axes, countries)):
        prices = df_plot[df_plot['country'] == country][PRICE_COL_MWH].dropna()
        if prices.empty:
            continue
        
        kde = stats.gaussian_kde(prices)
        x_range = np.linspace(prices.min() - 10, prices.max() + 10, 500)
        pdf = kde(x_range)
        
        color = COUNTRY_COLORS.get(country, MCKINSEY_COLORS['cat_1'])
        ax.plot(x_range, pdf, color=color, linewidth=2)
        ax.fill_between(x_range, pdf, alpha=0.5, color=color)
        
        ax.text(0.02, 0.1, country, transform=ax.transAxes, fontsize=MCKINSEY_FONTS['subtitle_size'], fontweight='bold', color=color)
        ax.set_yticks([])
        ax.spines['left'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.spines['bottom'].set_edgecolor(MCKINSEY_COLORS['gray_light'])
        ax.tick_params(axis='x', colors=MCKINSEY_COLORS['gray_dark'])

    plt.subplots_adjust(hspace=-0.5)
    axes[-1].set_xlabel('Price (EUR/MWh)', fontsize=MCKINSEY_FONTS['axis_label_size'], color=MCKINSEY_COLORS['gray_dark'])
    fig.patch.set_facecolor(MCKINSEY_COLORS['background'])
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    return fig

def plot_da_price_heatmap_mckinsey(day_ahead_df: pd.DataFrame, country: str, time_range: str = 'full') -> go.Figure:
    """Creates an hourly-by-month heatmap of day-ahead prices."""
    country_col = 'DE_LU' if country == 'DE' else country
    if country_col not in day_ahead_df.columns:
        raise ValueError(f"Country {country} not found in day-ahead data")
    
    df_filtered = _filter_by_time_range(day_ahead_df[[TIMESTAMP_COL, country_col]], time_range)
    enriched = df_filtered.assign(
        hour=lambda d: d[TIMESTAMP_COL].dt.hour,
        month=lambda d: d[TIMESTAMP_COL].dt.month,
        day_of_week=lambda d: d[TIMESTAMP_COL].dt.day_name()
    )
    pivot = enriched.pivot_table(index="hour", columns="day_of_week", values=country_col, aggfunc="mean")
    pivot = pivot[['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']]

    fig = go.Figure(data=go.Heatmap(
        z=pivot.values, x=pivot.columns, y=pivot.index,
        colorscale='Viridis', hoverongaps=False,
        hovertemplate='Day: %{x}<br>Hour: %{y}:00<br>Avg Price: %{z:.2f} EUR/MWh<extra></extra>'
    ))
    fig = apply_mckinsey_style(fig, title=f'Average Day-Ahead Price by Hour and Day of Week - {country}')
    fig.update_layout(xaxis_title='Day of Week', yaxis_title='Hour of Day', height=500)
    return fig

def plot_price_statistics_mckinsey(tables: Dict[str, pd.DataFrame], country: str) -> go.Figure:
    """Creates a bar chart of key price statistics for a given country."""
    stats = {}
    for market, df in tables.items():
        country_col = 'DE_LU' if country == 'DE' and market == 'day_ahead' else country
        if market == 'afrr_capacity' or market == 'afrr_energy':
            pos_col, neg_col = f'{country}_Pos', f'{country}_Neg'
            if pos_col in df.columns:
                stats[f'{market}_pos'] = df[pos_col].describe()
            if neg_col in df.columns:
                stats[f'{market}_neg'] = df[neg_col].describe()
        elif country_col in df.columns:
            stats[market] = df[country_col].describe()

    fig = go.Figure()
    metrics = ['mean', 'std', 'min', '25%', '50%', '75%', 'max']
    for i, (market, s) in enumerate(stats.items()):
        fig.add_trace(go.Bar(
            name=market.replace('_', ' ').title(),
            x=metrics, y=[s.get(m, 0) for m in metrics],
            marker_color=list(MCKINSEY_COLORS.values())[i % len(MCKINSEY_COLORS)]
        ))
    
    fig = apply_mckinsey_style(fig, title=f'Price Statistics Comparison - {country}')
    fig.update_layout(barmode='group', xaxis_title='Statistic', yaxis_title='Price', height=500)
    return fig
