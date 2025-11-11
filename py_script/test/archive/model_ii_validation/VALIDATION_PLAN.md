# Model (ii) Seasonal Validation Plan
# Cyclic Aging Cost Integration - Comprehensive Testing Framework

**Document Version:** 1.0
**Created:** 2025-01-08
**Model:** BESSOptimizerModelII (Cyclic Aging Cost Integration)
**Purpose:** Validate Model (ii) implementation across diverse market conditions and compare with Model (i) baseline

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Validation Objectives](#validation-objectives)
3. [Test Matrix](#test-matrix)
4. [Validation Metrics](#validation-metrics)
5. [Must-Pass Criteria](#must-pass-criteria)
6. [Comparison Framework](#comparison-framework)
7. [Output Structure](#output-structure)
8. [Implementation Details](#implementation-details)
9. [Expected Outcomes](#expected-outcomes)
10. [Success Criteria](#success-criteria)

---

## 1. Executive Summary

This document outlines the comprehensive seasonal validation plan for **Model (ii): Cyclic Aging Cost Integration**, which extends Model (i) by incorporating piecewise-linear cyclic degradation costs into the optimization objective.

**Key Features of Validation:**
- **12 test scenarios** across 4 seasons and 3 configuration profiles per country
- **58 validation metrics** (48 base + 10 degradation-specific)
- **Direct comparison** with Model (i) baseline results
- **Two markets tested:** Hungary (HU) and Switzerland (CH)
- **Comprehensive reporting** with visualizations and analysis

**Validation Scope:**
- ✓ Solution quality and optimality
- ✓ Physical constraint satisfaction
- ✓ Degradation cost calculation accuracy
- ✓ Cycling behavior changes vs Model (i)
- ✓ Revenue and profit impact assessment
- ✓ Market participation pattern changes

---

## 2. Validation Objectives

### 2.1 Primary Objectives

1. **Verify Implementation Correctness**
   - All constraints satisfied across diverse scenarios
   - Degradation costs calculated accurately
   - Solver converges to optimal solutions
   - No numerical instabilities or errors

2. **Assess Degradation Cost Impact**
   - Quantify profit reduction vs Model (i)
   - Measure cycle count reduction
   - Analyze depth of discharge (DOD) changes
   - Evaluate alpha parameter effectiveness

3. **Validate Economic Behavior**
   - Model (ii) reduces cycling appropriately
   - Shift toward higher-value, fewer-cycle opportunities
   - Degradation costs are reasonable (not excessive)
   - Revenue mix changes are logical

4. **Enable Model Comparison**
   - Direct comparison with Model (i) using identical test weeks
   - Quantify trade-offs between profit and battery longevity
   - Validate that Model (ii) ⊇ Model (i) (superset behavior)

### 2.2 Secondary Objectives

- Generate comprehensive documentation and reports
- Create reusable validation framework for future models
- Identify optimal alpha parameter ranges
- Provide insights for model selection guidelines

---

## 3. Test Matrix

### 3.1 Test Weeks (Identical to Model i)

Four representative weeks from 2024, one per quarter:

| Quarter | Season | Week | Start Date | End Date | Market Characteristics |
|---------|--------|------|------------|----------|------------------------|
| Q1 | Winter | 7 | 2024-02-12 | 2024-02-18 | High demand, moderate price volatility |
| Q2 | Spring | 17 | 2024-04-22 | 2024-04-28 | Moderate conditions, shoulder season |
| Q3 | Summer | 30 | 2024-07-22 | 2024-07-28 | High solar, high volatility, best profits |
| Q4 | Fall | 48 | 2024-11-25 | 2024-12-01 | Moderate-high demand, variable renewable |

**Rationale:**
- Covers all four seasons with distinct market conditions
- Tests model robustness across price volatility ranges
- Enables seasonal performance comparison
- Matches Model (i) validation for direct comparability

### 3.2 Test Scenarios

Three configuration scenarios per test week:

| Scenario | c_rate | alpha | daily_cycle_limit | Description |
|----------|--------|-------|-------------------|-------------|
| **Baseline** | 0.5 | 1.0 | None | Standard operation, full degradation cost weighting |
| **Conservative** | 0.33 | 1.5 | None | Lower power, higher degradation penalty |
| **Aggressive** | 0.5 | 0.5 | None | Standard power, reduced degradation penalty |

**Key Differences from Model (i):**
- Replace `daily_cycle_limit` constraint with `alpha` parameter
- Model (ii) uses economic incentives (cost) instead of hard constraints (limit)
- Alpha controls degradation cost weighting in objective function

**Alpha Parameter Rationale:**
- α = 1.0 (Baseline): Full degradation cost consideration
- α = 1.5 (Conservative): 50% higher penalty, prioritize battery longevity
- α = 0.5 (Aggressive): 50% lower penalty, prioritize short-term profit

### 3.3 Countries Tested

- **Hungary (HU)**: Primary validation market
- **Switzerland (CH)**: Secondary validation for model generalization

**Total Tests:** 4 weeks × 3 scenarios × 2 countries = **24 test runs**

---

## 4. Validation Metrics

### 4.1 Metric Categories Overview

| Category | Code | Count | Description |
|----------|------|-------|-------------|
| Solution Quality | SQ | 6 | Solver performance and optimality |
| Revenue & Profit | RP | 8 | Financial performance metrics |
| Energy & Power | EP | 10 | Battery utilization and efficiency |
| State of Charge | SC | 8 | SOC behavior and range utilization |
| Market Participation | MP | 10 | Market engagement patterns |
| Model Variables | MV | 6 | Model (i) constraint verification |
| **Degradation** | **DG** | **10** | **Model (ii) specific metrics** |
| **Total** | | **58** | |

### 4.2 Base Metrics (48 total - Inherited from Model i)

#### SQ: Solution Quality (6 metrics)
- **SQ1**: Solver status (optimal/feasible/failed)
- **SQ2**: Optimality gap (%)
- **SQ3**: Solve time (seconds)
- **SQ4**: Constraint violations count
- **SQ5**: Variable count
- **SQ6**: Constraint count

#### RP: Revenue & Profit (8 metrics)
- **RP1**: Total profit (EUR)
- **RP2**: DA energy profit (EUR)
- **RP3**: aFRR energy profit (EUR)
- **RP4**: FCR capacity revenue (EUR)
- **RP5**: aFRR capacity revenue (EUR)
- **RP6**: Profit per day (EUR/day)
- **RP7**: Profit per MWh throughput (EUR/MWh)
- **RP8**: Revenue Herfindahl index (diversification)

#### EP: Energy & Power Utilization (10 metrics)
- **EP1**: Energy charged (kWh)
- **EP2**: Energy discharged (kWh)
- **EP3**: Energy throughput (kWh)
- **EP4**: Round-trip efficiency (%)
- **EP5**: Max charge power (kW)
- **EP6**: Max discharge power (kW)
- **EP7**: Average charge power (kW)
- **EP8**: Average discharge power (kW)
- **EP9**: Power capacity utilization (%)
- **EP10**: Idle time (hours)

#### SC: State of Charge (8 metrics)
- **SC1**: Initial SOC (kWh)
- **SC2**: Final SOC (kWh)
- **SC3**: Min SOC reached (kWh)
- **SC4**: Max SOC reached (kWh)
- **SC5**: SOC range used (kWh)
- **SC6**: SOC range utilization (%)
- **SC7**: Number of full cycles (equivalent 100% DOD)
- **SC8**: SOC violations count

#### MP: Market Participation (10 metrics)
- **MP1**: DA charging intervals (#)
- **MP2**: DA discharging intervals (#)
- **MP3**: aFRR-E positive total bids (kW)
- **MP4**: aFRR-E negative total bids (kW)
- **MP5**: aFRR-E positive bid intervals (#)
- **MP6**: aFRR-E negative bid intervals (#)
- **MP7**: FCR blocks bid (#)
- **MP8**: aFRR positive capacity blocks (#)
- **MP9**: aFRR negative capacity blocks (#)
- **MP10**: Market diversity index

#### MV: Model Variables (6 metrics)
- **MV1**: p_total_ch correct (boolean)
- **MV2**: p_total_dis correct (boolean)
- **MV3**: Binaries linked correctly (boolean)
- **MV4**: Min bid enforced (boolean)
- **MV5**: Exclusivity satisfied (boolean)
- **MV6**: SOC uses total power (boolean)

### 4.3 Degradation Metrics (10 new - Model ii Specific)

#### DG: Degradation & Cycling (10 metrics)

**DG1: Total Cyclic Degradation Cost (EUR)**
- Sum of all cyclic aging costs across the week
- Formula: Σ_t Σ_j (c_cost[j] × p_dis_j[t,j] × η_dis⁻¹ × dt)
- Expected range: 100-5,000 EUR depending on cycling intensity

**DG2: Degradation Cost per Full Cycle (EUR/cycle)**
- Average degradation cost per equivalent 100% DOD cycle
- Formula: DG1 / SC7
- Expected: ~232.86 EUR for balanced cycling across segments

**DG3: Degradation Cost Ratio (%)**
- Degradation cost as percentage of gross revenue (before subtracting degradation)
- Formula: DG1 / (RP1 + DG1) × 100
- Expected range: 5-30% depending on alpha and market conditions

**DG4: Net Profit After Degradation (EUR)**
- Total profit including degradation costs (should match RP1 in Model ii)
- Formula: Gross revenue - degradation costs
- Verification: Should equal RP1

**DG5: Profit Reduction vs Model (i) (%)**
- Percentage profit decrease compared to Model (i) baseline
- Formula: (RP1_model_i - RP1_model_ii) / RP1_model_i × 100
- Expected range: 5-40% depending on alpha

**DG6: Cycle Count Reduction vs Model (i) (%)**
- Percentage reduction in equivalent full cycles
- Formula: (SC7_model_i - SC7_model_ii) / SC7_model_i × 100
- Expected: 10-30% fewer cycles (degradation awareness reduces cycling)

**DG7: Average Depth of Discharge (%)**
- Average DOD across all discharge cycles
- Formula: Average of (energy discharged per cycle / E_nom × 100)
- Expected: Model (ii) should have lower average DOD (shallower cycles)

**DG8: Shallow Cycle Count (#)**
- Number of cycles with DOD < 50%
- Count discharge events with energy < 0.5 × E_nom
- Expected: Higher in Model (ii) (prefers shallow cycles)

**DG9: Deep Cycle Count (#)**
- Number of cycles with DOD > 80%
- Count discharge events with energy > 0.8 × E_nom
- Expected: Lower in Model (ii) (avoids deep cycles due to cost)

**DG10: Alpha Effectiveness Score**
- Metric to assess if alpha parameter achieves intended balance
- Formula: (DG6 / 10) × (1 - DG5 / 100)
- Score of 1.0 = optimal: 10% cycle reduction, 0% profit loss (theoretical max)
- Higher score = better balance between longevity and profitability

---

## 5. Must-Pass Criteria

### 5.1 Base Criteria (10 - From Model i)

All tests must satisfy these fundamental requirements:

1. **Solver Success**: Status is 'optimal' or 'feasible'
2. **Zero Violations**: All constraints satisfied (SQ4 = 0)
3. **SOC Bounds**: 0 ≤ e_soc[t] ≤ E_nom ∀t
4. **Power Bounds**: All power variables ≤ P_max_config
5. **Binary Consistency**: All binaries ∈ {0, 1}
6. **No Simultaneous Charge/Discharge**: y_ch[t] + y_dis[t] ≤ 1 ∀t
7. **Total Power Charging Correct**: p_total_ch[t] = p_ch[t] + p_afrr_neg_e[t] ∀t
8. **Total Power Discharging Correct**: p_total_dis[t] = p_dis[t] + p_afrr_pos_e[t] ∀t
9. **Positive Profit**: Total profit > 0 (after degradation costs)
10. **No NaN/Inf**: All metrics are valid finite numbers

### 5.2 Model (ii) Specific Criteria (3 new)

Additional requirements specific to cyclic aging model:

11. **Valid Degradation Costs**
    - All degradation costs ≥ 0 (DG1 ≥ 0)
    - Costs must be finite and non-negative
    - No calculation errors or NaN values

12. **Reasonable Profit Reduction**
    - 0% ≤ DG5 ≤ 50% (profit reduction vs Model i should be reasonable)
    - Lower bound: Model (ii) can match Model (i) if no cycling occurs
    - Upper bound: Degradation shouldn't eliminate all profit
    - Validates that degradation costs are not excessive

13. **Cycle Reduction (Economic Rationality)**
    - DG6 ≥ 0% (Model ii should cycle same or less than Model i)
    - Validates that degradation costs discourage cycling
    - Exception: If Model (i) used aggressive cycle limit, Model (ii) with low alpha might cycle more
    - Must pass for baseline scenario (alpha=1.0)

### 5.3 Pass/Fail Logic

**Test Result:**
- **PASS**: All 13 criteria satisfied
- **WARNING**: Base criteria pass, but 1-2 Model (ii) criteria marginal
- **FAIL**: Any base criterion fails OR >2 Model (ii) criteria fail

**Target:** 100% PASS rate (24/24 tests)

---

## 6. Comparison Framework

### 6.1 Model (i) Reference Data

For each test, load corresponding Model (i) results from:
```
results/model_i_validation/{country}_seasonal/Q{n}_{season}_{scenario}.json
```

**Key Metrics to Compare:**
- RP1: Total profit
- SC7: Number of full cycles
- EP3: Energy throughput
- MP: Market participation patterns
- RP8: Revenue diversification

### 6.2 Delta Metrics

Compute differences between Model (ii) and Model (i):

| Delta Metric | Formula | Interpretation |
|--------------|---------|----------------|
| Δ Profit (EUR) | RP1_ii - RP1_i | Absolute profit change |
| Δ Profit (%) | (RP1_ii - RP1_i) / RP1_i × 100 | Relative profit change |
| Δ Cycles | SC7_ii - SC7_i | Cycle count change |
| Δ Cycles (%) | (SC7_ii - SC7_i) / SC7_i × 100 | Relative cycle change |
| Δ Throughput (kWh) | EP3_ii - EP3_i | Energy flow change |
| Δ Revenue Mix | RP8_ii - RP8_i | Diversification change |

### 6.3 Comparison Scenarios

**Three Comparison Types:**

1. **Direct Comparison (Baseline)**
   - Model (i): c_rate=0.5, daily_cycle_limit=1.5
   - Model (ii): c_rate=0.5, alpha=1.0
   - Purpose: Measure degradation cost impact under similar conditions

2. **Conservative Comparison**
   - Model (i): c_rate=0.33, daily_cycle_limit=1.0
   - Model (ii): c_rate=0.33, alpha=1.5
   - Purpose: Assess conservative operation strategies

3. **Aggressive Comparison**
   - Model (i): c_rate=0.5, daily_cycle_limit=2.0
   - Model (ii): c_rate=0.5, alpha=0.5
   - Purpose: Evaluate high-utilization scenarios

**Note:** Comparisons are approximate (different constraint mechanisms), but provide directional insights.

---

## 7. Output Structure

### 7.1 Directory Organization

```
results/model_ii_validation/
├── HU_seasonal/                               # Hungary validation results
│   ├── Q1_Winter_baseline.json                # Baseline scenario (alpha=1.0)
│   ├── Q1_Winter_baseline_timeseries.csv
│   ├── Q1_Winter_conservative.json            # Conservative (alpha=1.5)
│   ├── Q1_Winter_conservative_timeseries.csv
│   ├── Q1_Winter_aggressive.json              # Aggressive (alpha=0.5)
│   ├── Q1_Winter_aggressive_timeseries.csv
│   ├── ... (Q2, Q3, Q4 similar structure)
│   ├── comparison_with_model_i/
│   │   ├── profit_comparison.csv              # Profit delta for all 12 tests
│   │   ├── cycle_comparison.csv               # Cycle delta for all 12 tests
│   │   ├── degradation_analysis.csv           # Degradation metrics summary
│   │   └── revenue_mix_changes.csv            # Market participation changes
│   └── VALIDATION_REPORT.md                   # Comprehensive report
├── CH_seasonal/                               # Switzerland validation
│   └── [Same structure as HU_seasonal]
└── visualizations/
    ├── profit_comparison_model_i_vs_ii.png    # Main comparison chart
    ├── degradation_cost_breakdown.png         # Cost by segment and season
    ├── cycle_reduction_analysis.png           # Cycle count comparison
    ├── revenue_mix_changes.png                # DA/aFRR/capacity shifts
    ├── seasonal_performance.png               # 4-season trend analysis
    ├── alpha_sensitivity.png                  # Alpha parameter impact
    ├── dod_distribution.png                   # Depth of discharge histogram
    └── best_week_detailed.png                 # Detailed analysis of best week
```

### 7.2 JSON Result File Format

Each test produces a JSON file with:

```json
{
  "model": "BESSOptimizerModelII",
  "model_version": "1.0",
  "week": "Q3_Summer",
  "week_info": {
    "week": 30,
    "start_date": "2024-07-22",
    "end_date": "2024-07-28",
    "season": "Summer"
  },
  "country": "HU",
  "scenario": {
    "name": "baseline",
    "c_rate": 0.5,
    "alpha": 1.0,
    "enforce_segment_binary": true
  },
  "degradation_config": {
    "num_segments": 10,
    "segment_capacity_kwh": 447.2,
    "config_file": "data/phase2_aging_config/aging_config.json"
  },
  "metrics": {
    "SQ1_solver_status": "optimal",
    "SQ2_optimality_gap": 0.0,
    "RP1_total_profit": 48234.56,
    "SC7_full_cycles": 4.2,
    "DG1_degradation_cost": 978.42,
    "DG2_cost_per_cycle": 232.96,
    "DG3_degradation_ratio": 1.99,
    "DG5_profit_reduction_vs_model_i": 15.3,
    "DG6_cycle_reduction_vs_model_i": 22.1,
    ... (all 58 metrics)
  },
  "violations": [],
  "must_pass": {
    "1_solver_success": true,
    "2_zero_violations": true,
    ... (all 13 checks)
  },
  "all_passed": true,
  "model_i_comparison": {
    "model_i_profit": 56987.34,
    "profit_delta_eur": -8752.78,
    "profit_delta_pct": -15.36,
    "model_i_cycles": 5.4,
    "cycle_delta": -1.2,
    "cycle_delta_pct": -22.22
  },
  "computation": {
    "timestamp": "2025-01-08T14:32:15",
    "solve_time_seconds": 11.3,
    "python_version": "3.10.7",
    "pyomo_version": "6.7.0"
  }
}
```

### 7.3 CSV Timeseries Format

Columns:
```
t, p_ch, p_dis, p_afrr_pos_e, p_afrr_neg_e, e_soc,
p_ch_j1, p_ch_j2, ..., p_ch_j10,
p_dis_j1, p_dis_j2, ..., p_dis_j10,
e_soc_j1, e_soc_j2, ..., e_soc_j10
```

**Total Columns:** 36
- 6 base variables (time, main powers, total SOC)
- 10 segment charge powers
- 10 segment discharge powers
- 10 segment SOC values

**Rows:** 672 (168 hours × 4 intervals per hour)

### 7.4 Validation Report Structure

**VALIDATION_REPORT.md** contains:

1. **Executive Summary**
   - Pass/fail count (target: 12/12)
   - Overall assessment (PASS/WARNING/FAIL)
   - Key findings (3-5 bullet points)

2. **Test Results Summary Table**
   - 12 rows (4 weeks × 3 scenarios)
   - Columns: Week, Scenario, Status, Profit, Cycles, Degradation Cost, Pass/Fail

3. **Seasonal Performance Analysis**
   - Profit by season (bar chart data)
   - Best/worst performing seasons
   - Seasonal degradation cost patterns

4. **Model (ii) vs Model (i) Comparison**
   - Profit reduction analysis
   - Cycle reduction analysis
   - Economic trade-off assessment

5. **Degradation Metrics Deep Dive**
   - Total degradation costs across all tests
   - Cost per cycle validation
   - DOD distribution analysis
   - Alpha effectiveness scores

6. **Must-Pass Criteria Summary**
   - 13 criteria pass rates
   - Any failures or warnings
   - Recommendations

7. **Constraint Violations**
   - Detailed violation log (should be empty)
   - If any: root cause analysis

8. **Key Performance Insights**
   - Revenue mix changes
   - Market participation shifts
   - Optimal alpha range recommendations

9. **Visualizations**
   - References to generated plots
   - Interpretation of key trends

10. **Conclusions**
    - Overall model quality assessment
    - Readiness for production use
    - Comparison with expectations

11. **Recommendations**
    - Optimal parameter ranges
    - Best use cases for Model (ii) vs Model (i)
    - Future validation needs

---

## 8. Implementation Details

### 8.1 Script Workflow

#### `run_seasonal_validation.py`

```python
# High-level workflow

1. Load configuration
   - Degradation config from aging_config.json
   - Test weeks and scenarios from config

2. Load full year data
   - data/processed/TechArena2025_data_tidy.jsonl

3. For each country in [HU, CH]:
   For each test week in [Q1, Q2, Q3, Q4]:
     For each scenario in [baseline, conservative, aggressive]:

       a) Extract week data (7 days)
       b) Extract country data
       c) Load Model (i) reference results
       d) Initialize BESSOptimizerModelII with scenario params
       e) Build optimization model
       f) Solve model
       g) Compute 58 metrics
       h) Validate 13 must-pass criteria
       i) Compare with Model (i)
       j) Save JSON and CSV results
       k) Log progress

4. Generate comparison CSVs
5. Generate validation report
6. Log completion summary
```

#### Key Functions to Implement

**1. `compute_degradation_metrics(solution, model, scenario)`**
```python
def compute_degradation_metrics(solution, model, scenario):
    """
    Compute 10 degradation-specific metrics (DG1-DG10).

    Returns:
        dict: Degradation metrics
    """
    # DG1: Sum cyclic costs from objective
    # DG2: Cost per cycle
    # DG3: Cost ratio
    # DG4: Net profit (verification)
    # DG5-DG6: Model (i) comparison (requires reference)
    # DG7-DG9: DOD analysis
    # DG10: Alpha effectiveness
```

**2. `compare_with_model_i(model_ii_metrics, model_i_results)`**
```python
def compare_with_model_i(model_ii_metrics, model_i_results):
    """
    Compute delta metrics between Model (ii) and Model (i).

    Returns:
        dict: Comparison metrics
    """
    # Compute profit delta
    # Compute cycle delta
    # Compute throughput delta
    # Compute revenue mix changes
```

**3. `validate_must_pass_criteria(metrics, solution, violations, model_i_comparison)`**
```python
def validate_must_pass_criteria(metrics, solution, violations, model_i_comparison):
    """
    Check all 13 must-pass criteria.

    Returns:
        dict: {criterion_id: pass/fail boolean}
        bool: all_passed
    """
    # Check base 10 criteria
    # Check degradation-specific 3 criteria
```

**4. `analyze_dod_distribution(timeseries_data)`**
```python
def analyze_dod_distribution(timeseries_data):
    """
    Analyze depth of discharge for all cycles in the week.

    Returns:
        dict: DOD statistics (mean, std, shallow_count, deep_count)
    """
    # Identify discharge events
    # Calculate DOD for each
    # Categorize as shallow/medium/deep
```

### 8.2 Dependencies

**Required Python Packages:**
```
pyomo >= 6.7.0
pandas >= 2.0.0
numpy >= 1.24.0
matplotlib >= 3.7.0
seaborn >= 0.12.0
highspy >= 1.5.0  # Or other solver
pytest >= 7.4.0
```

**Required Data:**
```
data/processed/TechArena2025_data_tidy.jsonl
data/phase2_aging_config/aging_config.json
results/model_i_validation/HU_seasonal/*.json
results/model_i_validation/CH_seasonal/*.json
```

### 8.3 Execution

**Command:**
```bash
# Run HU validation
cd py_script/validation/model_ii_validation
python run_seasonal_validation.py

# Run CH validation
python run_ch_validation.py

# Generate visualizations
python visualize_validation.py

# Compare with Model (i)
python compare_with_model_i.py

# Regenerate report
python generate_report.py
```

**Expected Runtime:**
- Model build + solve: ~10-15 seconds per test
- Total per country: ~12 tests × 15s = ~3 minutes
- Both countries: ~6-7 minutes total
- Visualization: ~30 seconds
- Report generation: ~10 seconds

**Total Validation Time:** ~8 minutes

---

## 9. Expected Outcomes

### 9.1 Solution Quality Expectations

| Metric | Expected Value | Tolerance |
|--------|----------------|-----------|
| Solver status | optimal | 100% |
| Optimality gap | 0.0% | ≤ 0.1% |
| Solve time | 10-15s | ≤ 30s |
| Constraint violations | 0 | 0 |
| Must-pass rate | 100% | ≥ 95% |

### 9.2 Degradation Impact Expectations

#### Profit Reduction (DG5)

| Scenario | Expected Range | Rationale |
|----------|----------------|-----------|
| Baseline (α=1.0) | 10-25% | Moderate degradation consideration |
| Conservative (α=1.5) | 20-35% | Higher penalty reduces cycling |
| Aggressive (α=0.5) | 5-15% | Lower penalty, more cycling tolerated |

#### Cycle Reduction (DG6)

| Scenario | Expected Range | Rationale |
|----------|----------------|-----------|
| Baseline (α=1.0) | 15-30% | Model avoids marginal-profit cycles |
| Conservative (α=1.5) | 25-40% | Stronger cycle avoidance |
| Aggressive (α=0.5) | 5-20% | Weaker cycle avoidance |

#### Degradation Cost Ratio (DG3)

| Scenario | Expected Range | Interpretation |
|----------|----------------|----------------|
| All | 5-30% | Degradation costs as % of gross revenue |
| Baseline | 10-20% | Typical range for balanced operation |

### 9.3 Seasonal Patterns

**Expected Profit Ranking (Baseline):**
1. Q3 Summer: ~€45,000-50,000 (highest volatility)
2. Q2 Spring: ~€28,000-32,000
3. Q4 Fall: ~€25,000-28,000
4. Q1 Winter: ~€18,000-22,000 (lowest volatility)

**Expected Cycle Reduction Pattern:**
- All scenarios should show fewer cycles than Model (i)
- Greater reduction in low-profit-margin periods
- Less reduction in high-profit periods (worth cycling despite cost)

### 9.4 Economic Behavior

**Expected Revenue Mix Changes:**
- Slight shift toward aFRR energy (higher margins)
- Reduced DA energy cycling (lower margins)
- Capacity markets unchanged (no cycling required)

**Expected DOD Changes:**
- Average DOD: 5-15% lower than Model (i)
- Shallow cycles: +20-40% increase
- Deep cycles: -30-50% decrease
- Validates preference for shallow cycles (lower marginal cost)

---

## 10. Success Criteria

### 10.1 Validation Success Definition

The validation is considered **SUCCESSFUL** if:

✅ **Primary Criteria:**
1. **100% pass rate** on must-pass criteria (24/24 tests)
2. **Zero constraint violations** across all tests
3. **All solutions optimal** (0% gap)
4. **Degradation costs reasonable** (5-30% of revenue)
5. **Cycle reduction observed** (vs Model i baseline)

✅ **Secondary Criteria:**
6. **Profit reduction within expectations** (5-40% range)
7. **DOD distribution shifts** toward shallower cycles
8. **Solve time acceptable** (< 30s per test)
9. **All metrics computed** without errors
10. **Seasonal patterns logical** and explainable

### 10.2 Warning Conditions

⚠️ **Validation issues a WARNING if:**
- 1-2 tests have marginal Model (ii) criteria (but pass base criteria)
- Profit reduction exceeds 40% in aggressive scenario (but < 50%)
- Solve time exceeds 30s but < 60s
- Minor numerical precision issues (ε < 1e-6) in metrics

**Action:** Review specific test cases, but proceed with deployment

### 10.3 Failure Conditions

❌ **Validation FAILS if:**
- Any test fails base must-pass criteria (criteria 1-10)
- > 2 tests fail Model (ii) criteria
- Constraint violations occur
- Solver fails to converge
- Degradation costs negative or NaN
- Cycle count increases vs Model (i) in baseline
- Profit reduction > 50% (excessive degradation penalty)

**Action:** Debug implementation, do not deploy until fixed

### 10.4 Acceptance Decision

| Validation Result | Tests Passed | Action |
|-------------------|--------------|--------|
| **SUCCESS** | 24/24 | ✅ Approve for production use |
| **SUCCESS with WARNINGS** | 22-23/24 | ✅ Approve with documentation of edge cases |
| **PARTIAL FAILURE** | 20-21/24 | ⚠️ Review failures, conditional approval |
| **FAILURE** | < 20/24 | ❌ Do not deploy, fix bugs |

---

## 11. Future Extensions

### 11.1 Phase 2 Enhancements

After successful validation:
1. **Sensitivity analysis** on alpha parameter (α ∈ [0.1, 2.0])
2. **Full year validation** (52 weeks instead of 4)
3. **Multi-country expansion** (test all available markets)
4. **Calendar aging integration** (Model iii validation)
5. **Parameter optimization** (find optimal α for different use cases)

### 11.2 Continuous Validation

Establish continuous validation framework:
- Run validation weekly with new market data
- Track model performance drift over time
- Automate regression testing
- Monitor solver performance trends

---

## 12. References

**Related Documents:**
- `doc/dev_plan/model_ii_implementation_plan.md` - Implementation specification
- `py_script/validation/model_i_validation/README.md` - Model (i) validation reference
- `doc/p2_model/p2_bi_model_ggdp.tex` - Mathematical formulation
- `tests/test_model_ii.py` - Unit test suite

**Key Scripts:**
- `py_script/core/optimizer.py:1166-1532` - BESSOptimizerModelII implementation
- `py_script/validation/model_i_validation/run_seasonal_validation.py` - Model (i) reference

**Data Sources:**
- `data/processed/TechArena2025_data_tidy.jsonl` - Full year market data
- `data/phase2_aging_config/aging_config.json` - Degradation cost parameters

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-01-08 | Claude Code | Initial validation plan |

---

**End of Validation Plan**
