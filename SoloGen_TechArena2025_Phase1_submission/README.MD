# TechArena 2025 Phase 1 - Battery Energy Storage System Optimization

**Team:** SoloGen  
**Challenge:** Huawei TechArena 2025 Phase I  
**Date:** October 2025

## Executive Summary

This submission presents an advanced **Battery Energy Storage System (BESS) optimization framework** that simultaneously optimizes:
- **Operational dispatch** across day-ahead energy arbitrage and ancillary service markets (FCR, aFRR)
- **Technical configuration** (C-rate and daily cycle limits)
- **Investment location** (5 European countries: DE, AT, CH, HU, CZ)

Our solution achieves **100% successful optimization** across all 45 scenarios, with levelized ROI ranging from 47.6% to 268.5% over a 10-year investment horizon.

---

## Validation Results

### Configuration Optimization

| Country | Best C-rate | Daily Cycles | Annual Profit (kEUR/MW) | Levelized ROI (%) |
|---------|-------------|--------------|-------------------------|-------------------|
| **CZ**  | **0.50 C**  | **1.5**      | **1,074.12**            | **268.53%**       |
| CH      | 0.50 C      | 1.5          | 588.12                  | 147.03%           |
| DE      | 0.50 C      | 2.0          | 580.77                  | 145.19%           |
| AT      | 0.50 C      | 1.5          | 579.30                  | 144.83%           |
| HU      | 0.50 C      | 2.0          | 190.40                  | 47.60%            |

**Key Finding:** Czech Republic (CZ) offers the highest investment potential with 268.5% levelized ROI, nearly 2× higher than other Central European markets. The optimal configuration across all countries is **0.5C (2,236 kW) with 1.5-2.0 daily cycles**.

### Validation Status

✅ **ALL 45 SCENARIOS SUCCESSFULLY OPTIMIZED**
- 5 Countries (DE, AT, CH, HU, CZ)
- 9 Configurations per country (3 C-rates × 3 daily cycle limits)
- 100% success rate with optimal solutions found
- Full year 2024 simulation (35,040 time intervals at 15-min resolution)

---

## Mathematical Model

Our optimization framework implements a **Mixed-Integer Linear Programming (MILP)** model that co-optimizes battery dispatch across multiple energy markets while respecting technical and market constraints.

### Problem Dimensions

- **Decision Variables:** ~105,000 (70,000 continuous + 35,000 binary)
- **Constraints:** ~140,000
- **Time Horizon:** 1 year (2024) with 15-minute resolution
- **Solver:** CPLEX/HiGHS with 1% optimality gap tolerance

### Operational Optimization Model

#### Objective Function

Maximize total net profit over the one-year horizon:

$$
\\max Z = \\sum_{t \\in T} \\left[ \\frac{P_{DA}(t)}{1000} \\cdot p_{dis}(t) - \\frac{P_{DA}(t)}{1000} \\cdot p_{ch}(t) \\right] \\cdot \\Delta t + \\sum_{b \\in B} \\left[ P_{FCR}(b) \\cdot c_{fcr}(b) + P_{aFRR}^{pos}(b) \\cdot c_{afrr}^{pos}(b) + P_{aFRR}^{neg}(b) \\cdot c_{afrr}^{neg}(b) \\right] \\cdot \\Delta b
$$

Where:
- **First term:** Day-ahead energy arbitrage revenue (power in kW, price in EUR/MWh)
- **Second term:** Ancillary service capacity payments (bids in MW, prices in EUR/MW)

#### Constraint Equations

**1. State of Charge (SOC) Dynamics**

Energy balance accounting for charging/discharging efficiencies:

$$
e_{soc}(t) = e_{soc}(t-1) + \\left[ p_{ch}(t) \\cdot \\eta_{ch} - \\frac{p_{dis}(t)}{\\eta_{dis}} \\right] \\cdot \\Delta t \\quad \\forall t \\in T
$$

Initial condition: $e_{soc}(1) = e_{soc}^{init} + \\left[ p_{ch}(1) \\cdot \\eta_{ch} - \\frac{p_{dis}(1)}{\\eta_{dis}} \\right] \\cdot \\Delta t$

**2. SOC Limits**

$$
SOC_{min} \\cdot E_{nom} \\leq e_{soc}(t) \\leq SOC_{max} \\cdot E_{nom} \\quad \\forall t \\in T
$$

**3. Power Limits with Binary Linking**

$$
p_{ch}(t) \\leq y_{ch}(t) \\cdot P_{max}^{config} \\quad \\forall t \\in T
$$
$$
p_{dis}(t) \\leq y_{dis}(t) \\cdot P_{max}^{config} \\quad \\forall t \\in T
$$

**4. No Simultaneous Charge/Discharge**

$$
y_{ch}(t) + y_{dis}(t) \\leq 1 \\quad \\forall t \\in T
$$

**5. Market Co-optimization Power Limits** *(Critical Constraint)*

Allocates total available power between energy arbitrage and ancillary service reserves:

$$
p_{ch}(t) + 1000 \\cdot c_{fcr}(b) + 1000 \\cdot c_{aFRR}^{pos}(b) \\leq P_{max}^{config} \\quad \\forall b \\in B, \\forall t \\in b
$$
$$
p_{dis}(t) + 1000 \\cdot c_{fcr}(b) + 1000 \\cdot c_{aFRR}^{neg}(b) \\leq P_{max}^{config} \\quad \\forall b \\in B, \\forall t \\in b
$$

**6. Daily Cycle Limit**

Limits total daily discharged energy to prevent battery degradation:

$$
\\sum_{t \\in d} p_{dis}(t) \\cdot \\Delta t \\leq N_{cycles} \\cdot E_{nom} \\quad \\forall d \\in D
$$

**7. Ancillary Service Energy Reserve** *(Critical Constraint)*

Maintains sufficient SOC to deliver awarded AS capacity for 15 minutes:

$$
e_{soc}(t) \\geq SOC_{min} \\cdot E_{nom} + (1000 \\cdot c_{fcr}(b) + 1000 \\cdot c_{aFRR}^{pos}(b)) \\cdot \\Delta t \\quad \\forall b \\in B, \\forall t \\in b
$$
$$
e_{soc}(t) \\leq SOC_{max} \\cdot E_{nom} - (1000 \\cdot c_{fcr}(b) + 1000 \\cdot c_{aFRR}^{neg}(b)) \\cdot \\Delta t \\quad \\forall b \\in B, \\forall t \\in b
$$

**8. Minimum Bid Size Constraints**

Enforces market rules requiring minimum bid sizes (1 MW):

$$
c_{fcr}(b) \\geq y_{fcr}(b) \\cdot MinBid_{fcr} \\quad \\forall b \\in B
$$
$$
c_{fcr}(b) \\leq y_{fcr}(b) \\cdot \\frac{P_{max}^{config}}{1000} \\quad \\forall b \\in B
$$

(Similar constraints for $c_{aFRR}^{pos}(b)$ and $c_{aFRR}^{neg}(b)$)

**9. Ancillary Service Market Mutual Exclusivity**

Prevents simultaneous participation in multiple AS markets:

$$
y_{fcr}(b) + y_{aFRR}^{pos}(b) + y_{aFRR}^{neg}(b) \\leq 1 \\quad \\forall b \\in B
$$

#### Sets, Parameters, and Variables

**Sets:**
- $T$ = Set of 15-minute time intervals, $|T| = 35,040$ (full year 2024)
- $B$ = Set of 4-hour ancillary service blocks, $|B| = 2,190$
- $D$ = Set of 24-hour days, $|D| = 366$

**Parameters:**
- $P_{DA}(t)$ = Day-ahead electricity price [EUR/MWh]
- $P_{FCR}(b)$, $P_{aFRR}^{pos}(b)$, $P_{aFRR}^{neg}(b)$ = Ancillary service capacity prices [EUR/MW]
- $E_{nom}$ = 4,472 kWh (nominal battery capacity)
- $P_{max}^{config}$ = Maximum power based on C-rate [kW]
- $\\eta_{ch}$ = $\\eta_{dis}$ = 0.95 (charging/discharging efficiency)
- $N_{cycles}$ = Daily cycle limit (1.0, 1.5, or 2.0)
- $\\Delta t$ = 0.25 h, $\\Delta b$ = 4 h

**Decision Variables:**
- $p_{ch}(t)$, $p_{dis}(t)$ = Charge/discharge power [kW] (continuous)
- $e_{soc}(t)$ = State of charge [kWh] (continuous)
- $c_{fcr}(b)$, $c_{aFRR}^{pos}(b)$, $c_{aFRR}^{neg}(b)$ = AS capacity bids [MW] (continuous)
- $y_{ch}(t)$, $y_{dis}(t)$, $y_{fcr}(b)$, $y_{aFRR}^{pos}(b)$, $y_{aFRR}^{neg}(b)$ = Binary operation states

---

### Investment Optimization Model

#### Objective

Evaluate financial viability across countries and configurations using **10-year Discounted Cash Flow (DCF) analysis** to determine Net Present Value (NPV) and Levelized Return on Investment (ROI).

#### Step 1: Projecting Nominal Profits

For each country, take the best annual profit from operational optimization ($\\Pi_{2024}$) and project over 10 years with country-specific inflation rate ($\\pi$):

$$
\\Pi_y = \\Pi_{2024} \\cdot (1 + \\pi)^{y-1} \\quad \\text{for } y = 1, 2, \\ldots, 10
$$

#### Step 2: Net Present Value (NPV)

Calculate NPV using country-specific Weighted Average Cost of Capital (WACC, denoted $i$) as the nominal discount rate:

$$
NPV = \\sum_{y=1}^{10} \\frac{\\Pi_y}{(1 + i)^y} - CAPEX
$$

Where $CAPEX = 200 \\text{ EUR/kWh} \\times 4,472 \\text{ kWh} = 894,400 \\text{ EUR}$

#### Step 3: Levelized Return on Investment

$$
\\text{Levelized ROI (\\%)} = \\frac{PV(\\text{Total Profits})}{CAPEX \\times \\text{Lifetime}} \\times 100
$$

Where $PV(\\text{Total Profits}) = \\sum_{y=1}^{10} \\frac{\\Pi_y}{(1 + i)^y}$

---

## Implementation

### Architecture

The implementation consists of three main modules:

1. **`model.py`** - `ImprovedBESSOptimizer` class
   - Pyomo-based MILP model with complete constraint formulation
   - Pre-computed index mappings for computational efficiency
   - Support for multiple solvers (CPLEX, Gurobi, HiGHS)

2. **`investment_analysis.py`** - `InvestmentAnalyzer` class
   - 10-year DCF analysis with country-specific parameters
   - NPV and levelized ROI calculations
   - Inflation-adjusted cash flow projections

3. **`main.py`** - Orchestration script
   - Runs all 45 scenarios (5 countries × 9 configurations)
   - Generates 3 required Excel output files
   - Progress tracking and error handling

### Key Technical Features

- **Computational Efficiency:** Pre-computed block-time mappings reduce constraint evaluation overhead
- **Solver Robustness:** 1% MIP gap tolerance and 10-minute time limit per scenario
- **Data Validation:** Comprehensive input validation including timestamp alignment and missing value checks
- **Output Compliance:** Excel files exactly match TechArena Phase 1 specification

---

## Quick Start

### Prerequisites

- Python 3.9+
- Optimization solver (CPLEX, Gurobi, or HiGHS)
- Dependencies: `pip install -r requirements.txt`

### Execution

```bash
# Navigate to submission folder
cd SoloGen_TechArena2025_Phase1_submission

# Run complete optimization
python main.py

# Verify output files
ls output/
```

### Expected Output

Three Excel files in `output/` directory:

1. **`TechArena_Phase1_Configuration.xlsx`**
   - 9 configurations per country (3 C-rates × 3 cycle limits)
   - Columns: C-rate, number of cycles, yearly profits [kEUR/MW], levelized ROI [%]

2. **`TechArena_Phase1_Investment.xlsx`**
   - 10-year DCF analysis per country
   - Columns: Year, Yearly Profits, PV Yearly Profits, Cumulative NPV, Levelized ROI [%]

3. **`TechArena_Phase1_Operation.xlsx`**
   - Full year optimal schedule for best scenario (35,136 rows)
   - Columns: Timestamp, Stored energy [MWh], SoC [-], Charge [MWh], Discharge [MWh], FCR bid [MW], aFRR pos/neg bids [MW]

---

## Key Insights

### 1. Ancillary Services Dominate Revenue

Across all scenarios, ancillary service (FCR/aFRR) capacity payments contribute **60-80% of total revenue**, making them the primary value driver. This is due to:
- Stable, guaranteed revenue from capacity reservation
- High capacity prices in Central European markets (especially DE, CH, CZ)
- Lower risk compared to volatile day-ahead arbitrage

### 2. Energy Reserve Constraints Are Binding

The energy reserve constraints (Constraint 7) often dominate the daily cycle limit constraints (Constraint 6). Large AS capacity bids require maintaining SOC buffers:

$$
\\text{Effective Usable Capacity} = E_{nom} - 2 \\times \\text{AS\_MW} \\times 250 \\text{ kWh}
$$

For a 2 MW AS bid, this reduces usable capacity from 4,472 kWh to ~3,472 kWh, making higher cycle limits (2.0 vs 1.0) less impactful than expected.

### 3. Market Co-optimization Trade-off

The power allocation constraint (Constraint 5) creates a **zero-sum trade-off** between:
- **Day-ahead arbitrage:** Requires power for charging/discharging (uncertain revenue)
- **Ancillary services:** Requires power held in reserve (guaranteed revenue)

When AS prices are high, the optimizer rationally allocates most power to reserves, leaving minimal capacity for DA arbitrage.

### 4. Optimal Configuration Consistency

Across all countries, **0.5C C-rate performs best**, indicating that:
- Power capacity (2,236 kW) is the binding constraint, not energy capacity
- Higher power enables larger AS bids and more frequent arbitrage opportunities
- The slight increase in CAPEX from higher C-rate is easily justified by revenue gains

---

## Technical Specifications

### Battery Parameters (Fixed)

- **Nominal Energy Capacity:** 4,472 kWh (Huawei LUNA2000-4.5MWh)
- **Rated Power:** 2,236 kW (at 0.5C)
- **Initial Investment Cost:** 200 EUR/kWh
- **Charging/Discharging Efficiency:** 95%
- **SOC Range:** 0-100% (full operational range)

### Configuration Scenarios

| C-rate | Max Power (kW) | Daily Cycles | Max Daily Discharge (kWh) |
|--------|----------------|--------------|---------------------------|
| 0.25 C | 1,118          | 1.0, 1.5, 2.0 | 4,472 / 6,708 / 8,944    |
| 0.33 C | 1,476          | 1.0, 1.5, 2.0 | 4,472 / 6,708 / 8,944    |
| 0.50 C | 2,236          | 1.0, 1.5, 2.0 | 4,472 / 6,708 / 8,944    |

### Market Participation Rules

| Feature | Day-Ahead (EPEX SPOT) | FCR Capacity | aFRR Capacity |
|---------|-----------------------|--------------|---------------|
| **Mechanism** | Blind Auction | Daily Auction | Daily Auction |
| **Gate Closure (D-1)** | 12:00 CET | 8:00 CET | 9:00 CET |
| **Product Granularity** | 15 minutes | 4 hours | 4 hours |
| **Bid Structure** | Energy (MWh) | Symmetric Capacity (MW) | Asymmetric Capacity (MW) |
| **Minimum Bid Size** | 0.1 MW | 1 MW | 1 MW |

---

## Computational Performance

- **Problem Scale:** 105,000 variables, 140,000 constraints per scenario
- **Runtime:** 3-10 minutes per scenario (CPLEX with 1% MIP gap)
- **Total Execution:** ~5-8 hours for all 45 scenarios
- **Memory Usage:** 2-4 GB peak per scenario
- **Success Rate:** 100% optimal solutions found

---

## References

- **Pyomo Documentation:** https://pyomo.readthedocs.io/
- **TechArena 2025 Challenge:** Huawei Energy Management System Optimization
- **Mathematical Formulation:** See `doc/chapters/3_a_modeling.tex` and `3_b_model_investment_opt.tex`

---

## License

This project is developed for the Huawei TechArena 2025 challenge and follows the competition guidelines and terms.

---

**Team:** SoloGen  
**Date:** October 2025  
**Python Version:** 3.9+  
**Primary Solver:** CPLEX (HiGHS alternative available)
