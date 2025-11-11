# Model (ii) Seasonal Validation

Comprehensive validation framework for **Model (ii): Cyclic Aging Cost Integration** across diverse seasonal market conditions.

## Quick Start

```bash
# Navigate to validation directory
cd py_script/validation/model_ii_validation

# Run Hungary validation (12 tests, ~3 minutes)
python run_seasonal_validation.py

# Run Switzerland validation (12 tests, ~3 minutes)
python run_ch_validation.py

# Generate visualizations
python visualize_validation.py

# Generate comparison report
python compare_with_model_i.py

# View results
cat ../../results/model_ii_validation/HU_seasonal/VALIDATION_REPORT.md
```

---

## What is Model (ii) Validation?

This validation framework tests **Model (ii)**, which extends Model (i) by incorporating **cyclic degradation costs** into the BESS optimization objective. The validation:

- Tests **4 representative weeks** from each season (Q1-Q4)
- Evaluates **3 scenarios** per week (baseline, conservative, aggressive)
- Validates against **58 metrics** across 7 categories
- **Compares with Model (i)** to quantify degradation impact
- Tests **2 countries** (Hungary and Switzerland)

**Total:** 24 comprehensive test scenarios

---

## Model (ii) Overview

### Key Differences from Model (i)

| Feature | Model (i) | Model (ii) |
|---------|-----------|------------|
| **Objective** | Maximize profit | Maximize profit - α × degradation cost |
| **Cycle Control** | Hard constraint (daily_cycle_limit) | Economic incentive (cost-based) |
| **SOC Tracking** | Aggregate (single variable) | Segment-based (10 segments) |
| **Degradation** | Not considered | Piecewise-linear cyclic aging cost |
| **Optimization** | Profit-only focus | Profit-longevity trade-off |

### Alpha Parameter (α)

Controls degradation cost weighting in objective:
- **α = 1.0** (Baseline): Full degradation cost consideration
- **α = 1.5** (Conservative): 50% higher penalty, prioritize longevity
- **α = 0.5** (Aggressive): 50% lower penalty, prioritize short-term profit

---

## Test Matrix

### Test Weeks (Seasonal Representatives)

| Quarter | Season | Week | Dates | Market Characteristics |
|---------|--------|------|-------|------------------------|
| Q1 | Winter | 7 | Feb 12-18 | High demand, moderate volatility |
| Q2 | Spring | 17 | Apr 22-28 | Shoulder season, moderate conditions |
| Q3 | Summer | 30 | Jul 22-28 | High solar, high volatility (best profits) |
| Q4 | Fall | 48 | Nov 25-Dec 1 | Variable renewable, moderate-high demand |

### Test Scenarios

| Scenario | c_rate | alpha | Description |
|----------|--------|-------|-------------|
| **Baseline** | 0.5 | 1.0 | Standard operation |
| **Conservative** | 0.33 | 1.5 | Battery longevity focus |
| **Aggressive** | 0.5 | 0.5 | Short-term profit focus |

---

## Validation Metrics

### 58 Total Metrics Across 7 Categories

#### Base Metrics (48 - inherited from Model i)
- **SQ** - Solution Quality (6): Solver performance, optimality
- **RP** - Revenue & Profit (8): Financial metrics
- **EP** - Energy & Power (10): Battery utilization
- **SC** - State of Charge (8): SOC behavior and cycling
- **MP** - Market Participation (10): Market engagement patterns
- **MV** - Model Variables (6): Constraint verification

#### Degradation Metrics (10 - Model ii specific)
- **DG1**: Total cyclic degradation cost (EUR)
- **DG2**: Degradation cost per full cycle (EUR/cycle)
- **DG3**: Degradation cost ratio (% of revenue)
- **DG4**: Net profit after degradation (EUR)
- **DG5**: Profit reduction vs Model (i) (%)
- **DG6**: Cycle count reduction vs Model (i) (%)
- **DG7**: Average depth of discharge (%)
- **DG8**: Shallow cycle count (DOD < 50%)
- **DG9**: Deep cycle count (DOD > 80%)
- **DG10**: Alpha effectiveness score

---

## Must-Pass Criteria

All tests must satisfy **13 criteria**:

### Base Criteria (10)
1. Solver success (optimal/feasible)
2. Zero constraint violations
3. SOC within bounds [0, E_nom]
4. Power within bounds [0, P_max]
5. Binary consistency {0, 1}
6. No simultaneous charge/discharge
7. Total charging power correct
8. Total discharging power correct
9. Positive profit (after degradation)
10. No NaN/Inf values

### Model (ii) Specific (3)
11. Valid degradation costs (≥ 0)
12. Reasonable profit reduction (0-50% vs Model i)
13. Cycle reduction observed (≤ Model i for baseline)

**Target:** 100% pass rate (24/24 tests)

---

## Expected Results

### Profit Impact

| Scenario | Expected Profit Reduction vs Model (i) |
|----------|---------------------------------------|
| Baseline (α=1.0) | 10-25% |
| Conservative (α=1.5) | 20-35% |
| Aggressive (α=0.5) | 5-15% |

### Cycling Behavior

| Scenario | Expected Cycle Reduction vs Model (i) |
|----------|---------------------------------------|
| Baseline (α=1.0) | 15-30% |
| Conservative (α=1.5) | 25-40% |
| Aggressive (α=0.5) | 5-20% |

### Seasonal Ranking (Baseline)
1. **Q3 Summer:** ~€45k-50k (highest)
2. **Q2 Spring:** ~€28k-32k
3. **Q4 Fall:** ~€25k-28k
4. **Q1 Winter:** ~€18k-22k (lowest)

---

## Output Structure

```
results/model_ii_validation/
├── HU_seasonal/
│   ├── Q1_Winter_baseline.json              # Baseline scenario results
│   ├── Q1_Winter_baseline_timeseries.csv    # Timeseries data
│   ├── Q1_Winter_conservative.json          # Conservative scenario
│   ├── Q1_Winter_conservative_timeseries.csv
│   ├── Q1_Winter_aggressive.json            # Aggressive scenario
│   ├── Q1_Winter_aggressive_timeseries.csv
│   ├── [Q2, Q3, Q4 similar structure...]
│   ├── comparison_with_model_i/
│   │   ├── profit_comparison.csv
│   │   ├── cycle_comparison.csv
│   │   ├── degradation_analysis.csv
│   │   └── revenue_mix_changes.csv
│   └── VALIDATION_REPORT.md                 # Main report
├── CH_seasonal/
│   └── [Same structure]
└── visualizations/
    ├── profit_comparison_model_i_vs_ii.png
    ├── degradation_cost_breakdown.png
    ├── cycle_reduction_analysis.png
    ├── revenue_mix_changes.png
    ├── seasonal_performance.png
    ├── alpha_sensitivity.png
    ├── dod_distribution.png
    └── best_week_detailed.png
```

---

## Usage

### 1. Run Main Validation (Hungary)

```bash
python run_seasonal_validation.py
```

**What it does:**
- Loads full year data and Model (i) reference results
- Runs 12 test scenarios (4 weeks × 3 scenarios)
- Computes 58 metrics per test
- Validates 13 must-pass criteria
- Compares with Model (i) baseline
- Saves JSON and CSV results
- Generates validation report

**Output:**
- `results/model_ii_validation/HU_seasonal/*.json` (12 files)
- `results/model_ii_validation/HU_seasonal/*.csv` (12 files)
- `results/model_ii_validation/HU_seasonal/VALIDATION_REPORT.md`

**Expected runtime:** ~3 minutes

### 2. Run Switzerland Validation

```bash
python run_ch_validation.py
```

Same as above, but for Switzerland market.

**Output:** `results/model_ii_validation/CH_seasonal/`

**Expected runtime:** ~3 minutes

### 3. Generate Visualizations

```bash
python visualize_validation.py
```

**Generates 8 plots:**
1. Profit comparison (Model i vs ii)
2. Degradation cost breakdown
3. Cycle reduction analysis
4. Revenue mix changes
5. Seasonal performance trends
6. Alpha sensitivity analysis
7. DOD distribution histograms
8. Best week detailed analysis

**Output:** `results/model_ii_validation/visualizations/*.png`

**Expected runtime:** ~30 seconds

### 4. Detailed Model Comparison

```bash
python compare_with_model_i.py
```

**Creates comparison datasets:**
- Profit deltas for all 24 tests
- Cycle count deltas
- Degradation cost summary
- Revenue mix shifts
- Statistical analysis

**Output:** `results/model_ii_validation/*/comparison_with_model_i/*.csv`

**Expected runtime:** ~10 seconds

### 5. Regenerate Report

```bash
python generate_report.py
```

Regenerates `VALIDATION_REPORT.md` from existing JSON results.

Useful after manual edits or additional analysis.

---

## Interpreting Results

### Validation Report

Open `results/model_ii_validation/HU_seasonal/VALIDATION_REPORT.md`

**Key sections:**
1. **Executive Summary**: Pass/fail overview
2. **Test Results Table**: All 12 tests with key metrics
3. **Seasonal Analysis**: Performance by quarter
4. **Model Comparison**: Impact of degradation costs
5. **Degradation Deep Dive**: Cost analysis and cycling behavior
6. **Conclusions**: Overall assessment

### Success Indicators

✅ **PASS:** All tests show:
- Status: optimal
- Violations: 0
- Must-pass: 13/13
- Profit reduction: 5-40%
- Cycle reduction: > 0%

⚠️ **WARNING:** Minor issues:
- 1-2 tests have marginal Model (ii) criteria
- Profit reduction 40-50%
- Solve time 30-60s

❌ **FAIL:** Critical issues:
- Any constraint violations
- Solver failures
- Negative degradation costs
- Cycle increase vs Model (i)
- Profit reduction > 50%

### Key Metrics to Check

**1. DG5: Profit Reduction vs Model (i)**
- Baseline: 10-25% expected
- If < 5%: Degradation cost too low, not meaningful
- If > 40%: Degradation cost too high, excessive penalty

**2. DG6: Cycle Reduction vs Model (i)**
- Should be positive (fewer cycles)
- Indicates degradation awareness working
- If negative: Model (ii) cycling more (unexpected)

**3. DG3: Degradation Cost Ratio**
- 5-30% of gross revenue expected
- Shows magnitude of degradation consideration
- Should be consistent across similar scenarios

**4. DG7: Average DOD**
- Should be lower than Model (i)
- Validates preference for shallow cycles
- Indicates battery-friendly operation

---

## Troubleshooting

### Issue: Solver Fails

**Symptoms:** SQ1 = "failed", solve time very high

**Solutions:**
1. Check solver installation: `python -c "import highspy; print(highspy.__version__)"`
2. Try different solver: CBC, GLPK, Gurobi
3. Reduce problem size: test single day instead of week
4. Check data quality: ensure no NaN/Inf in input data

### Issue: Constraint Violations

**Symptoms:** SQ4 > 0, must-pass criterion 2 fails

**Solutions:**
1. Check violation details in JSON output
2. Review constraint formulation in `optimizer.py`
3. Verify input data ranges (SOC, power limits)
4. Check numerical tolerances in solver settings

### Issue: Negative Degradation Costs

**Symptoms:** DG1 < 0, must-pass criterion 11 fails

**Solutions:**
1. Verify `aging_config.json` has all positive costs
2. Check segment discharge power calculation
3. Review objective function modification code
4. Ensure no negative power variables

### Issue: Model (ii) Cycles More Than Model (i)

**Symptoms:** DG6 < 0, must-pass criterion 13 fails

**Solutions:**
1. Verify alpha parameter is correct (should be ≥ 0.5 for baseline)
2. Check Model (i) reference results are correct
3. Review degradation cost calculation
4. Consider if Model (i) had very restrictive cycle limit

### Issue: Extremely Long Solve Time

**Symptoms:** SQ3 > 60s, validation takes > 30 minutes

**Solutions:**
1. Disable segment binary constraints: `enforce_segment_binary=False`
2. Use commercial solver (Gurobi/CPLEX instead of HiGHS)
3. Warm-start from previous solution
4. Reduce MIP gap tolerance slightly

---

## Advanced Usage

### Custom Test Weeks

Edit script to test different weeks:

```python
TEST_WEEKS = {
    'Custom_Week1': {'week': 10, 'start_date': '2024-03-04', 'season': 'Spring'},
    # Add more weeks
}
```

### Custom Alpha Values

Test different degradation weighting:

```python
SCENARIOS = {
    'ultra_aggressive': {'c_rate': 0.5, 'alpha': 0.1},
    'ultra_conservative': {'c_rate': 0.33, 'alpha': 2.0},
}
```

### Single Test Execution

Run one specific test for debugging:

```python
python run_seasonal_validation.py --week Q3_Summer --scenario baseline --country HU
```

### Comparison with Custom Baseline

Compare with different Model (i) results:

```python
python compare_with_model_i.py --baseline custom_model_i_results/
```

---

## Dependencies

### Required Packages

```bash
pip install pyomo>=6.7.0 pandas>=2.0.0 numpy>=1.24.0 matplotlib>=3.7.0 seaborn>=0.12.0
```

### Required Solvers

At least one of:
- **HiGHS** (recommended): `pip install highspy`
- **CBC**: `conda install coin-or-cbc`
- **GLPK**: `conda install glpk`
- **Gurobi**: Commercial license required

### Required Data

Ensure these files exist:
```
data/processed/TechArena2025_data_tidy.jsonl
data/phase2_aging_config/aging_config.json
results/model_i_validation/HU_seasonal/*.json
results/model_i_validation/CH_seasonal/*.json
```

---

## Validation Workflow

```
┌─────────────────────────────────────────────────────────┐
│ 1. Run Model (i) Validation (if not done)             │
│    py_script/validation/model_i_validation/            │
└────────────────────┬───────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│ 2. Run Model (ii) Validation                           │
│    python run_seasonal_validation.py                    │
│    python run_ch_validation.py                          │
└────────────────────┬───────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│ 3. Generate Comparison Analysis                        │
│    python compare_with_model_i.py                       │
└────────────────────┬───────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│ 4. Create Visualizations                               │
│    python visualize_validation.py                       │
└────────────────────┬───────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│ 5. Review Validation Report                            │
│    Open VALIDATION_REPORT.md                            │
│    Check: 24/24 tests pass, all criteria satisfied     │
└────────────────────┬───────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│ 6. Decision: Approve or Debug                          │
│    ✅ All pass → Approve for production                │
│    ⚠️  Warnings → Review edge cases                    │
│    ❌ Failures → Debug and rerun                       │
└─────────────────────────────────────────────────────────┘
```

---

## Related Documentation

**Implementation:**
- `doc/dev_plan/model_ii_implementation_plan.md` - Implementation guide
- `py_script/core/optimizer.py:1166-1532` - Model (ii) code
- `tests/test_model_ii.py` - Unit tests

**Validation:**
- `VALIDATION_PLAN.md` - Detailed validation plan (this directory)
- `py_script/validation/model_i_validation/README.md` - Model (i) reference

**Mathematical Formulation:**
- `doc/p2_model/p2_bi_model_ggdp.tex` - LaTeX formulation
- `doc/p2_model/p2_3models_formulation.tex` - Three-model comparison

**Configuration:**
- `data/phase2_aging_config/aging_config.json` - Degradation parameters

---

## Support

**Issues:**
- Check existing issues in project tracker
- Review troubleshooting section above
- Consult Model (i) validation for similar issues

**Questions:**
- Review VALIDATION_PLAN.md for detailed methodology
- Check unit tests for implementation examples
- Refer to implementation plan for design decisions

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-01-08 | Initial validation framework |

---

**Status:** Ready for implementation
**Last Updated:** 2025-01-08
