
# Objective: 
Create a Jupyter Notebook to serve as a testing and validation harness for the BESS optimization framework. 

## Context
This notebook will majorly based on existing scripts from `./py_script/`, esp.:
 - `load_process_market_data.py` to load and preprocess market data. (Refer to `p2a_market_data.ipynb` for examples.), and
 - `optimizer.py` to understand the model implementation, and 
 - other scripts in `./py_script/test` to get useful testing modules
 - `visualize_market_data.py` for extract solutions from solved optimizer and visualize the results.

## Delivery: 
the updated Jupyter Notebook `p2b_optimizer.ipynb` in the `./notebook/` directory.

### Structure of the `p2b_optimizer.ipynb`

**Feature 1**: Flexible Model Testing Harness
1. Data Loading:
    - Develop and encapsulate a function to load and preprocess the market data (refer to the code in `p2a_market_data.ipynb`:
        ```python
        # Load all Phase 2 market tables (day_ahead, fcr, afrr_capacity, afrr_energy)
        p2_market_tables = load_phase2_market_tables(phase2_data_path)

        # Display what was loaded
        print("Loaded tables:")
        for table_name, table_df in p2_market_tables.items():
        print(f"  ✓ {table_name:20s}: {len(table_df):,} rows x {len(table_df.columns)} columns")
        ```
2. Flexible Scenario Execution:
    - Create a core testing function that can instantiate and run a single optimization pass. This function must be configurable to test:
        a. Different BESS optimization models: BESSOptimizerModelI, BESSOptimizerModelII, and BESSOptimizerModelIII.
        b. Time Horizon: Allow flexible selection of the data time length (e.g., use timestamps (date_range('2024-01-01')), "D1, D2, ..., D365" "Q1, Q2, Q3", "M1, M2, ..., M12", etc.).
        c. Parameters: The function must accept a dictionary of parameters to override the defaults in the models.            
          - Parameter Sweep Setup:
            ○ Build on the function from (1.2) to demonstrate testing of different parameter combinations.
            ○ The notebook should clearly show how to change the following parameters for a test run:
                § c_rate (e.g., 0.25, 0.33, 0.5).
                § alpha (the degradation cost meta-parameter for Model II and III).
                § use_afrr_ev_weighting (True/False).
                § solver_name (e.g., 'cplex', 'highs', 'cbc').
                § daily_cycle_limit (for Model I).
                § The path to aging_config.json (for Model II and III).

        d. develop module to load the configs files in `./data/aging_config/` for default parameters.)
Task 2: Result Retrieval and Validation Plotting
    1. Result Retrieval:
        ○ After a model is solved, extract the solution dictionary and key metrics (e.g., total profit, profit components, degradation costs) into a pandas DataFrame.
    2. Core Validation Plots (Crucial):
        ○ Implement plotting functions to visually validate the degradation models from BESSOptimizerModelIII.
        ○ Plot 2.1: Cyclic Aging (Xu et al. Model) Validation:
            § Objective: Verify the "stacked tank" logic of the 10 SOC segments.
            § Plot: Create a stacked area chart showing the energy in each segment (e_soc_j for $j=1..10$) over time.
            § Success Criteria: The plot must visually confirm that shallower segments (e.g., j=1) are emptied before deeper segments (e.g., j=2) begin to discharge.
        ○ Plot 2.2: Calendar Aging (Collath et al. Model) Validation:
            § Objective: Verify the SOS2 piecewise-linear cost function.
            § Plot: Create a 2D scatter plot where:
                □ X-axis: Total State of Charge (e_soc(t)) [kWh].
                □ Y-axis: Calculated Calendar Cost (c_cal_cost(t)) [EUR/hr].
            § Success Criteria: The resulting plot should clearly trace the 5-point convex curve defined by the breakpoints in aging_config.json (e.g., (0 kWh, 1.79 EUR/hr), (1118 kWh, 2.15 EUR/hr), etc.).
    3. (Optional) MPC/Meta-Optimizer Plots:
        ○ Show a simple example of how to run MPCSimulator and plot the resulting annual SOC trajectory (soc_15min).
Show a simple example of how to run MetaOptimizer and plot the resulting alpha vs. roi_10_year curve.