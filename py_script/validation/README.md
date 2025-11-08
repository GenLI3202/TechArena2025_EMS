# Model Validation Scripts

This folder contains benchmark validation scripts for testing and comparing BESS optimization models.

## Scripts

### 1. `run_seasonal_validation.py`
**Purpose:** Main seasonal validation script for running benchmark tests across representative weeks from each season.

**Features:**
- Tests 4 seasonal weeks (Q1/Winter, Q2/Spring, Q3/Summer, Q4/Fall)
- Runs 3 configuration scenarios: baseline, conservative, aggressive
- Generates comprehensive JSON metrics and CSV timeseries for each test
- Creates VALIDATION_REPORT.md summarizing all results
- Implements 10 must-pass criteria for model verification

**Usage:**
```bash
python py_script/validation/run_seasonal_validation.py
```

**Output Location:** `results/model_i_validation/HU_seasonal/`

### 2. `compare_validation_results.py`
**Purpose:** Compare validation results between different model versions or implementations.

**Features:**
- Loads results from two validation runs (old vs new)
- Calculates profit changes, revenue mix differences, and block allocation changes
- Generates comparison visualizations showing impact of changes
- Creates detailed comparison CSV with all metrics

**Usage:**
```bash
python py_script/validation/compare_validation_results.py
```

**Expected Directories:**
- Old results: `results/model_i_validation_old_EUR_MW_unit_ver/HU_seasonal/`
- New results: `results/model_i_validation/HU_seasonal/`
- Output: `results/model_i_validation/comparison/`

### 3. `visualize_validation.py`
**Purpose:** Create visualizations from validation results.

**Features:**
- Profit comparison charts across seasons and scenarios
- Revenue mix analysis (DA, aFRR-E, FCR, aFRR capacity)
- Performance summary metrics
- Best performing week analysis

**Usage:**
```bash
python py_script/validation/visualize_validation.py
```

**Output:** `results/model_i_validation/HU_seasonal/plots/`

### 4. `generate_report.py`
**Purpose:** Generate markdown validation report from JSON results.

**Features:**
- Aggregates all test results into summary tables
- Calculates seasonal performance metrics
- Analyzes must-pass criteria success rates
- Creates executive summary with key findings

**Usage:**
```bash
python py_script/validation/generate_report.py
```

**Output:** `results/model_i_validation/HU_seasonal/VALIDATION_REPORT.md`

## Validation Strategy

### Test Weeks (Hungary Market 2024)
- **Q1 Winter:** Week 7 (Feb 12-18, 2024)
- **Q2 Spring:** Week 17 (Apr 22-28, 2024)
- **Q3 Summer:** Week 30 (Jul 22-28, 2024)
- **Q4 Fall:** Week 48 (Nov 25-Dec 1, 2024)

### Configuration Scenarios

| Scenario | C-Rate | Daily Cycle Limit | Description |
|----------|--------|-------------------|-------------|
| Baseline | 0.5 | 1.5 | Standard operational parameters |
| Conservative | 0.33 | 1.0 | Lower degradation risk |
| Aggressive | 0.5 | 2.0 | Maximum utilization |

### Must-Pass Criteria

1. **Solver Success:** Optimal solution found
2. **Zero Violations:** No constraint violations
3. **SOC Bounds:** State of charge within [0, E_nom]
4. **Power Bounds:** Power within [0, P_max]
5. **Binary Consistency:** Binary variables properly linked
6. **No Simultaneous C/D:** No simultaneous charge/discharge
7. **Total Power Charging:** p_total = p_DA + p_aFRR_E (charging)
8. **Total Power Discharging:** p_total = p_DA + p_aFRR_E (discharging)
9. **Positive Profit:** Total profit > 0
10. **No NaN/Inf:** All metrics are valid numbers

## Usage for Model (ii) and (iii) Benchmarking

When implementing Models (ii) and (iii), use these scripts to:

1. **Run the same validation tests:**
   - Update optimizer reference in `run_seasonal_validation.py`
   - Keep all test configurations identical
   - Store results in separate directories (e.g., `model_ii_validation/`, `model_iii_validation/`)

2. **Compare with Model (i) baseline:**
   - Use `compare_validation_results.py` to analyze differences
   - Expected changes for Model (ii): Higher degradation costs due to cyclic aging
   - Expected changes for Model (iii): Calendar aging costs, different SOC strategies

3. **Verify improvements:**
   - Ensure all must-pass criteria still pass
   - Analyze profit changes (may decrease due to degradation costs)
   - Check if operational strategies change appropriately

## History

- **2025-11-08:** Initial validation setup for Model (i)
- **2025-11-08:** Bug fix - Capacity market revenue calculation (EUR/MW → EUR/MW/h with * db)
- Results from buggy version archived in `results/model_i_validation_old_EUR_MW_unit_ver/`

## Notes

- All scripts assume data is available in `data/processed/HU/`
- Scripts use the optimizer from `py_script/core/optimizer.py`
- Validation results are deterministic (same inputs → same outputs)
- Scripts are compatible with Windows (uses Path for cross-platform compatibility)
