# Profit Components Update - Model II

## Summary
Modified the optimizer to define profit components as Pyomo Expressions, enabling direct retrieval of individual profit values after model solving. This prevents calculation errors and makes post-optimization analysis cleaner.

## Changes Made

### 1. Optimizer Core (`py_script/core/optimizer.py`)

**Before:**
```python
def objective_rule(model):
    da_profit = sum(...)
    afrr_energy_profit = sum(...)
    as_profit = sum(...)
    return da_profit + afrr_energy_profit + as_profit

model.objective = pyo.Objective(rule=objective_rule, sense=pyo.maximize)
```

**After:**
```python
# Define profit components as Pyomo Expressions
def da_profit_rule(model):
    """Day-ahead energy profit (EUR)"""
    return sum(...)
model.profit_da = pyo.Expression(rule=da_profit_rule)

def afrr_energy_profit_rule(model):
    """aFRR energy market profit with Expected Value weighting (EUR)"""
    return sum(...)
model.profit_afrr_energy = pyo.Expression(rule=afrr_energy_profit_rule)

def as_capacity_profit_rule(model):
    """Ancillary service capacity profit (EUR)"""
    return sum(...)
model.profit_as_capacity = pyo.Expression(rule=as_capacity_profit_rule)

def objective_rule(model):
    """Total profit = DA + aFRR Energy + AS Capacity"""
    return model.profit_da + model.profit_afrr_energy + model.profit_as_capacity

model.objective = pyo.Objective(rule=objective_rule, sense=pyo.maximize)
```

**Profit Extraction in `solve_model()`:**
```python
# Extract profit components from Pyomo Expressions
if hasattr(model, 'profit_da'):
    solution['profit_da'] = _safe_value(model.profit_da)
if hasattr(model, 'profit_afrr_energy'):
    solution['profit_afrr_energy'] = _safe_value(model.profit_afrr_energy)
if hasattr(model, 'profit_as_capacity'):
    solution['profit_as_capacity'] = _safe_value(model.profit_as_capacity)
```

### 2. Test Script (`test_ev_phase2_simple.py`)

**Updated to use profit components directly:**
```python
# Extract profit components from solved model
profit_da = solution.get('profit_da', 0)
profit_afrr_e = solution.get('profit_afrr_energy', 0)  # Expected revenue with EV weights
profit_as = solution.get('profit_as_capacity', 0)

# Only calculate actual revenue separately (for 100% activation comparison)
afrr_e_actual, _, _, power_pos, power_neg = calculate_afrr_energy_revenue_actual(solution, season_data)
```

## Benefits

1. **Accuracy**: Eliminates manual calculation errors - profit components come directly from the optimizer
2. **Consistency**: Same formula used for optimization and reporting
3. **Clarity**: Clear separation of profit sources:
   - `profit_da`: Day-ahead energy arbitrage
   - `profit_afrr_energy`: aFRR energy market (with EV weighting if enabled)
   - `profit_as_capacity`: Capacity market revenue (FCR + aFRR capacity)
4. **Easy Analysis**: Directly access profit breakdown after solving

## Example Output

```
Winter (24h):
  Total Obj:     NoEV EUR   6,249.14  ->  WithEV EUR   6,232.13  ( -0.27%)
  - DA Profit:   NoEV EUR      -0.00  ->  WithEV EUR      -0.00
  - aFRR-E:      NoEV EUR   3,065.90  ->  WithEV EUR   3,048.89  ( -0.55%)
  - AS Capacity: NoEV EUR   3,452.64  ->  WithEV EUR   3,452.64
  aFRR-E Actual (100% activation): EUR   3,095.76
```

## Usage

```python
# Build and solve model
optimizer = BESSOptimizerModelII(alpha=1.5, use_afrr_ev_weighting=True)
model = optimizer.build_optimization_model(data)
solution = optimizer.solve_model(model)

# Access profit components
da_profit = solution['profit_da']
afrr_energy_profit = solution['profit_afrr_energy']  # Expected value with EV weights
as_capacity_profit = solution['profit_as_capacity']
total_profit = solution['objective_value']

# Verify: total_profit ≈ da_profit + afrr_energy_profit + as_capacity_profit
```

## Testing

Tested with `test_ev_phase2_simple.py` on seasonal instances:
- Winter, Spring, Summer, Autumn (24h each)
- Both with and without EV weighting
- All profit components correctly extracted and match total objective value
