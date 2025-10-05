# Step 3 · Validation

## Objective
Confirm the correctness, robustness, and reproducibility of the optimization pipeline before final reporting and submission.

## Key Tasks
- Develop regression tests that replay representative country/configuration scenarios and compare outcomes against stored baselines.
- Stress-test edge cases: sustained high prices, negative pricing events, constrained ancillary services, and maximum daily cycle utilization.
- Cross-check annual profit summaries against independent spreadsheet or analytical calculations.
- Validate financial metrics in `investment_analysis.py`, including discount rate computation and 10-year NPV/ROI formulas.
- Inspect the generated CSVs for schema compliance (column names, units, ordering) and absence of missing values.

## Deliverables
- Automated test suite (e.g., `pytest`) with clear fixtures for data slices and expected KPIs.
- Validation report summarizing discrepancies found and resolved, plus open issues if any remain.
- Signed-off copies of the three submission CSVs stored in `SoloGen_TechArena2025_Phase1/output/`.

## Checks Before Moving On
- All tests pass on a clean environment using `requirements.txt`.
- Operation CSV contains physically plausible SoC trajectories (no negative energy, no exceeding capacity).
- ROI values in the investment output remain consistent when recomputed manually or via spreadsheet spot checks.
