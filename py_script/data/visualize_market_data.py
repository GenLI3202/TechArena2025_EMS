"""Market data exploration utilities for TechArena 2025 Phase I.

This module loads the official Huawei TechArena 2025 data workbook, reshapes the
Day-Ahead, FCR, and aFRR market tables into wide-format pandas DataFrames, and offers
both Plotly-based visualizations and format conversion utilities.

Data Format
-----------
By default, the module loads data in    melted_df = afrr_raw.melt(
        id_vars=[TIMESTAMP_COL],
        value_vars=country_dir_cols,
        var_name="country_direction",
        value_name=PRICE_COL_MW,
    ).dropna(subset=[PRICE_COL_MW])format:
- Day-ahead & FCR: columns [timestamp, DE_LU/DE, AT, CH, HU, CZ]  
- aFRR: columns [timestamp, DE_Pos, DE_Neg, AT_Pos, AT_Neg, ...]

Format conversion helpers are provided to convert between wide and tidy formats
as needed for different analysis tasks.

Typical usage
-------------
>>> from pathlib import Path
>>> from market_da import (
...     load_market_tables,
...     wide_to_tidy_day_ahead,
...     plot_day_ahead_distribution,
... )
>>> # Load data in wide format (default)
>>> tables = load_market_tables(Path("../SoloGen_TechArena2025_Phase1/input/TechArena2025_data.xlsx"))
>>> print(tables["day_ahead"].columns)  # ['timestamp', 'DE_LU', 'AT', 'CH', 'HU', 'CZ']
>>> 
>>> # Convert to tidy format for specific analyses
>>> tidy_da = wide_to_tidy_day_ahead(tables["day_ahead"]) 
>>> print(tidy_da.columns)  # ['timestamp', 'country', 'price_eur_mwh']
>>>
>>> # Plotting works with both formats
>>> da_fig = plot_day_ahead_distribution(tables["day_ahead"])
>>> da_fig.show()

All helpers return pandas DataFrames or Plotly Figure instances so they can be
embedded into notebooks, dashboards, or downstream reports.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DAY_AHEAD_SHEET = "Day-ahead prices"
FCR_SHEET = "FCR prices"
AFRR_SHEET = "aFRR capacity prices"

TIMESTAMP_COL = "timestamp"
COUNTRY_COL = "country"
PRICE_COL_MWH = "price_eur_mwh"  # For day-ahead (energy prices)
PRICE_COL_MW = "price_eur_mw"    # For FCR and aFRR (capacity prices)
DIRECTION_COL = "direction"

AFRR_DIRECTION_ALIASES = {
    "positive": "positive",
    "pos": "positive",
    "up": "positive",
    "+": "positive",
    "upward": "positive",
    "negative": "negative",
    "neg": "negative",
    "down": "negative",
    "-": "negative",
    "downward": "negative",
}


@dataclass(frozen=True)
class MarketTables:
    """Container aggregating tidy DataFrames for each market."""

    day_ahead: pd.DataFrame
    fcr: pd.DataFrame
    afrr: pd.DataFrame

    def as_dict(self) -> Dict[str, pd.DataFrame]:
        """Return the three tables as a dictionary."""
        return {"day_ahead": self.day_ahead, "fcr": self.fcr, "afrr": self.afrr}


# ---------------------------------------------------------------------------
# Loading helpers
# ---------------------------------------------------------------------------


def load_market_tables(workbook_path: Path, *, prefer_csv: bool = False) -> Dict[str, pd.DataFrame]:
    """Load the three market tables as tidy DataFrames.

    Parameters
    ----------
    workbook_path:
        Path to ``TechArena2025_data.xlsx`` or a directory containing CSV exports
        named ``day_ahead.csv``, ``fcr.csv``, and ``afrr.csv``.
    prefer_csv:
        If ``True`` and CSV files exist alongside the workbook, they are used as
        the source of truth. Otherwise the Excel workbook is parsed directly.

    Returns
    -------
    dict
        Keys: ``"day_ahead"``, ``"fcr"``, ``"afrr"``. Values: wide format DataFrames
        with timestamp as first column and countries/directions as separate columns.
        Day-ahead and FCR: timestamp, DE_LU, AT, CH, HU, CZ
        aFRR: timestamp, DE_Pos, DE_Neg, AT_Pos, AT_Neg, CH_Pos, CH_Neg, HU_Pos, HU_Neg, CZ_Pos, CZ_Neg
    """

    workbook_path = workbook_path.expanduser().resolve()

    if workbook_path.is_dir():
        # Interpret the input as a folder containing CSV files.
        directory = workbook_path
        day_ahead_df = _load_csv(directory / "day_ahead.csv", value_name=PRICE_COL_MWH)
        fcr_df = _load_csv(directory / "fcr.csv", value_name=PRICE_COL_MW)
        afrr_df = _load_csv(directory / "afrr.csv", value_name=PRICE_COL_MW)
    else:
        directory = workbook_path.parent
        csv_candidates = {
            "day_ahead": directory / "day_ahead.csv",
            "fcr": directory / "fcr.csv",
            "afrr": directory / "afrr.csv",
        }
        if prefer_csv and all(path.exists() for path in csv_candidates.values()):
            day_ahead_df = _load_csv(csv_candidates["day_ahead"], value_name=PRICE_COL_MWH)
            fcr_df = _load_csv(csv_candidates["fcr"], value_name=PRICE_COL_MW)
            afrr_df = _load_csv(csv_candidates["afrr"], value_name=PRICE_COL_MW)
        else:
            xl = pd.ExcelFile(workbook_path)
            day_ahead_raw = xl.parse(DAY_AHEAD_SHEET)
            fcr_raw = xl.parse(FCR_SHEET)
            afrr_raw = xl.parse(AFRR_SHEET)

            day_ahead_df = _tidy_market_frame(day_ahead_raw, value_name=PRICE_COL_MWH)
            fcr_df = _tidy_market_frame(fcr_raw, value_name=PRICE_COL_MW)
            afrr_df = _tidy_afrr_frame(afrr_raw)
            
            # Convert price columns to numeric for all tables
            for col in day_ahead_df.columns[1:]:
                day_ahead_df[col] = pd.to_numeric(day_ahead_df[col], errors='coerce')
            for col in fcr_df.columns[1:]:
                fcr_df[col] = pd.to_numeric(fcr_df[col], errors='coerce')
            for col in afrr_df.columns[1:]:
                afrr_df[col] = pd.to_numeric(afrr_df[col], errors='coerce')

    return MarketTables(day_ahead_df, fcr_df, afrr_df).as_dict()


def _load_csv(csv_path: Path, *, value_name: str) -> pd.DataFrame:
    """Load CSV exports that follow the tidy schema used in this module."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Expected CSV file not found: {csv_path}")
    df = pd.read_csv(csv_path)
    if TIMESTAMP_COL in df.columns:
        df[TIMESTAMP_COL] = pd.to_datetime(df[TIMESTAMP_COL])
    return df


def load_data(jsonl_path: str) -> list:
    """Load market data from JSONL file.
    
    Args:
        jsonl_path: Path to the JSONL file containing market data
        
    Returns:
        List of dictionaries containing market data records
    """
    import json
    
    data = []
    with open(jsonl_path, 'r') as f:
        for line in f:
            try:
                record = json.loads(line.strip())
                data.append(record)
            except json.JSONDecodeError:
                continue  # Skip malformed lines
    
    return data


def _coerce_timestamp_column(series: pd.Series) -> pd.Series:
    """Coerce heterogeneous timestamp column into pandas datetime, dropping header artifacts."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return series
    cleaned = series.astype(str).str.strip()
    cleaned = cleaned.replace({"": None, "nan": None, "NaT": None, "Timestep": None, "Timestamp": None})
    return pd.to_datetime(cleaned, errors="coerce")


def _tidy_market_frame(df: pd.DataFrame, value_name: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    # Skip the first row which contains country names, and use the original wide format
    df_clean = df.iloc[1:].copy()  # Skip header row
    
    # Set proper column names: first column is timestamp, rest are country prices
    original_ts_col = df.columns[0]
    df_clean = df_clean.rename(columns={original_ts_col: TIMESTAMP_COL})
    
    # Clean up the timestamp column
    df_clean[TIMESTAMP_COL] = pd.to_datetime(df_clean[TIMESTAMP_COL])
    
    # Get country names from the first row
    country_names = df.iloc[0, 1:].values  # Skip first column (timestamp header)
    
    # Rename columns to country names
    for i, country in enumerate(country_names, 1):
        if i < len(df.columns):
            df_clean = df_clean.rename(columns={df.columns[i]: str(country).strip()})
    
    # Keep only valid columns (timestamp + countries with actual data)  
    valid_cols = [TIMESTAMP_COL]
    for col in df_clean.columns[1:]:
        # Only check first 6 columns (timestamp + 5 countries) and skip NaN columns  
        if len(valid_cols) >= 6:  # timestamp + 5 countries max
            break
        try:
            has_data = not df_clean[col].isna().all()
            if has_data:
                valid_cols.append(col)
        except:
            continue
    
    df_clean = df_clean[valid_cols]
    
    # Remove rows with invalid timestamps and sort
    df_clean = df_clean.dropna(subset=[TIMESTAMP_COL]).sort_values(TIMESTAMP_COL).reset_index(drop=True)
    
    return df_clean


def _tidy_afrr_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    # Skip the first two rows which contain country names and pos/neg labels
    df_clean = df.iloc[2:].copy()
    
    # Set timestamp column name
    original_ts_col = df.columns[0]
    df_clean = df_clean.rename(columns={original_ts_col: TIMESTAMP_COL})
    
    # Clean up the timestamp column
    df_clean[TIMESTAMP_COL] = pd.to_datetime(df_clean[TIMESTAMP_COL])
    
    # Get country names and directions from first two rows
    countries_row = df.iloc[0, 1:].values  # Country names
    directions_row = df.iloc[1, 1:].values  # Pos/Neg labels
    
    # Create column names like "DE_Pos", "DE_Neg", "AT_Pos", etc.
    new_column_names = [TIMESTAMP_COL]
    current_country = None
    
    for i, (country, direction) in enumerate(zip(countries_row, directions_row), 1):
        if pd.notna(country) and str(country).strip():
            current_country = str(country).strip()
        
        if pd.notna(direction) and str(direction).strip() and current_country:
            direction_str = str(direction).strip()
            # Standardize direction naming
            if direction_str.lower() in ['pos', 'positive', '+']:
                direction_str = 'Pos'
            elif direction_str.lower() in ['neg', 'negative', '-']:
                direction_str = 'Neg'
            
            col_name = f"{current_country}_{direction_str}"
            new_column_names.append(col_name)
        else:
            new_column_names.append(f"Unknown_{i}")
    
    # Rename columns
    old_columns = df_clean.columns.tolist()
    rename_dict = {old_columns[i]: new_column_names[i] for i in range(min(len(old_columns), len(new_column_names)))}
    df_clean = df_clean.rename(columns=rename_dict)
    
    # Keep only valid columns (timestamp + columns with actual data)
    valid_cols = [TIMESTAMP_COL]
    for col in df_clean.columns[1:]:
        if not df_clean[col].isna().all():
            valid_cols.append(col)
    
    df_clean = df_clean[valid_cols]
    
    # Remove rows with invalid timestamps and sort
    df_clean = df_clean.dropna(subset=[TIMESTAMP_COL]).sort_values(TIMESTAMP_COL).reset_index(drop=True)
    
    return df_clean


def _split_afrr_series_labels(labels: pd.Series) -> Tuple[pd.Series, pd.Series]:
    """Split combined labels such as "Germany_positive" into components."""
    country_tokens = []
    direction_tokens = []
    for label in labels:
        parts = str(label).replace("-", "_").replace("/", "_").split("_")
        parts = [token for token in parts if token]
        if not parts:
            country_tokens.append("unknown")
            direction_tokens.append("unspecified")
            continue

        # Assume the last token encodes the direction (positive/negative).
        *country_part, direction_part = parts if len(parts) > 1 else (parts[0], "unspecified")
        direction_normalised = AFRR_DIRECTION_ALIASES.get(direction_part.lower(), "unspecified")
        country_label = " ".join(country_part).strip() or "unknown"
        country_tokens.append(country_label)
        direction_tokens.append(direction_normalised)

    return pd.Series(country_tokens), pd.Series(direction_tokens)


# ---------------------------------------------------------------------------
# Format conversion helpers
# ---------------------------------------------------------------------------


def wide_to_tidy_day_ahead(day_ahead_df: pd.DataFrame) -> pd.DataFrame:
    """Convert day-ahead DataFrame from wide format to tidy format.
    
    Parameters
    ----------
    day_ahead_df : pd.DataFrame
        Wide format DataFrame with columns: timestamp, DE_LU, AT, CH, HU, CZ
        
    Returns
    -------
    pd.DataFrame
        Tidy format DataFrame with columns: timestamp, country, price_eur_mwh
    """
    country_cols = [col for col in day_ahead_df.columns if col != TIMESTAMP_COL]
    
    tidy_df = day_ahead_df.melt(
        id_vars=[TIMESTAMP_COL],
        value_vars=country_cols,
        var_name=COUNTRY_COL,
        value_name=PRICE_COL_MWH
    ).dropna(subset=[PRICE_COL_MWH])
    
    return tidy_df.sort_values([COUNTRY_COL, TIMESTAMP_COL]).reset_index(drop=True)


def wide_to_tidy_fcr(fcr_df: pd.DataFrame) -> pd.DataFrame:
    """Convert FCR DataFrame from wide format to tidy format.
    
    Parameters
    ----------
    fcr_df : pd.DataFrame
        Wide format DataFrame with columns: timestamp, DE, AT, CH, HU, CZ
        
    Returns
    -------
    pd.DataFrame
        Tidy format DataFrame with columns: timestamp, country, price_eur_mwh
    """
    country_cols = [col for col in fcr_df.columns if col != TIMESTAMP_COL]
    
    tidy_df = fcr_df.melt(
        id_vars=[TIMESTAMP_COL],
        value_vars=country_cols,
        var_name=COUNTRY_COL,
        value_name=PRICE_COL_MW
    ).dropna(subset=[PRICE_COL_MW])
    
    return tidy_df.sort_values([COUNTRY_COL, TIMESTAMP_COL]).reset_index(drop=True)


def wide_to_tidy_afrr(afrr_df: pd.DataFrame) -> pd.DataFrame:
    """Convert aFRR DataFrame from wide format to tidy format.
    
    Parameters
    ----------
    afrr_df : pd.DataFrame
        Wide format DataFrame with columns: timestamp, DE_Pos, DE_Neg, AT_Pos, AT_Neg, etc.
        
    Returns
    -------
    pd.DataFrame
        Tidy format DataFrame with columns: timestamp, country, direction, price_eur_mwh
    """
    country_dir_cols = [col for col in afrr_df.columns if col != TIMESTAMP_COL]
    
    # Melt to long format
    melted_df = afrr_df.melt(
        id_vars=[TIMESTAMP_COL],
        value_vars=country_dir_cols,
        var_name="country_direction",
        value_name=PRICE_COL_MW
    ).dropna(subset=[PRICE_COL_MW])
    
    # Split country_direction column into separate country and direction columns
    melted_df[COUNTRY_COL] = melted_df["country_direction"].str.rsplit("_", n=1).str[0]
    melted_df[DIRECTION_COL] = melted_df["country_direction"].str.rsplit("_", n=1).str[1].str.lower()
    
    # Standardize direction labels
    melted_df[DIRECTION_COL] = melted_df[DIRECTION_COL].map({
        'pos': 'positive',
        'neg': 'negative'
    }).fillna(melted_df[DIRECTION_COL])
    
    return (
        melted_df.drop(columns=["country_direction"])
        .sort_values([COUNTRY_COL, DIRECTION_COL, TIMESTAMP_COL])
        .reset_index(drop=True)
    )


def convert_tables_to_tidy(tables: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """Convert all market tables from wide format to tidy format.
    
    Parameters
    ----------
    tables : dict
        Dictionary with keys 'day_ahead', 'fcr', 'afrr' and wide format DataFrames as values
        
    Returns
    -------
    dict
        Dictionary with the same keys but tidy format DataFrames as values
    """
    tidy_tables = {}
    
    if 'day_ahead' in tables:
        tidy_tables['day_ahead'] = wide_to_tidy_day_ahead(tables['day_ahead'])
    
    if 'fcr' in tables:
        tidy_tables['fcr'] = wide_to_tidy_fcr(tables['fcr'])
        
    if 'afrr' in tables:
        tidy_tables['afrr'] = wide_to_tidy_afrr(tables['afrr'])
    
    return tidy_tables


# The converters from tidy to wide are just written by Claude Sonnet 4, not so useful 
## as we already loaded the data in wide format.

def tidy_to_wide_day_ahead(day_ahead_tidy_df: pd.DataFrame) -> pd.DataFrame:
    """Convert day-ahead DataFrame from tidy format back to wide format.
    
    Parameters
    ----------
    day_ahead_tidy_df : pd.DataFrame
        Tidy format DataFrame with columns: timestamp, country, price_eur_mwh
        
    Returns
    -------
    pd.DataFrame
        Wide format DataFrame with countries as separate columns
    """
    return day_ahead_tidy_df.pivot(
        index=TIMESTAMP_COL, 
        columns=COUNTRY_COL, 
        values=PRICE_COL_MWH
    ).reset_index()


def tidy_to_wide_fcr(fcr_tidy_df: pd.DataFrame) -> pd.DataFrame:
    """Convert FCR DataFrame from tidy format back to wide format.
    
    Parameters
    ----------
    fcr_tidy_df : pd.DataFrame
        Tidy format DataFrame with columns: timestamp, country, price_eur_mwh
        
    Returns
    -------
    pd.DataFrame
        Wide format DataFrame with countries as separate columns
    """
    return fcr_tidy_df.pivot(
        index=TIMESTAMP_COL, 
        columns=COUNTRY_COL, 
        values=PRICE_COL_MW
    ).reset_index()


def tidy_to_wide_afrr(afrr_tidy_df: pd.DataFrame) -> pd.DataFrame:
    """Convert aFRR DataFrame from tidy format back to wide format.
    
    Parameters
    ----------
    afrr_tidy_df : pd.DataFrame
        Tidy format DataFrame with columns: timestamp, country, direction, price_eur_mwh
        
    Returns
    -------
    pd.DataFrame
        Wide format DataFrame with country_direction as separate columns
    """
    # Create combined country_direction column for pivoting
    afrr_tidy_df = afrr_tidy_df.copy()
    direction_map = {'positive': 'Pos', 'negative': 'Neg'}
    afrr_tidy_df['country_direction'] = (
        afrr_tidy_df[COUNTRY_COL] + '_' + 
        afrr_tidy_df[DIRECTION_COL].map(direction_map).fillna(afrr_tidy_df[DIRECTION_COL])
    )
    
    return afrr_tidy_df.pivot(
        index=TIMESTAMP_COL, 
        columns='country_direction', 
        values=PRICE_COL_MW
    ).reset_index()



# ---------------------------------------------------------------------------
# Analytical summaries
# ---------------------------------------------------------------------------


def summarize_day_ahead(day_ahead_df: pd.DataFrame) -> pd.DataFrame:
    """
    Summarize day-ahead market data volatility by country.
    """
    summary = day_ahead_df.groupby("country").agg(
        mean_price=("price_eur_mwh", "mean"),
        median_price=("price_eur_mwh", "median"),
        std_dev_price=("price_eur_mwh", "std"),
        # var_price=("price_eur_mwh", "var"),
        min_price=("price_eur_mwh", "min"),
        max_price=("price_eur_mwh", "max"),
        price_range=("price_eur_mwh", lambda x: x.max() - x.min()),
    ).reset_index().sort_values("country")
    return summary

def summarize_fcr(fcr_df: pd.DataFrame) -> pd.DataFrame:
    """Compute average FCR price per country."""
    # Get country columns (all except timestamp)
    summary = fcr_df.groupby("country").agg(
        mean_price_eur_mw=("price_eur_mwh", "mean"),
        median_price_eur_mw=("price_eur_mwh", "median"),
        std_dev_price_eur_mw=("price_eur_mwh", "std"),
        min_price_eur_mw=("price_eur_mwh", "min"),
        max_price_eur_mw=("price_eur_mwh", "max"),
        price_range_eur_mw=("price_eur_mwh", lambda x: x.max() - x.min()),
    ).reset_index().sort_values("country")
    return summary

def summarize_afrr(afrr_df: pd.DataFrame) -> pd.DataFrame:
    """Summarize aFRR prices by country and direction."""
    summary = afrr_df.groupby(["country", "direction"]).agg(
        mean_price_eur_mw=("price_eur_mwh", "mean"),
        median_price_eur_mw=("price_eur_mwh", "median"),
        std_dev_price_eur_mw=("price_eur_mwh", "std"),
        min_price_eur_mw=("price_eur_mwh", "min"),
        max_price_eur_mw=("price_eur_mwh", "max"),
        price_range_eur_mw=("price_eur_mwh", lambda x: x.max() - x.min()),
    ).reset_index().sort_values(["country", "direction"])
    return summary


# ---------------------------------------------------------------------------
# Plotting helpers
# ---------------------------------------------------------------------------

def _is_tidy_format(df: pd.DataFrame, expected_columns: list) -> bool:
    """Check if DataFrame is in tidy format based on expected column names."""
    return all(col in df.columns for col in expected_columns)

def plot_day_ahead_distribution(day_ahead_df: pd.DataFrame) -> go.Figure:
    """Box plot comparing Day-Ahead price distributions across countries."""
    
    # Check if data is in tidy format
    if not _is_tidy_format(day_ahead_df, [TIMESTAMP_COL, COUNTRY_COL, PRICE_COL_MWH]):
        # Data is in wide format, convert to long format for plotting using `tidy_to_wide_day_ahead`
        melted = wide_to_tidy_day_ahead(day_ahead_df.copy())
    else: # Data is already in tidy format 
        melted = day_ahead_df.copy()
    melted = melted.rename(columns={PRICE_COL_MWH: 'price', COUNTRY_COL: 'country'})
    
    # Drop NaN values
    melted = melted.dropna(subset=['price'])
    
    # Ensure price column is numeric
    melted['price'] = pd.to_numeric(melted['price'], errors='coerce')
    melted = melted.dropna(subset=['price'])
    
    if melted.empty:
        # Return empty figure if no valid data
        fig = go.Figure()
        fig.add_annotation(
            text="No valid price data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        fig.update_layout(title="Day-Ahead Price Distribution by Country")
        return fig
    
    fig = px.box(
        melted,
        x='country',
        y='price',
        color='country',
        title="Day-Ahead Price Distribution by Country",
        points="suspectedoutliers",
    )
    fig.update_layout(showlegend=False, xaxis_title="Country", yaxis_title="Price [EUR/MWh]")
    return fig

def plot_day_ahead_trend(day_ahead_df: pd.DataFrame, *, countries: Optional[Iterable[str]] = None) -> go.Figure:
    """Line plot of Day-Ahead prices across 2024, optionally filtered by country."""
    
    # Check if data is in tidy format
    if _is_tidy_format(day_ahead_df, [TIMESTAMP_COL, COUNTRY_COL, PRICE_COL_MWH]):
        # Data is already in tidy format
        melted = day_ahead_df.copy()
        melted = melted.rename(columns={PRICE_COL_MWH: 'price', COUNTRY_COL: 'country'})
        
        # Filter countries if specified
        if countries:
            melted = melted[melted['country'].isin(countries)]
    else:
        # Data is in wide format
        all_country_cols = [col for col in day_ahead_df.columns if col != TIMESTAMP_COL]
        
        if countries:
            # Filter to specified countries
            available_countries = [col for col in all_country_cols if col in countries]
        else:
            available_countries = all_country_cols
        
        # Convert wide format to long format for plotting
        melted = day_ahead_df.melt(
            id_vars=[TIMESTAMP_COL],
            value_vars=available_countries,
            var_name='country',
            value_name='price'
        )
    
    # Clean data
    melted = melted.dropna(subset=['price'])
    melted['price'] = pd.to_numeric(melted['price'], errors='coerce')
    melted = melted.dropna(subset=['price'])
    
    if melted.empty:
        # Return empty figure if no valid data
        fig = go.Figure()
        fig.add_annotation(
            text="No valid price data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        fig.update_layout(title="Day-Ahead Price Trend (2024)")
        return fig
    
    fig = px.line(
        melted,
        x=TIMESTAMP_COL,
        y='price',
        color='country',
        title="Day-Ahead Price Trend (2024)",
    )
    fig.update_layout(xaxis_title="Timestamp", yaxis_title="Price [EUR/MWh]")
    return fig

def plot_fcr_distribution(fcr_df: pd.DataFrame) -> go.Figure:
    """Box plot comparing FCR price distributions across countries."""
    
    # Check if data is in tidy format
    if _is_tidy_format(fcr_df, [TIMESTAMP_COL, COUNTRY_COL, PRICE_COL_MW]):
        # Data is already in tidy format
        melted = fcr_df.copy()
        melted = melted.rename(columns={PRICE_COL_MW: 'price', COUNTRY_COL: 'country'})
    else:
        # Data is in wide format, convert to long format for plotting
        country_cols = [col for col in fcr_df.columns if col != TIMESTAMP_COL]
        melted = fcr_df.melt(
            id_vars=[TIMESTAMP_COL],
            value_vars=country_cols,
            var_name='country',
            value_name='price'
        )
    
    # Clean data
    melted = melted.dropna(subset=['price'])
    melted['price'] = pd.to_numeric(melted['price'], errors='coerce')
    melted = melted.dropna(subset=['price'])
    
    if melted.empty:
        # Return empty figure if no valid data
        fig = go.Figure()
        fig.add_annotation(
            text="No valid price data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        fig.update_layout(title="FCR Price Distribution by Country")
        return fig
    
    fig = px.box(
        melted,
        x='country',
        y='price',
        color='country',
        title="FCR Price Distribution by Country",
        points="suspectedoutliers",
    )
    fig.update_layout(showlegend=False, xaxis_title="Country", yaxis_title="Price [EUR/MW]")
    return fig

def plot_afrr_distribution(afrr_df: pd.DataFrame) -> go.Figure:
    """Box plots for aFRR positive and negative capacity prices by country."""
    
    # Check if data is in tidy format
    if _is_tidy_format(afrr_df, [TIMESTAMP_COL, COUNTRY_COL, DIRECTION_COL, PRICE_COL_MW]):
        # Data is already in tidy format
        melted = afrr_df.copy()
        
        # Standardize direction values using aliases
        melted[DIRECTION_COL] = melted[DIRECTION_COL].str.lower().map(AFRR_DIRECTION_ALIASES).fillna(melted[DIRECTION_COL])
        
    else:
        # Data is in wide format, convert to long format for plotting
        country_dir_cols = [col for col in afrr_df.columns if col != TIMESTAMP_COL]
        
        melted_data = []
        for col in country_dir_cols:
            if '_' in col:
                country, direction = col.rsplit('_', 1)
                # Standardize direction using aliases
                direction = AFRR_DIRECTION_ALIASES.get(direction.lower(), direction.lower())
            else:
                country = col
                direction = 'unknown'
            
            col_data = afrr_df[[TIMESTAMP_COL, col]].dropna()
            for _, row in col_data.iterrows():
                melted_data.append({
                    TIMESTAMP_COL: row[TIMESTAMP_COL],
                    COUNTRY_COL: country,
                    DIRECTION_COL: direction,
                    PRICE_COL_MW: row[col]
                })
        
        melted = pd.DataFrame(melted_data)
    
    if melted.empty:
        # Return empty figure if no valid data
        fig = go.Figure()
        fig.add_annotation(
            text="No valid price data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        fig.update_layout(title="aFRR Capacity Price Distribution")
        return fig
    
    # Clean data
    melted = melted.dropna(subset=[PRICE_COL_MW])
    melted[PRICE_COL_MW] = pd.to_numeric(melted[PRICE_COL_MW], errors='coerce')
    melted = melted.dropna(subset=[PRICE_COL_MW])
    
    # Filter out unknown directions for cleaner visualization
    melted = melted[melted[DIRECTION_COL].isin(['positive', 'negative'])]
    
    if melted.empty:
        # Return empty figure if no valid data after cleaning
        fig = go.Figure()
        fig.add_annotation(
            text="No valid price data available after cleaning",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        fig.update_layout(title="aFRR Capacity Price Distribution")
        return fig
    
    fig = px.box(
        melted,
        x=COUNTRY_COL,
        y=PRICE_COL_MW,
        color=DIRECTION_COL,
        facet_col=DIRECTION_COL,
        facet_col_spacing=0.07,
        category_orders={DIRECTION_COL: ['positive', 'negative']},
        title="aFRR Capacity Price Distribution (Positive vs Negative)",
    )
    fig.update_layout(
        xaxis_title="Country", 
        yaxis_title="Price [EUR/MW]", 
        showlegend=False
    )
    fig.update_xaxes(tickangle=45)  # Rotate country labels for better readability
    return fig

def plot_day_ahead_heatmap(day_ahead_df: pd.DataFrame, country: str) -> go.Figure:
    """Hourly-by-month heatmap to reveal charging/discharging windows for a country."""
    
    # Check if data is in tidy format
    if _is_tidy_format(day_ahead_df, [TIMESTAMP_COL, COUNTRY_COL, PRICE_COL_MWH]):
        # Data is in tidy format
        if country not in day_ahead_df[COUNTRY_COL].unique():
            raise ValueError(f"No Day-Ahead data available for country '{country}'.")
        
        # Filter for the specific country
        country_df = day_ahead_df[day_ahead_df[COUNTRY_COL] == country].copy()
        if country_df.empty:
            raise ValueError(f"No Day-Ahead data available for country '{country}'.")
        
        # Use the price column for values
        price_column = PRICE_COL_MWH
        
    else:
        # Data is in wide format (original logic)
        if country not in day_ahead_df.columns:
            raise ValueError(f"No Day-Ahead data available for country '{country}'.")
        
        # Create a subset with just timestamp and the selected country
        country_df = day_ahead_df[[TIMESTAMP_COL, country]].dropna()
        if country_df.empty:
            raise ValueError(f"No Day-Ahead data available for country '{country}'.")
        
        # Use the country column for values
        price_column = country

    enriched = country_df.assign(
        hour=lambda d: d[TIMESTAMP_COL].dt.hour,
        month=lambda d: d[TIMESTAMP_COL].dt.month,
    )
    
    pivot = (
        enriched.pivot_table(
            index="month",
            columns="hour",
            values=price_column,
            aggfunc="mean",
        )
        .sort_index()
        .sort_index(axis=1)
    )

    fig = px.imshow(
        pivot,
        aspect="auto",
        color_continuous_scale="Turbo",
        labels=dict(x="Hour of Day", y="Month", color="Avg Price [EUR/MWh]"),
        title=f"Hourly vs Monthly Day-Ahead Prices · {country}",
    )
    return fig


# ---------------------------------------------------------------------------
# Solution Analysis and Visualization Functions
# ---------------------------------------------------------------------------

def plot_battery_operation_schedule(solution_data: Dict, country_data: pd.DataFrame, 
                                   title_suffix: str = "") -> go.Figure:
    """Plot battery charge/discharge schedule with market prices.
    
    Parameters
    ----------
    solution_data : dict
        Solution dictionary containing charge ('p_ch'), discharge ('p_dis'), soc ('e_soc') data
    country_data : pd.DataFrame
        Market data with datetime, price_day_ahead, price_fcr, price_afrr_pos columns
    title_suffix : str
        Additional text for plot title
        
    Returns
    -------
    go.Figure
        Plotly figure with battery operation schedule
    """
    # Check if we have the required data
    required_vars = ['p_ch', 'p_dis', 'e_soc']
    for var in required_vars:
        if var not in solution_data:
            raise ValueError(f"Solution data must contain '{var}' key")
    
    # Extract time series data
    time_indices = sorted(solution_data['p_ch'].keys())
    
    charge_values = [solution_data['p_ch'][t] for t in time_indices]
    discharge_values = [solution_data['p_dis'][t] for t in time_indices]
    soc_values = [solution_data['e_soc'][t] for t in time_indices]
    
    # Get corresponding datetime values from country_data
    if 'timestamp' in country_data.columns:
        datetime_values = country_data['timestamp'].iloc[:len(time_indices)].tolist()
    else:
        # Generate datetime index if not available
        datetime_values = pd.date_range(start='2024-01-01', periods=len(time_indices), freq='15min').tolist()
    
    day_ahead_prices = country_data['price_day_ahead'].iloc[:len(time_indices)].tolist()
    
    # Create figure with secondary y-axes
    fig = go.Figure()
    
    # Add battery charge (positive values)
    fig.add_trace(go.Scatter(
        x=datetime_values,
        y=charge_values,
        mode='lines',
        name='Charge (kW)',
        line=dict(color='green', width=2),
        fill='tozeroy',
        fillcolor='rgba(0,255,0,0.3)'
    ))
    
    # Add battery discharge (negative for visualization)
    fig.add_trace(go.Scatter(
        x=datetime_values,
        y=[-d for d in discharge_values],  # Negative for discharge
        mode='lines',
        name='Discharge (kW)',
        line=dict(color='red', width=2),
        fill='tozeroy',
        fillcolor='rgba(255,0,0,0.3)'
    ))
    
    # Add SoC on secondary y-axis
    fig.add_trace(go.Scatter(
        x=datetime_values,
        y=soc_values,
        mode='lines',
        name='State of Charge (kWh)',
        line=dict(color='blue', width=2, dash='dash'),
        yaxis='y2'
    ))
    
    # Add day-ahead prices on tertiary y-axis
    fig.add_trace(go.Scatter(
        x=datetime_values,
        y=day_ahead_prices,
        mode='lines',
        name='Day-Ahead Price (€/MWh)',
        line=dict(color='orange', width=1),
        yaxis='y3',
        opacity=0.7
    ))
    
    # Update layout
    fig.update_layout(
        title=f'Battery Operation Schedule {title_suffix}',
        xaxis_title='Time',
        yaxis=dict(
            title='Power (kW)',
            side='left'
        ),
        yaxis2=dict(
            title='SoC (kWh)',
            side='right',
            overlaying='y',
            showgrid=False
        ),
        yaxis3=dict(
            title='Price (€/MWh)',
            side='right',
            overlaying='y',
            position=0.95,
            showgrid=False
        ),
        hovermode='x unified',
        width=1000,
        height=500
    )
    
    return fig


def plot_market_price_bid_comparison(solution_data: Dict, country_data: pd.DataFrame, 
                                    market_type: str = 'day_ahead', 
                                    title_suffix: str = "") -> go.Figure:
    """Plot market prices vs battery bids for arbitrage analysis.
    
    Parameters
    ----------
    solution_data : dict
        Solution dictionary containing charge ('p_ch'), discharge ('p_dis') data
    country_data : pd.DataFrame
        Market data with price information
    market_type : str
        Type of market ('day_ahead', 'fcr', 'afrr')
    title_suffix : str
        Additional text for plot title
        
    Returns
    -------
    go.Figure
        Plotly figure comparing market prices and bids
    """
    # Check required variables
    required_vars = ['p_ch', 'p_dis']
    for var in required_vars:
        if var not in solution_data:
            raise ValueError(f"Solution data must contain '{var}' key")
    
    # Determine price column
    price_col_map = {
        'day_ahead': 'price_day_ahead',
        'fcr': 'price_fcr', 
        'afrr': 'price_afrr_pos'  # Use positive aFRR as representative
    }
    
    if market_type not in price_col_map:
        raise ValueError(f"Market type must be one of {list(price_col_map.keys())}")
    
    price_col = price_col_map[market_type]
    
    # Extract time series data
    time_indices = sorted(solution_data['p_ch'].keys())
    
    # Get datetime values
    if 'timestamp' in country_data.columns:
        datetime_values = country_data['timestamp'].iloc[:len(time_indices)].tolist()
    else:
        datetime_values = pd.date_range(start='2024-01-01', periods=len(time_indices), freq='15min').tolist()
    
    market_prices = country_data[price_col].iloc[:len(time_indices)].tolist()
    
    # Calculate net power (charge - discharge)
    charge_vals = [solution_data['p_ch'][t] for t in time_indices]
    discharge_vals = [solution_data['p_dis'][t] for t in time_indices]
    net_power = [c - d for c, d in zip(charge_vals, discharge_vals)]
    
    fig = go.Figure()
    
    # Add market prices
    fig.add_trace(go.Scatter(
        x=datetime_values,
        y=market_prices,
        mode='lines',
        name=f'{market_type.replace("_", " ").title()} Price (€/MWh)',
        line=dict(color='blue', width=2)
    ))
    
    # Add battery actions
    fig.add_trace(go.Scatter(
        x=datetime_values,
        y=charge_vals,
        mode='lines',
        name='Battery Charging (kW)',
        line=dict(color='green', width=1.5, dash='dot'),
        yaxis='y2'
    ))
    
    fig.add_trace(go.Scatter(
        x=datetime_values,
        y=discharge_vals,
        mode='lines',
        name='Battery Discharging (kW)',
        line=dict(color='red', width=1.5, dash='dot'),
        yaxis='y2'
    ))
    
    fig.add_trace(go.Scatter(
        x=datetime_values,
        y=net_power,
        mode='lines',
        name='Net Power (kW)',
        line=dict(color='purple', width=1, dash='dash'),
        yaxis='y2'
    ))
    
    # Update layout
    fig.update_layout(
        title=f'{market_type.replace("_", " ").title()} Market: Price vs Battery Actions {title_suffix}',
        xaxis_title='Time',
        yaxis=dict(
            title='Market Price (€/MWh)',
            side='left'
        ),
        yaxis2=dict(
            title='Battery Power (kW)',
            side='right',
            overlaying='y'
        ),
        hovermode='x unified',
        width=1000,
        height=500
    )
    
    return fig


def plot_arbitrage_opportunities(solution_data: Dict, country_data: pd.DataFrame,
                                title_suffix: str = "") -> go.Figure:
    """Plot arbitrage opportunities highlighting profitable periods.
    
    Parameters
    ----------
    solution_data : dict
        Solution dictionary with charge ('p_ch'), discharge ('p_dis') data
    country_data : pd.DataFrame
        Market data with price information
    title_suffix : str
        Additional text for plot title
        
    Returns
    -------
    go.Figure
        Plotly figure showing arbitrage analysis
    """
    # Check required variables
    required_vars = ['p_ch', 'p_dis']
    for var in required_vars:
        if var not in solution_data:
            raise ValueError(f"Solution data must contain '{var}' key")
    
    # Extract time series
    time_indices = sorted(solution_data['p_ch'].keys())
    
    # Get datetime values
    if 'timestamp' in country_data.columns:
        datetime_values = country_data['timestamp'].iloc[:len(time_indices)].tolist()
    else:
        datetime_values = pd.date_range(start='2024-01-01', periods=len(time_indices), freq='15min').tolist()
    
    day_ahead_prices = country_data['price_day_ahead'].iloc[:len(time_indices)].tolist()
    
    charge_values = [solution_data['p_ch'][t] for t in time_indices]
    discharge_values = [solution_data['p_dis'][t] for t in time_indices]
    
    # Calculate arbitrage indicators
    charge_periods = [i for i, c in enumerate(charge_values) if c > 1e-6]
    discharge_periods = [i for i, d in enumerate(discharge_values) if d > 1e-6]
    
    # Calculate price differences for arbitrage analysis
    price_rolling_mean = pd.Series(day_ahead_prices).rolling(window=4, center=True).mean()
    price_deviations = [p - pm if pd.notna(pm) else 0 for p, pm in zip(day_ahead_prices, price_rolling_mean)]
    
    fig = go.Figure()
    
    # Add price line
    fig.add_trace(go.Scatter(
        x=datetime_values,
        y=day_ahead_prices,
        mode='lines',
        name='Day-Ahead Price (€/MWh)',
        line=dict(color='blue', width=2)
    ))
    
    # Add rolling mean
    fig.add_trace(go.Scatter(
        x=datetime_values,
        y=price_rolling_mean.tolist(),
        mode='lines',
        name='Price Moving Average',
        line=dict(color='gray', width=1, dash='dash'),
        opacity=0.7
    ))
    
    # Highlight charging periods (low prices)
    if charge_periods:
        charge_times = [datetime_values[i] for i in charge_periods]
        charge_prices = [day_ahead_prices[i] for i in charge_periods]
        fig.add_trace(go.Scatter(
            x=charge_times,
            y=charge_prices,
            mode='markers',
            name='Battery Charging (Buy)',
            marker=dict(color='green', size=8, symbol='circle')
        ))
    
    # Highlight discharging periods (high prices)
    if discharge_periods:
        discharge_times = [datetime_values[i] for i in discharge_periods]
        discharge_prices = [day_ahead_prices[i] for i in discharge_periods]
        fig.add_trace(go.Scatter(
            x=discharge_times,
            y=discharge_prices,
            mode='markers',
            name='Battery Discharging (Sell)',
            marker=dict(color='red', size=8, symbol='triangle-up')
        ))
    
    # Add price deviation as background color
    fig.add_trace(go.Scatter(
        x=datetime_values,
        y=price_deviations,
        mode='lines',
        name='Price Deviation from Average',
        line=dict(color='orange', width=1),
        yaxis='y2',
        opacity=0.5
    ))
    
    # Update layout
    fig.update_layout(
        title=f'Arbitrage Opportunities Analysis {title_suffix}',
        xaxis_title='Time',
        yaxis=dict(
            title='Price (€/MWh)',
            side='left'
        ),
        yaxis2=dict(
            title='Price Deviation (€/MWh)',
            side='right',
            overlaying='y',
            showgrid=False
        ),
        hovermode='x unified',
        width=1000,
        height=500
    )
    
    return fig


def plot_revenue_breakdown(solution_data: Dict, country_data: pd.DataFrame,
                          title_suffix: str = "") -> go.Figure:
    """Plot revenue breakdown by market and time period.
    
    Parameters
    ----------
    solution_data : dict
        Solution dictionary with charge ('p_ch'), discharge ('p_dis') data
    country_data : pd.DataFrame
        Market data for revenue calculation
    title_suffix : str
        Additional text for plot title
        
    Returns
    -------
    go.Figure
        Plotly figure showing revenue breakdown
    """
    # Check required variables
    required_vars = ['p_ch', 'p_dis']
    for var in required_vars:
        if var not in solution_data:
            raise ValueError(f"Solution data must contain '{var}' key")
    
    # Calculate revenue streams
    time_indices = sorted(solution_data['p_ch'].keys())
    
    # Get datetime values
    if 'timestamp' in country_data.columns:
        datetime_values = country_data['timestamp'].iloc[:len(time_indices)].tolist()
    else:
        datetime_values = pd.date_range(start='2024-01-01', periods=len(time_indices), freq='15min').tolist()
    
    # Day-ahead revenue calculation
    charge_values = [solution_data['p_ch'][t] for t in time_indices]
    discharge_values = [solution_data['p_dis'][t] for t in time_indices]
    da_prices = country_data['price_day_ahead'].iloc[:len(time_indices)].tolist()
    
    # Calculate instantaneous revenue (simplified)
    da_revenue = []
    for i, (c, d, price) in enumerate(zip(charge_values, discharge_values, da_prices)):
        # Revenue = discharge * price - charge * price (simplified, no efficiency loss here)
        instant_revenue = (d - c) * price * 0.25  # 0.25 for 15-min to 1-hour conversion
        da_revenue.append(instant_revenue)
    
    # Cumulative revenue
    cumulative_revenue = pd.Series(da_revenue).cumsum().tolist()
    
    # Daily aggregation
    df_temp = pd.DataFrame({
        'datetime': datetime_values,
        'revenue': da_revenue
    })
    df_temp['date'] = pd.to_datetime(df_temp['datetime']).dt.date
    daily_revenue = df_temp.groupby('date')['revenue'].sum().reset_index()
    
    # Create subplots
    fig = go.Figure()
    
    # Instantaneous revenue
    fig.add_trace(go.Scatter(
        x=datetime_values,
        y=da_revenue,
        mode='lines',
        name='Instantaneous Revenue (€/15min)',
        line=dict(color='green', width=1),
        opacity=0.7
    ))
    
    # Cumulative revenue
    fig.add_trace(go.Scatter(
        x=datetime_values,
        y=cumulative_revenue,
        mode='lines',
        name='Cumulative Revenue (€)',
        line=dict(color='blue', width=2),
        yaxis='y2'
    ))
    
    # Update layout
    fig.update_layout(
        title=f'Revenue Analysis {title_suffix}',
        xaxis_title='Time',
        yaxis=dict(
            title='Instantaneous Revenue (€/15min)',
            side='left'
        ),
        yaxis2=dict(
            title='Cumulative Revenue (€)',
            side='right',
            overlaying='y'
        ),
        hovermode='x unified',
        width=1000,
        height=500
    )
    
    return fig


def plot_battery_efficiency_analysis(solution_data: Dict, country_data: pd.DataFrame,
                                    title_suffix: str = "") -> go.Figure:
    """Plot battery efficiency and cycling analysis.
    
    Parameters
    ----------
    solution_data : dict
        Solution dictionary with charge ('p_ch'), discharge ('p_dis'), soc ('e_soc') data
    country_data : pd.DataFrame
        Market data
    title_suffix : str
        Additional text for plot title
        
    Returns
    -------
    go.Figure
        Plotly figure showing efficiency analysis
    """
    # Check required variables
    required_vars = ['p_ch', 'p_dis', 'e_soc']
    for var in required_vars:
        if var not in solution_data:
            raise ValueError(f"Solution data must contain '{var}' key")
    
    # Extract time series
    time_indices = sorted(solution_data['p_ch'].keys())
    
    # Get datetime values
    if 'timestamp' in country_data.columns:
        datetime_values = country_data['timestamp'].iloc[:len(time_indices)].tolist()
    else:
        datetime_values = pd.date_range(start='2024-01-01', periods=len(time_indices), freq='15min').tolist()
    
    charge_values = [solution_data['p_ch'][t] for t in time_indices]
    discharge_values = [solution_data['p_dis'][t] for t in time_indices]
    soc_values = [solution_data['e_soc'][t] for t in time_indices]
    
    # Calculate efficiency metrics
    total_charge = sum(charge_values) * 0.25  # Convert to MWh
    total_discharge = sum(discharge_values) * 0.25  # Convert to MWh
    round_trip_efficiency = total_discharge / total_charge if total_charge > 0 else 0
    
    # Calculate SoC utilization
    soc_range = max(soc_values) - min(soc_values)
    soc_utilization = soc_range / max(soc_values) if max(soc_values) > 0 else 0
    
    # Calculate cycling frequency (simplified)
    soc_diff = [abs(soc_values[i] - soc_values[i-1]) for i in range(1, len(soc_values))]
    avg_soc_change = sum(soc_diff) / len(soc_diff) if soc_diff else 0
    
    fig = go.Figure()
    
    # SoC profile
    fig.add_trace(go.Scatter(
        x=datetime_values,
        y=soc_values,
        mode='lines',
        name='State of Charge (MWh)',
        line=dict(color='blue', width=2)
    ))
    
    # Add charge/discharge indicators
    charge_mask = [c > 1e-6 for c in charge_values]
    discharge_mask = [d > 1e-6 for d in discharge_values]
    
    # Charging periods
    if any(charge_mask):
        charge_times = [datetime_values[i] for i, mask in enumerate(charge_mask) if mask]
        charge_soc = [soc_values[i] for i, mask in enumerate(charge_mask) if mask]
        fig.add_trace(go.Scatter(
            x=charge_times,
            y=charge_soc,
            mode='markers',
            name='Charging Periods',
            marker=dict(color='green', size=4, symbol='circle')
        ))
    
    # Discharging periods
    if any(discharge_mask):
        discharge_times = [datetime_values[i] for i, mask in enumerate(discharge_mask) if mask]
        discharge_soc = [soc_values[i] for i, mask in enumerate(discharge_mask) if mask]
        fig.add_trace(go.Scatter(
            x=discharge_times,
            y=discharge_soc,
            mode='markers',
            name='Discharging Periods',
            marker=dict(color='red', size=4, symbol='triangle-up')
        ))
    
    # Add efficiency metrics as annotations
    fig.add_annotation(
        x=0.02, y=0.98,
        xref="paper", yref="paper",
        text=f"Round-trip Efficiency: {round_trip_efficiency:.2%}<br>"
             f"SoC Utilization: {soc_utilization:.2%}<br>"
             f"Avg SoC Change: {avg_soc_change:.2f} MWh",
        showarrow=False,
        bgcolor="white",
        bordercolor="black",
        borderwidth=1
    )
    
    # Update layout
    fig.update_layout(
        title=f'Battery Efficiency Analysis {title_suffix}',
        xaxis_title='Time',
        yaxis_title='State of Charge (MWh)',
        hovermode='x unified',
        width=1000,
        height=500
    )
    
    return fig


# ---------------------------------------------------------------------------
# Convenience utilities
# ---------------------------------------------------------------------------


def ensure_csv_exports(tables: Dict[str, pd.DataFrame], directory: Path) -> None:
    """Persist tidy tables to CSV for faster reloads during experimentation."""
    directory.mkdir(parents=True, exist_ok=True)
    for key, df in tables.items():
        df.to_csv(directory / f"{key}.csv", index=False)


# ===========================================================================
# PHASE 2 EXTENSIONS
# ===========================================================================

# Phase 2 Constants
AFRR_ENERGY_SHEET = "aFRR energy prices"

# Validation Constants
PRICE_BOUNDS = {
    'day_ahead': (-500, 2000),    # EUR/MWh (allow extreme scarcity prices)
    'fcr': (0, 10000),             # EUR/MW (capacity always non-negative)
    'afrr_capacity': (0, 10000),   # EUR/MW
    'afrr_energy': (-500, 2000)    # EUR/MWh (allow extreme scarcity prices)
}
ZERO_THRESHOLD_PCT = 95  # Flag if >95% zeros

def convert_afrr_energy_zero_to_nan(df: pd.DataFrame) -> pd.DataFrame:
    """
    Preprocesses market data to handle non-activated aFRR energy markets.

    When aFRR energy prices are 0, it signifies not the prices, but that "the market was NOT activated".
    This function replaces these zero prices with NaN to prevent the optimizer
    from incorrectly treating them as free energy.

    Args:
        df: A DataFrame containing market data with columns
            'price_afrr_energy_pos' and 'price_afrr_energy_neg'.

    Returns:
        The DataFrame with zero aFRR energy prices replaced by np.nan.
    """
    df_processed = df.copy()
    
    # Replace 0 with NaN for aFRR energy prices
    if 'price_afrr_energy_pos' in df_processed.columns:
        df_processed['price_afrr_energy_pos'] = df_processed['price_afrr_energy_pos'].replace(0, np.nan)
    
    if 'price_afrr_energy_neg' in df_processed.columns:
        df_processed['price_afrr_energy_neg'] = df_processed['price_afrr_energy_neg'].replace(0, np.nan)
        
    return df_processed


def load_phase2_market_tables(workbook_path: Path, *, prefer_csv: bool = False) -> Dict[str, pd.DataFrame]:
    """Load Phase 2 market tables including aFRR energy prices.

    Parameters
    ----------
    workbook_path : Path
        Path to TechArena2025_Phase2_data.xlsx
    prefer_csv : bool, optional
        If True and CSV cache exists, use it instead of Excel

    Returns
    -------
    dict
        Keys: 'day_ahead', 'fcr', 'afrr_capacity', 'afrr_energy' (NEW)
        Values: Wide-format DataFrames

    DataFrame Formats
    -----------------
    day_ahead:
        Columns: [timestamp, DE_LU, AT, CH, HU, CZ]

    fcr:
        Columns: [timestamp, DE, AT, CH, HU, CZ]

    afrr_capacity:
        Columns: [timestamp, DE_Pos, DE_Neg, AT_Pos, AT_Neg, ...]

    afrr_energy (NEW):
        Columns: [timestamp, DE_Pos, DE_Neg, AT_Pos, AT_Neg, ...]
    """
    from core.exceptions import DataLoadingError
    import logging

    logger = logging.getLogger(__name__)
    workbook_path = workbook_path.expanduser().resolve()

    try:
        xl = pd.ExcelFile(workbook_path)
    except FileNotFoundError:
        raise DataLoadingError(f"Excel file not found: {workbook_path}")
    except Exception as e:
        raise DataLoadingError(f"Failed to open Excel file: {e}")

    tables = {}

    # Load each sheet with individual error handling
    sheet_configs = [
        (DAY_AHEAD_SHEET, 'day_ahead', _tidy_market_frame, PRICE_COL_MWH),
        (FCR_SHEET, 'fcr', _tidy_market_frame, PRICE_COL_MW),
        (AFRR_SHEET, 'afrr_capacity', _tidy_afrr_frame, None),
        (AFRR_ENERGY_SHEET, 'afrr_energy', _tidy_afrr_frame, None)  # NEW
    ]

    for sheet_name, table_key, loader_func, value_name in sheet_configs:
        try:
            raw_df = xl.parse(sheet_name)

            if value_name:
                processed_df = loader_func(raw_df, value_name=value_name)
            else:
                processed_df = loader_func(raw_df)

            # Convert to numeric
            for col in processed_df.columns[1:]:  # Skip timestamp
                processed_df[col] = pd.to_numeric(processed_df[col], errors='coerce')

            tables[table_key] = processed_df
            logger.info(f"Loaded {table_key}: {len(processed_df)} rows, {len(processed_df.columns)} columns")

        except KeyError:
            logger.warning(f"Sheet '{sheet_name}' not found, skipping...")
            continue  # Allow partial loading
        except Exception as e:
            logger.error(f"Error processing sheet '{sheet_name}': {e}")
            raise DataLoadingError(f"Failed to process sheet '{sheet_name}': {e}")

    # Validate we have minimum required tables
    if 'day_ahead' not in tables:
        raise DataLoadingError("Critical: Day-ahead data missing")

    return tables


def validate_phase2_data(tables: Dict[str, pd.DataFrame]) -> Dict[str, any]:
    """Comprehensive Phase 2 data quality validation.

    Validates:
    - Row count alignment
    - Timestamp continuity and gaps
    - Price bounds (detect outliers)
    - Excessive zeros
    - Data correlations

    Parameters
    ----------
    tables : dict
        Dictionary of market DataFrames from load_phase2_market_tables()

    Returns
    -------
    dict
        Validation report with keys:
        - 'errors': list of error messages
        - 'warnings': list of warning messages
        - 'stats': dict of validation statistics
        - 'passed': bool indicating if validation passed

    Raises
    ------
    DataValidationError
        If critical errors are found (via calling code)
    """
    report = {
        "errors": [],
        "warnings": [],
        "stats": {},
        "passed": True
    }

    # 1. Validate timestamp alignment (15-min data)
    if 'day_ahead' in tables and 'afrr_energy' in tables:
        day_ahead = tables['day_ahead']
        afrr_energy = tables['afrr_energy']

        if len(afrr_energy) != len(day_ahead):
            report["errors"].append(
                f"Row count mismatch: aFRR energy ({len(afrr_energy)}) "
                f"!= day-ahead ({len(day_ahead)})"
            )
            report["passed"] = False

    # 2. Check timestamp continuity and gaps
    for market, df in tables.items():
        if TIMESTAMP_COL not in df.columns:
            continue

        ts = df[TIMESTAMP_COL]
        expected_freq = '15T' if market in ['day_ahead', 'afrr_energy'] else '4H'

        # Check for gaps
        time_diff = ts.diff()[1:]
        expected_delta = pd.Timedelta(expected_freq)
        gaps = time_diff[time_diff > expected_delta]

        if len(gaps) > 0:
            report["warnings"].append(
                f"{market}: Found {len(gaps)} timestamp gaps "
                f"(largest: {gaps.max()})"
            )
            report["stats"][f"{market}_gaps"] = len(gaps)

    # 3. Price bounds validation
    for market, df in tables.items():
        # Get bounds for this market
        bounds_key = market if market in PRICE_BOUNDS else 'day_ahead'
        bounds = PRICE_BOUNDS.get(bounds_key, (-1000, 10000))

        price_cols = [col for col in df.columns if col != TIMESTAMP_COL]

        for col in price_cols:
            min_val = df[col].min()
            max_val = df[col].max()

            if min_val < bounds[0]:
                report["errors"].append(
                    f"{market}.{col}: Min price {min_val:.2f} < lower bound {bounds[0]}"
                )
                report["passed"] = False

            if max_val > bounds[1]:
                report["errors"].append(
                    f"{market}.{col}: Max price {max_val:.2f} > upper bound {bounds[1]}"
                )
                report["passed"] = False

            # Statistics
            report["stats"][f"{market}.{col}_min"] = float(min_val)
            report["stats"][f"{market}.{col}_max"] = float(max_val)
            report["stats"][f"{market}.{col}_mean"] = float(df[col].mean())

    # 4. Check for excessive zeros (may indicate missing data)
    if 'afrr_energy' in tables:
        afrr_energy = tables['afrr_energy']
        for col in afrr_energy.columns[1:]:  # Skip timestamp
            zero_pct = (afrr_energy[col] == 0).sum() / len(afrr_energy) * 100
            report["stats"][f"afrr_energy.{col}_zero_pct"] = float(zero_pct)

            if zero_pct > ZERO_THRESHOLD_PCT:
                report["warnings"].append(
                    f"aFRR energy {col}: {zero_pct:.1f}% zeros "
                    f"(common for activation prices, but verify)"
                )

    # 5. Correlation checks (sanity check: DA prices should correlate across countries)
    if 'day_ahead' in tables:
        day_ahead = tables['day_ahead']
        da_price_cols = [col for col in day_ahead.columns if col != TIMESTAMP_COL]

        if len(da_price_cols) >= 2:
            corr_matrix = day_ahead[da_price_cols].corr()
            min_corr = corr_matrix.min().min()

            if min_corr < 0.3:  # Expect some correlation in European markets
                report["warnings"].append(
                    f"Day-ahead: Low price correlation detected (min={min_corr:.2f}). "
                    f"Verify data integrity."
                )

            report["stats"]["day_ahead_min_correlation"] = float(min_corr)

    return report


# ===========================================================================
# VIEW 1: DATA EXPLORATION VISUALIZATIONS (McKinsey Style)
# ===========================================================================

def _filter_by_time_range(df: pd.DataFrame, time_range: str) -> pd.DataFrame:
    """Filter DataFrame by time range string.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with 'timestamp' column
    time_range : str
        One of: 'full', 'Q1', 'Q2', 'Q3', 'Q4', or 'YYYY-MM'

    Returns
    -------
    pd.DataFrame
        Filtered DataFrame
    """
    if time_range == 'full':
        return df
    elif time_range in ['Q1', 'Q2', 'Q3', 'Q4']:
        quarter_map = {'Q1': [1,2,3], 'Q2': [4,5,6], 'Q3': [7,8,9], 'Q4': [10,11,12]}
        months = quarter_map[time_range]
        return df[df[TIMESTAMP_COL].dt.month.isin(months)]
    else:
        # Assume format 'YYYY-MM'
        return df[df[TIMESTAMP_COL].dt.strftime('%Y-%m') == time_range]


def plot_price_time_series_mckinsey(
    tables: Dict[str, pd.DataFrame],
    country: str,
    time_range: str = 'full',
    markets: list = None
) -> go.Figure:
    """Plot multi-market price time series with McKinsey styling.

    Module A: Electricity Price Time Series

    Creates an interactive multi-series line chart showing DA, FCR, aFRR capacity,
    and aFRR energy prices for a selected country.

    Parameters
    ----------
    tables : dict
        Dictionary with keys: 'day_ahead', 'fcr', 'afrr_capacity', 'afrr_energy'
    country : str
        Country code (DE, AT, CH, HU, CZ)
    time_range : str, optional
        'full', 'Q1', 'Q2', 'Q3', 'Q4', or 'YYYY-MM' (default: 'full')
    markets : list, optional
        List of markets to plot. Default: all

    Returns
    -------
    go.Figure
        McKinsey-styled Plotly figure

    Example
    -------
    >>> tables = load_phase2_market_tables(Path("data/TechArena2025_Phase2_data.xlsx"))
    >>> fig = plot_price_time_series_mckinsey(tables, country='DE', time_range='Q1')
    >>> fig.show()
    """
    from visualization.config import MCKINSEY_COLORS, get_country_color, apply_mckinsey_style

    if markets is None:
        markets = ['day_ahead', 'fcr', 'afrr_capacity', 'afrr_energy']

    fig = go.Figure()

    # Add DA prices (15-min, EUR/MWh)
    if 'day_ahead' in markets and 'day_ahead' in tables:
        df_da = tables['day_ahead']
        country_col = 'DE_LU' if country == 'DE' else country

        if country_col in df_da.columns:
            df_filtered = _filter_by_time_range(df_da, time_range)

            fig.add_trace(go.Scatter(
                x=df_filtered[TIMESTAMP_COL],
                y=df_filtered[country_col],
                mode='lines',
                name='Day-Ahead',
                line=dict(color=MCKINSEY_COLORS['cat_1'], width=1.5),
                hovertemplate='%{y:.2f} EUR/MWh<extra></extra>'
            ))

    # Add FCR prices (4-hour blocks, EUR/MW) - on secondary axis
    if 'fcr' in markets and 'fcr' in tables:
        df_fcr = tables['fcr']

        if country in df_fcr.columns:
            df_filtered = _filter_by_time_range(df_fcr, time_range)

            fig.add_trace(go.Scatter(
                x=df_filtered[TIMESTAMP_COL],
                y=df_filtered[country],
                mode='lines',
                name='FCR Capacity',
                line=dict(color=MCKINSEY_COLORS['cat_2'], width=1.5, dash='dot'),
                hovertemplate='%{y:.2f} EUR/MW<extra></extra>',
                yaxis='y2'  # Secondary axis
            ))

    # Add aFRR capacity (4-hour blocks, EUR/MW, Pos/Neg)
    if 'afrr_capacity' in markets and 'afrr_capacity' in tables:
        df_afrr_cap = tables['afrr_capacity']
        df_filtered = _filter_by_time_range(df_afrr_cap, time_range)

        if f'{country}_Pos' in df_afrr_cap.columns:
            fig.add_trace(go.Scatter(
                x=df_filtered[TIMESTAMP_COL],
                y=df_filtered[f'{country}_Pos'],
                mode='lines',
                name='aFRR Cap (Pos)',
                line=dict(color=MCKINSEY_COLORS['positive'], width=1.5, dash='dash'),
                hovertemplate='%{y:.2f} EUR/MW<extra></extra>',
                yaxis='y2'
            ))

        if f'{country}_Neg' in df_afrr_cap.columns:
            fig.add_trace(go.Scatter(
                x=df_filtered[TIMESTAMP_COL],
                y=df_filtered[f'{country}_Neg'],
                mode='lines',
                name='aFRR Cap (Neg)',
                line=dict(color=MCKINSEY_COLORS['negative'], width=1.5, dash='dash'),
                hovertemplate='%{y:.2f} EUR/MW<extra></extra>',
                yaxis='y2'
            ))

    # Add aFRR energy (15-min, EUR/MWh, Pos/Neg) - NEW
    if 'afrr_energy' in markets and 'afrr_energy' in tables:
        df_afrr_energy = tables['afrr_energy']
        df_filtered = _filter_by_time_range(df_afrr_energy, time_range)

        if f'{country}_Pos' in df_afrr_energy.columns:
            fig.add_trace(go.Scatter(
                x=df_filtered[TIMESTAMP_COL],
                y=df_filtered[f'{country}_Pos'],
                mode='lines',
                name='aFRR Energy (Pos)',
                line=dict(color=MCKINSEY_COLORS['teal'], width=1.5),
                hovertemplate='%{y:.2f} EUR/MWh<extra></extra>'
            ))

        if f'{country}_Neg' in df_afrr_energy.columns:
            fig.add_trace(go.Scatter(
                x=df_filtered[TIMESTAMP_COL],
                y=df_filtered[f'{country}_Neg'],
                mode='lines',
                name='aFRR Energy (Neg)',
                line=dict(color=MCKINSEY_COLORS['cat_5'], width=1.5),
                hovertemplate='%{y:.2f} EUR/MWh<extra></extra>'
            ))

    # Apply McKinsey styling and layout
    fig = apply_mckinsey_style(
        fig,
        title=f'Electricity Market Prices - {country} ({time_range})'
    )

    fig.update_layout(
        xaxis_title='Time',
        yaxis_title='Energy Price (EUR/MWh)',
        yaxis2=dict(
            title='Capacity Price (EUR/MW)',
            overlaying='y',
            side='right',
            showgrid=False
        ),
        hovermode='x unified',
        height=500,
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        )
    )

    return fig


def plot_da_price_distribution_mckinsey(
    day_ahead_df: pd.DataFrame,
    country: str,
    bins: int = 50
) -> go.Figure:
    """Plot day-ahead price distribution with McKinsey styling.

    Module B: Price Distribution (DA)

    Creates a histogram with KDE overlay showing the frequency distribution
    of day-ahead prices.

    Parameters
    ----------
    day_ahead_df : pd.DataFrame
        Wide-format day-ahead data
    country : str
        Country code
    bins : int, optional
        Number of histogram bins (default: 50)

    Returns
    -------
    go.Figure
        Histogram with KDE overlay

    Example
    -------
    >>> tables = load_phase2_market_tables(Path("data/TechArena2025_Phase2_data.xlsx"))
    >>> fig = plot_da_price_distribution_mckinsey(tables['day_ahead'], country='DE')
    >>> fig.show()
    """
    from visualization.config import MCKINSEY_COLORS, apply_mckinsey_style
    import numpy as np
    from scipy import stats

    # Get prices for country
    country_col = 'DE_LU' if country == 'DE' else country

    if country_col not in day_ahead_df.columns:
        raise ValueError(f"Country {country} not found in day-ahead data")

    prices = day_ahead_df[country_col].dropna()

    # Create figure
    fig = go.Figure()

    # Histogram
    fig.add_trace(go.Histogram(
        x=prices,
        nbinsx=bins,
        name='Frequency',
        marker_color=MCKINSEY_COLORS['navy'],
        opacity=0.7,
        hovertemplate='Price: %{x:.2f} EUR/MWh<br>Count: %{y}<extra></extra>'
    ))

    # KDE overlay
    try:
        kde = stats.gaussian_kde(prices)
        x_range = np.linspace(prices.min(), prices.max(), 200)
        kde_values = kde(x_range)

        # Scale KDE to match histogram height
        kde_scaled = kde_values * len(prices) * (prices.max() - prices.min()) / bins

        fig.add_trace(go.Scatter(
            x=x_range,
            y=kde_scaled,
            mode='lines',
            name='Density',
            line=dict(color=MCKINSEY_COLORS['teal'], width=2),
            yaxis='y2',
            hovertemplate='Price: %{x:.2f} EUR/MWh<extra></extra>'
        ))
    except:
        pass  # Skip KDE if scipy not available or data issue

    # Add vertical lines for mean and median
    mean_price = prices.mean()
    median_price = prices.median()

    fig.add_vline(
        x=mean_price,
        line_dash="dash",
        line_color=MCKINSEY_COLORS['gray_dark'],
        annotation_text=f"Mean: {mean_price:.1f}",
        annotation_position="top"
    )

    fig.add_vline(
        x=median_price,
        line_dash="dot",
        line_color=MCKINSEY_COLORS['gray_dark'],
        annotation_text=f"Median: {median_price:.1f}",
        annotation_position="bottom"
    )

    # Apply McKinsey styling
    fig = apply_mckinsey_style(
        fig,
        title=f'Day-Ahead Price Distribution - {country}'
    )

    fig.update_layout(
        xaxis_title='Price (EUR/MWh)',
        yaxis_title='Frequency',
        yaxis2=dict(
            overlaying='y',
            side='right',
            showgrid=False
        ),
        height=400,
        showlegend=True
    )

    return fig


def plot_da_price_distribution_multi_country_mckinsey(
    day_ahead_df: pd.DataFrame,
    countries: list = None,
    bins: int = 50
) -> go.Figure:
    """Plot day-ahead price distribution comparison across multiple countries.

    Module B: Multi-Country Price Distribution (DA)

    Creates overlaid histograms with KDE curves for comparing price distributions
    across countries, using McKinsey styling.

    Parameters
    ----------
    day_ahead_df : pd.DataFrame
        Wide-format day-ahead data
    countries : list, optional
        List of country codes to compare (default: ['DE', 'AT', 'CH', 'HU', 'CZ'])
    bins : int, optional
        Number of histogram bins (default: 50)

    Returns
    -------
    go.Figure
        Overlaid histograms with KDE curves

    Example
    -------
    >>> tables = load_phase2_market_tables(Path("data/TechArena2025_Phase2_data.xlsx"))
    >>> fig = plot_da_price_distribution_multi_country_mckinsey(tables['day_ahead'])
    >>> fig.show()
    """
    from visualization.config import COUNTRY_COLORS, apply_mckinsey_style, get_country_color
    import numpy as np
    from scipy import stats

    if countries is None:
        countries = ['DE', 'AT', 'CH', 'HU', 'CZ']

    fig = go.Figure()

    # Add histogram and KDE for each country
    for country in countries:
        country_col = 'DE_LU' if country == 'DE' else country

        if country_col not in day_ahead_df.columns:
            print(f"Warning: Country {country} not found, skipping")
            continue

        prices = day_ahead_df[country_col].dropna()
        color = get_country_color(country)

        # Histogram (semi-transparent)
        fig.add_trace(go.Histogram(
            x=prices,
            nbinsx=bins,
            name=f'{country} (Histogram)',
            marker_color=color,
            opacity=0.3,
            showlegend=False,
            hovertemplate=f'{country}<br>Price: %{{x:.2f}} EUR/MWh<br>Count: %{{y}}<extra></extra>'
        ))

        # KDE overlay (prominent line)
        try:
            kde = stats.gaussian_kde(prices)
            x_range = np.linspace(prices.min(), prices.max(), 200)
            kde_values = kde(x_range)

            # Scale KDE to match histogram height approximately
            kde_scaled = kde_values * len(prices) * (prices.max() - prices.min()) / bins

            fig.add_trace(go.Scatter(
                x=x_range,
                y=kde_scaled,
                mode='lines',
                name=f'{country}',
                line=dict(color=color, width=2.5),
                hovertemplate=f'{country}<br>Price: %{{x:.2f}} EUR/MWh<extra></extra>'
            ))
        except Exception as e:
            print(f"Warning: Could not compute KDE for {country}: {e}")

    # Apply McKinsey styling
    fig = apply_mckinsey_style(
        fig,
        title='Day-Ahead Price Distribution - Multi-Country Comparison'
    )

    fig.update_layout(
        xaxis_title='Price (EUR/MWh)',
        yaxis_title='Frequency',
        barmode='overlay',  # Overlay histograms
        height=500,
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.99,
            xanchor="right",
            x=0.99
        )
    )

    return fig


def plot_da_price_ridgeline_mckinsey(
    day_ahead_df: pd.DataFrame,
    countries: list = None,
    bins: int = 100
):
    """Plot day-ahead price distribution as ridgeline plot (joy plot) with McKinsey styling.

    Module B: Multi-Country Price Distribution (Ridgeline)

    Creates a ridgeline (joy plot) visualization using matplotlib showing 
    overlapping KDE curves for comparing price distributions across countries. 
    This format provides better visual separation than overlaid histograms.

    Parameters
    ----------
    day_ahead_df : pd.DataFrame
        Wide-format day-ahead data
    countries : list, optional
        List of country codes to compare (default: ['DE', 'AT', 'CH', 'HU', 'CZ'])
    bins : int, optional
        Number of points for KDE calculation (default: 100)

    Returns
    -------
    matplotlib.figure.Figure
        Ridgeline plot with vertically offset KDE curves

    Example
    -------
    >>> tables = load_phase2_market_tables(Path("data/TechArena2025_Phase2_data.xlsx"))
    >>> fig = plot_da_price_ridgeline_mckinsey(tables['day_ahead'])
    >>> fig.show()  # or plt.show()
    """
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    from visualization.config import COUNTRY_COLORS, get_country_color
    import numpy as np
    from scipy import stats

    if countries is None:
        countries = ['DE', 'AT', 'CH', 'HU', 'CZ']

    # Prepare data
    all_prices = []
    kde_data = []
    
    for country in countries:
        country_col = 'DE_LU' if country == 'DE' else country
        
        if country_col not in day_ahead_df.columns:
            print(f"Warning: Country {country} not found, skipping")
            continue
            
        prices = day_ahead_df[country_col].dropna()
        
        if len(prices) < 10:
            print(f"Warning: Insufficient data for {country}, skipping")
            continue
            
        all_prices.extend(prices.values)
        kde_data.append({
            'country': country,
            'prices': prices.values,
            'mean': prices.mean(),
            'color': get_country_color(country)
        })
    
    if not kde_data:
        raise ValueError("No valid data found for specified countries")
    
    # Calculate global x range
    x_min, x_max = np.percentile(all_prices, [1, 99])
    x = np.linspace(x_min, x_max, bins)
    
    # Create figure with McKinsey styling
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # McKinsey color palette - convert hex to RGB
    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16)/255 for i in (0, 2, 4))
    
    # Plot each country's distribution
    vertical_spacing = 0.05  # Spacing as fraction of max density
    
    for idx, data in enumerate(kde_data):
        # Calculate KDE
        kde = stats.gaussian_kde(data['prices'])
        density = kde(x)
        
        # Normalize to 0-1 range for consistent height
        density_norm = density / density.max()
        
        # Vertical offset
        y_offset = idx * vertical_spacing
        y = density_norm + y_offset
        
        # Get color
        color_hex = data['color']
        color_rgb = hex_to_rgb(color_hex)
        
        # Plot filled curve
        ax.fill_between(x, y_offset, y, 
                        alpha=0.7, 
                        color=color_rgb,
                        linewidth=0)
        
        # Plot outline
        ax.plot(x, y, 
               color=color_rgb, 
               linewidth=2.5,
               solid_capstyle='round')
        
        # Plot baseline
        ax.plot(x, np.full_like(x, y_offset), 
               color=color_rgb, 
               linewidth=1.5, 
               alpha=0.5)
        
        # Add mean line
        mean_val = data['mean']
        density_at_mean = kde(mean_val)[0] / kde(x).max()
        ax.plot([mean_val, mean_val], 
               [y_offset, y_offset + density_at_mean * 0.7],
               color=color_rgb,
               linewidth=2.5,
               linestyle='--',
               alpha=0.8)
        
        # Add country label
        ax.text(x_min - (x_max - x_min) * 0.02, 
               y_offset + 0.4,
               data['country'],
               fontsize=14,
               fontweight='bold',
               color=color_rgb,
               ha='right',
               va='center',
               family='sans-serif')
    
    # Styling
    ax.set_xlim(x_min - (x_max - x_min) * 0.05, x_max + (x_max - x_min) * 0.02)
    ax.set_ylim(-0.01, len(kde_data) * vertical_spacing + 1.1)
    
    # Remove y-axis
    ax.set_yticks([])
    ax.spines['left'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    
    # X-axis styling
    ax.set_xlabel('Price (EUR/MWh)', fontsize=12, fontweight='bold', family='sans-serif')
    ax.spines['bottom'].set_linewidth(1.5)
    ax.tick_params(axis='x', labelsize=11, length=6, width=1.5)
    
    # Title
    ax.set_title('Day-Ahead Price Distribution - Multi-Country Comparison',
                fontsize=16, fontweight='bold', pad=20, family='sans-serif')
    
    # Grid
    ax.grid(axis='x', alpha=0.3, linewidth=0.8, linestyle='-')
    ax.set_axisbelow(True)
    
    # Background
    ax.set_facecolor('white')
    fig.patch.set_facecolor('white')
    
    # Tight layout
    plt.tight_layout()
    
    return fig


def plot_da_price_heatmap_mckinsey(
    day_ahead_df: pd.DataFrame,
    country: str
) -> go.Figure:
    """Plot hour-of-day vs month heatmap with McKinsey styling.

    Module C: DA Price Heatmap

    Creates a 2D heatmap showing average day-ahead prices by hour and month.

    Parameters
    ----------
    day_ahead_df : pd.DataFrame
        Wide-format day-ahead data with timestamp column
    country : str
        Country code

    Returns
    -------
    go.Figure
        Heatmap visualization

    Example
    -------
    >>> tables = load_phase2_market_tables(Path("data/TechArena2025_Phase2_data.xlsx"))
    >>> fig = plot_da_price_heatmap_mckinsey(tables['day_ahead'], country='DE')
    >>> fig.show()
    """
    from visualization.config import MCKINSEY_COLORS, apply_mckinsey_style

    # Get data for country
    country_col = 'DE_LU' if country == 'DE' else country

    if country_col not in day_ahead_df.columns:
        raise ValueError(f"Country {country} not found in day-ahead data")

    df = day_ahead_df[[TIMESTAMP_COL, country_col]].copy()
    df['hour'] = df[TIMESTAMP_COL].dt.hour
    df['month'] = df[TIMESTAMP_COL].dt.month

    # Pivot to create hour x month matrix
    pivot = df.pivot_table(
        index='hour',
        columns='month',
        values=country_col,
        aggfunc='mean'
    )

    # Create custom colorscale (diverging: negative=blue, zero=white, positive=red)
    colorscale = [
        [0.0, '#003f5c'],   # Dark blue (negative)
        [0.25, '#2f4b7c'],  # Blue
        [0.5, '#ffffff'],   # White (zero)
        [0.75, '#ff6361'],  # Coral
        [1.0, '#bc5090']    # Purple (high positive)
    ]

    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
           'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
        y=list(range(24)),
        colorscale=colorscale,
        colorbar=dict(
            title=dict(
                text='Avg Price<br>(EUR/MWh)',
                side='right'
            )
        ),
        hovertemplate='Month: %{x}<br>Hour: %{y}:00<br>Avg Price: %{z:.2f} EUR/MWh<extra></extra>'
    ))

    # Apply McKinsey styling
    fig = apply_mckinsey_style(
        fig,
        title=f'Day-Ahead Price Pattern - {country}'
    )

    fig.update_layout(
        xaxis_title='Month',
        yaxis_title='Hour of Day',
        height=500,
        yaxis=dict(
            tickmode='linear',
            tick0=0,
            dtick=2  # Show every 2 hours
        )
    )

    return fig


def calculate_price_statistics_mckinsey(
    tables: Dict[str, pd.DataFrame],
    country: str,
    market: str = 'day_ahead'
) -> pd.DataFrame:
    """Calculate comprehensive price statistics.

    Module D: Price Statistics

    Calculates descriptive statistics for a selected market and country.

    Parameters
    ----------
    tables : dict
        All market tables
    country : str
        Country code
    market : str, optional
        One of: 'day_ahead', 'fcr', 'afrr_capacity_pos', 'afrr_capacity_neg',
                'afrr_energy_pos', 'afrr_energy_neg' (default: 'day_ahead')

    Returns
    -------
    pd.DataFrame
        Statistics table ready for display

    Example
    -------
    >>> tables = load_phase2_market_tables(Path("data/TechArena2025_Phase2_data.xlsx"))
    >>> stats = calculate_price_statistics_mckinsey(tables, country='DE', market='day_ahead')
    >>> print(stats)
    """
    # Get appropriate data
    if market == 'day_ahead':
        col = 'DE_LU' if country == 'DE' else country
        data = tables['day_ahead'][col]
        unit = 'EUR/MWh'
    elif market == 'fcr':
        data = tables['fcr'][country]
        unit = 'EUR/MW'
    elif market.startswith('afrr_capacity'):
        direction = 'Pos' if 'pos' in market else 'Neg'
        data = tables['afrr_capacity'][f'{country}_{direction}']
        unit = 'EUR/MW'
    elif market.startswith('afrr_energy'):
        direction = 'Pos' if 'pos' in market else 'Neg'
        data = tables['afrr_energy'][f'{country}_{direction}']
        unit = 'EUR/MWh'
    else:
        raise ValueError(f"Unknown market: {market}")

    # Calculate statistics
    stats = {
        'Metric': ['Mean', 'Median', 'Std Dev', 'Min', 'Max', 'Range',
                   '10th Percentile', '90th Percentile'],
        'Value': [
            f"{data.mean():.2f}",
            f"{data.median():.2f}",
            f"{data.std():.2f}",
            f"{data.min():.2f}",
            f"{data.max():.2f}",
            f"{data.max() - data.min():.2f}",
            f"{data.quantile(0.1):.2f}",
            f"{data.quantile(0.9):.2f}"
        ],
        'Unit': [unit] * 8
    }

    return pd.DataFrame(stats)


def plot_price_statistics_mckinsey(
    stats_df: pd.DataFrame,
    country: str,
    market: str
) -> go.Figure:
    """Display statistics as a clean table figure.

    Module D: Price Statistics (Visualization)

    Creates a professional table visualization for price statistics.

    Parameters
    ----------
    stats_df : pd.DataFrame
        Statistics from calculate_price_statistics_mckinsey()
    country : str
        Country code
    market : str
        Market name for title

    Returns
    -------
    go.Figure
        Table visualization

    Example
    -------
    >>> stats = calculate_price_statistics_mckinsey(tables, 'DE', 'day_ahead')
    >>> fig = plot_price_statistics_mckinsey(stats, 'DE', 'day_ahead')
    >>> fig.show()
    """
    from visualization.config import MCKINSEY_COLORS, MCKINSEY_FONTS

    fig = go.Figure(data=[go.Table(
        header=dict(
            values=['<b>Metric</b>', '<b>Value</b>', '<b>Unit</b>'],
            fill_color=MCKINSEY_COLORS['navy'],
            font=dict(color='white', size=MCKINSEY_FONTS['axis_label_size']),
            align='left',
            height=30
        ),
        cells=dict(
            values=[stats_df['Metric'], stats_df['Value'], stats_df['Unit']],
            fill_color=[[MCKINSEY_COLORS['bg_light_gray'], 'white'] * 4],
            font=dict(size=MCKINSEY_FONTS['tick_label_size']),
            align='left',
            height=25
        )
    )])

    fig.update_layout(
        title=f'Price Statistics - {market.replace("_", " ").title()} - {country}',
        height=350,
        margin=dict(l=20, r=20, t=60, b=20)
    )

    return fig


# ---------------------------------------------------------------------------
# CLI bootstrap
# ---------------------------------------------------------------------------


def _cli_example(workbook: Path) -> None:
    tables = load_market_tables(workbook)
    volatility = summarize_day_ahead(tables["day_ahead"])
    fcr_summary = summarize_fcr(tables["fcr"])
    afrr_summary = summarize_afrr(tables["afrr"])

    print("Top 5 arbitrage opportunities (Day-Ahead volatility):")
    print(volatility.head())
    print("\nFCR average prices by country:")
    print(fcr_summary.sort_values("mean", ascending=False))
    print("\naFRR summary (positive vs negative):")
    print(afrr_summary)


if __name__ == "__main__":
    default_path = Path(__file__).resolve().parents[1] / "SoloGen_TechArena2025_Phase1" / "input" / "TechArena2025_data.xlsx"
    if default_path.exists():
        _cli_example(default_path)
    else:
        raise SystemExit(
            "Unable to locate the default workbook. Pass a valid path or adjust the script."
        )
