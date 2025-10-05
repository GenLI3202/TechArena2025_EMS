# Project Instruction

## Purpose
This repository supports the Huawei TechArena 2025 Phase I challenge. Our goal is to develop a Python-based Energy Management System (EMS) algorithm for a utility-scale Battery Energy Storage System (BESS) that optimizes financial performance by participating in multiple European electricity markets. The canonical blueprint for the workflow, mathematical models, assumptions, and required outputs is captured in `doc/project_description.tex`.

## Challenge Context & Objectives

The challenge consists of three interconnected optimization tasks with a nested hierarchical relationship:

### 1. Operation Optimization (Core)
Maximize the BESS's revenue over 2024 by developing an optimal charge/discharge strategy. This involves:
- **Energy arbitrage** on the day-ahead wholesale market (EPEX SPOT)
- **Capacity bids** on Frequency Containment Reserve (FCR) and automatic Frequency Restoration Reserve (aFRR) ancillary service markets

### 2. Configuration Optimization (Base)
Determine the optimal BESS configuration by analyzing the impact of different parameters on profitability:
- **C-rates**: 0.25C, 0.33C, 0.50C (affecting maximum power)
- **Daily cycle limits**: 1.0, 1.5, 2.0 cycles per day (affecting energy throughput)

### 3. Investment Optimization (Top)
Identify which of five European countries offers the highest Return on Investment (ROI) over a 10-year period:
- **Countries**: Germany, Austria, Switzerland, Hungary, Czech Republic
- **Analysis**: Incorporate country-specific WACC and inflation rates using Discounted Cash Flow (DCF) methodology

## Technical Specifications 
**IMPORTANT**: Use only the exact BESS parameters and market rules provided below. Deviations will lead to disqualification!

### BESS Parameters
- **Nominal Energy Capacity**: 4,472 kWh
- **Rated Power**: 2,236 kW  
- **Round-trip Efficiency**: 85% (√0.85 for both charge and discharge)
- **Maximum Lifetime Cycles**: 4,500
- **Investment Cost**: €200 per kWh

### Configuration Matrix
| C-rate | Max Power (kW) | Cycles/day | Max Daily Discharge (kWh) |
|--------|----------------|------------|---------------------------|
| 0.25C  | 1,118          | 1.0        | 4,472                     |
| 0.33C  | 1,476          | 1.5        | 6,708                     |
| 0.50C  | 2,236          | 2.0        | 8,944                     |

### Market Participation Rules
| Market | Mechanism | Gate Closure | Product Granularity | Bid Structure | Minimum Bid |
|--------|-----------|--------------|--------------------|--------------|-----------| 
| Day-Ahead (EPEX) | Blind Auction | 12:00 CET (D-1) | 15 minutes | Energy (MWh) | 0.1 MW |
| FCR | Daily Auction | 8:00 CET (D-1) | 4 hours | Symmetric Capacity (MW) | 1 MW |
| aFRR | Daily Auction | 9:00 CET (D-1) | 4 hours | Asymmetric Capacity (MW) | 1 MW |

## Mathematical Model Framework

The optimization model maximizes total net profit through:

### Objective Function
$$\max Z = \sum_{t\in T} \left( \frac{P_{DA}(t)}{1000} p_{\mathrm{dis}}(t) - \frac{P_{DA}(t)}{1000} p_{\mathrm{ch}}(t) \right) \Delta t + \sum_{b\in B} \left( P_{FCR}(b) c_{fcr}(b) + P^{\mathrm{pos}}_{aFRR}(b) c^{\mathrm{pos}}_{aFRR}(b) + P^{\mathrm{neg}}_{aFRR}(b) c^{\mathrm{neg}}_{aFRR}(b) \right) \Delta b$$

### Key Constraints
1. **SOC Dynamics**: Energy balance with efficiency losses
2. **SOC Limits**: Operational boundaries (typically 10%-90%)
3. **Power Limits**: Configuration-dependent maximum charge/discharge
4. **Simultaneous Operation Prevention**: No charging and discharging simultaneously
5. **Market Co-optimization**: Power allocation between energy and reserves
6. **Daily Cycle Limit**: Maximum energy throughput per day
7. **Ancillary Service Energy Reserve**: Maintain capacity to deliver awarded reserves
8. **Minimum Bid Size**: 1 MW for FCR/aFRR markets

### Investment Analysis
10-year DCF analysis using:
- **Nominal cash flows**: Initial profit grown at inflation rate
- **Nominal discount rate**: Country-specific WACC
- **Levelized ROI**: $\frac{\text{PV(Total Profits)}}{\text{CAPEX} \times \text{Lifetime}} \times 100$

### Country-Specific Financial Parameters
| Country | WACC (%) | Inflation Rate (%) |
|---------|----------|-------------------|
| Germany (DE) | 8.3 | 2.0 |
| Austria (AT) | 8.3 | 3.3 |
| Switzerland (CH) | 8.3 | 0.1 |
| Czech Republic (CZ) | 12.0 | 2.9 |
| Hungary (HU) | 15.0 | 4.6 |

## Key Deliverables
The `main.py` script must generate exactly three submission-ready output CSV files under `SoloGen_TechArena2025_Phase1/output/` with the following names, and in each file there are five sheets for the five countries (DE, AT, CH, HU, CZ) respectively:

1. **`TechArena_Phase1_Configuration.xlsx`**:
Optimal BESS configuration parameters
Required columns (with exactly the same columns headers!): "C-rate", "number of cycles", "yearly profits [kEUR/MW]", "levelized ROI [%]"

2. **`TechArena_Phase1_Operation.xlsx`** 
Required columns (with exactly the same columns headers!): "Timestamp", "Stored energy [MWh]", "SoC [-]", "Charge [MWh]", "Discharge [MWh]", "Day-ahead buy [MWh]", "Day-ahead sell [MWh]", "FCR Capacity [MW]", "aFRR Capacity POS [MW]", "aFRR Capacity NEG [MW]"
3. **`TechArena_Phase1_Investment.xlsx`**:
Investment analysis and ROI calculations MUST include: "WACC", "inflation rate", "discount rate", "yearly profits", "year-by-year analysis", "levelized ROI" and in the following table format:

```tex
\begin{table}[h]
\centering
\begin{tabular}{|l|l|l|l|}
\hline
WACC & Value & & \\
\hline
Inflation Rate & value & & \\
\hline
Discount Rate & Value & & \\
\hline
Yearly Profits (2024) & Value & & \\
\hline
\multicolumn{4}{|c|}{} \\
\hline
Year & & Initial Investment [kEUR/MWh] & Yearly profits [kEUR/MWh] \\
\hline
& 2023 & & \\
\hline
& 2024 & & \\
\hline
& 2025 & & \\
\hline
& 2026 & & \\
\hline
& 2027 & & \\
\hline
& 2028 & & \\
\hline
& 2029 & & \\
\hline
& 2030 & & \\
\hline
& 2031 & & \\
\hline
& 2032 & & \\
\hline
& 2033 & & \\
\hline
\end{tabular}
\end{table}
```

Supporting modules: `io.py`, `bess_model.py`, `operation.py`, `scenarios.py`, `investment_analysis.py`, and orchestrating `main.py`.

## Implementation Strategy

### Hierarchical Optimization Approach
The three optimization tasks have a nested relationship:

1. **Configuration Optimization (Base Level)**: C-rate and daily cycle limits define BESS physical constraints
2. **Operation Optimization (Core Level)**: Takes configuration parameters and calculates maximum annual revenue for each country/configuration combination  
3. **Investment Optimization (Top Level)**: Uses operational revenue to calculate 10-year ROI across all scenarios

### Workflow Phases
1. **Phase 0 – Foundation & Discovery**: Problem internalization, data exploration, and mathematical model validation
2. **Phase 1 – Core Algorithm**: Implement BESS operational model with single configuration/country testing
3. **Phase 2 – Scaled Analysis**: Matrix execution across all 45 scenarios (5 countries × 9 configurations)
4. **Phase 3 – Investment Analysis**: DCF modeling and ROI calculations
5. **Phase 4 – Refinement & Submission**: Code hardening, validation, and deliverable packaging

## Implementation Guidelines

### Technical Constraints
- **Time Resolution**: 15-minute intervals for DA market; 4-hour blocks for ancillary services (forward-fill resampling)
- **BESS Parameters**: Use exact values from technical specifications (4,472 kWh, 2,236 kW, 85% efficiency)
- **Market Constraints**: Respect minimum bid sizes, gate closure times, and product granularities
- **SOC Management**: Maintain operational boundaries and reserve capacity for awarded ancillary services

### Financial Modeling
- **CapEx**: €200 per kWh of energy capacity  
- **DCF Approach**: Use nominal cash flows with nominal WACC discount rate
- **Inflation Growth**: Apply country-specific inflation to project future profits
- **ROI Calculation**: Levelized methodology as specified in competition guidelines

### Code Organization
- Use only relative paths inside `SoloGen_TechArena2025_Phase1`
- Modular design with clear separation of concerns (I/O, modeling, optimization, investment)
- Pyomo-based optimization framework for mathematical model implementation

## Evaluation Criteria

Submissions are evaluated based on:

1. **Revenue Maximization (50%)**: Algorithm effectiveness in maximizing revenue based on market prices
2. **Investment Optimization (20%)**: Assessment of optimal investment locations and market analysis  
3. **Configuration Optimization (20%)**: Evaluation of configuration parameter impact on BESS revenue
4. **Code Quality and Documentation (10%)**: Clarity, structure, and documentation of implementation

## Quality Assurance

### Validation Requirements
- Automated checks for data integrity, BESS physical limits, and revenue calculations
- Validate final CSV row counts, column names, and ordering before submission
- Unit tests for critical model components and constraint validation
- Reproducibility verification in clean environment

### Documentation Standards
- Maintain up-to-date `requirements.txt` with exact dependency versions
- Record modeling assumptions and deviations in technical documentation
- Clear code comments explaining mathematical model implementation
- Results interpretation and sensitivity analysis documentation
