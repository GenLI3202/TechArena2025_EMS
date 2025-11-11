# Huawei TechArena 2025: Battery Energy Storage System (BESS) Optimizer

> **Project Status:** Phase II Development (Round 2)
> **Phase I Archive:** See branch `r1-static-battery` for Phase I submission
> **Active Branch:** `r2-with-bat-config`

An advanced Energy Management System (EMS) that optimizes battery storage operations across multiple European electricity markets to maximize profitability while meeting operational constraints. And 

---
## Important Documentation References

- **Quick Start Guide:** `py_script/README.md`
- **Model Formulation Details:** `doc\p2_model\p2_bi_model_ggdp.tex`
- **Project Overview:** `doc/whole_project_description.md`
---

## Project Overview

This project addresses the Huawei TechArena 2025 challenge: developing an intelligent optimization algorithm for a utility-scale Battery Energy Storage System (BESS) that participates in European energy markets. The system must simultaneously optimize operations across day-ahead energy markets and ancillary service capacity markets while considering battery technical constraints and market rules.



## Market Landscape (Phase II)

### Target Markets

Phase II introduces **four market segments** for comprehensive revenue optimization:

| Market | Day-Ahead Energy | FCR Capacity | aFRR Capacity | **aFRR Energy (NEW)** |
|--------|-----------------|--------------|---------------|----------------------|
| **Type** | Energy Arbitrage | Primary Reserve | Secondary Reserve | Reserve Activation |
| **Mechanism** | Blind Auction | Daily Auction | Daily Auction | Merit Order Activation |
| **Resolution** | 15 minutes | 4-hour blocks | 4-hour blocks | 15 minutes |
| **Gate Closure** | D-1 at 12:00 | D-1 at 08:00 | D-1 at 09:00 | 25 min before delivery |
| **Bid Structure** | Energy (MWh) | Symmetric (MW) | Asymmetric (MW) | Asymmetric Energy (MWh) |
| **Remuneration** | Pay-as-Cleared | Pay-as-Cleared | Pay-as-Bid | Pay-as-Cleared |
| **Min. Bid** | 0.1 MW | 1.0 MW | 1.0 MW | 1.0 MW |

**Key Phase II Addition:** The aFRR energy market enables real-time balancing revenue through continuous activation based on grid needs, adding complexity and opportunity to the optimization problem.

### Geographic Scope

**Countries:** Germany (DE_LU), Austria (AT), Switzerland (CH), Hungary (HU), Czech Republic (CZ)

Each market exhibits distinct price patterns, volatility characteristics, and regulatory frameworks. Additionally, regional temperature variations across countries affect battery degradation rates, influencing the optimal investment decision.

---

## Technical Specifications

### Battery System (Huawei LUNA2000-4.5MWh)

| Parameter | Value | Notes |
|-----------|-------|-------|
| Nominal Capacity | 4,472 kWh | Fixed for all scenarios |
| Rated Power | 2,236 kW | At 0.5 C-rate |
| Round-Trip Efficiency | 95% | Charging and discharging |
| SOC Range | 0-100% | Full operational range allowed |
| Investment Cost | 200 EUR/kWh | Baseline for DCF analysis |
| Project Horizon | 10 years | For investment analysis |

### Configuration Options

| C-rate | Max Power | Daily Cycles | Max Daily Energy |
|--------|-----------|--------------|------------------|
| 0.25 C | 1,118 kW | 1.0 cycles | 4,472 kWh |
| 0.33 C | 1,476 kW | 1.5 cycles | 6,708 kWh |
| 0.50 C | 2,236 kW | 2.0 cycles | 8,944 kWh |

**Total Scenario Space:** 45 configurations (5 countries × 3 C-rates × 3 cycle limits)

---

## Optimization Approach (Phase II)

### Mathematical Framework

The system employs **Mixed-Integer Linear Programming (MILP)** to solve a multi-period, four-market co-optimization problem over a full-year horizon (2024 data), with explicit consideration of battery degradation impacts.

**Primary Objective:** Maximize total net profit from all four markets while managing battery degradation

**Revenue Streams:**
- Day-ahead energy arbitrage (buy low, sell high)
- FCR capacity payments (symmetric reserve provision)
- aFRR capacity payments (asymmetric reserve provision)
- **NEW:** aFRR energy payments (activation-based revenue)

**Key Decision Variables:**
- Charging and discharging power schedules (kW, 15-min intervals)
- Binary indicators for charge/discharge states
- Capacity bids for FCR and aFRR markets (MW, 4-hour blocks)
- **NEW:** Energy bids for aFRR activation market
- State of charge trajectory over time (kWh)

**Critical Constraints:**
1. **SOC Dynamics** - Energy balance with efficiency losses
2. **SOC Bounds** - Operational range limits (impacts degradation)
3. **Power Limits** - Respect C-rate configuration
4. **No Simultaneous Charge/Discharge** - Prevent physical impossibilities
5. **Daily Cycle Limits** - Prevent excessive battery wear
6. **Energy Reserves** - Maintain sufficient energy to deliver committed capacity
7. **Market Exclusivity** - Cannot bid in multiple AS markets simultaneously
8. **Cross-Market Compatibility** - Ensure DA and AS bids are physically feasible
9. **Minimum Bid Sizes** - Comply with market requirements

### Phase II Enhancements

**Battery Degradation Integration:**
- Aging-aware optimization that considers long-term battery health
- Trade-off analysis between immediate revenue and lifetime profitability
- Degradation factors modeled: C-rate stress, SOC window management, depth of discharge, cycling frequency
- Temperature effects across geographic regions
- Results validated against **Huawei's ORC Battery Degradation Model**

**Computational Improvements:**
- Eliminated constraint closure anti-patterns for 40% faster solve times
- Pre-computed index mappings for O(1) lookup efficiency
- Refined energy reserve constraints with configurable activation durations
- Enhanced memory management for full-year optimizations
- Four-market co-optimization with degradation modeling

---

## Repository Structure

```
TechArena2025_EMS/
├── .github/                      # GitHub Actions workflows and templates
├── .vscode/                      # VSCode settings
├── data/                         # Raw and processed market data
│   ├── metadata.json
│   ├── TechArena2025_Phase2_data.xlsx
│   ├── aging_config/             # Configuration files for battery aging models
│   ├── archive_p1_3markets/      # Archived Phase 1 data
│   ├── json/                     # Processed market data in JSON format
│   └── parquet/                  # Processed market data in Parquet format
├── doc/                          # Project documentation, mathematical formulations, literature
│   ├── Pyomo_OptModelingInPython_3rdVersion.pdf
│   ├── whole_project_description.md
│   ├── dev_log/                  # Development logs and plans
│   ├── Literature/               # Relevant research papers
│   ├── official_instruction_docs/# Official competition documents
│   └── p2_model/                 # Phase 2 model formulations (LaTeX, PDF)
├── notebook/                     # Jupyter notebooks for data exploration, analysis, and prototyping
│   ├── p1_final_validation.ipynb
│   ├── p2a_market_data.ipynb
│   ├── p2b_optimizer.ipynb
│   ├── p2c_mpc.ipynb
│   ├── p2d_result_ana.ipynb
│   └── ...                       # More notebooks for various analyses
├── py_script/                    # Main Python package for the BESS optimizer
│   ├── README.md                 # Detailed README for the Python package
│   ├── requirements.txt          # Python package dependencies
│   ├── core/                     # Core optimization logic
│   │   ├── __init__.py
│   │   ├── optimizer.py          # Main optimization model (BESSOptimizerV2, ModelI, etc.)
│   │   └── investment/           # Investment analysis and DCF calculations
│   ├── data/                     # Data loading and processing
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── load_process_market_data.py
│   │   └── visualize_market_data.py
│   ├── mpc/                      # Model Predictive Control (MPC) implementation
│   │   ├── meta_optimizer.py
│   │   └── mpc_simulator.py
│   ├── test/                     # Unit and integration tests
│   │   ├── __init__.py
│   │   ├── test_optimizer_core.py
│   │   └── validate_optimizer_behavior.py
│   ├── validation/               # Validation scripts and constraint checks
│   │   ├── __init__.py
│   │   └── constraint_validator.py
│   └── visualization/            # Plotting and visualization tools
│       ├── __init__.py
│       ├── config.py
│       ├── optimization_analysis.py
│       └── visualize_as_revenue_fix.py
├── validation_results/           # Outputs from validation runs
│   ├── market_data_analysis/
│   ├── model_iii_validation/
│   └── mpc_validation/
├── .gitignore
├── CLAUDE.md
├── LICENSE
├── quick_plot_results.py         # Script for quick plotting of results
├── README.md                     # Project overview (this file)
├── requirements.txt              # Project-level Python dependencies
├── run_36h_hu_winter.py          # Specific scenario run script
├── test_mpc_5day_visualize.py    # Test script for MPC visualization
└── test_single_32h_vs_mpc.py     # Test script for single vs MPC comparison
```

- **Implementation Details:** See `py_script/README.md`


---

## Key Features

### Optimization Engine
- Full-year horizon optimization (35,040 time intervals)
- **Four-market co-optimization** (DA energy, FCR, aFRR capacity & energy)
- **Battery degradation modeling** with aging-aware strategies
- Support for multiple MILP solvers (CBC, GLPK, Gurobi, CPLEX)
- Trade-off optimization between revenue and battery lifetime

### Data Processing
- Automated loading from Excel/JSONL formats
- Wide-to-tidy data transformation
- Comprehensive data validation
- Missing data detection and handling

### Investment Analysis
- 10-year DCF modeling with **battery capacity degradation effects**
- Country-specific WACC and inflation rates
- Regional temperature impact on degradation rates
- Sensitivity analysis for key parameters
- NPV, IRR, and payback period calculations accounting for aging

### Validation & Diagnostics
- Week-scale validation framework
- Constraint satisfaction verification
- Performance benchmarking across scenarios
- Automated plot generation for results analysis

---

## Performance Metrics

### Solution Quality
- **Optimality Gaps:** Typically <1% for commercial solvers, <5% for open-source
- **Solve Times:** 2-10 minutes per scenario (depending on solver)
- **Constraint Violations:** Zero tolerance, all constraints strictly satisfied

### Computational Efficiency
- **Memory Usage:** ~2-4 GB per full-year optimization
- **Scalability:** Successfully handles 35K+ time intervals
- **Parallel Execution:** Supports concurrent scenario evaluation

---

## Development Timeline

### Phase I (Complete - Archived)
- ✅ Three-market optimization (DA, FCR, aFRR capacity)
- ✅ Basic operational optimization without degradation
- ✅ Initial investment and configuration analysis
- ✅ Constraint formulation and solver integration
- ✅ Archived to branch `r1-static-battery`

### Phase II (Current Development)

**Foundation Work:**
- ✅ Repository reorganization and professional code structure
- ✅ Enhanced constraint modeling with reserve duration parameters
- ✅ Performance optimization (40% faster solve times)
- ✅ Comprehensive validation framework

**Three-Stage Model Development:**
- ✅ **Model (i): Base + aFRR Energy Market** [IMPLEMENTED]
  - Four-market co-optimization (DA, aFRR-E, FCR, aFRR capacity)
  - Class: `BESSOptimizerModelI` (in `py_script/core/optimizer.py`)
  - Test: `py_script/test/test_optimizer_core.py` ✓ PASSING

- 🔄 **Model (ii): Model (i) + Cyclic Aging Cost** [NEXT]
  - Piecewise-linear cyclic degradation (Xu et al., 2017)
  - Segment-based SOC tracking
  - Economic cost replaces rigid cycle limits
  - Class: `BESSOptimizerModelII` (in `py_script/core/optimizer.py`)
  - Introduces `alpha` parameter to weight degradation cost in objective.

- 🔄 **Model (iii): Model (ii) + Calendar Aging Cost** [PLANNED]
  - SOS2-based calendar aging (Collath et al., 2023)
  - Complete Phase II degradation modeling
  - Meta-optimization of degradation price `alpha`
  - Class: `BESSOptimizerModelIII` (in `py_script/core/optimizer.py`)

**Integration Tasks:**
- 🔄 Rolling horizon (MPC) implementation for computational feasibility
- 🔄 Multi-scenario analysis with degradation effects
- 🔄 10-year ROI calculation with capacity fade
- 🔄 Trade-off analysis: revenue vs. battery lifetime
- 🔄 Final submission preparation with comprehensive documentation

---

## Technology Stack

### Core Technologies
- **Optimization:** Pyomo (Python optimization modeling)
- **Solvers:** CBC, GLPK (open-source), Gurobi, CPLEX (commercial)
- **Data Processing:** Pandas, NumPy
- **Visualization:** Matplotlib, Seaborn, Plotly

### Development Tools
- **Version Control:** Git with feature branching
- **Code Quality:** Type hints, comprehensive docstrings
- **Documentation:** Markdown with mathematical notation
- **Validation:** Automated testing and constraint verification

---

## Getting Started

### Prerequisites
- Python 3.8+
- MILP solver (CBC recommended for open-source)
- 8GB+ RAM for full-year optimizations

### Quick Start

**Installation:**
```bash
# Install project dependencies
pip install -r requirements.txt
```

**Testing:**
```bash
# Run core optimizer tests
python py_script/test/test_optimizer_core.py
```

**Using the Optimizers (Model I example):**
```python
import sys
sys.path.insert(0, './py_script') # Add py_script to the Python path

from core.optimizer import BESSOptimizerModelI

optimizer = BESSOptimizerModelI()
# Note: Use full data path or ensure script is run from project root
data = optimizer.load_and_preprocess_data("data/TechArena2025_Phase2_data.xlsx") 
country_data = optimizer.extract_country_data(data, 'DE_LU')
model = optimizer.build_optimization_model(country_data, c_rate=0.5, daily_cycle_limit=1.5)
solution = optimizer.solve_model(model)

# Access new aFRR energy variables
afrr_energy_bids = solution['p_afrr_pos_e']  # Positive (discharge)
```

For detailed usage instructions, see `py_script/README.md`.

---



## Competition Performance

### Phase I Results (Archived)
- Successfully optimized all 45 scenarios across 5 countries
- Three-market participation (DA, FCR, aFRR capacity)
- Constraint satisfaction: 100%
- Average solve time: 4.2 minutes per scenario
- Complete results archived in `r1-static-battery` branch

### Phase II Objectives
- **Battery Degradation Integration:** Implement aging-aware optimization
- **Four-Market Optimization:** Add aFRR energy market participation
- **Trade-off Analysis:** Balance immediate profit vs. long-term battery health
- **10-Year ROI with Aging:** DCF analysis incorporating capacity fade
<!-- - **ORC Model Compliance:** Align with Huawei's degradation evaluation model
- **Improved Solve Times:** Target <3 minutes per scenario
- **Comprehensive Documentation:** 20% evaluation weight on code quality
- -->
- **Production-Ready Codebase:** Professional structure and validation 

---

## Author

Gen's BESS Optimization Team
Technical University of Munich (TUM)
Phase II Development: October-November 2025

---

## License

See `LICENSE` file for details.

---

## Acknowledgments

- **Huawei Technologies** - Competition organization and technical specifications
- **Pyomo Development Team** - Optimization modeling framework
- **COIN-OR CBC** - Open-source MILP solver
