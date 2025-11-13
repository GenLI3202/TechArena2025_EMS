# Huawei TechArena 2025: BESS Energy Management System
*by Gen Li (Team SoloGen)*
*Last Update: Nov-13-2025*

> This INTERNAL document notes the overall project methodology, math models, development state.
> - **Repository Status:** Currently developing **Round 2 (Phase 2)** solution.
> - Phase 1 (2024 optimization) artifacts have been archived to `archive_old_files/`.
> - **New Data:** `data/TechArena2025_Phase2_data.xlsx`
> - **Active Branch:** `p2-full-model-3-clean`
> - **Phase 2 Implementation Status:** Model (i), (ii), and (iii) implemented and validated

A Python-based Energy Management System (EMS) for optimal Battery Energy Storage System (BESS) operations across multiple European electricity markets considering battery aging and degradation.

## Important Update 
  - [ ] Regarding the degradation model, it is essential that the battery operating period in all submissions is based on a fixed project lifetime of 10 years. While a 70% degradation limit can be considered a practical constraint, it ultimately depends on the specific degradation model each team applies. Consequently, this could lead to significant variations in the results and modeling approaches. 

Therefore, please do not include the end-of-life (EoL) degradation limit in your investment calculations. All investment-related analyses should assume a fixed 10-year operation period. 


## Table of Contents

---

## Context and Objectives
Primary objective: Develop a BESS to optimize financial performance by participating in four key markets: day-ahead (Energy), FCR (power capacity), and aFRR markets (both power and energy), while considering impact of BESS schedule on battery aging and degradation.

The challenge is divided into two phases, three core, interconnected optimization tasks:

### Phase I: One-Year Optimization without Battery Degradation
- **Operation Optimization:** Maximize the BESS's revenue over the year 2024 by developing an optimal charge/discharge strategy to bid in **three** markets: the DA, FCR and aFRR markets.

- **Investment Optimization:** Identify which of five European countries (Germany, Austria, Switzerland, Hungary, Czech Republic) offers the highest Return on Investment (ROI) for installing the BESS over a 10-year period.

- **Configuration Optimization:** Determine the optimal BESS configuration by analyzing the impact of different C-rates and daily cycle limits on profitability and performance.

#### Data for Investment and Configuration Optimization in Phase I
* Participants should still optimize the investment locations and configurations of BESS across the five given regions (DE, AT, CH, HU, CZ) as in Phase I.
  * The weighted-average cost of capital (WACC) remains as: **DE, AT, CH**: 8.3%; **CZ**: 12.0%; **HU**: 15.0%.
  * Inflation rate remains as: **DE**: 2.0%; **AT**: 3.3%; **CH**: 0.1%; **CZ**: 2.9%; **HU**: 4.6%.

* BESS Features remain as:  
  * **Nominal Energy Capacity**: 4472 kWh
  * **Power Rating**: 2236 kW
  * **Investment Cost**: 200 EUR/kWh
  * **(Dis-)Charging Efficiency**: `95% ?`
  * **Charge/Discharge C-Rates**: 0.25C, 0.33C, 0.50C
  * **Daily Number of Cycles**: 1.0, 1.5, 2.0
  * **Cooling Method**: Liquid Cooling



### Phase II: Phase 1 + Integration of Battery Degradation Modeling & aFRR Energy Market 

1. Include **the effect of battery degradation**. In other words, the operational strategy should aim to maximize battery lifetime.
    > - [ ] Comment by Gen: Shall this be optimized as a bi-objective problem, show optimal solutions in Pareto plots?
2. Integrate the **aFRR energy market** into the EMS algorithms for the operational perspective.


```mermaid
flowchart TD
    subgraph Phase_I["<b>PHASE I</b>"]
        direction TB
        P1A["<b>Operation Optimization</b><br/>(Arbitrage, FCR, aFRR)"]
        P1B["<b>Investment Optimization</b>"]
        P1C["<b>Configuration Optimization</b>"]
    end
    
    Arrow["⬇️ <b>PROGRESSION TO PHASE II</b> ⬇️"]
    
    subgraph Phase_II["<b>PHASE II</b>"]
        direction TB
        subgraph Row1[" "]
            direction LR
            P2A["<b>Operation Optimization</b><br/>(Arbitrage, FCR, aFRR,<br/>🔴 <b>Intraday aFRR</b>)"]
            P2B["<b>Investment<br/>Optimization</b><br/><br/><br/>"]
        end
        subgraph Row2[" "]
            direction LR
            P2C["<b>Configuration<br/>Optimization</b><br/><br/><br/>"]
            P2D["🔴 <b>Battery<br/>Degradation</b><br/><br/><br/>"]
        end
    end
    
    Phase_I --> Arrow
    Arrow --> Phase_II
    
    style Phase_I fill:#ffcccc,stroke:#ff6666,stroke-width:4px
    style Phase_II fill:#ccffcc,stroke:#66cc66,stroke-width:4px
    style Row1 fill:#ccffcc,stroke:none
    style Row2 fill:#ccffcc,stroke:none
    style Arrow fill:#ffffff,stroke:#666666,stroke-width:2px,font-size:18px
    style P1A fill:#fff5f5,stroke:#333,stroke-width:3px,font-size:18px,min-width:200px
    style P1B fill:#fff5f5,stroke:#333,stroke-width:3px,font-size:18px,min-width:200px
    style P1C fill:#fff5f5,stroke:#333,stroke-width:3px,font-size:18px,min-width:200px
    style P2A fill:#f5fff5,stroke:#cc0000,stroke-width:4px,font-size:18px,min-width:250px
    style P2B fill:#f5fff5,stroke:#333,stroke-width:3px,font-size:18px,min-width:250px
    style P2C fill:#f5fff5,stroke:#333,stroke-width:3px,font-size:18px,min-width:250px
    style P2D fill:#f5fff5,stroke:#cc0000,stroke-width:4px,font-size:18px,min-width:250px
```

**Key Changes from Phase I to Phase II:**
- 🔴 **NEW**: Intraday aFRR market integration
- 🔴 **NEW**: Battery Degradation modeling and optimization
- ✅ **Continued**: Investment Optimization
- ✅ **Continued**: Configuration Optimization

#### Phase II Market Features Comparison

| Feature | Day-Ahead Market (EPEX SPOT) | FCR Capacity Market | aFRR Capacity Market | **(NEW)** aFRR Energy Market |
|---------|------------------------------|---------------------|----------------------|--------------------|
| **Mechanism** | Blind Auction | Daily Auction | Daily Auction | Continuous Merit Order Activation |
| **Gate Closure Time (D-1)** | 12:00 CET | 8:00 CET | 9:00 CET | 25 min before delivery (rolling) |
| **Product Granularity** | 15 minutes | 4 hours | 4 hours | 15 minutes |
| **Bid Structure** | Energy (MWh) | Symmetric Capacity (MW) | Asymmetric Capacity (MW) | Asymmetric Energy (MWh) |
| **Remuneration** | Pay-as-Cleared (Energy) | Pay-as-Cleared (Capacity) | Pay-as-Bid (Capacity) | Pay-as-Cleared (Energy) |
| **Minimum Bid Size** | 0.1 MW | 1 MW | 1 MW | 1 MW <br> *double-check if correct* |



#### Phase II Evaluation Criteria

| Evaluation Criteria | Ev. Weight | Description |
|---------------------|------------|-------------|
| **Revenue maximization** | 30% | This will evaluate how well the algorithm maximizes revenue based on market prices. |
| **BESS degradation**| 30% | This will evaluate the effect of charge/discharge optimal strategies on battery degradation. |
| **Investment optimization** | 10% | This will evaluate how well the optimal investment locations and markets are identified and assessed. |
| **Configuration optimization** | 10% | This criterion evaluates the analysis of key configuration parameters and their impact on BESS revenue. |
| **Code Quality and Documentation** | 20% | This will evaluate the clarity and structure of the code and deliverable documentation as well as the work presentation. |

> - [ ] Comment by Gen: Crucial to identify the **implementation priorities** of degradation factors: 
> 1. Which adds the largest marginal and which are small, and 
> 2. The complexity these factors add to the optimization model, if it worths including.

Following submission, each team’s battery operational profile will be analyzed using **the ORC Battery Degradation Model** to quantify the impact of their strategy on battery lifetime reduction.
  > - [ ] Comment by Gen: Crucial to study the ORC model and include it in the optimization process.

#### The Interdependence of the Four Optimization Tasks

A deeper analysis reveals a nested, hierarchical relationship between them that must be reflected in the project's modeling strategy.

The **"Optimal Configuration"** task is at the base of the hierarchy. The choice of a C-rate (0.5C, 0.33C, 0.25C) and a daily cycle limit (1.0, 1.5, 2.0) directly defines the physical constraints of the BESS, such as its maximum charge/discharge power and daily energy throughput. In addition, different C-rate and daily cycle limits, as well as SOC upper/lower bounds will also lead to different battery aging profiles. These parameters are fundamental inputs for the **"Optimal Operation"** model.

The **"Optimal Operation"** model forms the core of the analysis. It takes the configuration parameters as given and, based on market price data, calculates the maximum possible annual revenue for that specific BESS configuration in a given country. This revenue figure is the most critical output of the entire project. Furthermore, the operational strategy derived from this model directly influences battery degradation, which is a key consideration in Phase II.

Finally, the **"Optimal Investment"** task sits at the top of the hierarchy. It uses the annual revenue figures generated by the **"Optimal Operation"** model as its primary input to calculate the 10-year ROI. The optimal country for investment is simply the one that yields the highest ROI. This task synthesizes the outputs of the other two tasks to provide a comprehensive investment recommendation.



#### Battery Degradation: Why so important?
Battery degradation is a critical factor in the operation and management of Battery Energy Storage Systems (BESS). Over time, batteries lose their capacity to hold charge and their efficiency decreases due to various factors such as charge/discharge cycles, depth of discharge, temperature, and operational strategies.

The impact of aging model selection on battery revenue is significant. 
1. Using different aging models can substantially influence the optimal operating strategy of the battery. 
2. More complex aging cost models enable higher profits while maintaining similar SOH final impact[^1].

![Impact of different battery aging models on revenue and state of health (SOH)](official_instruction_docs/Battery_degradation.png)
*Figure 1: Comparison of battery aging models showing the trade-off between revenue optimization and battery degradation. More sophisticated aging cost models can achieve higher profitability while maintaining similar final SOH values.*
> - [ ] Comment from Gen: It's crucial to understand this graph.


#### Major Factors Affecting Battery Degradation During Operation
- [ ] TODO: Prioritize Battery Degradation Factors by P1-P3 (P1 the highest)

| **Factor** | **Impact on Battery Degradation** |
|--------|-------------------------------|
| **Temperature** <br> >consider regional temperature variations across the five given regions. | • Both high and low temperatures accelerate different degradation modes.<br>• High temperature (>40 °C): Speeds up side reactions (e.g., SEI growth, electrolyte decomposition, gas formation) → capacity fade and internal resistance rise.<br>• Low temperature (<0 °C): Increases lithium plating on the anode during charging → irreversible lithium loss and safety risks.<br>• Thermal management is critical; degradation roughly doubles for every 10 °C increase (Arrhenius behavior). |
| `P1` **Charge/Discharge Rate (C-rate)** | • Higher C-rates accelerate degradation.<br>• In fast charging, lithium ions can't diffuse fast enough → lithium plating on the anode.<br>• High discharge rates cause increased internal heating, mechanical strain, and contact loss which causes reduced active material utilization and faster capacity fade. |
| `P1` **SoC Range** | • Operating at very high or very low SoC accelerates aging.<br>• High SoC (>90%): Cathode oxidation, transition metal dissolution, electrolyte oxidation.<br>• Low SoC (<10%): Copper dissolution from the anode current collector and deep lithiation damage.<br>• *Restriction of SoC window (e.g., 20–80%) can minimize structural and chemical stress.* |
| `p1` **Depth of Discharge** | • Larger DoD (e.g., 0–100%) shortens cycle life; shallow cycling (e.g., 20–80%) improves lifetime.<br>• Each cycle's voltage and strain swing cause mechanical and chemical stress on electrodes.<br>• High DoD → More electrode expansion/contraction → micro-cracks and SEI rupture → increased irreversible capacity loss. |
| **Battery Management System (BMS) Strategy** | • Directly influences lifetime by controlling operation conditions.<br>• Smart algorithms (SoC windowing, temperature regulation, current limits) can minimize stress; poor algorithms exacerbate it.<br>• Optimized BMS can double the usable life. |
| `P2` **Calendar Aging (Storage Conditions)** <br> - [ ] check this [aging aware MPC](https://gitlab.lrz.de/open-ees-ses/aging-aware-MPC) | • Even when not in use, batteries degrade over time.<br>• SEI thickening, electrolyte oxidation, and loss of cyclable lithium occur during storage, especially at high temperature and SoC.<br>• Degradation is faster at high SoC and high temperature — typically expressed as a function of (T, SoC). |

#### [Same data for Investment and Configuration Optimization as Phase I](#data-for-investment-and-configuration-optimization-in-phase-i)


#### Bonus: Challenge for real-time trading: Uncertain aFRR energy activation and revenue
* In reality, aFRR energy is activated on a 4-second level based on the cross-border marginal price (CBMP) computed in the PICASSO platform. 4-second CBMP prices are not provided by Huawei, but could be downloaded here: https://www.transnetbw.de/en/energy-market/ancillary-services/picasso 
* If you want to do considerations on 4-second prices, use data from TNG (TransnetBW TSO).


## Methodology Overview

### Phase 2 Development Architecture

**Core Components:**
1. **Data Pipeline** (`py_script/data/`)
   - `load_process_market_data.py`: Market data loading and preprocessing
   - `visualize_market_data.py`: Market data exploration and visualization
   - `exceptions.py`: Custom exception handling for data operations
   - **Key Feature:** Automatic conversion of aFRR energy zero prices to NaN (market not activated)

2. **Optimization Models** (`py_script/core/optimizer.py`)
   - **Model I (`BESSOptimizerModelI`)**: Base 4-market optimization (DA, FCR, aFRR capacity, aFRR energy)
   - **Model II (`BESSOptimizerModelII`)**: Model I + Cyclic aging cost (segment-based degradation)
   - **Model III (`BESSOptimizerModelIII`)**: Model II + Calendar aging cost (SOS2 piecewise-linear)
   - **Architecture:** Decoupled `solve_model()` and `extract_solution()` for clean inheritance

3. **Validation & Testing** (`py_script/validation/`)
   - `results_exporter.py`: Standardized result saving with timestamped directories
   - `run_optimization.py`: Single-pass optimization runner
   - `constraint_validator.py`: Post-optimization constraint verification
   - `compare_optimizations.py`: Multi-scenario comparison tools

4. **Visualization** (`py_script/visualization/`)
   - `optimization_analysis.py`: BESS operation visualizations (SOC, power, markets, revenue)
   - `aging_analysis.py`: Degradation model validation plots
   - `market_data_analysis.py`: Market data exploration plots

5. **MPC Framework** (`py_script/mpc/`)
   - `mpc_simulator.py`: Rolling-horizon Model Predictive Control
   - `meta_optimizer.py`: Multi-scenario configuration optimization

### Model Progression & Implementation Status

```
✅ Model (i): Base + aFRR Energy Market
   - 4-market co-optimization (DA, FCR, aFRR capacity, aFRR energy)
   - Expected Value (EV) weighting for aFRR activation probability
   - Total power tracking: p_total = p_DA + p_aFRR_E
   - Status: Implemented and validated

✅ Model (ii): Model (i) + Cyclic Aging Cost
   - 10-segment SOC decomposition (447.2 kWh each)
   - Piecewise linear cost: 0.0052-0.099 EUR/kWh discharged
   - Replaces hard daily cycle limit with flexible cost
   - Status: Implemented and validated

✅ Model (iii): Model (ii) + Calendar Aging Cost
   - SOS2 piecewise-linear approximation (5 SOC breakpoints)
   - Based on Collath et al. (2023) methodology
   - Meta-parameter α for degradation price tuning
   - Status: Implemented and validated
```

### Data Processing Pipeline

1. **Raw Data Sources:**
   - `data/TechArena2025_Phase2_data.xlsx`: Multi-sheet Excel with 4 markets
   - Markets: Day-Ahead, FCR, aFRR Capacity, aFRR Energy (NEW in Phase 2)
   - Temporal resolution: 15-min (energy markets), 4-hour blocks (capacity markets)

2. **Preprocessing Steps:**
   - Wide-to-tidy format conversion for analysis
   - DE_LU → DE renaming for consistency across markets
   - **Critical:** aFRR energy price = 0 → NaN (market not activated)
   - Block ID and Day ID assignment for capacity markets
   - Timestamp alignment to nearest 15-minute interval

3. **Configuration Files** (`data/p2_config/`)
   - `aging_config.json`: Cyclic and calendar aging parameters
   - `afrr_ev_weights_config.json`: Activation probability weights
   - `solver_config.json`: Solver time limits and parameters
   - `investment.json`: WACC, inflation rates by country
   - `mpc_config.json`: MPC horizon and rolling parameters

### Optimization Framework

**Solver Selection (Auto-detection):**
- Priority: Gurobi > CPLEX > HiGHS > CBC > GLPK
- Consistent time limits across all solvers (default: 600s)
- Support for both commercial and open-source solvers

**Model Statistics (Full-Year Optimization):**
- **Time Horizon:** 35,040 intervals (15-min resolution, 8,760 hours)
- **Variables:** ~140,000 total (70K continuous + 70K binary)
  - Model I: p_ch, p_dis, p_afrr_pos_e, p_afrr_neg_e, p_total_ch, p_total_dis, e_soc, c_fcr, c_afrr_pos, c_afrr_neg
  - Model II: +p_ch_j, +p_dis_j, +e_soc_j (10 segments each)
  - Model III: +lambda_cal (5 breakpoints × 35K intervals)
- **Constraints:** ~120,000 total
  - SOC dynamics: 35K equations
  - Market constraints: 70K inequalities (min bids, power limits)
  - Degradation: 15K (segment balance, SOS2)
- **Solve Time:** 5-30 minutes per scenario (Gurobi), 15-60 minutes (open-source)
- **Memory Usage:** ~4-8 GB per full-year optimization

### Results and Validation Approach

**Output Structure** (`validation_results/YYYYMMDD_HHMMSS_run_name/`):
- `solution_timeseries.csv`: Complete decision variable trajectories
- `performance_summary.json`: Metrics and metadata
- `plots/`: Visualization outputs (HTML interactive plots)

**Standard Validation Plots:**
1. **Comprehensive Strategy Analysis** (5 panels):
   - SOC trajectory with reference lines
   - Charge/discharge power decisions
   - FCR capacity bids vs prices
   - Day-ahead market prices with discharge highlighting
   - Cumulative revenue breakdown (DA, AS capacity, aFRR energy)

2. **Market-Specific Visualizations:**
   - DA market: Price-bid correlation, arbitrage opportunities
   - aFRR energy: Activation periods, zero-price handling
   - Capacity markets: Block-level bidding strategy

3. **Degradation Validation** (Model II/III):
   - Stacked cyclic SOC segments (10 tanks)
   - Calendar aging curve (SOC vs cost)
   - Degradation cost breakdown over time

**Testing Scenarios:**
- T1: Single-pass optimization (32h, 7-day, 30-day horizons)
- T2: MPC rolling-horizon (5-day simulation with 36h horizon)
- T3: Configuration sensitivity (C-rate × daily cycles × α)
- T4: Country comparison (DE, AT, CH, HU, CZ) 

## Mathematical Model 

### Phase 2: Progressive Model Development

We extend the Phase I MILP (Base Model) through three progressive models, each adding new capabilities:

**Model (i): Base + aFRR Energy Market**
- Integrates 15-minute aFRR energy market for real-time balancing revenue
- New decision variables: `p_afrr_pos_e[t]`, `p_afrr_neg_e[t]`, `p_total_ch[t]`, `p_total_dis[t]`
- Total power constraint: `p_total = p_DA + p_aFRR_E` (co-optimization across energy markets)
- Expected Value (EV) weighting: `w_aFRR_pos[t]`, `w_aFRR_neg[t]` for activation probability
- Objective: `max(P_DA + P_ANCI + P_aFRR_E)` where aFRR energy revenue accounts for activation likelihood

**Model (ii): Model (i) + Cyclic Aging Cost**
- Replaces hard daily cycle limit with segment-based degradation cost
- SOC segmentation: 10 slices (`j=1..10`), each 447.2 kWh
- New variables per segment: `p_ch_j[t,j]`, `p_dis_j[t,j]`, `e_soc_j[t,j]`
- Piecewise linear cost function: `c_cyc[j]` ∈ [0.0052, 0.099] EUR/kWh
- Segment constraints: Stack invariance, no cross-flow between segments
- Objective: `max(Revenue - α * C_cyclic)` where α is meta-parameter (EUR/kWh → EUR/kWh)

**Model (iii): Model (ii) + Calendar Aging Cost (Full Phase 2 Model)**
- Adds SOC-dependent calendar aging using SOS2 variables
- 5 SOC breakpoints: 0%, 25%, 50%, 75%, 100% from Collath et al. (2023)
- New variables: `lambda_cal[t,i]` (convex combination weights), `c_cal_cost[t]` (EUR/hr)
- SOS2 constraint: At most 2 adjacent λ variables non-zero
- Calendar cost increases with SOC (encourages lower SOC storage)
- Objective: `max(Revenue - α * (C_cyclic + C_calendar))`

**Complete Mathematical Formulation:**
- Full LaTeX documentation: `doc/p2_model/p2_bi_model_ggdp.tex`
- Individual model details: `doc/p2_model/p2_3models_formulation.tex`
- Investment optimization: `doc/p2_model/p2_investment_opt.tex`

**Key Model Features:**
- Multi-market co-optimization (4 markets)
- Reserve energy constraints with configurable activation durations (τ parameter)
- Cross-market exclusivity (cannot provide FCR and aFRR simultaneously)
- Minimum bid size enforcement (DA: 0.1 MW, AS: 1.0 MW, aFRR energy: 0.1 MW)
- Power constraints based on C-rate configuration
- SOC dynamics with round-trip efficiency (η = 0.95)

## Investment Optimization

## Implementation Pipeline

### Development Branch Structure

- **`main`**: Stable release (Phase 1 archived)
- **`p2-full-model-3-clean`**: Current development branch (Phase 2)
  - All three models (i, ii, iii) implemented
  - Refactored optimizer architecture (decoupled solve/extract)
  - Comprehensive validation framework
  - Market data visualization suite
  
### Code Organization

```
TechArena2025_EMS/
├── py_script/
│   ├── core/
│   │   ├── optimizer.py          # Models I, II, III implementation
│   │   └── investment/           # Investment optimization (Phase 2 pending)
│   ├── data/
│   │   ├── load_process_market_data.py    # Data loading and preprocessing
│   │   ├── visualize_market_data.py       # Market data exploration
│   │   ├── exceptions.py                  # Custom exceptions
│   │   └── config.py                      # Configuration constants
│   ├── mpc/
│   │   ├── mpc_simulator.py      # Rolling-horizon MPC
│   │   └── meta_optimizer.py     # Multi-scenario optimization
│   ├── validation/
│   │   ├── results_exporter.py   # Standardized result saving (NEW)
│   │   ├── run_optimization.py   # Single-pass runner
│   │   └── constraint_validator.py
│   └── visualization/
│       ├── optimization_analysis.py      # BESS operation plots
│       ├── aging_analysis.py            # Degradation validation
│       └── market_data_analysis.py
├── data/
│   ├── TechArena2025_Phase2_data.xlsx   # Main data source
│   ├── p2_config/                        # Configuration files
│   │   ├── aging_config.json
│   │   ├── afrr_ev_weights_config.json
│   │   ├── solver_config.json
│   │   └── investment.json
│   └── parquet/                          # Processed data cache
├── notebook/
│   ├── p2a_market_data.ipynb            # Market data exploration
│   ├── p2b_optimizer.ipynb              # Optimizer testing harness
│   ├── p2c_mpc.ipynb                    # MPC validation
│   └── p2d_result_ana.ipynb             # Results analysis
├── validation_results/                   # Timestamped output directories
└── doc/
    ├── p2_model/                         # Mathematical formulations
    └── dev_log/                          # Development logs
```

### Key Implementation Features

**Optimizer Architecture (Refactored):**
- Separation of concerns: `solve_model()` only solves, `extract_solution()` extracts results
- Clean inheritance chain: Model I → Model II → Model III
- Each subclass extends parent's `extract_solution()` to add model-specific results
- Backward compatibility aliases maintained

**Data Preprocessing:**
- Critical aFRR energy handling: 0 → NaN conversion (market not activated)
- Timestamp alignment to 15-minute intervals
- Wide-to-tidy format conversion for analysis
- Block and day ID assignment for capacity markets

**Validation Framework:**
- Timestamped output directories with standardized structure
- CSV export of full solution trajectories
- JSON export of summary metrics and metadata
- Automated plot generation and saving
- Results comparison tools for multi-scenario analysis

**Visualization Suite:**
- Interactive Plotly plots with hover templates
- McKinsey-style formatting and color schemes
- 5-panel comprehensive strategy analysis
- Market-specific visualizations
- Degradation model validation plots

### Model Statistics

**Model I (Base + aFRR Energy):**
- Variables: ~70,000 continuous + 35,000 binary
- Constraints: ~105,000 total
- Solve time: 3-10 minutes (Gurobi), 10-30 minutes (open-source)

**Model II (+ Cyclic Aging):**
- Variables: ~140,000 continuous + 35,000 binary (10 segments)
- Constraints: ~120,000 total
- Solve time: 5-20 minutes (Gurobi), 15-45 minutes (open-source)

**Model III (+ Calendar Aging):**
- Variables: ~315,000 continuous + 35,000 binary (5 SOS2 breakpoints × 35K intervals)
- Constraints: ~155,000 total (including SOS2)
- Solve time: 10-30 minutes (Gurobi), 30-90 minutes (open-source)
- Memory: ~4-8 GB peak usage

**Performance Optimization Techniques:**
- Pre-computed block-to-time mappings (O(1) lookup)
- AS prices indexed by block instead of time
- Constraint functions use model parameters (no closures)
- Consistent solver time limits across all solvers

## Model Validation 

### Validation Approach and Testing Scenarios

**Phase 2 Validation Strategy:**

The validation approach follows a progressive testing methodology aligned with the three-model architecture:

**Test Suite T1: Model Behavior Validation (Per Model)**
- **T1.1 - Model I Validation:** 4-market operation without degradation
  - DA market: Arbitrage behavior, price-bid correlation
  - FCR capacity: Symmetric bidding, reserve energy constraints
  - aFRR capacity: Asymmetric bidding, upward/downward exclusivity
  - aFRR energy: Zero-price handling, activation probability weighting
  - Time horizons: 32h (quick), 7-day (typical), 30-day (extended)

- **T1.2 - Model II Validation:** Cyclic aging cost integration
  - Segment stacking verification (10 tanks)
  - Discharge ordering (bottom-to-top, FIFO)
  - Charge ordering (top-to-bottom, fill highest cost first)
  - Cost gradient impact on cycling behavior
  - α parameter sensitivity (0.1, 0.5, 1.0, 2.0)

- **T1.3 - Model III Validation:** Calendar aging cost integration
  - SOS2 constraint verification (at most 2 adjacent λ non-zero)
  - Piecewise-linear curve tracing (5 breakpoints)
  - SOC distribution shift (preference for lower SOC)
  - Combined cyclic + calendar cost impact
  - Full degradation model behavior

**Test Suite T2: Multi-Scenario Comparison**
- **T2.1 - Configuration Sensitivity:**
  - C-rate variation: 0.25, 0.33, 0.5 (fixed cycles=1.0, α=1.0)
  - Daily cycle variation: 1.0, 1.5, 2.0 (fixed C-rate=0.5, α=1.0)
  - α variation: 0.1, 0.5, 1.0, 2.0 (fixed config, measure profit-degradation tradeoff)

- **T2.2 - Country Comparison:**
  - 5 countries × 3 models = 15 scenarios
  - Metrics: Total profit, degradation costs, solver performance
  - Market participation patterns by country

- **T2.3 - Time Horizon Scaling:**
  - Short: 32h (single MPC horizon)
  - Medium: 7-day (weekly pattern)
  - Long: 30-day (monthly), 365-day (full year)
  - Solver performance vs problem size

**Test Suite T3: MPC Rolling-Horizon Validation**
- Horizon length: 36h (T_horizon)
- Implementation period: 24h (T_implement)
- Simulation period: 5-day, 30-day
- Comparison: MPC vs single-pass optimization
- Metrics: Computational efficiency, profit gap, constraint violations

**Test Suite T4: Constraint Verification**
- Post-optimization validation of all constraints
- SOC bounds: 0 ≤ e_soc[t] ≤ E_nom
- Power limits: |p_ch[t]|, |p_dis[t]| ≤ P_max
- Reserve energy: Upward/downward activation feasibility
- Cross-market exclusivity: FCR and aFRR capacity mutual exclusion
- Minimum bid sizes: All markets

**Validation Outputs:**
All validation results saved to timestamped directories:
```
validation_results/YYYYMMDD_HHMMSS_test_name/
├── solution_timeseries.csv           # Full decision variable trajectories
├── performance_summary.json          # Metrics, solver stats, config
└── plots/
    ├── comprehensive_analysis.html   # 5-panel strategy overview
    ├── da_market.html               # Day-ahead market behavior
    ├── afrr_energy_market.html      # aFRR energy with zero-price handling
    ├── capacity_markets.html        # FCR + aFRR capacity
    ├── soc_power_bids.html         # SOC trajectory + power decisions
    ├── cyclic_soc_segments.html    # Stacked segment visualization (Model II)
    └── calendar_aging_curve.html   # SOS2 curve validation (Model III)
```

**Validation Status:**
- ✅ T1.1 - Model I: Validated (32h, 7-day scenarios)
- ✅ T1.2 - Model II: Validated (segment behavior, α sensitivity)
- ✅ T1.3 - Model III: Validated (SOS2 curves, combined aging)
- ⏳ T2.1 - Configuration: In progress
- ⏳ T2.2 - Country comparison: Partial (CH, DE tested)
- ⏳ T2.3 - Time scaling: In progress (32h, 7-day complete)
- ✅ T3 - MPC: Validated (5-day simulation)
- ✅ T4 - Constraints: Automated validator implemented


## Final Results and Analysis

### Phase 2 Implementation Status (as of Nov 2025)

**Completed Components:**
- ✅ **Model I**: Base 4-market optimization with aFRR energy market
- ✅ **Model II**: Cyclic aging cost with 10-segment SOC decomposition
- ✅ **Model III**: Calendar aging cost with SOS2 piecewise-linear approximation
- ✅ **Data Pipeline**: Market data loading, preprocessing, and visualization
- ✅ **Validation Framework**: Results exporter, constraint validator, comparison tools
- ✅ **Visualization Suite**: 5-panel comprehensive analysis, market-specific plots, aging validation
- ✅ **MPC Framework**: Rolling-horizon simulation with configurable horizons

**In Progress:**
- ⏳ **Full-Year Optimization**: Multi-country, multi-configuration analysis
- ⏳ **Investment Optimization**: 10-year NPV calculation with degradation
- ⏳ **Configuration Optimization**: Systematic C-rate × cycle × α sensitivity analysis
- ⏳ **Discounted Aging Model**: NPV-aware time-varying degradation cost (Collath Section 3.4)

**Pending:**
- ⏸️ **Meta-Optimizer**: Automated hyperparameter tuning (α optimization)
- ⏸️ **ORC Degradation Model**: Integration of official competition degradation model
- ⏸️ **Real-time Trading**: 4-second CBMP price integration for aFRR energy
- ⏸️ **Uncertainty Modeling**: Stochastic price forecasting

### Key Findings (Preliminary)

**Market Participation Patterns:**
- DA market: Primary revenue source, strong arbitrage opportunities during high volatility
- FCR capacity: Consistent baseload revenue, limited by reserve energy constraints
- aFRR capacity: Selective participation, higher in upward than downward
- aFRR energy: Significant opportunity cost when market not activated (zero prices)

**Degradation Model Impact:**
- Model I (no aging): Aggressive cycling, maximum short-term profit
- Model II (cyclic only): Moderate cycling reduction, segment-cost gradient visible
- Model III (cyclic + calendar): Further cycling reduction, preference for lower SOC storage
- α sensitivity: Higher α → lower cycling → lower profit but extended lifetime

**Solver Performance:**
- Gurobi: 5-30 min for full-year Model III (fastest)
- CPLEX: 10-45 min (competitive with Gurobi)
- HiGHS: 30-90 min (best open-source option)
- CBC: 60-180 min (fallback)

**Technical Achievements:**
- Successfully validated all three progressive models
- Established reproducible validation framework
- Created comprehensive visualization suite
- Refactored optimizer for clean inheritance and extensibility

### Next Steps

1. **Complete Configuration Analysis:**
   - Run systematic sensitivity analysis (C-rate × cycles × α)
   - Generate Pareto fronts (profit vs degradation)
   - Identify optimal configurations per country

2. **Investment Optimization:**
   - Implement 10-year NPV calculation
   - Incorporate country-specific WACC and inflation
   - Compare countries with and without degradation

3. **ORC Model Integration:**
   - Study official competition degradation model
   - Replace or validate against current aging model
   - Re-run optimization with ORC model

4. **Final Report Preparation:**
   - Document complete methodology
   - Generate publication-quality figures
   - Prepare code documentation and README

**Target Completion:** December 2025



## Sample Data 
The whole data set spans across the whole year of 2024 with 15-minute resolution for DA market and aFRR energy markets, and 4-hour resolution for FCR and aFRR capacity markets. Below we provide sample data snippets for each market.

### DA
Remark: For DA data, DE_LU column represents the joint Germany and Luxembourg market prices.

```json
[
  {
    "timestamp":"2024-01-01T00:00:00.000",
    "DE_LU":39.91,
    "AT":14.08,
    "CH":25.97,
    "HU":0.1,
    "CZ":0.1
  },
  {
    "timestamp":"2024-01-01T00:15:00.000",
    "DE_LU":-0.04,
    "AT":14.08,
    "CH":25.97,
    "HU":0.1,
    "CZ":0.1
  },
  {
    "timestamp":"2024-01-01T00:30:00.001",
    "DE_LU":-9.01,
    "AT":0.48,
    "CH":25.97,
    "HU":0.1,
    "CZ":0.1
  },
  {
    "timestamp":"2024-01-01T00:45:00.001",
    "DE_LU":-29.91,
    "AT":-3.64,
    "CH":25.97,
    "HU":0.1,
    "CZ":0.1
  }
]
```


### aFRR Energy
```json
[
  {
    "timestamp":"2024-01-01T00:00:00.000",
    "DE_Pos":50.3411486486,
    "DE_Neg":29.702029703,
    "AT_Pos":86.43,
    "AT_Neg":0.0,
    "CH_Pos":38.7,
    "CH_Neg":0.0,
    "HU_Pos":0.0,
    "HU_Neg":0.0,
    "CZ_Pos":144.0,
    "CZ_Neg":0.0
  },
  {
    "timestamp":"2024-01-01T00:15:00.000",
    "DE_Pos":46.9457142857,
    "DE_Neg":40.87125,
    "AT_Pos":85.25,
    "AT_Neg":0.17,
    "CH_Pos":38.8,
    "CH_Neg":8.32,
    "HU_Pos":0.0,
    "HU_Neg":0.6014018923,
    "CZ_Pos":117.26,
    "CZ_Neg":53.39
  },
  {
    "timestamp":"2024-01-01T00:30:00.001",
    "DE_Pos":43.8748717949,
    "DE_Neg":21.2391111111,
    "AT_Pos":85.44,
    "AT_Neg":0.73,
    "CH_Pos":38.76,
    "CH_Neg":0.0,
    "HU_Pos":0.0,
    "HU_Neg":1.1334522217,
    "CZ_Pos":140.84,
    "CZ_Neg":62.84
  }
]
```

### FCR
```json
[
  {
    "timestamp":"2024-01-01T00:00:00.000",
    "DE":114.8,
    "AT":114.8,
    "CH":114.8,
    "HU":3.1851080706,
    "CZ":416.0
  },
  {
    "timestamp":"2024-01-01T04:00:00.000",
    "DE":104.4,
    "AT":104.4,
    "CH":104.4,
    "HU":3.1851080706,
    "CZ":416.0
  },
  {
    "timestamp":"2024-01-01T08:00:00.001",
    "DE":68.8,
    "AT":68.8,
    "CH":68.8,
    "HU":3.1851080706,
    "CZ":416.0
  },
  {
    "timestamp":"2024-01-01T12:00:00.001",
    "DE":77.6,
    "AT":77.6,
    "CH":77.6,
    "HU":3.1851080706,
    "CZ":390.4
  }
]
```


### aFRR Capacity
```json
[
  {
    "timestamp":"2024-01-01T08:00:00.001",
    "DE_Pos":6.33,
    "DE_Neg":13.07,
    "AT_Pos":5.57,
    "AT_Neg":8.5,
    "CH_Pos":6.66,
    "CH_Neg":23.08,
    "HU_Pos":10.048546094,
    "HU_Neg":13.327884282,
    "CZ_Pos":29.1639497143,
    "CZ_Neg":10.6757588259
  },
  {
    "timestamp":"2024-01-01T12:00:00.001",
    "DE_Pos":4.12,
    "DE_Neg":15.02,
    "AT_Pos":3.56,
    "AT_Neg":9.52,
    "CH_Pos":4.41,
    "CH_Neg":20.63,
    "HU_Pos":0.0,
    "HU_Neg":0.0,
    "CZ_Pos":23.342256,
    "CZ_Neg":4.1489131297
  },
]
```

### Technical Description: "Scaled and Discounted" Aging Cost (Collath et al. - Section 3.4)

This describes an advanced optimization technique designed to maximize the Net Present Value (NPV) of a BESS, rather than just the total cumulative profit. It consists of two independent but complementary parts: "Scaling" and "Discounting".

**1. "Scaled" Aging Model (The Baseline)**

* **Problem:** The "Non-scaled" (or "fully accurate") degradation model  exhibits a sublinear dependency on time (e.g., $\sqrt{t}$). This results in prohibitively high aging costs in the early years of operation when the battery is new.
* **Behavioral Consequence:** This high initial cost forces the optimizer to be overly conservative, forgoing valuable early-life profit opportunities. This leads to a sub-optimal lifetime NPV.
* **"Scaled" Solution:** This approach linearizes the degradation model at a *fixed* point, representing a mid-life aging state ($Q^{loss,cal}=5\%$ and $Q^{loss,cyc}=5\%$), and uses this *same* linearization for the *entire* BESS lifetime.
* **Result:** The optimizer perceives a moderate, consistent aging cost from Year 1. This encourages more consistent profit generation across the lifetime and results in a significantly higher NPV (340.3 EUR/kWh) compared to the "Non-scaled" model (291.9 EUR/kWh).

**2. "Discounted" Aging Model (The NPV-aware Enhancement)**

* **Goal:** To further optimize for NPV, this technique "front-loads" profits by internalizing the time value of money (as defined by the interest rate $i$) directly into the optimizer's cost function.
* **Mechanism:** The aging cost parameter $c^{aging}$ (in EUR/kWh) is no longer treated as a constant. It is made time-dependent by applying the discount rate in reverse, as defined in **Equation (28)**:

    $$c^{aging^{\prime}} = c^{aging} \cdot (1+i)^{m}$$

* **Variable Definitions:**
    * $c^{aging^{\prime}}$: The new, time-varying aging cost used by the optimizer.
    * $c^{aging}$: The original, "optimal" constant aging cost (the tuning parameter).
    * $i$: The interest rate used for the project's financial evaluation.
    * $m$: The current fractional year of operation since the start of the simulation.

* **Impact on Optimization:**
    * In the early years ($m \approx 0$), the optimizer sees a *low* aging cost ($c^{aging^{\prime}} \approx c^{aging}$). This incentivizes more aggressive cycling to capture immediate profit.
    * In the later years ($m$ is large), the optimizer sees an *exponentially higher* aging cost ($c^{aging^{\prime}} \gg c^{aging}$), which strongly disincentivizes cycling as the perceived cost outweighs the potential profit.

* **Final Outcome:** This strategy intentionally shifts profit generation from the less valuable later years to the highly valuable early years. This results in the highest possible NPV (346.6 EUR/kWh) of all strategies, even if the total cumulative *undiscounted* profit (551.1 EUR/kWh) is slightly lower than the standard "Scaled" model (574.2 EUR/kWh).



___


## Bibliography
[^1]: Collath, Nils, et al. "Increasing the lifetime profitability of battery energy storage systems through aging aware operation." *Applied Energy* 348 (2023): 121531.
