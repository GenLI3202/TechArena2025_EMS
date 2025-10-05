# Step 1 · Data Analysis

## Objective
Internalize the structure of the TechArena 2025 datasets and derive the preprocessing routines required to feed the optimization pipeline.

## Key Tasks
- Ground yourself in the official workflow by scanning `doc/project_description.tex` (Phase 0) for dataset definitions, cadence requirements, and submission expectations.
- Standardize on `pandas`, `numpy`, and `plotly` as the primary analysis stack; verify versions align with `requirements.txt`.
- Create `py_script/market_da.py` containing reusable utilities that:
	- Load market-specific tables from `SoloGen_TechArena2025_Phase1/input/TechArena2025_data.xlsx` (or derived CSV extracts) into tidy DataFrames. 
	- Provide helper functions to filter by country, market, and price type.
	- Expose plotting functions that return Plotly figures for downstream notebooks/reports.
- Implement Day-Ahead market exploration inside `market_da.py` (or a companion notebook) including:
	- Price distribution comparison (box plot) across countries to rank arbitrage potential.
	- Yearly price trend line chart to expose seasonal patterns.
	- Hourly/monthly heatmaps that highlight intraday charge/discharge windows.
- Implement FCR market routines that compute country-level averages and generate price distribution box plots to flag stable, high-paying markets.
- Implement aFRR market analysis that treats upward and downward reserves separately with dedicated distribution plots and summary tables.
- Document how these visuals will inform hypotheses for the optimization model (e.g., market selection, operating heuristics).

## Deliverables
- `py_script/market_da.py` with data-loading abstractions, filtering helpers, and Plotly chart builders for Day-Ahead, FCR, and aFRR markets.
- Cleaned, merged datasets saved as intermediate parquet/CSV files or cached objects to accelerate later phases.
- Plot gallery (static exports or interactive dashboards) showcasing the key visualizations for each market.
- Notebook or script snippets documenting preprocessing decisions, daylight-saving handling, and missing-data treatment.
- A brief insights memo ranking countries by revenue potential and capturing hypotheses for the modeling phase.

## Checks Before Moving On
- Confirm 35,136 rows for 2024 (leap year) after resampling.
- Validate that price columns remain numeric and free of NaN values.
- Smoke-test every plotting helper in `market_da.py` to ensure figures render without errors for at least one representative country per market.
- Ensure the preprocessing logic is encapsulated in reusable functions (`io.py`) and mirrored by the helpers in `market_da.py` for downstream modules.
