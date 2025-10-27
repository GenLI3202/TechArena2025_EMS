# Huawei TechArena 2025: BESS Energy Management System
*by Gen Li (Team SoloGen)*

> **Repository Status:** Currently developing **Round 2 (Phase 2)** solution.
> Phase 1 (2024 optimization) artifacts have been archived to `archive_old_files/`.
> **New Data:** `data/TechArena2025_Phase2_data.xlsx`
> **Active Branch:** `r2-with-bat-config`

A Python-based Energy Management System (EMS) for optimal Battery Energy Storage System (BESS) operations across multiple European electricity markets considering battery aging and degradation.

## Table of Contents

---

## Context and Objectives
Primary objective: Develop a BESS to optimize financial performance by participating in four key markets: day-ahead (Energy), FCR (power capacity), and aFRR markets (both power and energy), while considering impact of BESS schedule on battery aging and degradation.

The challenge is divided into three core, interconnected optimization tasks:

- **Operation Optimization:** Maximize the BESS's revenue over the year 2024 by developing an optimal charge/discharge strategy to bid in the DA, FCR and aFRR markets.

- **Investment Optimization:** Identify which of five European countries (Germany, Austria, Switzerland, Hungary, Czech Republic) offers the highest Return on Investment (ROI) for installing the BESS over a 10-year period.

- **Configuration Optimization:** Determine the optimal BESS configuration by analyzing the impact of different C-rates and daily cycle limits on profitability and performance.



## Methodology Overview

- Data pipeline 
- Modelling (assumption, model used, and implementation method)
- Optimization (solver, parameters, and performance)
- Results and analysis, visualization approach
- Important finding, figures, pictures and Conclusion 

## Mathematical Model 

### Phase 1: One-Year Optimization without Battery Degradation



### Phase 2: Phase 1 + Battery Degradation Modeling


## Investment Optimization

## Implementation Pipeline

### Model Statistics 
- **Variables**: ~`xxx`total (70,000 continuous + 35,000 binary)
- **Constraints**: ~`xxx` total (35K SOC dynamics + 105K market/power constraints)
- **Solve Time**: `xxx` minutes per scenario with `SolverName` (`??s` time limit)
- **Memory Usage**: ~`xxx` GB per optimization instance

## Model Validation 

### Validation Approach and Testing Scenarios

**Scenarios:**
  i) Scenario 1 (S1): Baseline without battery degradation
  ii) Scenario 2 (S2): Including battery degradation effects

1. T1: model behaviors in four markets in S1 (4 in total):
2. T2: model behaviors in four markets in S2 with different battery degradation profiles ($4N$ in total, where $N$ is the number of degradation profiles tested)


## Final Results and Analysis



## Appendix

### Pyomo Framework Overview

