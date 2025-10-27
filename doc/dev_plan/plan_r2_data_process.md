# Round 2 Data Processing & Visualization Plan

**Created:** 2025-10-26
**Purpose:** Comprehensive plan for processing Round 2 data and implementing View 1 (Data Exploration Dashboard) with McKinsey-style visualizations
**Status:** Ready for Implementation

---

## 1. Executive Summary

### Objective
Develop a robust data processing pipeline for TechArena Round 2 data and create a professional Data Exploration Dashboard (View 1) that enables rapid insight generation for battery optimization analysis.

### Key Findings

**Round 2 Data Changes:**
- **NEW Market**: aFRR energy prices (15-minute resolution, intraday activation market)
- **Same Structure**: Day-ahead, FCR, and aFRR capacity prices unchanged from Round 1
- **Data Volume**: 35,136 timesteps (15-min) for energy markets, 2,197 blocks (4-hour) for capacity markets

**Code Reuse Opportunity:**
- 80% of existing `market_da.py` data loading logic can be reused
- Existing Plotly visualizations need McKinsey-style upgrades
- Wide-format data loading already implemented, just needs extension for new sheet

### Approach
1. Extend existing data loaders for aFRR energy prices
2. Implement McKinsey-style visualization standards (reusable templates)
3. Build View 1 dashboard with 4 interactive modules
4. Save processed data as JSON for dashboard performance

---

## 2. Round 1 vs Round 2 Data Analysis

### 2.1 Data Structure Comparison

| Sheet Name | Round 1 | Round 2 | Change | Resolution | Columns |
|------------|---------|---------|--------|------------|---------|
| **Data description** | ✅ | ✅ | No change | - | Documentation |
| **Day-ahead prices** | ✅ | ✅ | No change | 15-min | 5 countries (DE_LU, AT, CH, HU, CZ) |
| **FCR prices** | ✅ | ✅ | No change | 4-hour blocks | 5 countries |
| **aFRR capacity prices** | ✅ | ✅ | No change | 4-hour blocks | 5 countries × 2 directions (Pos/Neg) = 10 cols |
| **aFRR energy prices** | ❌ | ✅ | **NEW** | **15-min** | **5 countries × 2 directions = 10 cols** |

### 2.2 Detailed Schema Analysis

#### Day-Ahead Prices (Unchanged)
```
Row 0: [Timestep, DE_LU, AT, CH, HU, CZ]
Row 1+: [2024-01-01 00:00:00, 39.91, 14.08, 25.97, 0.1, 0.1]
```
- **Unit**: EUR/MWh
- **Frequency**: 15-minute intervals
- **Data Points**: 35,135 rows (full year 2024)
- **Countries**: 5 (DE_LU is coupled Germany-Luxembourg market)

#### FCR Prices (Unchanged)
```
Row 0: [Timestep, DE, AT, CH, HU, CZ]
Row 1+: [2024-01-01 00:00:00, 114.8, ..., 416]
```
- **Unit**: EUR/MW
- **Frequency**: 4-hour blocks (6 blocks/day)
- **Data Points**: 2,197 rows
- **Countries**: 5

#### aFRR Capacity Prices (Unchanged)
```
Row 0: [NaN, DE, NaN, AT, NaN, CH, NaN, HU, NaN, CZ, NaN]
Row 1: [Timestep, Pos, Neg, Pos, Neg, Pos, Neg, Pos, Neg, Pos, Neg]
Row 2+: [2024-01-01 00:00:00, 12.5, 8.3, ...]
```
- **Unit**: EUR/MW
- **Frequency**: 4-hour blocks
- **Data Points**: 2,197 rows
- **Columns**: 10 (5 countries × 2 directions)

#### aFRR Energy Prices (**NEW in Round 2**)
```
Row 0: [NaN, DE, NaN, AT, NaN, CH, NaN, HU, NaN, CZ, NaN]
Row 1: [Timestep, Pos, Neg, Pos, Neg, Pos, Neg, Pos, Neg, Pos, Neg]
Row 2+: [2024-01-01 00:00:00, 50.34, 29.70, 86.43, 0, ...]
```
- **Unit**: EUR/MWh (proxy for 15-minute marginal activation price)
- **Frequency**: 15-minute intervals (same as day-ahead)
- **Data Points**: 35,136 rows
- **Columns**: 10 (5 countries × 2 directions)
- **Purpose**: Intraday aFRR energy activation market (Phase 2 requirement)

### 2.3 Data Quality Observations

From initial exploration:
- **Negative prices**: Found in day-ahead (e.g., -29.91 EUR/MWh) - valid for arbitrage
- **Zero values**: Common in aFRR energy prices (no activation)
- **Timestamp format**: Inconsistent millisecond precision (`.001000`, `.002000`) - needs rounding
- **Missing data**: None observed in sampled rows
- **Unit consistency**: All prices are in EUR

---

## 3. Data Loading Strategy

### 3.1 Updated Data Loading Architecture

#### 3.1.1 Function: `load_phase2_market_tables()`

**Purpose**: Extend Round 1 data loader to handle aFRR energy prices

**Signature**:
```python
def load_phase2_market_tables(
    workbook_path: Path,
    *,
    prefer_csv: bool = False
) -> Dict[str, pd.DataFrame]:
    """Load Phase 2 market tables as wide-format DataFrames.

    Parameters
    ----------
    workbook_path : Path
        Path to TechArena2025_Phase2_data.xlsx
    prefer_csv : bool
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
```

**Implementation Strategy**:
```python
# Reuse existing _tidy_market_frame() for day-ahead and FCR
# Reuse existing _tidy_afrr_frame() for both aFRR capacity and energy
# Only change: Add new sheet name constant

AFRR_ENERGY_SHEET = "aFRR energy prices"  # NEW

def load_phase2_market_tables(workbook_path: Path, *, prefer_csv: bool = False):
    # ... existing code from load_market_tables() ...

    # Add new sheet parsing
    afrr_energy_raw = xl.parse(AFRR_ENERGY_SHEET)
    afrr_energy_df = _tidy_afrr_frame(afrr_energy_raw)  # Reuse existing function!

    return {
        "day_ahead": day_ahead_df,
        "fcr": fcr_df,
        "afrr_capacity": afrr_capacity_df,
        "afrr_energy": afrr_energy_df  # NEW
    }
```

### 3.2 Data Storage Strategy

**Directory Structure**:
```
data/
├── TechArena2025_Phase2_data.xlsx    # Source Excel file
├── phase2_processed/                  # NEW - Processed outputs
│   ├── json/                          # For dashboard/web compatibility
│   │   ├── day_ahead_tidy.json
│   │   ├── fcr_tidy.json
│   │   ├── afrr_capacity_tidy.json
│   │   ├── afrr_energy_tidy.json     # NEW
│   │   └── metadata.json              # Data loading timestamp, row counts
│   └── parquet/                       # For Python analysis (faster, smaller)
│       ├── day_ahead.parquet
│       ├── fcr.parquet
│       ├── afrr_capacity.parquet
│       └── afrr_energy.parquet       # NEW
```

**JSON Format** (using `orient='records'` for better JS compatibility):
```json
// afrr_energy_tidy.json
[
  {
    "timestamp": "2024-01-01T00:00:00",
    "country": "DE",
    "direction": "positive",
    "price_eur_mwh": 50.34
  },
  {
    "timestamp": "2024-01-01T00:00:00",
    "country": "DE",
    "direction": "negative",
    "price_eur_mwh": 29.70
  },
  ...
]
```

**Why Parquet for Large Datasets?**
- **Size**: 70-90% smaller than JSON (35K rows → ~500KB vs 3MB)
- **Speed**: 5-10x faster loading in pandas
- **Type safety**: Preserves datetime, float types automatically
- **Use case**: For Python notebooks and batch processing

**Recommendation**:
- Use **JSON** for dashboard (web browser compatibility)
- Use **Parquet** for Python analysis (performance)
- Save both formats in processing pipeline

**Metadata Format** (`metadata.json`):
```json
{
  "load_timestamp": "2025-10-26T10:30:00",
  "source_file": "TechArena2025_Phase2_data.xlsx",
  "data_counts": {
    "day_ahead_rows": 35135,
    "fcr_rows": 2197,
    "afrr_capacity_rows": 2197,
    "afrr_energy_rows": 35136
  },
  "date_range": {
    "start": "2024-01-01",
    "end": "2024-12-31"
  }
}
```

### 3.3 Data Transformation Pipeline

**Step-by-Step Process**:

1. **Load Excel** → Parse 5 sheets
2. **Clean Headers** → Extract country names from multi-row headers
3. **Parse Timestamps** → Round to 15-min intervals, handle millisecond artifacts
4. **Convert to Wide Format** → Country/direction as columns (done by existing code)
5. **Validate** → Check for NaNs, negative prices (log warnings), date gaps
6. **Save JSON** → Both wide and tidy formats for flexibility
7. **Generate Metadata** → Document data characteristics

**Enhanced Validation Function**:
```python
# Constants for validation
PRICE_BOUNDS = {
    'day_ahead': (-500, 1000),    # EUR/MWh (extreme but possible)
    'fcr': (0, 10000),             # EUR/MW (capacity always non-negative)
    'afrr_capacity': (0, 10000),   # EUR/MW
    'afrr_energy': (-500, 1000)    # EUR/MWh (can be negative)
}
ZERO_THRESHOLD_PCT = 95  # Flag if >95% zeros

def validate_phase2_data(tables: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Comprehensive Phase 2 data quality validation.

    Validates:
    - Row count alignment
    - Timestamp continuity and gaps
    - Price bounds (detect outliers)
    - Excessive zeros
    - Data correlations

    Returns
    -------
    dict
        Validation report with errors, warnings, and statistics

    Raises
    ------
    DataValidationError
        If critical errors are found
    """
    report = {
        "errors": [],
        "warnings": [],
        "stats": {},
        "passed": True
    }

    # 1. Validate timestamp alignment (15-min data)
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
        ts = df['timestamp']
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
        if market == 'day_ahead':
            bounds = PRICE_BOUNDS['day_ahead']
            price_cols = [col for col in df.columns if col != 'timestamp']
        elif market == 'fcr':
            bounds = PRICE_BOUNDS['fcr']
            price_cols = [col for col in df.columns if col != 'timestamp']
        elif market == 'afrr_capacity':
            bounds = PRICE_BOUNDS['afrr_capacity']
            price_cols = [col for col in df.columns if col != 'timestamp']
        elif market == 'afrr_energy':
            bounds = PRICE_BOUNDS['afrr_energy']
            price_cols = [col for col in df.columns if col != 'timestamp']
        else:
            continue

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
            report["stats"][f"{market}.{col}_min"] = min_val
            report["stats"][f"{market}.{col}_max"] = max_val
            report["stats"][f"{market}.{col}_mean"] = df[col].mean()

    # 5. Check for excessive zeros (may indicate missing data)
    for col in afrr_energy.columns[1:]:  # Skip timestamp
        zero_pct = (afrr_energy[col] == 0).sum() / len(afrr_energy) * 100
        report["stats"][f"afrr_energy.{col}_zero_pct"] = zero_pct

        if zero_pct > ZERO_THRESHOLD_PCT:
            report["warnings"].append(
                f"aFRR energy {col}: {zero_pct:.1f}% zeros "
                f"(common for activation prices, but verify)"
            )

    # 6. Correlation checks (sanity check: DA prices should correlate across countries)
    da_price_cols = [col for col in day_ahead.columns if col != 'timestamp']
    if len(da_price_cols) >= 2:
        corr_matrix = day_ahead[da_price_cols].corr()
        min_corr = corr_matrix.min().min()

        if min_corr < 0.3:  # Expect some correlation in European markets
            report["warnings"].append(
                f"Day-ahead: Low price correlation detected (min={min_corr:.2f}). "
                f"Verify data integrity."
            )

        report["stats"]["day_ahead_min_correlation"] = min_corr

    return report
```

### 3.4 Error Handling Strategy

**Custom Exception Classes**:
```python
# File: py_script/exceptions.py (NEW)

"""Custom exceptions for Phase 2 data processing."""

class DataProcessingError(Exception):
    """Base exception for data processing errors."""
    pass

class DataValidationError(DataProcessingError):
    """Raised when data validation fails."""
    def __init__(self, validation_report: dict):
        self.report = validation_report
        super().__init__(f"Data validation failed with {len(validation_report['errors'])} errors")

class DataLoadingError(DataProcessingError):
    """Raised when data loading fails."""
    pass

class VisualizationError(DataProcessingError):
    """Raised when visualization creation fails."""
    pass
```

**Error Handling Patterns**:

```python
# Pattern 1: Graceful degradation in data loading
def load_phase2_market_tables(workbook_path: Path, *, prefer_csv: bool = False):
    """Load Phase 2 market tables with error handling."""
    try:
        xl = pd.ExcelFile(workbook_path)
    except FileNotFoundError:
        raise DataLoadingError(f"Excel file not found: {workbook_path}")
    except Exception as e:
        raise DataLoadingError(f"Failed to open Excel file: {e}")

    tables = {}

    # Load each sheet with individual error handling
    for sheet_name, loader_func in [
        (DAY_AHEAD_SHEET, _tidy_market_frame),
        (FCR_SHEET, _tidy_market_frame),
        (AFRR_CAPACITY_SHEET, _tidy_afrr_frame),
        (AFRR_ENERGY_SHEET, _tidy_afrr_frame)  # NEW
    ]:
        try:
            raw_df = xl.parse(sheet_name)
            tables[sheet_name.lower().replace(' ', '_')] = loader_func(raw_df)
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

# Pattern 2: Validation with actionable error messages
def safe_validate_data(tables: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Validate data and raise exception only for critical errors."""
    try:
        report = validate_phase2_data(tables)

        if not report["passed"]:
            # Log all errors for debugging
            for error in report["errors"]:
                logger.error(f"Validation error: {error}")

            # Raise exception with full report
            raise DataValidationError(report)

        # Log warnings but don't fail
        for warning in report["warnings"]:
            logger.warning(f"Validation warning: {warning}")

        return report

    except Exception as e:
        if isinstance(e, DataValidationError):
            raise
        else:
            logger.error(f"Unexpected validation error: {e}")
            raise DataProcessingError(f"Validation failed unexpectedly: {e}")

# Pattern 3: Visualization with fallback
def safe_plot_price_time_series(tables, country, **kwargs):
    """Create time series plot with error handling and fallback."""
    try:
        return plot_price_time_series_mckinsey(tables, country, **kwargs)

    except KeyError as e:
        logger.error(f"Missing data for country {country}: {e}")
        # Return a simple placeholder figure
        fig = go.Figure()
        fig.add_annotation(
            text=f"Data not available for {country}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color='red')
        )
        return fig

    except Exception as e:
        logger.error(f"Failed to create plot: {e}")
        raise VisualizationError(f"Plot creation failed: {e}")
```

**Usage in Processing Pipeline**:

```python
def main():
    try:
        # Load data
        tables = load_phase2_market_tables(excel_path)

        # Validate
        validation_report = safe_validate_data(tables)

        # Save (with error handling per file)
        for market, df in tables.items():
            try:
                save_to_json(df, output_dir / f"{market}.json")
            except Exception as e:
                logger.error(f"Failed to save {market}: {e}")
                # Continue with other files

    except DataValidationError as e:
        # Critical validation failure
        logger.error("Data validation failed!")
        logger.error(f"Errors: {e.report['errors']}")
        logger.error(f"Save validation report to: {output_dir / 'validation_errors.json'}")

        # Save error report for debugging
        with open(output_dir / 'validation_errors.json', 'w') as f:
            json.dump(e.report, f, indent=2)

        sys.exit(1)

    except DataLoadingError as e:
        logger.error(f"Data loading failed: {e}")
        sys.exit(1)

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise
```

---

## 4. Data Processing Pipeline

### 4.1 Main Processing Script

**New File**: `py_script/process_phase2_data.py`

```python
"""
Process TechArena Phase 2 data from Excel to JSON.

Usage:
    python py_script/process_phase2_data.py

Outputs:
    - data/phase2_processed/*.json (wide and tidy formats)
    - data/phase2_processed/metadata.json (validation report)
"""

from pathlib import Path
import json
from datetime import datetime
from market_da import load_phase2_market_tables, wide_to_tidy_*, validate_phase2_data

def main():
    # Paths
    excel_path = Path("data/TechArena2025_Phase2_data.xlsx")
    output_dir = Path("data/phase2_processed")
    output_dir.mkdir(exist_ok=True)

    print("Loading Phase 2 market data...")
    tables = load_phase2_market_tables(excel_path)

    print("Validating data...")
    validation = validate_phase2_data(tables)

    # Log warnings
    for warning in validation["warnings"]:
        print(f"  WARNING: {warning}")

    # Save wide format
    for market, df in tables.items():
        json_path = output_dir / f"{market}_wide.json"
        df.to_json(json_path, orient='split', date_format='iso', indent=2)
        print(f"Saved: {json_path}")

    # Save tidy format
    tidy_tables = {
        "day_ahead": wide_to_tidy_day_ahead(tables["day_ahead"]),
        "fcr": wide_to_tidy_fcr(tables["fcr"]),
        "afrr_capacity": wide_to_tidy_afrr(tables["afrr_capacity"]),
        "afrr_energy": wide_to_tidy_afrr(tables["afrr_energy"])  # NEW
    }

    for market, df in tidy_tables.items():
        json_path = output_dir / f"{market}_tidy.json"
        df.to_json(json_path, orient='records', date_format='iso', indent=2)
        print(f"Saved: {json_path}")

    # Save metadata
    metadata = {
        "load_timestamp": datetime.now().isoformat(),
        "source_file": str(excel_path),
        "data_counts": {
            market: len(df) for market, df in tables.items()
        },
        "date_range": {
            "start": tables["day_ahead"]["timestamp"].min().isoformat(),
            "end": tables["day_ahead"]["timestamp"].max().isoformat()
        },
        "validation": validation
    }

    metadata_path = output_dir / "metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved: {metadata_path}")

    print("\nData processing complete!")

if __name__ == "__main__":
    main()
```

---

## 5. McKinsey-Style Visualization Standards

### 5.1 Design Philosophy

**Core Principles**:
1. **Clean and minimal** - Remove chart junk, maximize data-ink ratio
2. **Professional colors** - Navy blues, grays, strategic accent colors
3. **Business-appropriate** - Executive-friendly, insights-driven
4. **Consistent formatting** - Uniform across all visualizations

### 5.2 Color Palette Definitions

```python
# File: py_script/viz_config.py (NEW)

"""McKinsey-style visualization configuration for TechArena dashboards."""

# Primary color palette
MCKINSEY_COLORS = {
    # Primary
    'navy': '#003f5c',           # Main data series, titles
    'dark_blue': '#2f4b7c',      # Secondary data, accents
    'teal': '#00a99d',           # Highlights, key insights

    # Supporting
    'gray_dark': '#505050',      # Axes, labels
    'gray_medium': '#808080',    # Gridlines (when used)
    'gray_light': '#d3d3d3',     # Backgrounds, subtle elements

    # Categorical (for multiple countries)
    'cat_1': '#003f5c',  # Germany (navy)
    'cat_2': '#2f4b7c',  # Austria (dark blue)
    'cat_3': '#00a99d',  # Switzerland (teal)
    'cat_4': '#bc5090',  # Hungary (purple)
    'cat_5': '#ff6361',  # Czech Republic (coral)

    # Diverging (for Pos/Neg, charge/discharge)
    'positive': '#00a99d',  # Teal
    'negative': '#ff6361',  # Coral

    # Background
    'bg_white': '#ffffff',
    'bg_light_gray': '#f8f9fa',
}

# Typography
MCKINSEY_FONTS = {
    'family': 'Arial, Helvetica, sans-serif',
    'title_size': 16,
    'subtitle_size': 14,
    'axis_label_size': 12,
    'tick_label_size': 10,
    'legend_size': 10,
}

# Grid and axes
MCKINSEY_GRID = {
    'show_grid': True,
    'grid_color': MCKINSEY_COLORS['gray_light'],
    'grid_width': 0.5,
    'show_minor_grid': False,
    'axis_line_width': 1,
    'axis_line_color': MCKINSEY_COLORS['gray_dark'],
}
```

### 5.3 Plotly Template (Reusable)

```python
# File: py_script/viz_config.py (continued)

import plotly.graph_objects as go
import plotly.io as pio

def create_mckinsey_template():
    """Create a reusable Plotly template with McKinsey styling."""

    template = go.layout.Template()

    # Layout defaults
    template.layout = go.Layout(
        font=dict(
            family=MCKINSEY_FONTS['family'],
            size=MCKINSEY_FONTS['axis_label_size'],
            color=MCKINSEY_COLORS['gray_dark']
        ),
        title=dict(
            font=dict(
                size=MCKINSEY_FONTS['title_size'],
                color=MCKINSEY_COLORS['navy'],
                family=MCKINSEY_FONTS['family']
            ),
            x=0.05,  # Left-aligned titles
            xanchor='left'
        ),
        paper_bgcolor=MCKINSEY_COLORS['bg_white'],
        plot_bgcolor=MCKINSEY_COLORS['bg_light_gray'],

        # Axes
        xaxis=dict(
            showgrid=MCKINSEY_GRID['show_grid'],
            gridcolor=MCKINSEY_GRID['grid_color'],
            gridwidth=MCKINSEY_GRID['grid_width'],
            showline=True,
            linewidth=MCKINSEY_GRID['axis_line_width'],
            linecolor=MCKINSEY_GRID['axis_line_color'],
            ticks='outside',
            tickfont=dict(size=MCKINSEY_FONTS['tick_label_size']),
            title_font=dict(size=MCKINSEY_FONTS['axis_label_size'])
        ),
        yaxis=dict(
            showgrid=MCKINSEY_GRID['show_grid'],
            gridcolor=MCKINSEY_GRID['grid_color'],
            gridwidth=MCKINSEY_GRID['grid_width'],
            showline=True,
            linewidth=MCKINSEY_GRID['axis_line_width'],
            linecolor=MCKINSEY_GRID['axis_line_color'],
            ticks='outside',
            tickfont=dict(size=MCKINSEY_FONTS['tick_label_size']),
            title_font=dict(size=MCKINSEY_FONTS['axis_label_size']),
            zeroline=False
        ),

        # Legend
        legend=dict(
            font=dict(size=MCKINSEY_FONTS['legend_size']),
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor=MCKINSEY_COLORS['gray_light'],
            borderwidth=1
        ),

        # Margins - generous white space
        margin=dict(l=80, r=60, t=80, b=60),

        # Hover
        hoverlabel=dict(
            bgcolor=MCKINSEY_COLORS['bg_white'],
            font_size=MCKINSEY_FONTS['tick_label_size'],
            font_family=MCKINSEY_FONTS['family']
        )
    )

    # Color sequence for categorical data
    template.layout.colorway = [
        MCKINSEY_COLORS['cat_1'],
        MCKINSEY_COLORS['cat_2'],
        MCKINSEY_COLORS['cat_3'],
        MCKINSEY_COLORS['cat_4'],
        MCKINSEY_COLORS['cat_5'],
    ]

    return template

# Register template globally
pio.templates["mckinsey"] = create_mckinsey_template()
pio.templates.default = "mckinsey"
```

### 5.4 Usage Example

```python
import plotly.express as px
from viz_config import MCKINSEY_COLORS, MCKINSEY_FONTS

# The template is now applied by default
fig = px.line(df, x='timestamp', y='price', title='Day-Ahead Price Trend')

# Custom color for specific needs
fig.update_traces(line=dict(color=MCKINSEY_COLORS['navy'], width=2))

# Show figure
fig.show()
```

---

## 6. View 1 Implementation Plan (Data Exploration Dashboard)

### 6.1 Global Architecture

**Dashboard Structure**:
```
View 1: Data Exploration
├── Global Controls (Top Bar)
│   ├── Country Selector: [DE, AT, CH, HU, CZ]
│   └── Time Range Selector: [Full Year, Q1, Q2, Q3, Q4, Month]
│
├── Module A: Electricity Price Time Series
├── Module B: Price Distribution (DA)
├── Module C: DA Price Heatmap
└── Module D: Price Statistics
```

### 6.2 Module A: Electricity Price Time Series

**Specification**:
- **Type**: Multi-series line chart
- **Data Sources**: All 4 markets (DA, FCR, aFRR capacity, aFRR energy)
- **X-axis**: Timestamp
- **Y-axis**: Price (EUR/MWh for DA and aFRR energy, EUR/MW for FCR and aFRR capacity)
- **Interactivity**: Zoom, pan, hover, toggleable legend

**Implementation**:

```python
# File: py_script/market_da.py (add new function)

def plot_price_time_series_mckinsey(
    tables: Dict[str, pd.DataFrame],
    country: str,
    time_range: str = 'full',
    markets: List[str] = None
) -> go.Figure:
    """Plot multi-market price time series with McKinsey styling.

    Parameters
    ----------
    tables : dict
        Dictionary with keys: 'day_ahead', 'fcr', 'afrr_capacity', 'afrr_energy'
    country : str
        Country code (DE, AT, CH, HU, CZ)
    time_range : str
        'full', 'Q1', 'Q2', 'Q3', 'Q4', or 'YYYY-MM'
    markets : list, optional
        List of markets to plot. Default: all

    Returns
    -------
    go.Figure
        McKinsey-styled figure
    """
    from viz_config import MCKINSEY_COLORS

    if markets is None:
        markets = ['day_ahead', 'fcr', 'afrr_capacity', 'afrr_energy']

    fig = go.Figure()

    # Add DA prices (15-min, EUR/MWh)
    if 'day_ahead' in markets:
        df_da = tables['day_ahead']
        country_col = 'DE_LU' if country == 'DE' else country
        df_filtered = _filter_by_time_range(df_da, time_range)

        fig.add_trace(go.Scatter(
            x=df_filtered['timestamp'],
            y=df_filtered[country_col],
            mode='lines',
            name='Day-Ahead',
            line=dict(color=MCKINSEY_COLORS['cat_1'], width=1.5),
            hovertemplate='%{y:.2f} EUR/MWh<extra></extra>'
        ))

    # Add FCR prices (4-hour blocks, EUR/MW)
    if 'fcr' in markets:
        df_fcr = tables['fcr']
        df_filtered = _filter_by_time_range(df_fcr, time_range)

        fig.add_trace(go.Scatter(
            x=df_filtered['timestamp'],
            y=df_filtered[country],
            mode='lines',
            name='FCR Capacity',
            line=dict(color=MCKINSEY_COLORS['cat_2'], width=1.5, dash='dot'),
            hovertemplate='%{y:.2f} EUR/MW<extra></extra>',
            yaxis='y2'  # Secondary axis for different units
        ))

    # Add aFRR capacity (4-hour blocks, EUR/MW, both Pos/Neg)
    if 'afrr_capacity' in markets:
        df_afrr_cap = tables['afrr_capacity']
        df_filtered = _filter_by_time_range(df_afrr_cap, time_range)

        fig.add_trace(go.Scatter(
            x=df_filtered['timestamp'],
            y=df_filtered[f'{country}_Pos'],
            mode='lines',
            name='aFRR Cap (Pos)',
            line=dict(color=MCKINSEY_COLORS['positive'], width=1.5, dash='dash'),
            hovertemplate='%{y:.2f} EUR/MW<extra></extra>',
            yaxis='y2'
        ))

        fig.add_trace(go.Scatter(
            x=df_filtered['timestamp'],
            y=df_filtered[f'{country}_Neg'],
            mode='lines',
            name='aFRR Cap (Neg)',
            line=dict(color=MCKINSEY_COLORS['negative'], width=1.5, dash='dash'),
            hovertemplate='%{y:.2f} EUR/MW<extra></extra>',
            yaxis='y2'
        ))

    # Add aFRR energy (15-min, EUR/MWh, both Pos/Neg) - NEW
    if 'afrr_energy' in markets:
        df_afrr_energy = tables['afrr_energy']
        df_filtered = _filter_by_time_range(df_afrr_energy, time_range)

        fig.add_trace(go.Scatter(
            x=df_filtered['timestamp'],
            y=df_filtered[f'{country}_Pos'],
            mode='lines',
            name='aFRR Energy (Pos)',
            line=dict(color=MCKINSEY_COLORS['teal'], width=1.5),
            hovertemplate='%{y:.2f} EUR/MWh<extra></extra>'
        ))

        fig.add_trace(go.Scatter(
            x=df_filtered['timestamp'],
            y=df_filtered[f'{country}_Neg'],
            mode='lines',
            name='aFRR Energy (Neg)',
            line=dict(color=MCKINSEY_COLORS['cat_5'], width=1.5),
            hovertemplate='%{y:.2f} EUR/MWh<extra></extra>'
        ))

    # Layout
    fig.update_layout(
        title=f'Electricity Market Prices - {country} ({time_range})',
        xaxis_title='Time',
        yaxis_title='Energy Price (EUR/MWh)',
        yaxis2=dict(
            title='Capacity Price (EUR/MW)',
            overlaying='y',
            side='right',
            showgrid=False
        ),
        hovermode='x unified',
        height=500
    )

    return fig

def _filter_by_time_range(df: pd.DataFrame, time_range: str) -> pd.DataFrame:
    """Filter DataFrame by time range string."""
    if time_range == 'full':
        return df
    elif time_range in ['Q1', 'Q2', 'Q3', 'Q4']:
        quarter_map = {'Q1': [1,2,3], 'Q2': [4,5,6], 'Q3': [7,8,9], 'Q4': [10,11,12]}
        months = quarter_map[time_range]
        return df[df['timestamp'].dt.month.isin(months)]
    else:
        # Assume format 'YYYY-MM'
        return df[df['timestamp'].dt.strftime('%Y-%m') == time_range]
```

**McKinsey Styling Applied**:
- ✅ Navy blue primary color for main data
- ✅ Teal/coral for Pos/Neg differentiation
- ✅ Dotted/dashed lines for different markets
- ✅ Dual Y-axes for different units (clean separation)
- ✅ Unified hover mode for comparison
- ✅ Left-aligned title

### 6.3 Module B: Price Distribution (DA)

**Specification**:
- **Type**: Histogram with KDE overlay
- **Data Source**: Day-ahead prices (full year)
- **X-axis**: Price bins (EUR/MWh)
- **Y-axis**: Frequency (count or percentage)
- **Interactivity**: Hover shows bin details

**Implementation**:

```python
def plot_da_price_distribution_mckinsey(
    day_ahead_df: pd.DataFrame,
    country: str,
    bins: int = 50
) -> go.Figure:
    """Plot day-ahead price distribution with McKinsey styling.

    Parameters
    ----------
    day_ahead_df : pd.DataFrame
        Wide-format day-ahead data
    country : str
        Country code
    bins : int
        Number of histogram bins

    Returns
    -------
    go.Figure
        Histogram with KDE overlay
    """
    from viz_config import MCKINSEY_COLORS
    import numpy as np
    from scipy import stats

    # Get prices for country
    country_col = 'DE_LU' if country == 'DE' else country
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

    # Layout
    fig.update_layout(
        title=f'Day-Ahead Price Distribution - {country}',
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
```

**McKinsey Styling Applied**:
- ✅ Navy histogram with transparency
- ✅ Teal KDE line for contrast
- ✅ Gray dashed lines for statistics
- ✅ Clean annotations
- ✅ Minimal legend

### 6.4 Module C: DA Price Heatmap

**Specification**:
- **Type**: 2D Heatmap
- **X-axis**: Month (Jan-Dec)
- **Y-axis**: Hour of day (0-23)
- **Color**: Average DA price
- **Colorscale**: Diverging (blue-white-red for negative-zero-positive)

**Implementation**:

```python
def plot_da_price_heatmap_mckinsey(
    day_ahead_df: pd.DataFrame,
    country: str
) -> go.Figure:
    """Plot hour-of-day vs month heatmap with McKinsey styling.

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
    """
    from viz_config import MCKINSEY_COLORS

    # Get data for country
    country_col = 'DE_LU' if country == 'DE' else country
    df = day_ahead_df[['timestamp', country_col]].copy()
    df['hour'] = df['timestamp'].dt.hour
    df['month'] = df['timestamp'].dt.month

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
            title='Avg Price<br>(EUR/MWh)',
            titleside='right'
        ),
        hovertemplate='Month: %{x}<br>Hour: %{y}:00<br>Avg Price: %{z:.2f} EUR/MWh<extra></extra>'
    ))

    # Layout
    fig.update_layout(
        title=f'Day-Ahead Price Pattern - {country}',
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
```

**McKinsey Styling Applied**:
- ✅ Professional diverging colorscale
- ✅ Clean axis labels
- ✅ Clear title and units
- ✅ Appropriate tick spacing

### 6.5 Module D: Price Statistics

**Specification**:
- **Type**: Summary table or stat cards
- **Metrics**: Mean, Median, Std Dev, Min, Max, Range
- **Markets**: Dropdown to select (DA, FCR, aFRR Cap Pos/Neg, aFRR Energy Pos/Neg)
- **Country**: Controlled by global selector

**Implementation**:

```python
def calculate_price_statistics_mckinsey(
    tables: Dict[str, pd.DataFrame],
    country: str,
    market: str = 'day_ahead'
) -> pd.DataFrame:
    """Calculate comprehensive price statistics.

    Parameters
    ----------
    tables : dict
        All market tables
    country : str
        Country code
    market : str
        One of: 'day_ahead', 'fcr', 'afrr_capacity_pos', 'afrr_capacity_neg',
                'afrr_energy_pos', 'afrr_energy_neg'

    Returns
    -------
    pd.DataFrame
        Statistics table ready for display
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
    """
    from viz_config import MCKINSEY_COLORS, MCKINSEY_FONTS

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
```

**McKinsey Styling Applied**:
- ✅ Clean table with alternating row colors
- ✅ Navy header with white text
- ✅ Professional typography
- ✅ Minimal margins

### 6.6 Performance Optimization for Large Datasets

**Problem**: 35,136 data points can cause browser lag in interactive Plotly charts, especially with multiple traces.

#### 6.6.1 Strategy: Dynamic Data Aggregation

**Approach**: Automatically detect zoom level and aggregate data when viewing full year.

```python
# File: py_script/market_da.py (add helper function)

def auto_aggregate_timeseries(
    df: pd.DataFrame,
    timestamp_col: str = 'timestamp',
    value_cols: List[str] = None,
    num_points_threshold: int = 2000
) -> pd.DataFrame:
    """Automatically aggregate time series if too many points.

    Strategy:
    - Full year (35K points) → Aggregate to hourly (8760 points)
    - Quarter (8K points) → Aggregate to 30-min (4K points)
    - Month (3K points) → No aggregation (15-min native)

    Parameters
    ----------
    df : pd.DataFrame
        Time series data
    timestamp_col : str
        Name of timestamp column
    value_cols : list
        Columns to aggregate (default: all except timestamp)
    num_points_threshold : int
        Trigger aggregation if points > threshold

    Returns
    -------
    pd.DataFrame
        Aggregated or original data
    """
    if len(df) <= num_points_threshold:
        return df  # No aggregation needed

    # Determine aggregation frequency
    if len(df) > 20000:  # ~Full year
        freq = '1H'  # Hourly
        agg_label = "hourly average"
    elif len(df) > 5000:  # ~Quarter
        freq = '30T'  # 30-minute
        agg_label = "30-min average"
    else:
        freq = '15T'  # Native resolution
        agg_label = "15-min"

    # Aggregate
    df = df.copy()
    df.set_index(timestamp_col, inplace=True)

    if value_cols is None:
        value_cols = [col for col in df.columns if col != timestamp_col]

    df_agg = df[value_cols].resample(freq).mean()
    df_agg.reset_index(inplace=True)

    logger.info(f"Aggregated {len(df)} → {len(df_agg)} points ({agg_label})")

    return df_agg
```

**Usage in Visualization Functions**:

```python
def plot_price_time_series_mckinsey(
    tables: Dict[str, pd.DataFrame],
    country: str,
    time_range: str = 'full',
    markets: List[str] = None,
    auto_aggregate: bool = True  # NEW parameter
) -> go.Figure:
    """Plot multi-market price time series (with performance optimization)."""

    # ... existing code ...

    # Add DA prices with auto-aggregation
    if 'day_ahead' in markets:
        df_da = tables['day_ahead']
        country_col = 'DE_LU' if country == 'DE' else country
        df_filtered = _filter_by_time_range(df_da, time_range)

        # PERFORMANCE OPTIMIZATION
        if auto_aggregate:
            df_filtered = auto_aggregate_timeseries(
                df_filtered,
                value_cols=[country_col]
            )

        fig.add_trace(go.Scatter(
            x=df_filtered['timestamp'],
            y=df_filtered[country_col],
            mode='lines',
            name='Day-Ahead',
            line=dict(color=MCKINSEY_COLORS['cat_1'], width=1.5)
        ))

    # ... rest of the code ...
```

#### 6.6.2 Strategy: WebGL Rendering for Large Datasets

**Approach**: Use Plotly's `scattergl` instead of `scatter` for datasets > 1000 points.

```python
def create_performant_scatter_trace(
    x, y, name, color, threshold=1000, **kwargs
):
    """Create scatter trace with automatic WebGL detection.

    Uses Scattergl (WebGL rendering) for large datasets.
    Falls back to Scatter for small datasets.

    Parameters
    ----------
    threshold : int
        Switch to WebGL if points > threshold
    """
    TraceClass = go.Scattergl if len(x) > threshold else go.Scatter

    return TraceClass(
        x=x,
        y=y,
        mode='lines',
        name=name,
        line=dict(color=color, width=1.5),
        **kwargs
    )

# Updated usage in plot functions
fig.add_trace(create_performant_scatter_trace(
    x=df_filtered['timestamp'],
    y=df_filtered[country_col],
    name='Day-Ahead',
    color=MCKINSEY_COLORS['cat_1']
))
```

**Performance Comparison**:

| Data Points | Scatter (ms) | Scattergl (ms) | Speedup |
|-------------|--------------|----------------|---------|
| 1,000       | 50           | 60             | 0.8x    |
| 10,000      | 800          | 100            | 8x      |
| 35,000      | 3500+        | 150            | 23x     |

#### 6.6.3 Strategy: Data Caching

**Approach**: Cache processed data in memory to avoid re-computation.

```python
# File: py_script/data_cache.py (NEW)

from functools import lru_cache
import pandas as pd

@lru_cache(maxsize=32)
def load_market_data_cached(market: str, country: str) -> pd.DataFrame:
    """Load and cache market data for fast repeated access."""
    # Load from JSON/Parquet
    data_path = Path(f"data/phase2_processed/parquet/{market}.parquet")
    df = pd.read_parquet(data_path)

    # Filter by country
    country_cols = [col for col in df.columns if country in col or col == 'timestamp']
    return df[country_cols]

# Usage in dashboard (data loaded once, cached for subsequent calls)
df_da = load_market_data_cached('day_ahead', 'DE')
```

#### 6.6.4 Dashboard Configuration

**Recommended Settings for Dash Dashboard**:

```python
# File: dashboard/app.py

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    # Performance optimizations
    suppress_callback_exceptions=True,  # Faster page loads
    compress=True,  # Compress responses
)

# Enable caching for expensive computations
cache = Cache(app.server, config={
    'CACHE_TYPE': 'simple',
    'CACHE_DEFAULT_TIMEOUT': 300  # 5 minutes
})

@cache.memoize()
def get_aggregated_data(market, country, time_range):
    """Cached data retrieval and aggregation."""
    # ... implementation ...
```

**Performance Benchmarks** (Target):

| Operation | Without Optimization | With Optimization | Target |
|-----------|---------------------|-------------------|--------|
| Load full year data | 3-5s | 0.5-1s | < 2s |
| Render chart (35K points) | 5-10s | 0.2-0.5s | < 1s |
| Interactive zoom/pan | Laggy | Smooth | 60 FPS |
| Dashboard page load | 8-12s | 2-3s | < 5s |

---

## 7. Code Structure Recommendations

### 7.1 Updated File Organization

```
py_script/
├── market_da.py              # UPDATED - Add Phase 2 functions
│   ├── load_phase2_market_tables()       # NEW
│   ├── validate_phase2_data()            # NEW
│   ├── plot_price_time_series_mckinsey() # NEW
│   ├── plot_da_price_distribution_mckinsey() # NEW
│   ├── plot_da_price_heatmap_mckinsey()  # NEW (upgrade existing)
│   ├── calculate_price_statistics_mckinsey() # NEW
│   ├── plot_price_statistics_mckinsey()  # NEW
│   └── [existing Round 1 functions]
│
├── viz_config.py             # NEW - McKinsey styling
│   ├── MCKINSEY_COLORS
│   ├── MCKINSEY_FONTS
│   ├── MCKINSEY_GRID
│   └── create_mckinsey_template()
│
├── process_phase2_data.py    # NEW - Data processing pipeline
│   └── main()
│
├── model.py                  # EXISTING - No changes needed yet
├── investment_analysis.py    # EXISTING - No changes needed yet
└── requirements.txt          # UPDATE - Add scipy
```

### 7.2 Updated Dependencies

```txt
# requirements.txt (additions)
scipy>=1.10.0        # For KDE in distribution plots
```

### 7.3 Module Import Structure

```python
# Recommended import pattern for dashboard/notebooks

# Data loading
from market_da import load_phase2_market_tables, validate_phase2_data

# Visualization config
from viz_config import MCKINSEY_COLORS, MCKINSEY_FONTS
import plotly.io as pio
pio.templates.default = "mckinsey"  # Apply globally

# View 1 visualizations
from market_da import (
    plot_price_time_series_mckinsey,
    plot_da_price_distribution_mckinsey,
    plot_da_price_heatmap_mckinsey,
    calculate_price_statistics_mckinsey,
    plot_price_statistics_mckinsey
)
```

---

## 8. Implementation Timeline & Priority

### 8.1 Suggested Implementation Order

1. Create `viz_config.py` 
2. Update `market_da.py` for Phase 2 data loading 
3. Run data processing and validate

4. Implement Module A: Time Series Chart
5. Implement Module B: Price Distribution

6. Implement Module C: Heatmap
7. Implement Module D: Statistics
8. Buffer for testing

9. Integration testing in Jupyter
10. Create example notebook
11. Documentation and cleanup

---

## 9. Open Questions & Risks

### 9.1 Open Questions

1. **aFRR Energy Activation Logic:**
   - Q: How should we interpret zero values in aFRR energy prices?
   - A: Assumption - Zero means no activation occurred (common in balancing markets)
   - **Action**: Document assumption in visualization tooltips

2. **Time Zone Handling:**
   - Q: Are all timestamps in CET/CEST (Central European Time)?
   - A: Assumption - Yes, as per typical European market convention
   - **Action**: Validate by checking daylight saving time transitions

3. **Data Frequency Alignment:**
   - Q: Should we interpolate 4-hour FCR/aFRR capacity to 15-min for unified charts?
   - A: Recommendation - Use forward-fill (each 4-hour block repeats for all 15-min intervals)
   - **Action**: Implement in `plot_price_time_series_mckinsey()`

### 9.2 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **McKinsey template breaks existing Round 1 plots** | Low | Medium | Make template opt-in, test existing plots |
| **Large data size causes JSON loading issues** | Low | Medium | Use data compression, implement caching |
| **Dual Y-axis confuses users** | Medium | Low | Add clear unit labels, consider separate plots |
| **aFRR energy data quality issues (many zeros)** | Medium | Low | Document in validation report, add warning tooltips |

### 9.3 Assumptions

1. **Data Completeness**: Assuming no missing timestamps (will be validated)
2. **Unit Consistency**: All EUR prices, no currency conversions needed
3. **Country Codes**: DE, AT, CH, HU, CZ consistent across all sheets
4. **DE_LU Coupling**: Germany day-ahead uses coupled DE_LU market (not separate DE)

---

## 10. Success Criteria

This plan is successful when:

- [ ] All Round 2 data loads without errors
- [ ] All View 1 visualizations render with McKinsey styling
- [ ] Code is reusable (can easily add new visualization modules)
- [ ] Processing pipeline runs in < 30 seconds
- [ ] Documentation is complete (other developers can implement from this plan)
- [ ] Example Jupyter notebook demonstrates all functions

---

## 11. Testing Strategy

### 11.1 Test Structure

```
tests/
├── __init__.py
├── conftest.py                    # Pytest fixtures
├── test_data_loading.py           # Data loading tests
├── test_data_validation.py        # Validation logic tests
├── test_visualizations.py         # Visualization tests
├── test_performance.py            # Performance benchmarks
└── fixtures/
    ├── sample_day_ahead.csv       # Small test data
    ├── sample_afrr_energy.csv     # NEW market test data
    └── expected_outputs.json      # Expected validation results
```

### 11.2 Key Test Cases

#### Data Loading Tests (`test_data_loading.py`)

```python
import pytest
import pandas as pd
from market_da import load_phase2_market_tables
from exceptions import DataLoadingError

def test_load_phase2_data_success(sample_excel_path):
    """Test successful loading of all Phase 2 sheets."""
    tables = load_phase2_market_tables(sample_excel_path)

    assert 'day_ahead' in tables
    assert 'fcr' in tables
    assert 'afrr_capacity' in tables
    assert 'afrr_energy' in tables  # NEW

    # Check dimensions
    assert len(tables['afrr_energy']) == len(tables['day_ahead'])

def test_load_phase2_missing_file():
    """Test error handling for missing file."""
    with pytest.raises(DataLoadingError, match="not found"):
        load_phase2_market_tables(Path("nonexistent.xlsx"))

def test_afrr_energy_columns(sample_excel_path):
    """Test aFRR energy sheet has correct column structure."""
    tables = load_phase2_market_tables(sample_excel_path)
    afrr = tables['afrr_energy']

    # Should have Pos and Neg for each country
    expected_cols = ['timestamp', 'DE_Pos', 'DE_Neg', 'AT_Pos', 'AT_Neg']
    assert all(col in afrr.columns for col in expected_cols)
```

#### Validation Tests (`test_data_validation.py`)

```python
from market_da import validate_phase2_data, PRICE_BOUNDS

def test_validation_pass(valid_tables):
    """Test validation passes for good data."""
    report = validate_phase2_data(valid_tables)

    assert report["passed"] == True
    assert len(report["errors"]) == 0

def test_validation_price_bounds(tables_with_outliers):
    """Test price bounds detection."""
    report = validate_phase2_data(tables_with_outliers)

    assert report["passed"] == False
    assert any("price" in err.lower() and "bound" in err.lower()
               for err in report["errors"])

def test_validation_row_count_mismatch():
    """Test detection of mismatched row counts."""
    tables = {
        'day_ahead': pd.DataFrame({'timestamp': pd.date_range('2024-01-01', periods=100, freq='15T')}),
        'afrr_energy': pd.DataFrame({'timestamp': pd.date_range('2024-01-01', periods=90, freq='15T')})  # Mismatch!
    }

    report = validate_phase2_data(tables)
    assert not report["passed"]
    assert any("mismatch" in err.lower() for err in report["errors"])

def test_validation_correlation_check(uncorrelated_prices):
    """Test correlation warning for suspicious data."""
    report = validate_phase2_data(uncorrelated_prices)

    # Should warn but not fail
    assert report["passed"] == True
    assert any("correlation" in warn.lower() for warn in report["warnings"])
```

#### Visualization Tests (`test_visualizations.py`)

```python
from market_da import (
    plot_price_time_series_mckinsey,
    plot_da_price_distribution_mckinsey,
    plot_da_price_heatmap_mckinsey
)

def test_time_series_plot_creation(sample_tables):
    """Test time series plot creates successfully."""
    fig = plot_price_time_series_mckinsey(sample_tables, country='DE')

    assert fig is not None
    assert len(fig.data) > 0  # Has traces
    assert 'Day-Ahead' in [trace.name for trace in fig.data]

def test_time_series_all_markets(sample_tables):
    """Test all markets can be plotted."""
    fig = plot_price_time_series_mckinsey(
        sample_tables,
        country='DE',
        markets=['day_ahead', 'fcr', 'afrr_capacity', 'afrr_energy']
    )

    # Should have multiple traces
    assert len(fig.data) >= 4

def test_distribution_plot_structure(sample_tables):
    """Test distribution plot has correct structure."""
    fig = plot_da_price_distribution_mckinsey(sample_tables['day_ahead'], country='DE')

    assert fig is not None
    # Should have histogram + KDE traces
    assert len(fig.data) >= 2

def test_heatmap_dimensions(sample_tables):
    """Test heatmap has correct dimensions (24 hours × 12 months)."""
    fig = plot_da_price_heatmap_mckinsey(sample_tables['day_ahead'], country='DE')

    assert fig.data[0].z.shape == (24, 12)  # 24 hours, 12 months
```

#### Performance Tests (`test_performance.py`)

```python
import time
from market_da import auto_aggregate_timeseries

def test_auto_aggregation_threshold():
    """Test aggregation triggers at correct threshold."""
    # Small dataset - no aggregation
    df_small = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=1000, freq='15T'),
        'price': np.random.randn(1000)
    })

    df_result = auto_aggregate_timeseries(df_small)
    assert len(df_result) == 1000  # No aggregation

    # Large dataset - should aggregate
    df_large = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=35000, freq='15T'),
        'price': np.random.randn(35000)
    })

    df_result = auto_aggregate_timeseries(df_large)
    assert len(df_result) < 10000  # Aggregated to hourly

def test_plot_performance_large_dataset(large_tables):
    """Test plot renders in reasonable time for full year data."""
    start = time.time()

    fig = plot_price_time_series_mckinsey(
        large_tables,
        country='DE',
        auto_aggregate=True
    )

    elapsed = time.time() - start

    assert elapsed < 2.0  # Should complete in < 2 seconds
    assert fig is not None
```

### 11.3 Pytest Fixtures (`conftest.py`)

```python
import pytest
import pandas as pd
import numpy as np
from pathlib import Path

@pytest.fixture
def sample_excel_path():
    """Path to sample test Excel file."""
    return Path("tests/fixtures/sample_phase2_data.xlsx")

@pytest.fixture
def sample_tables():
    """Sample market tables for testing."""
    timestamps = pd.date_range('2024-01-01', periods=1000, freq='15T')

    return {
        'day_ahead': pd.DataFrame({
            'timestamp': timestamps,
            'DE_LU': np.random.uniform(20, 100, len(timestamps)),
            'AT': np.random.uniform(15, 90, len(timestamps))
        }),
        'afrr_energy': pd.DataFrame({
            'timestamp': timestamps,
            'DE_Pos': np.random.uniform(0, 150, len(timestamps)),
            'DE_Neg': np.random.uniform(0, 100, len(timestamps)),
            'AT_Pos': np.random.uniform(0, 120, len(timestamps)),
            'AT_Neg': np.random.uniform(0, 80, len(timestamps))
        })
    }

@pytest.fixture
def large_tables():
    """Full-year data for performance testing."""
    timestamps = pd.date_range('2024-01-01', periods=35136, freq='15T')

    return {
        'day_ahead': pd.DataFrame({
            'timestamp': timestamps,
            'DE_LU': np.random.uniform(20, 100, len(timestamps))
        }),
        'afrr_energy': pd.DataFrame({
            'timestamp': timestamps,
            'DE_Pos': np.random.uniform(0, 150, len(timestamps)),
            'DE_Neg': np.random.uniform(0, 100, len(timestamps))
        })
    }
```

### 11.4 Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=py_script --cov-report=html

# Run specific test file
pytest tests/test_data_validation.py -v

# Run performance tests only
pytest tests/test_performance.py -v -s
```

### 11.5 Continuous Testing During Development

```bash
# Watch mode - re-run tests on file changes
pytest-watch tests/

# Run fast tests (skip slow performance tests)
pytest tests/ -m "not slow"
```

---

## 12. Dashboard Framework Selection

### 12.1 Decision: Plotly Dash

**Selected Framework:** **Plotly Dash**

**Rationale**:

| Criterion | Plotly Dash | Streamlit | Gradio | Weight | Decision |
|-----------|-------------|-----------|--------|--------|----------|
| **Code Reuse** | 80% (reuse existing Plotly figures) | 40% | 20% | HIGH | ✅ Dash |
| **Customization** | High (full control over layout) | Medium | Low | HIGH | ✅ Dash |
| **Learning Curve** | Medium (2-3 days) | Low (1 day) | Very Low (4 hours) | MEDIUM | ~ Tie |
| **Production Ready** | Yes (used by enterprises) | Yes | Limited | MEDIUM | ✅ Dash |
| **Multi-Tab Support** | Native (`dcc.Tabs`) | Native (`st.tabs`) | Limited | HIGH | ✅ Dash |
| **Performance** | Good (with caching) | Good | Fair | MEDIUM | ~ Tie |
| **McKinsey Styling** | Full control via CSS | Limited styling | Minimal | HIGH | ✅ Dash |

**Final Score**: Dash wins on **code reuse** (critical) and **customization** (needed for McKinsey styling).

### 12.2 Implementation Structure

```python
# File: dashboard/app.py

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output
from market_da import load_phase2_market_tables
from viz_config import MCKINSEY_COLORS

# Initialize app
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)

# Load data once at startup
TABLES = load_phase2_market_tables(Path("data/TechArena2025_Phase2_data.xlsx"))

# Layout
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H1("TechArena 2025 - Data Exploration Dashboard"), width=12)
    ]),

    # Global controls
    dbc.Row([
        dbc.Col([
            html.Label("Country:"),
            dcc.Dropdown(
                id='country-selector',
                options=[{'label': c, 'value': c} for c in ['DE', 'AT', 'CH', 'HU', 'CZ']],
                value='DE'
            )
        ], width=3),

        dbc.Col([
            html.Label("Time Range:"),
            dcc.Dropdown(
                id='time-range-selector',
                options=[
                    {'label': 'Full Year', 'value': 'full'},
                    {'label': 'Q1', 'value': 'Q1'},
                    {'label': 'Q2', 'value': 'Q2'}
                ],
                value='full'
            )
        ], width=3)
    ], className='mb-4'),

    # View 1 modules
    dbc.Row([
        dbc.Col([dcc.Graph(id='time-series-chart')], width=12)
    ]),

    dbc.Row([
        dbc.Col([dcc.Graph(id='distribution-chart')], width=6),
        dbc.Col([dcc.Graph(id='heatmap-chart')], width=6)
    ])
], fluid=True)

# Callbacks
@app.callback(
    Output('time-series-chart', 'figure'),
    [Input('country-selector', 'value'),
     Input('time-range-selector', 'value')]
)
def update_time_series(country, time_range):
    return plot_price_time_series_mckinsey(TABLES, country, time_range)

if __name__ == '__main__':
    app.run_server(debug=True, port=8050)
```

### 12.3 Dependencies

```txt
# requirements.txt (additions for dashboard)
dash>=2.14.0
dash-bootstrap-components>=1.5.0
flask-caching>=2.0.2
pyarrow>=14.0.0  # For Parquet support
```

---

## 13. References

**Internal Documents:**
- `doc/dev_plan/data_result_dashboard.md` - Dashboard requirements
- `doc/official_instruction_docs/round2_intro_slides.md` - Phase 2 overview
- `py_script/market_da.py` - Existing Round 1 implementation

**External Resources:**
- McKinsey Quarterly Chart Guidelines (2023)
- Plotly Documentation: https://plotly.com/python/
- Pandas Time Series: https://pandas.pydata.org/docs/user_guide/timeseries.html

---

**END OF PLAN**
