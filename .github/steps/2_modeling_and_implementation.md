# Step 2 · Modeling and Implementation

## Objective
Build the modular codebase that simulates BESS operation, optimizes market participation, and orchestrates configuration sweeps in `Pyomo`, refering to document outlined in `doc/project_description.tex` and `doc\Pyomo_OptModelingInPython_3rdVersion.pdf`(Phases 1 and 2).

## Key Tasks
- Implement `io.py` utilities to load processed datasets, enforce 15-minute cadence, and provide typed DataFrame outputs.
- Create `bess_model.py` with a `BESS` class encapsulating capacity, power, efficiency, SoC, and cycle accounting.
- Prototype a baseline heuristic controller in `operation.py` to validate SoC dynamics before introducing optimization.
- Transition to a linear program (e.g., PuLP) that maximizes revenue subject to charge/discharge, SoC, and market allocation constraints.
- Encapsulate scenario execution in `scenarios.py` with `run_simulation(country_data, bess_config)` returning annual profits and metadata.
- Coordinate the process in `main.py`, iterating over countries and configuration combinations using only relative paths under `SoloGen_TechArena2025_Phase1`.

## Deliverables
- Functional modules (`io.py`, `bess_model.py`, `operation.py`, `scenarios.py`, `main.py`) with docstrings and type hints.
- Unit or integration tests covering SoC boundary conditions, energy conservation with efficiency losses, and LP feasibility.
- Interim CSV/Parquet outputs for at least one country-config combination demonstrating end-to-end flow.

## Checks Before Moving On
- Verify that the LP respects 4.5 MWh energy capacity, 2.25 MW power, 85% round-trip efficiency, and configured daily cycle caps.
- Ensure operation logs contain 35,136 rows with consistent timestamps.
- Confirm the code executes from repository root using `python SoloGen_TechArena2025_Phase1/main.py` (or documented entry point).
