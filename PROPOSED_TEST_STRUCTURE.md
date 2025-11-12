# Proposed Test Utilities Refactoring

## Problem
Current test scripts are too specific (hardcoded countries, hours, scenarios).
They should be general-purpose utilities that can be parameterized.

## Proposed Structure

### 1. **py_script/test/test_optimizer_core.py** (Keep as-is, add refactoring tests)
   - Formal pytest unit tests
   - Fast, deterministic tests
   - **NEW**: Add `TestRefactoredStructure` class from test_refactoring.py

### 2. **py_script/validation/run_optimization.py** (NEW - General Runner)
   **Purpose**: General-purpose optimization runner with flexible parameters

   **Features**:
   - CLI interface with argparse
   - Supports all three models (I, II, III)
   - Flexible time windows (any hours, any start point)
   - Any country from available data
   - Configurable solver, alpha, c-rate, etc.
   - Auto-generates visualizations
   - Saves results in organized output structure

   **Usage Examples**:
   ```bash
   # Run 36h HU winter (replaces run_36h_hu_winter.py)
   python run_optimization.py --model III --country HU --hours 36 --start-step 0 --alpha 0.5 --plots

   # Run 48h DE summer
   python run_optimization.py --model II --country DE --hours 48 --start-step 4000 --alpha 1.0

   # Quick 12h test with Model I
   python run_optimization.py --model I --country AT --hours 12 --c-rate 0.33 --cycles 1.5
   ```

### 3. **py_script/validation/compare_optimizations.py** (NEW - General Comparator)
   **Purpose**: Compare different optimization approaches/configurations

   **Features**:
   - Compare single-shot vs MPC
   - Compare Model I vs Model II vs Model III
   - Compare different alphas
   - Compare different countries
   - Generate comparison plots and summary tables

   **Usage Examples**:
   ```bash
   # Compare 32h single vs MPC (replaces test_single_32h_vs_mpc.py)
   python compare_optimizations.py --compare-type single-vs-mpc --hours 32 --country HU

   # Compare Model I vs Model II
   python compare_optimizations.py --compare-type models --models I II --hours 24 --country DE

   # Compare different alphas for Model III
   python compare_optimizations.py --compare-type alpha --alphas 0.5 1.0 1.5 --hours 36 --country HU
   ```

### 4. **py_script/validation/validation_utils.py** (NEW - Shared Utilities)
   **Purpose**: Common functions used by validation scripts

   **Functions**:
   - `load_market_data(country, start_step, num_steps)` - Load data slice
   - `run_single_optimization(optimizer, data, **kwargs)` - Standard run pattern
   - `save_results(solution, metadata, output_dir)` - Standard save format
   - `generate_standard_plots(solution, data, output_dir)` - All 4 plots
   - `extract_performance_summary(solution)` - Key metrics extraction
   - `validate_solution_constraints(solution, model)` - Constraint checking

### 5. **py_script/validation/batch_validation.py** (NEW - Batch Runner)
   **Purpose**: Run multiple validation scenarios in batch

   **Features**:
   - Run predefined validation suites
   - Compare across multiple countries
   - Test sensitivity to parameters
   - Generate comprehensive reports

   **Usage Examples**:
   ```bash
   # Run full validation suite (all countries, all models, standard scenarios)
   python batch_validation.py --suite full --output-dir results/validation_suite_2025

   # Run sensitivity analysis for alpha
   python batch_validation.py --suite alpha-sensitivity --country HU --hours 36
   ```

## Migration Plan

### Phase 1: Create Core Utilities
1. Create `validation_utils.py` with shared functions
2. Extract common patterns from existing scripts

### Phase 2: Create General Runners
1. Create `run_optimization.py` (generalizes run_36h_hu_winter.py)
2. Create `compare_optimizations.py` (generalizes test_single_32h_vs_mpc.py)

### Phase 3: Migrate Existing Scripts
1. Keep old scripts as examples/deprecated
2. Add deprecation warnings pointing to new utilities
3. Update documentation

### Phase 4: Add Advanced Features
1. Create `batch_validation.py`
2. Add configuration file support (YAML/JSON)
3. Add result database/tracking

## Benefits

✓ **Reusability**: Write once, use for any scenario
✓ **Maintainability**: Single source of truth for test patterns
✓ **Flexibility**: Easy to add new test cases
✓ **Consistency**: Standardized output format and structure
✓ **Documentation**: CLI help serves as documentation
✓ **Automation**: Easy to integrate into CI/CD

## File Organization

```
py_script/
├── test/
│   └── test_optimizer_core.py          (pytest unit tests)
│
├── validation/
│   ├── __init__.py
│   ├── validation_utils.py             (shared utilities)
│   ├── run_optimization.py             (general runner)
│   ├── compare_optimizations.py        (general comparator)
│   ├── batch_validation.py             (batch runner)
│   │
│   └── examples/                       (example configs/scripts)
│       ├── example_36h_hu_winter.sh
│       ├── example_model_comparison.sh
│       └── validation_suite.yaml
│
└── test/deprecated/                    (move old scripts here)
    ├── run_36h_hu_winter.py           (keep for reference)
    └── test_single_32h_vs_mpc.py      (keep for reference)
```

## Example: validation_suite.yaml

```yaml
# Predefined validation scenarios
scenarios:
  quick_test:
    description: "Quick 12h test for all models"
    hours: 12
    countries: [DE_LU, HU]
    models: [I, II, III]

  full_validation:
    description: "Comprehensive validation"
    hours: 36
    countries: [DE_LU, AT, CH, HU, CZ]
    models: [I, II, III]
    alphas: [0.5, 1.0, 1.5]

  hu_winter_benchmark:
    description: "HU winter 36h benchmark"
    hours: 36
    countries: [HU]
    models: [III]
    start_step: 0
    alpha: 0.5
```
