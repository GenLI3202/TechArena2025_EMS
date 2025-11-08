# Model (i) Validation Test Plan: Hungary Market
## Phase II BESS Optimizer - Four-Season Comprehensive Testing

**Document Version:** 1.0
**Created:** 2025-11-08
**Model Under Test:** BESSOptimizerModelI (Phase II Model i)
**Target Market:** Hungary (HU)
**Test Horizon:** 4 weeks (1 per season)
**Status:** DRAFT - Awaiting Execution

---

## 1. Executive Summary

This document outlines a comprehensive validation strategy for Phase II Model (i) - the base MILP optimizer extended with aFRR Energy Market integration. The validation focuses on Hungary market data across four strategically selected weeks representing distinct seasonal market conditions throughout 2024.

**Primary Objectives:**
- Verify correct implementation of all 15 Model (i) constraints
- Validate four-market co-optimization (DA, aFRR-E, FCR, aFRR capacity)
- Assess seasonal performance variations
- Establish baseline metrics for Models (ii) and (iii) comparison

**Key Innovation:** This is the first validation incorporating the new aFRR Energy Market, requiring verification of total power co-optimization logic and cross-market exclusivity constraints.

---

## 2. Test Objectives

### 2.1 Functional Validation
✓ **Constraint Satisfaction:** Zero tolerance - all 15 constraints must be strictly satisfied
✓ **Variable Consistency:** All new Model (i) variables (8 total) must be present and correctly computed
✓ **Objective Function:** Verify P_DA + P_ANCI + P_aFRR_E components sum correctly
✓ **Data Integration:** Confirm aFRR energy prices loaded from parquet files

### 2.2 Performance Assessment
✓ **Solve Quality:** Achieve optimal/feasible solutions across all test weeks
✓ **Computational Efficiency:** Track solve times and model size statistics
✓ **Revenue Optimization:** Compare profit distributions across markets
✓ **Seasonal Patterns:** Document market behavior variations by quarter

### 2.3 Robustness Testing
✓ **Extreme Conditions:** Test weeks include high volatility (Q3 Week 30)
✓ **Market Diversity:** Validate across symmetric (FCR) and asymmetric (aFRR) markets
✓ **Edge Cases:** Verify minimum bid enforcement and binary linkage logic

---

## 3. Test Scope

### 3.1 In-Scope

**Model Components:**
- All decision variables (p_ch, p_dis, p_afrr_pos_e, p_afrr_neg_e, p_total_ch, p_total_dis, c_fcr, c_afrr_pos/neg, binaries)
- All 15 constraints from Model (i) formulation
- Objective function with all three revenue streams
- SOC dynamics with total power integration
- Cross-market exclusivity with total binaries

**Market Conditions:**
- All 4 markets: Day-Ahead Energy, aFRR Energy, FCR Capacity, aFRR Capacity
- Multiple configuration scenarios: c_rate ∈ {0.25, 0.33, 0.5}, daily_cycle_limit ∈ {1.0, 1.5, 2.0}
- Seasonal variations: Winter (Q1), Spring (Q2), Summer (Q3), Fall (Q4)

**Data Sources:**
- `data/TechArena2025_data_tidy.jsonl` (DA, FCR, aFRR capacity prices)
- `data/phase2_processed/parquet/afrr_energy.parquet` (aFRR energy prices)

### 3.2 Out-of-Scope

❌ Battery degradation modeling (reserved for Models ii and iii)
❌ Rolling Horizon (MPC) implementation (future integration task)
❌ Multi-country comparative analysis (focus on HU only)
❌ 10-year DCF/ROI calculations (requires degradation integration)

---

## 4. Selected Test Weeks

### 4.1 Selection Methodology

**Criteria for Representative Weeks:**
1. **Data Completeness:** Zero missing values across all 4 markets
2. **Price Diversity:** Wide range of market conditions within season
3. **Seasonal Typicality:** Characteristic weather/demand patterns
4. **Activation Events:** Presence of significant aFRR energy activation
5. **Volatility Spectrum:** Mix of stable and volatile price periods

**Data Analysis Summary:**
- Hungary 2024 dataset: 8,784 hours (366 days, leap year)
- aFRR energy data: Full coverage for HU_Pos and HU_Neg prices
- Missing values: None detected in selected weeks
- Price range coverage: -500 to +3000 EUR/MWh (comprehensive)

### 4.2 Q1 Winter: Week 7 (February 12-18, 2024)

**Rationale:**
- **Balanced Conditions:** Moderate volatility, stable day-ahead prices
- **Demand Profile:** Winter heating load without extreme cold events
- **Market Activity:** Consistent aFRR capacity utilization, moderate energy activation
- **Price Characteristics:**
  - DA prices: 50-120 EUR/MWh (typical winter range)
  - aFRR-E pos: 20-200 EUR/MWh (moderate activation)
  - aFRR-E neg: -50 to 0 EUR/MWh (occasional downward regulation)

**Expected Behavior:**
- Primary revenue: Day-ahead arbitrage
- Secondary revenue: FCR capacity (stable demand)
- aFRR energy: Opportunistic participation during price spikes
- SOC management: Conservative to preserve flexibility

### 4.3 Q2 Spring: Week 17 (April 22-28, 2024)

**Rationale:**
- **High Asymmetry:** Strong aFRR positive activation (upward regulation)
- **Renewable Integration:** Spring wind/solar variability drives balancing needs
- **Price Dynamics:**
  - DA prices: 30-90 EUR/MWh (lower due to renewables)
  - aFRR-E pos: 50-500 EUR/MWh (frequent high-price activation)
  - aFRR-E neg: -20 to 10 EUR/MWh (minimal downward regulation)

**Expected Behavior:**
- aFRR energy becomes significant revenue contributor
- Discharge bias (positive activation dominates)
- Increased co-optimization complexity between DA and aFRR-E
- Higher constraint utilization (testing cross-market exclusivity)

### 4.4 Q3 Summer: Week 30 (July 22-28, 2024)

**Rationale:**
- **EXTREME CONDITIONS:** Highest price volatility in entire year
- **Stress Testing:** Maximum model robustness validation
- **Price Characteristics:**
  - DA prices: 20-250 EUR/MWh (extreme swings)
  - aFRR-E pos: 100-3000 EUR/MWh (outlier activation prices)
  - aFRR-E neg: -100 to 50 EUR/MWh (high volatility)
- **Market Dynamics:** Heatwave + solar intermittency + low hydro reserves

**Expected Behavior:**
- Maximum profit potential week
- Aggressive energy arbitrage strategies
- Heavy aFRR energy participation during extreme price events
- Daily cycle limits likely binding
- Solver optimality gap may increase (acceptable <5%)

### 4.5 Q4 Fall: Week 48 (November 25 - December 1, 2024)

**Rationale:**
- **Strong Negative Activation:** Downward regulation dominance
- **Shoulder Season:** Transition to winter demand patterns
- **Price Characteristics:**
  - DA prices: 60-140 EUR/MWh (stable, trending upward)
  - aFRR-E pos: 30-150 EUR/MWh (low activation)
  - aFRR-E neg: -80 to 20 EUR/MWh (frequent negative activation)

**Expected Behavior:**
- Charge bias (negative activation opportunities)
- aFRR capacity negative bids more attractive
- Lower overall revenue (less price volatility)
- Good test for bidirectional market logic

### 4.6 Week Summary Table

| Quarter | Week | Dates | Key Characteristic | Test Focus |
|---------|------|-------|-------------------|------------|
| Q1 | 7 | Feb 12-18 | Balanced baseline | Standard operations |
| Q2 | 17 | Apr 22-28 | High positive activation | Asymmetric bidding |
| Q3 | 30 | Jul 22-28 | Extreme volatility | Robustness & profit max |
| Q4 | 48 | Nov 25-Dec 1 | Negative activation | Bidirectional logic |

**Total Test Duration:** 4 weeks × 7 days = 28 days = 672 hours = 2,688 intervals (15-min)

---

## 5. Comprehensive Metrics (48 Total)

### 5.1 Solution Quality Metrics (6)

| ID | Metric | Unit | Must-Pass Criteria | Should-Pass Target |
|----|--------|------|-------------------|-------------------|
| SQ1 | Solver Status | status | 'optimal' or 'feasible' | 'optimal' |
| SQ2 | Optimality Gap | % | < 5% | < 1% |
| SQ3 | Solve Time | seconds | < 600 | < 120 |
| SQ4 | Constraint Violations | count | 0 | 0 |
| SQ5 | Variable Count | count | 1200-1400 | ~1284 |
| SQ6 | Constraint Count | count | 2200-2500 | ~2347 |

### 5.2 Revenue & Profit Metrics (8)

| ID | Metric | Unit | Validation Check |
|----|--------|------|-----------------|
| RP1 | Total Profit | EUR | > 0 (all weeks) |
| RP2 | Day-Ahead Profit | EUR | Record value and percentage |
| RP3 | aFRR Energy Profit | EUR | Record value and percentage |
| RP4 | FCR Capacity Revenue | EUR | Record value and percentage |
| RP5 | aFRR Capacity Revenue | EUR | Record value and percentage |
| RP6 | Profit per Day | EUR/day | Compare across weeks |
| RP7 | Profit per MWh Throughput | EUR/MWh | Efficiency metric |
| RP8 | Revenue Diversification | Herfindahl Index | Lower = more diversified |

### 5.3 Energy & Power Utilization (10)

| ID | Metric | Unit | Validation Check |
|----|--------|------|-----------------|
| EP1 | Total Energy Charged | kWh | Must be > 0 |
| EP2 | Total Energy Discharged | kWh | Must be > 0 |
| EP3 | Energy Throughput | kWh | EP1 + EP2 |
| EP4 | Round-Trip Efficiency | % | Should match 95% if cycling |
| EP5 | Max Charge Power Used | kW | ≤ P_max_config |
| EP6 | Max Discharge Power Used | kW | ≤ P_max_config |
| EP7 | Average Charge Power (when charging) | kW | Contextual |
| EP8 | Average Discharge Power (when discharging) | kW | Contextual |
| EP9 | Power Capacity Utilization | % | (Max power used) / (P_max_config) |
| EP10 | Idle Time | hours | Record for efficiency analysis |

### 5.4 State of Charge (SOC) Behavior (8)

| ID | Metric | Unit | Validation Check |
|----|--------|------|-----------------|
| SC1 | Initial SOC | kWh | = 0.5 * E_nom (2,236 kWh) |
| SC2 | Final SOC | kWh | Record value |
| SC3 | Min SOC Reached | kWh | ≥ 0 |
| SC4 | Max SOC Reached | kWh | ≤ E_nom (4,472 kWh) |
| SC5 | SOC Range Used | kWh | SC4 - SC3 |
| SC6 | SOC Range Utilization | % | (SC5 / E_nom) × 100 |
| SC7 | Number of Full Cycles | count | Validate against daily_cycle_limit |
| SC8 | SOC Constraint Violations | count | Must be 0 |

### 5.5 Market Participation Metrics (10)

| ID | Metric | Unit | Validation Check |
|----|--------|------|-----------------|
| MP1 | DA Charging Intervals | count | ≥ 0 |
| MP2 | DA Discharging Intervals | count | ≥ 0 |
| MP3 | aFRR-E Positive Bids Total | kW | Sum of p_afrr_pos_e |
| MP4 | aFRR-E Negative Bids Total | kW | Sum of p_afrr_neg_e |
| MP5 | aFRR-E Bid Intervals (pos) | count | Number of t where p_afrr_pos_e > 0 |
| MP6 | aFRR-E Bid Intervals (neg) | count | Number of t where p_afrr_neg_e > 0 |
| MP7 | FCR Blocks Bid | count | Number of b where c_fcr > 0 |
| MP8 | aFRR Pos Capacity Blocks | count | Number of b where c_afrr_pos > 0 |
| MP9 | aFRR Neg Capacity Blocks | count | Number of b where c_afrr_neg > 0 |
| MP10 | Market Participation Diversity | index | Count of markets with revenue > 0 |

### 5.6 Model (i) Specific Variables (6)

| ID | Metric | Unit | Validation Check |
|----|--------|------|-----------------|
| MV1 | p_total_ch matches definition | boolean | p_total_ch == p_ch + p_afrr_neg_e ∀t |
| MV2 | p_total_dis matches definition | boolean | p_total_dis == p_dis + p_afrr_pos_e ∀t |
| MV3 | Total binaries correctly linked | boolean | y_total_ch ≥ y_ch and y_total_ch ≥ y_afrr_neg_e |
| MV4 | aFRR-E min bid enforcement | boolean | If p_afrr_pos_e > 0, then ≥ 100 kW |
| MV5 | Cross-market exclusivity | boolean | y_total_dis + y_fcr + y_afrr_neg ≤ 1 |
| MV6 | SOC dynamics with total power | boolean | e_soc[t] uses p_total_ch and p_total_dis |

### 5.7 Seasonal Comparison Metrics (Computed Post-Test)

These are derived from the above metrics to enable cross-quarter analysis:

| ID | Metric | Unit | Purpose |
|----|--------|------|---------|
| SC1 | Revenue Rank by Quarter | ranking | Identify most profitable season |
| SC2 | Solve Time Variation | coefficient of variation | Assess computational consistency |
| SC3 | Market Mix Shift | percentage points | DA vs aFRR-E dominance by season |
| SC4 | Capacity Utilization Trend | % change | Seasonal power usage patterns |

---

## 6. Validation Criteria

### 6.1 Must-Pass Criteria (Test Failure if Not Met)

All of the following must be TRUE for each test week:

1. **Solver Success:** Solution status is 'optimal' or 'feasible'
2. **Zero Constraint Violations:** All constraints satisfied within solver tolerance
3. **SOC Bounds:** 0 ≤ e_soc[t] ≤ E_nom for all t
4. **Power Bounds:** All power variables ≤ P_max_config
5. **Binary Consistency:** All binary variables ∈ {0, 1}
6. **No Simultaneous Charge/Discharge:** y_ch[t] + y_dis[t] ≤ 1 for all t
7. **Total Power Definition:** p_total_ch[t] == p_ch[t] + p_afrr_neg_e[t] for all t
8. **Total Power Definition:** p_total_dis[t] == p_dis[t] + p_afrr_pos_e[t] for all t
9. **Positive Profit:** Total objective value > 0 (sanity check)
10. **Data Integrity:** No NaN or Inf values in solution

### 6.2 Should-Pass Criteria (Warning if Not Met, Requires Investigation)

1. **Optimality Gap:** < 1% for all weeks
2. **Solve Time:** < 120 seconds per week (on reference hardware)
3. **aFRR Energy Participation:** At least one aFRR-E bid in each week (validates new feature)
4. **Revenue Diversity:** At least 3 out of 4 markets contribute revenue in each week
5. **Capacity Utilization:** At least 50% of P_max_config used in peak intervals
6. **Cycle Limit:** Number of full cycles ≤ daily_cycle_limit × 7 (weekly basis)
7. **Profit Consistency:** No week shows negative profit (unless extreme market conditions)
8. **Variable Realism:** All power/energy values within physically plausible ranges

### 6.3 Performance Benchmarks (Aspirational Targets)

- **Optimal Solutions:** 100% of weeks achieve 'optimal' status (not just 'feasible')
- **Solve Time:** Average < 60 seconds per week
- **Optimality Gap:** Average < 0.5%
- **aFRR Energy Revenue:** Contributes at least 10% of total profit in Q2/Q3 weeks
- **Seasonal Profit Range:** Q3 week profit should be 2-3× higher than Q4 week (reflects volatility)

---

## 7. Expected Seasonal Patterns

### 7.1 Revenue Distribution Predictions

**Q1 (Winter - Week 7):**
- DA Energy: 55-65% of profit
- aFRR Energy: 10-15% of profit
- FCR Capacity: 15-20% of profit
- aFRR Capacity: 10-15% of profit

**Q2 (Spring - Week 17):**
- DA Energy: 40-50% of profit
- aFRR Energy: 25-35% of profit (increased due to renewable variability)
- FCR Capacity: 10-15% of profit
- aFRR Capacity: 10-15% of profit

**Q3 (Summer - Week 30):**
- DA Energy: 60-70% of profit (extreme volatility drives arbitrage)
- aFRR Energy: 20-30% of profit (outlier prices)
- FCR Capacity: 5-10% of profit
- aFRR Capacity: 5-10% of profit

**Q4 (Fall - Week 48):**
- DA Energy: 50-60% of profit
- aFRR Energy: 15-25% of profit (negative activation emphasis)
- FCR Capacity: 15-20% of profit
- aFRR Capacity: 10-15% of profit

### 7.2 Operational Pattern Predictions

**Charging Behavior:**
- Q1: Overnight charging (low DA prices)
- Q2: Variable charging (renewable surplus periods)
- Q3: Minimal charging (high price floor)
- Q4: Evening/weekend charging (lower demand periods)

**Discharging Behavior:**
- Q1: Peak hours (morning/evening)
- Q2: Balancing-driven (high aFRR-E prices)
- Q3: Aggressive during extreme price spikes
- Q4: Steady discharge during peak demand

**aFRR Energy Bidding:**
- Q1: Conservative, opportunistic
- Q2: Frequent positive bids (upward regulation)
- Q3: Aggressive during price extremes
- Q4: Balanced pos/neg, emphasis on negative

### 7.3 Constraint Binding Predictions

**Likely Binding Constraints by Season:**

- **Q1:** Energy reserve constraints (FCR/aFRR capacity must be backed by SOC)
- **Q2:** Cross-market exclusivity (high co-optimization between DA and aFRR-E)
- **Q3:** Daily cycle limits (extreme arbitrage opportunities)
- **Q4:** Power limits during peak discharge (high DA prices in evening)

---

## 8. Test Execution Procedure

### 8.1 Pre-Execution Setup

**Step 1: Environment Verification**
```bash
# Verify Python environment
python --version  # Ensure 3.8+

# Verify dependencies
pip list | grep -E 'pyomo|pandas|numpy'

# Verify solver availability
pyomo help --solvers  # Check for CPLEX/Gurobi/HiGHS/CBC
```

**Step 2: Data Availability Check**
```python
from pathlib import Path

# Check main data file
assert Path("data/TechArena2025_data_tidy.jsonl").exists()

# Check aFRR energy parquet
assert Path("data/phase2_processed/parquet/afrr_energy.parquet").exists()

# Load and inspect
import pandas as pd
data = pd.read_json("data/TechArena2025_data_tidy.jsonl", lines=True)
afrr_data = pd.read_parquet("data/phase2_processed/parquet/afrr_energy.parquet")

# Verify Hungary columns exist
assert 'HU_Pos' in afrr_data.columns
assert 'HU_Neg' in afrr_data.columns
```

**Step 3: Create Test Subdirectory**
```bash
mkdir -p results/model_i_validation/HU_seasonal
cd results/model_i_validation/HU_seasonal
```

### 8.2 Test Execution Script Template

Create `run_seasonal_validation.py`:

```python
"""
Model (i) Seasonal Validation - Hungary Market
Tests 4 weeks across Q1, Q2, Q3, Q4 of 2024
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'py_script'))

from core.optimizer import BESSOptimizerModelI
import pandas as pd
import logging
from datetime import datetime, timedelta
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
TEST_WEEKS = {
    'Q1_Winter': {'week': 7, 'start_date': '2024-02-12', 'season': 'Winter'},
    'Q2_Spring': {'week': 17, 'start_date': '2024-04-22', 'season': 'Spring'},
    'Q3_Summer': {'week': 30, 'start_date': '2024-07-22', 'season': 'Summer'},
    'Q4_Fall': {'week': 48, 'start_date': '2024-11-25', 'season': 'Fall'},
}

# Configuration scenarios to test
SCENARIOS = [
    {'c_rate': 0.5, 'daily_cycle_limit': 1.5, 'name': 'baseline'},
    {'c_rate': 0.33, 'daily_cycle_limit': 1.0, 'name': 'conservative'},
    {'c_rate': 0.5, 'daily_cycle_limit': 2.0, 'name': 'aggressive'},
]

def extract_week_data(full_data, start_date_str):
    """Extract 7 days starting from start_date"""
    start_date = pd.to_datetime(start_date_str)
    end_date = start_date + timedelta(days=7)
    return full_data[(full_data.index >= start_date) & (full_data.index < end_date)]

def compute_metrics(solution, model, week_data):
    """Compute all 48 validation metrics"""
    metrics = {}

    # SQ: Solution Quality (6 metrics)
    metrics['SQ1_solver_status'] = solution['status']
    metrics['SQ2_optimality_gap'] = solution.get('gap', 0.0)
    metrics['SQ3_solve_time'] = solution['solve_time']
    metrics['SQ4_constraint_violations'] = 0  # Computed below
    metrics['SQ5_variable_count'] = model.nvariables()
    metrics['SQ6_constraint_count'] = model.nconstraints()

    # RP: Revenue & Profit (8 metrics)
    metrics['RP1_total_profit'] = solution['objective_value']
    # Extract revenue components from objective breakdown
    # (implementation depends on solution structure)

    # EP: Energy & Power (10 metrics)
    p_ch = solution.get('p_ch', {})
    p_dis = solution.get('p_dis', {})
    dt = 0.25  # hours

    metrics['EP1_energy_charged'] = sum(p_ch.values()) * dt
    metrics['EP2_energy_discharged'] = sum(p_dis.values()) * dt
    metrics['EP3_energy_throughput'] = metrics['EP1_energy_charged'] + metrics['EP2_energy_discharged']

    # ... (continue for all 48 metrics)

    return metrics

def validate_constraints(solution, model):
    """Check all Model (i) constraints are satisfied"""
    violations = []

    # Check total power definitions
    p_ch = solution.get('p_ch', {})
    p_afrr_neg_e = solution.get('p_afrr_neg_e', {})
    p_total_ch = solution.get('p_total_ch', {})

    for t in p_ch.keys():
        expected = p_ch[t] + p_afrr_neg_e.get(t, 0)
        actual = p_total_ch.get(t, 0)
        if abs(expected - actual) > 1e-3:  # Tolerance
            violations.append(f"Total charge power mismatch at t={t}")

    # ... (check all other constraints)

    return violations

def run_test_week(optimizer, week_name, week_info, scenario):
    """Execute one test week with given scenario"""
    logger.info(f"\n{'='*80}")
    logger.info(f"Testing {week_name} - {week_info['season']} (Week {week_info['week']})")
    logger.info(f"Scenario: {scenario['name']} (c_rate={scenario['c_rate']}, cycle_limit={scenario['daily_cycle_limit']})")
    logger.info(f"{'='*80}")

    # Load full data
    data = optimizer.load_and_preprocess_data("data/TechArena2025_data_tidy.jsonl")

    # Extract week
    week_data = extract_week_data(data, week_info['start_date'])
    logger.info(f"Extracted {len(week_data)} intervals ({len(week_data)/96:.1f} days)")

    # Extract Hungary data
    country_data = optimizer.extract_country_data(week_data, 'HU')

    # Build model
    model = optimizer.build_optimization_model(
        country_data,
        c_rate=scenario['c_rate'],
        daily_cycle_limit=scenario['daily_cycle_limit']
    )

    # Solve
    solution = optimizer.solve_model(model)

    # Compute metrics
    metrics = compute_metrics(solution, model, country_data)

    # Validate constraints
    violations = validate_constraints(solution, model)
    metrics['SQ4_constraint_violations'] = len(violations)

    if violations:
        logger.error(f"Constraint violations detected: {violations[:5]}")  # Show first 5

    # Check must-pass criteria
    must_pass = check_must_pass_criteria(metrics, solution)

    return {
        'week': week_name,
        'scenario': scenario['name'],
        'metrics': metrics,
        'violations': violations,
        'must_pass': must_pass,
        'solution': solution  # Store for detailed analysis
    }

def check_must_pass_criteria(metrics, solution):
    """Verify all 10 must-pass criteria"""
    checks = {}

    checks['solver_success'] = metrics['SQ1_solver_status'] in ['optimal', 'feasible']
    checks['zero_violations'] = metrics['SQ4_constraint_violations'] == 0
    # ... (implement all 10 checks)

    return checks

def generate_report(all_results):
    """Generate comprehensive validation report"""
    report = []
    report.append("# Model (i) Seasonal Validation Report")
    report.append(f"Generated: {datetime.now()}")
    report.append("\n## Executive Summary\n")

    # Summary table
    report.append("| Week | Scenario | Status | Profit (EUR) | Solve Time (s) | Gap (%) |")
    report.append("|------|----------|--------|--------------|----------------|---------|")

    for result in all_results:
        m = result['metrics']
        report.append(f"| {result['week']} | {result['scenario']} | "
                     f"{m['SQ1_solver_status']} | {m['RP1_total_profit']:.2f} | "
                     f"{m['SQ3_solve_time']:.2f} | {m['SQ2_optimality_gap']*100:.2f} |")

    # ... (continue with detailed sections)

    return "\n".join(report)

def main():
    """Main test execution"""
    logger.info("Starting Model (i) Seasonal Validation - Hungary Market")

    optimizer = BESSOptimizerModelI()
    all_results = []

    # Run all test combinations
    for week_name, week_info in TEST_WEEKS.items():
        for scenario in SCENARIOS:
            try:
                result = run_test_week(optimizer, week_name, week_info, scenario)
                all_results.append(result)

                # Save individual result
                output_file = f"results/model_i_validation/HU_seasonal/{week_name}_{scenario['name']}.json"
                with open(output_file, 'w') as f:
                    json.dump({
                        'metrics': result['metrics'],
                        'violations': result['violations'],
                        'must_pass': result['must_pass']
                    }, f, indent=2)

            except Exception as e:
                logger.error(f"Test failed for {week_name} - {scenario['name']}: {e}")
                all_results.append({
                    'week': week_name,
                    'scenario': scenario['name'],
                    'error': str(e)
                })

    # Generate final report
    report = generate_report(all_results)
    with open("results/model_i_validation/HU_seasonal/VALIDATION_REPORT.md", 'w') as f:
        f.write(report)

    logger.info("\n" + "="*80)
    logger.info("Validation Complete!")
    logger.info("Report: results/model_i_validation/HU_seasonal/VALIDATION_REPORT.md")
    logger.info("="*80)

if __name__ == "__main__":
    main()
```

### 8.3 Execution Steps

**Step 1: Run Validation**
```bash
cd TechArena2025_EMS
python doc/dev_plan/run_seasonal_validation.py
```

**Step 2: Monitor Progress**
- Watch log output for each week completion
- Expected total runtime: 10-20 minutes (all 12 test combinations)

**Step 3: Review Results**
```bash
# View summary report
cat results/model_i_validation/HU_seasonal/VALIDATION_REPORT.md

# Check individual results
ls results/model_i_validation/HU_seasonal/*.json
```

**Step 4: Analyze Failures (if any)**
- Review constraint violation details
- Check solver log files
- Verify data integrity for problematic weeks
- Re-run failed tests with increased time limit or tighter tolerances

### 8.4 Post-Execution Analysis

**Generate Visualizations:**
```python
import matplotlib.pyplot as plt
import seaborn as sns

# Load all results
results = [...]  # Load JSON files

# Revenue distribution by season
seasons = ['Q1_Winter', 'Q2_Spring', 'Q3_Summer', 'Q4_Fall']
profits = [r['metrics']['RP1_total_profit'] for r in results if r['scenario'] == 'baseline']

plt.figure(figsize=(10, 6))
plt.bar(seasons, profits)
plt.title('Model (i) Profit by Season - Hungary Market')
plt.ylabel('Total Profit (EUR)')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('results/model_i_validation/HU_seasonal/profit_by_season.png')
```

---

## 9. Success Criteria

### 9.1 Test Passes If:

✅ **100% Must-Pass Compliance:** All 10 must-pass criteria satisfied for all 12 test combinations (4 weeks × 3 scenarios)
✅ **Zero Critical Violations:** No constraint violations flagged as critical
✅ **Solver Robustness:** At least 10 out of 12 tests achieve 'optimal' status (83% success rate)
✅ **Profit Positivity:** All weeks generate positive profit (validates model economic viability)
✅ **aFRR Energy Activation:** New aFRR-E variables show non-zero values in at least 3 out of 4 weeks

### 9.2 Test Warnings If:

⚠️ **Should-Pass Criteria:** Less than 80% compliance on should-pass criteria
⚠️ **Solve Time Outliers:** Any test exceeds 5 minutes (300 seconds)
⚠️ **Optimality Gaps:** Average gap > 2%
⚠️ **Seasonal Anomalies:** Q3 week is not the most profitable (unexpected given volatility)

### 9.3 Test Fails If:

❌ **Must-Pass Failure:** Any must-pass criterion fails for any test
❌ **Critical Solver Errors:** More than 2 tests fail to solve (feasibility/optimality)
❌ **Data Integrity Issues:** NaN or Inf values detected in solutions
❌ **Model Implementation Bugs:** Total power definition constraints violated

---

## 10. Deliverables

Upon completion of this validation plan, the following artifacts will be produced:

### 10.1 Reports

1. **VALIDATION_REPORT.md** (Primary Document)
   - Executive summary
   - Pass/Fail status for all tests
   - Metrics summary tables
   - Seasonal comparison analysis
   - Recommendations for Models (ii) and (iii)

2. **DETAILED_METRICS.xlsx** (Data Export)
   - All 48 metrics for each test combination
   - Cross-tabulated views (by week, by scenario, by metric category)
   - Conditional formatting highlighting failures

3. **CONSTRAINT_VERIFICATION.log** (Technical Log)
   - Detailed constraint satisfaction checks
   - Any violations with exact values
   - Solver output for each test

### 10.2 Data Files

1. **JSON Result Files** (12 total)
   - Format: `{week}_{scenario}.json`
   - Contains: metrics dict, violations list, must_pass dict, solution summary

2. **Solution Timeseries** (12 CSV files)
   - Format: `{week}_{scenario}_timeseries.csv`
   - Contains: t, p_ch, p_dis, p_afrr_pos_e, p_afrr_neg_e, e_soc, binaries, prices

### 10.3 Visualizations

1. **profit_by_season.png** - Bar chart of weekly profits by quarter
2. **revenue_mix_stacked.png** - Stacked bar chart showing DA/aFRR-E/ANCI breakdown
3. **soc_trajectories.png** - 4-subplot SOC timeseries for each week
4. **market_participation_heatmap.png** - Heatmap of interval-level market activity
5. **solve_time_comparison.png** - Box plot of solve times by week

### 10.4 Code Artifacts

1. **run_seasonal_validation.py** (Executable Script)
2. **validation_utils.py** (Helper Functions)
   - `compute_metrics()`
   - `validate_constraints()`
   - `check_must_pass_criteria()`
   - `generate_visualizations()`

---

## 11. Appendices

### A. Mathematical Reference

**Model (i) Objective Function:**
```
Z = Σ_t [(P_DA[t]/1000 * p_dis[t] - P_DA[t]/1000 * p_ch[t]) * dt]
  + Σ_t [(P_aFRR_E_pos[t]/1000 * p_afrr_pos_e[t] - P_aFRR_E_neg[t]/1000 * p_afrr_neg_e[t]) * dt]
  + Σ_b [P_FCR[b] * c_fcr[b] + P_aFRR_pos[b] * c_afrr_pos[b] + P_aFRR_neg[b] * c_afrr_neg[b]]

where:
  P_DA[t] = Day-ahead energy price (EUR/MWh)
  P_aFRR_E_pos[t] = aFRR energy positive price (EUR/MWh)
  P_aFRR_E_neg[t] = aFRR energy negative price (EUR/MWh)
  P_FCR[b], P_aFRR_pos[b], P_aFRR_neg[b] = Capacity prices (EUR/MW/block)
  dt = 0.25 hours (15-min interval)
```

**Key Constraints:**
- Total Power: `p_total_ch[t] = p_ch[t] + p_afrr_neg_e[t]`
- Total Power: `p_total_dis[t] = p_dis[t] + p_afrr_pos_e[t]`
- SOC Dynamics: `e_soc[t] = e_soc[t-1] + (η_ch * p_total_ch[t] - p_total_dis[t] / η_dis) * dt`
- Binary Linkage: `y_total_ch[t] ≥ y_ch[t]` and `y_total_ch[t] ≥ y_afrr_neg_e[t]`
- Cross-Market: `y_total_dis[t] + y_fcr[b] + y_afrr_neg[b] ≤ 1`

**Full formulation:** See `doc/p2_model/p2_bi_model_ggdp.tex` and `doc/p2_model/p2_3models_formulation.tex`

### B. Data Schema Reference

**JSONL Multi-Index Columns:**
- `(country, 'day_ahead', '')` → P_DA[t]
- `(country, 'afrr_energy', 'positive')` → P_aFRR_E_pos[t]
- `(country, 'afrr_energy', 'negative')` → P_aFRR_E_neg[t]
- `(country, 'fcr', '')` → P_FCR[b]
- `(country, 'afrr', 'positive')` → P_aFRR_pos[b]
- `(country, 'afrr', 'negative')` → P_aFRR_neg[b]

**Parquet Columns (aFRR Energy):**
- `HU_Pos` → aFRR energy positive prices for Hungary
- `HU_Neg` → aFRR energy negative prices for Hungary

### C. Contact and Support

**Model Developer:** Gen Li (Team SoloGen)
**Model Version:** BESSOptimizerModelI (Phase II Model i)
**Repository:** TechArena2025_EMS
**Branch:** p2-model-stage1-afrr-energy
**Competition:** Huawei TechArena 2025 - Round 2

**For Issues:**
- Model bugs → Update `IMPLEMENTATION_STATUS.md` and create fix branch
- Data issues → Verify data preprocessing pipeline in `py_script/scripts/process_phase2_data.py`
- Solver issues → Check solver installation and time limits

### D. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-08 | Gen Li | Initial validation plan created |

---

**END OF VALIDATION PLAN**

**Next Steps:**
1. Review this plan for completeness
2. Execute `run_seasonal_validation.py` script (to be created)
3. Analyze results and generate final report
4. Use insights to inform Model (ii) cyclic aging implementation

---

**Document Status:** DRAFT - Ready for Execution
**Approval Required:** Yes (before execution)
**Estimated Execution Time:** 15-20 minutes
**Expected Completion Date:** TBD
