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
