# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository. To understand the ultimate purpose and structure of the project, please refer to `doc\whole_project_description.md`.

## Project Context

This is the Huawei TechArena 2025 BESS (Battery Energy Storage System) optimizer project for optimizing battery operations across European electricity markets. The system uses Mixed-Integer Linear Programming (MILP) to maximize profitability while managing battery degradation.

## Architecture Overview

### Core Model Hierarchy
The project implements three progressive optimization models:
- **Model I** (`BESSOptimizerModelI`): Base 4-market optimization (DA, FCR, aFRR capacity, aFRR energy)
- **Model II** (`BESSOptimizerModelII`): Model I + cyclic aging cost
- **Model III** (`BESSOptimizerModelIII`): Model II + calendar aging cost (full Phase II model)

### Key Components
- **py_script/core/optimizer.py**: Main optimization models using Pyomo MILP framework
- **py_script/data/market_data.py**: Market data loading and transformation
- **py_script/data/preprocessing.py**: Critical preprocessing for aFRR energy markets (0->NaN conversion)
- **py_script/visualization/**: Plotting utilities for results analysis

## Critical Data Processing

### aFRR Energy Market Preprocessing
**IMPORTANT**: aFRR energy price = 0 means market NOT activated, not free energy. The `preprocess_market_data()` function converts these to NaN to prevent false arbitrage opportunities.

### Data Sources
- **Phase 2 market data**: `data/phase2_processed/{market}.parquet` (aFRR energy prices)
- **Aging config**: `data/phase2_aging_config/` (degradation parameters, activation rates)
- **Load and process Market data**: use 
    ```python
       try:
            print(f"\n[OK] Loading data from: {data_file}")
            full_data = optimizer.load_and_preprocess_data(data_file)
            print(f"\n[OK] Loading data from: {data_dir}")
            from py_script.data.market_data import load_market_data
        
            print(f"[OK] Extracting data for country: {country}")
            country_data = optimizer.extract_country_data(full_data, country)
            # Load Phase 2 parquet data
            country_data = load_market_data(data_dir, country)
    ```

       75        try:
       76 -          print(f"\n[OK] Loading data from: {data_file}")
       77 -          full_data = optimizer.load_and_preprocess_data(data_file)
       76 +          print(f"\n[OK] Loading data from: {data_dir}")
       77 +          from py_script.data.market_data import load_market_data
       78
       79 -          print(f"[OK] Extracting data for country: {country}")
       80 -          country_data = optimizer.extract_country_data(full_data, country)
       79 +          # Load Phase 2 parquet data
       80 +          country_data = load_market_data(data_dir, country)
## Common Development Tasks


### Key Parameters
- **Countries**: DE_LU, AT, CH, HU, CZ
- **C-rates**: 0.25, 0.33, 0.5
- **Daily cycles**: 1.0, 1.5, 2.0
- **Alpha**: Degradation weight (0.5-1.0 typical)
- **Max AS ratio**: 0.8 (80% of power for ancillary services)

### Solver Configuration
The project auto-detects available MILP solvers in order: Gurobi > CPLEX > CBC > GLPK > HiGHS
- **CPLEX/Gurobi**: Best performance for large-scale problems
- **CBC**: Good open-source option
- **GLPK**: Fallback, slower for complex models

## Important Constraints

### Market Rules
- **Minimum bids**: FCR/aFRR = 1 MW, DA = 0.1 MW
- **Block structure**: AS markets use 4-hour blocks (6 blocks/day)
- **Exclusivity**: Cannot provide FCR and aFRR simultaneously (Cst-8)
- **Energy reserves**: Must maintain SOC for committed AS capacity (Cst-6)

### Battery Constraints
- **Capacity**: 4,472 kWh fixed
- **Efficiency**: 95% round-trip
- **SOC range**: 0-100% allowed
- **Power limits**: Based on C-rate configuration
- **Daily cycle limits**: Enforced per-day constraint (Cst-3)

## Model Formulation

### Objective Function (Model III)
Refer to `doc\p2_model\p2_bi_model_ggdp.tex`

### Key Decision Variables
- `p_ch[t]`, `p_dis[t]`: DA charge/discharge power
- `p_afrr_pos_e[t]`, `p_afrr_neg_e[t]`: aFRR energy bids
- `c_fcr[b]`, `c_afrr_pos[b]`, `c_afrr_neg[b]`: AS capacity bids (per block)
- `e_soc[t]`: State of charge trajectory
- `e_soc_seg[t,s]`: SOC in each degradation segment

## Testing and Validation

### Output Files
- **Solutions**: `results/model_iii_validation/solution_*.csv`
- **Visualizations**: `results/model_iii_validation/*/plots/*.html`
- **Metadata**: JSON files with optimization statistics

### Visualization Outputs
Four standard plots generated:
1. **da_market_price_bid.html**: Day-ahead market participation
2. **afrr_energy_market_price_bid.html**: aFRR energy market (shows 0 prices correctly)
3. **capacity_markets_price_bid.html**: FCR/aFRR capacity reservations
4. **soc_and_power_bids.html**: Battery SOC trajectory with all power flows

## Important Implementation Details

### aFRR Energy Market Handling
- Preprocessed prices (NaN) used for optimization constraints
- Original prices (including 0) stored for visualization
- Revenue calculated using preprocessed prices (0 revenue when not activated)

### SOC Segmentation (Model II/III)
- 10 segments for cyclic aging (447.2 kWh each)
- Piecewise linear cost function: 0.0052-0.099 EUR/kWh
- Calendar aging: 5 SOC breakpoints with SOS2 variables


## Known Issues and Workarounds

1. **aFRR zero prices**: Must use preprocessing to convert to NaN
2. **Solver timeouts**: Large problems may need increased time limits
3. **Memory usage**: Full-year optimization requires significant RAM
4. **Windows paths**: Use raw strings or forward slashes for file paths