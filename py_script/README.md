# BESS Optimization Model Implementation

This directory contains the implementation of the Battery Energy Storage System (BESS) optimization model for the Huawei TechArena 2025 challenge.

## Files

- `model.py` - Main optimization model implementation using Pyomo
- `test_model.py` - Test script with sample data
- `requirements.txt` - Python package dependencies

## Quick Start

### 1. Install Dependencies

```bash
# Install required Python packages
pip install -r requirements.txt
```

### 2. Install a Mixed-Integer Solver

The optimization model requires a solver capable of handling mixed-integer linear programming (MILP). Choose one:

**Option A: CBC (Open Source, Recommended)**
```bash
# Using conda
conda install -c conda-forge coincbc

# Or download from: https://www.coin-or.org/download/binary/Cbc/
```

**Option B: GLPK (Open Source)**
```bash
# Using conda  
conda install -c conda-forge glpk

# Or download from: https://www.gnu.org/software/glpk/
```

**Option C: Commercial Solvers (if available)**
- Gurobi: https://www.gurobi.com/
- CPLEX: https://www.ibm.com/products/ilog-cplex-optimization-studio

### 3. Test the Implementation

```bash
# Run the test with sample data
python test_model.py

# Or test directly in Python
python -c "from model import BESSOptimizer; print('Model loaded successfully!')"
```

### 4. Run Full Optimization

```bash
# Run optimization for all scenarios
python model.py
```

## Model Overview

The optimization model implements:

### Objective Function
- Maximize total profit from day-ahead energy arbitrage and ancillary service capacity payments
- Accounts for charging costs and operational constraints

### Key Constraints
1. **State of Charge (SOC) Dynamics** - Energy balance with charging/discharging efficiency
2. **SOC Limits** - Stay within 10-90% operational range
3. **Power Limits** - Respect C-rate configuration limits
4. **Market Co-optimization** - Allocate power between energy and reserves
5. **Daily Cycle Limits** - Limit total daily discharged energy
6. **Energy Reserves** - Maintain sufficient energy for ancillary service delivery
7. **Minimum Bid Sizes** - Respect market minimum bid requirements

### Configuration Scenarios
- **Countries**: DE, AT, CH, HU, CZ (5 options)
- **C-rates**: 0.25, 0.33, 0.5 (3 options)  
- **Daily Cycles**: 1.0, 1.5, 2.0 (3 options)
- **Total**: 45 optimization scenarios

### Technical Parameters
- Nominal Capacity: 4,472 kWh
- Charging/Discharging Efficiency: 95%
- Time Resolution: 15 minutes (day-ahead), 4 hours (ancillary services)
- Optimization Horizon: Full year 2024

## Data Format

The model expects data in JSONL format with the following structure:

```json
{"timestamp": "2024-01-01 00:00:00", "country": "DE", "price_eur_mwh": 50.0, "source": "day_ahead"}
{"timestamp": "2024-01-01 00:00:00", "country": "DE", "price_eur_mwh": 80.0, "source": "fcr"}
{"timestamp": "2024-01-01 00:00:00", "country": "DE", "price_eur_mwh": 15.0, "source": "afrr", "direction": "positive"}
{"timestamp": "2024-01-01 00:00:00", "country": "DE", "price_eur_mwh": 10.0, "source": "afrr", "direction": "negative"}
```

## Output

The optimization produces:
- Optimal charging/discharging schedules
- Ancillary service capacity bids
- Annual profit calculations
- Performance summary statistics

Results are saved in JSON format for further analysis and Excel export.

## Troubleshooting

### Common Issues

1. **"Solver not available"**
   - Install a solver (see step 2 above)
   - Ensure solver executable is in system PATH

2. **"Memory Error" or slow performance**
   - The full year optimization is computationally intensive
   - Consider using commercial solvers (Gurobi/CPLEX) for better performance
   - Set solver time limits in the model

3. **"Data loading errors"**
   - Verify data file format matches expected JSONL structure
   - Check that all required data sources are present

### Performance Tips

- Use CBC with time limits for reasonable solve times
- Consider running scenarios in parallel if computational resources allow
- Monitor memory usage for full-year optimizations

## Model Validation

The test script (`test_model.py`) validates:
1. Data loading and preprocessing
2. Model construction 
3. Basic solver functionality

Run tests before attempting full optimization to catch configuration issues early.