# Alpha Meta-Optimization Script Guide

## Overview

`p2e_alpha_meta_optimization.py` is an interactive Python script for finding the optimal alpha parameter (degradation cost weight) for the BESS MPC optimizer through comprehensive Pareto analysis.

### Purpose
- Run parallel MPC simulations across multiple alpha values
- Analyze trade-offs between profit maximization and aging cost minimization
- Generate interactive visualizations (Pareto front, SOC sensitivity, revenue breakdown)
- Support both quick testing (14-day) and full production runs (365-day)

### Test Configuration (Fixed)
- **Country**: CZ
- **C-rate**: 0.5
- **Rolling horizon**: 36h planning / 24h execution
- **Alpha range**: [0.5, 1.5] with 0.1 step (11 values total)
- **REQUIRE_SEQUENTIAL**: False
- **EPSILON**: 0

---

## Quick Start

### 1. Initial Test Run (14-day)

Before running the full year simulation, always start with a 14-day test to verify everything works:

```python
# In the script, ensure TEST_MODE = True (default)
TEST_MODE = True  # 14-day quick test
```

Then run:
```bash
cd notebook/py_version
python p2e_alpha_meta_optimization.py
```

**Expected output**:
- Console progress bars showing parallel execution
- Completion summary with optimal alpha candidates
- Auto-generated plots in `validation_results/alpha_meta_CZ_0.5C_14d_YYYYMMDD_HHMMSS/plots/`

**Estimated runtime**: 30-60 minutes (depends on N_JOBS)

### 2. Full Production Run (365-day)

After verifying the test run works correctly:

```python
# In the script, change TEST_MODE to False
TEST_MODE = False  # Full year simulation
```

**Expected runtime**: 3-6 hours (depends on N_JOBS)

---

## Configuration

### Parallel Execution

Adjust the number of parallel workers based on your CPU cores:

```python
N_JOBS = 4  # Default: 4 parallel workers
```

**Recommendations**:
- **4-core CPU**: `N_JOBS = 2` (safe)
- **8-core CPU**: `N_JOBS = 4` (balanced)
- **16+ core CPU**: `N_JOBS = 8` (fast)

**Memory warning**: Each worker needs ~2-4 GB RAM. Monitor memory usage during test runs.

### Alpha Range

To test different alpha ranges (default: [0.5, 1.5] step 0.1):

```python
ALPHA_MIN = 0.5
ALPHA_MAX = 1.5
ALPHA_STEP = 0.1  # Results in [0.5, 0.6, 0.7, ..., 1.5]
```

### Financial Parameters

Adjust for ROI/NPV calculations:

```python
WACC = 0.08  # Weighted Average Cost of Capital (8%)
INFLATION_RATE = 0.02  # Annual inflation (2%)
PROJECT_LIFETIME_YEARS = 10  # Project economic lifetime
```

---

## Usage Modes

### Mode 1: Automatic Plot Generation (Default)

The script automatically generates all three plots after the sweep completes:

```python
# At the end of the script (default behavior)
if __name__ == "__main__":
    print("[AUTO] Generating all plots automatically...")
    plot_pareto_front(results_df, output_base_dir)
    plot_soc_vs_alpha(results_df, output_base_dir)
    best_alpha = results_df.loc[results_df['net_profit_eur'].idxmax(), 'alpha']
    plot_revenue_breakdown_for_alpha(best_alpha, output_base_dir)
```

**Plots generated**:
1. `pareto_front.html` - Aging Cost vs Profit with optimal points highlighted
2. `soc_vs_alpha.html` - SOC statistics (avg, min, max) vs alpha
3. `revenue_breakdown_alpha_X.X.html` - Pie charts for best profit alpha

### Mode 2: Interactive Control Panel

For more flexibility, enable the interactive menu:

```python
# At the end of the script, uncomment:
if __name__ == "__main__":
    interactive_control()  # Launch interactive menu
```

**Menu options**:
```
[1] Generate Pareto Front Plot
[2] Generate SOC vs Alpha Plot
[3] Generate Revenue Breakdown for Specific Alpha
[4] Generate All Plots
[5] Export Results Summary & Exit
[0] Exit Without Saving
```

**Use case**: When you want to explore specific alphas or generate plots on-demand.

### Mode 3: Jupyter Notebook / Cell-by-Cell Execution

The script uses `# %%` cell markers for VS Code / Jupyter:

1. Open in VS Code
2. Install Python extension
3. Run cells individually with `Shift+Enter`

**Workflow**:
- **Cells 1-2**: Setup and configuration
- **Cell 3**: Run alpha sweep (can take hours, checkpoint-enabled)
- **Cell 4**: Results aggregation (fast, can re-run after sweep)
- **Cells 5-6**: Plotting functions (interactive, re-runnable)

---

## Output Structure

After running, you'll find:

```
validation_results/alpha_meta_CZ_0.5C_14d_20251117_143022/
├── sweep_config.json                    # Snapshot of run configuration
├── comparison_results.csv               # Aggregated metrics for all alphas
├── RESULTS_SUMMARY.txt                  # Human-readable summary (if exported)
├── plots/                               # Interactive visualizations
│   ├── pareto_front.html
│   ├── soc_vs_alpha.html
│   └── revenue_breakdown_alpha_X.X.html
├── alpha_0.5/                           # Individual alpha results
│   ├── performance_summary.json
│   ├── iteration_summary.csv
│   └── solution_timeseries.csv
├── alpha_0.6/
├── ...
└── alpha_1.5/
```

### Key Files

**`comparison_results.csv`**: Main results table with columns:
- `alpha`: Alpha value tested
- `net_profit_eur`: Total profit (revenue - costs)
- `total_aging_cost_eur`: Cyclic + calendar aging costs
- `annual_profit_estimate`: Annualized profit (extrapolated if test mode)
- `npv_eur`: Net Present Value over project lifetime
- `soc_avg_kwh`, `soc_min_kwh`, `soc_max_kwh`: SOC statistics
- `runtime_seconds`: Simulation runtime

**`RESULTS_SUMMARY.txt`**: Summary report with:
- Configuration parameters
- Optimal alpha recommendations (by profit, NPV, ROI)
- Full results table

---

## Interpreting Results

### 1. Pareto Front Plot

**X-axis**: Annual Aging Cost (EUR)
**Y-axis**: Annual Profit (EUR)

**Interpretation**:
- **Points moving right**: Higher aging cost (more aggressive operation)
- **Points moving up**: Higher profit
- **Ideal**: Top-left corner (high profit, low aging)
- **Red star**: Best net profit alpha
- **Gold diamond**: Best NPV alpha

**Decision guide**:
- If red star ≈ gold diamond: Clear optimal alpha
- If far apart: Trade-off decision needed (profit now vs. long-term value)

### 2. SOC vs Alpha Plot

**X-axis**: Alpha (degradation weight)
**Y-axis**: State of Charge (kWh)

**Interpretation**:
- **Higher alpha → Lower average SOC**: System avoids high SOC (calendar aging sensitive)
- **Narrower range (min-max)**: More conservative cycling
- **Wider range**: More aggressive cycling for profit

**Validation check**: SOC should be between 0 and 4,472 kWh (battery capacity)

### 3. Revenue Breakdown Pie Charts

**Left pie**: Revenue sources (DA discharge, FCR, aFRR capacity/energy)
**Right pie**: Cost sources (DA charge, cyclic aging, calendar aging)

**Interpretation**:
- **Dominated by DA discharge revenue**: Energy arbitrage strategy
- **Large AS capacity revenue**: Providing ancillary services
- **Cyclic vs calendar aging**: Which degradation mode is more expensive?

---

## Troubleshooting

### Issue: Parallel execution fails with memory errors

**Solution**: Reduce `N_JOBS`:
```python
N_JOBS = 2  # Or even 1 for sequential execution
```

### Issue: Solver timeouts or infeasibilities

**Check**: `solver_status` column in `comparison_results.csv`

**Solution**: Increase solver timeout in `mpc_config.json`:
```json
"solver": {
  "time_limit_seconds": 300  // Increase from 120 to 300
}
```

### Issue: NaN values in results

**Likely cause**: Simulation failed for that alpha

**Solution**: Check individual alpha directory for error logs:
```bash
cat validation_results/alpha_meta_*/alpha_0.5/performance_summary.json
```

### Issue: Script crashes partway through sweep

**Good news**: Checkpoints are enabled!

**Solution**: Results are auto-saved per alpha. Check what completed:
```bash
ls -d validation_results/alpha_meta_*/alpha_*
```

You can manually aggregate completed results by loading CSVs from each alpha directory.

### Issue: Plots not generating

**Check 1**: Ensure `iteration_summary.csv` exists in alpha directories
**Check 2**: Verify `results_df` is not empty in SECTION 4

**Debug**:
```python
# At end of SECTION 4, check:
print(results_df.head())
print(results_df.columns)
```

---

## Advanced Usage

### Custom Alpha Values (Non-uniform)

If you want to test specific alphas instead of uniform range:

```python
# Replace SECTION 2 alpha generation with:
alpha_values = np.array([0.3, 0.5, 0.7, 1.0, 1.3, 1.5])
```

### Loading Previous Results Without Re-running

If you already ran the sweep and want to re-generate plots:

```python
# In SECTION 4, load saved results:
output_base_dir = Path("validation_results/alpha_meta_CZ_0.5C_365d_20251117_120000")
comparison_csv_path = output_base_dir / "comparison_results.csv"
results_df = pd.read_csv(comparison_csv_path)

# Then jump to SECTION 5 to generate plots
```

### Generating Plots for Multiple Alphas

```python
# Generate revenue breakdown for multiple alphas
for alpha in [0.5, 1.0, 1.5]:
    plot_revenue_breakdown_for_alpha(alpha, output_base_dir)
```

### Exporting to Excel for External Analysis

```python
# After SECTION 4
results_df.to_excel(output_base_dir / "comparison_results.xlsx", index=False)
```

---

## Script Sections Reference

| Section | Purpose | Runtime | Re-runnable? |
|---------|---------|---------|--------------|
| 1 | Setup & Imports | <1 sec | Yes |
| 2 | Configuration | <1 sec | Yes (modify params) |
| 3 | Parallel Alpha Sweep | Hours | No (expensive) |
| 4 | Results Aggregation | <5 sec | Yes |
| 5 | Plotting Functions | <10 sec | Yes |
| 6 | Interactive Control | N/A | Yes |

**Tip**: After running Section 3 once, you can modify and re-run Sections 4-6 without re-running the expensive sweep.

---

## Performance Benchmarks

**Test environment**: 8-core CPU, 16 GB RAM

| Configuration | N_JOBS | Runtime (14-day) | Runtime (365-day) |
|---------------|--------|------------------|-------------------|
| Sequential | 1 | ~2 hours | ~24 hours |
| Parallel 2x | 2 | ~60 min | ~12 hours |
| Parallel 4x | 4 | ~30 min | ~6 hours |
| Parallel 8x | 8 | ~20 min | ~3 hours |

**Your mileage may vary** based on:
- CPU speed and cores
- Available RAM
- Solver performance (Gurobi/CPLEX faster than CBC/GLPK)
- Data loading speed (SSD vs HDD)

---

## Best Practices

### Before Full Run
1. ✅ **Always test with 14-day mode first**
2. ✅ **Check one alpha completes successfully** (verify solver, data loading)
3. ✅ **Monitor memory usage** during test run
4. ✅ **Verify output directory has enough disk space** (~1 GB for full run)

### During Run
- Use `tqdm` progress bars to monitor completion
- Check interim results in individual alpha directories
- Monitor CPU/memory usage (Task Manager / `htop`)

### After Run
- Review `comparison_results.csv` for any anomalies (NaN, negative profits)
- Check `solver_status` column for failures
- Generate all plots before making conclusions
- Export `RESULTS_SUMMARY.txt` for documentation

---

## Integration with Other Scripts

### Chain with p2d_results_ana.py

After finding optimal alpha, run detailed analysis:

```bash
# 1. Find optimal alpha from meta-optimization
# (e.g., α=1.0 from pareto_front.html)

# 2. Run detailed results analysis for that alpha
python p2d_results_ana.py
# (Point to the alpha_1.0 directory from meta-optimization output)
```

### Use with p2c_mpc_interactive.py

Test individual alpha values in isolation:

```python
# In p2c_mpc_interactive.py, set:
alpha = 1.0  # Optimal from meta-optimization

# Then run single MPC simulation for validation
```

---

## FAQ

**Q: Can I run this on a laptop?**
A: Yes, but use `N_JOBS=2` and `TEST_MODE=True` (14-day). Full 365-day runs may take 12+ hours.

**Q: What if I want to test different countries?**
A: Change `COUNTRY = "CZ"` to any of: `"DE_LU"`, `"AT"`, `"CH"`, `"HU"`, `"CZ"`

**Q: Can I modify C-rate or other parameters?**
A: Yes, edit SECTION 2. For systematic testing, consider creating a nested loop over C-rates.

**Q: How do I know which alpha to use for final submission?**
A: Recommendation:
1. Look at Pareto front for trade-offs
2. If profit difference <5% between alphas, choose lower alpha (less aging)
3. If submission requires maximum profit, use red star (best profit alpha)
4. If long-term operation, use gold diamond (best NPV alpha)

**Q: Why are my results different from p2c_mpc_interactive.py?**
A: Possible reasons:
- Different data range (test vs full year)
- Different random seed (if stochastic elements)
- Different solver tolerances
- Data loading method (Excel vs preprocessed)

**Q: Can I pause and resume the sweep?**
A: Not directly, but checkpoints are saved per alpha. If interrupted, manually check which alphas completed and re-run missing ones.

---

## Changelog

**v1.0 (2024-11-17)**
- Initial release
- Parallel alpha sweep with joblib
- Three core visualizations (Pareto, SOC, Revenue)
- Interactive control panel
- Test mode (14-day) support

---

## Contact & Support

For issues, questions, or feature requests:
- Check this README first
- Review `CLAUDE.md` for project context
- Consult `doc/whole_project_description.md` for model details

---

**Happy optimizing! 🚀**
