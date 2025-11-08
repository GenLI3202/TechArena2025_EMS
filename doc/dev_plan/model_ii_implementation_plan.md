# Model (ii) Implementation Plan: Cyclic Aging Cost Integration

**Project:** Huawei TechArena 2025 - BESS Energy Management System
**Phase:** Phase II - Battery Degradation Modeling
**Model:** Model (ii) - Base + aFRR Energy + Cyclic Aging Cost
**Author:** Gen Li (Team SoloGen)
**Date:** 2025-01-08
**Status:** Implementation Plan (Ready for Development)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Technical Background](#2-technical-background)
3. [Implementation Architecture](#3-implementation-architecture)
4. [Step-by-Step Implementation Guide](#4-step-by-step-implementation-guide)
5. [Detailed Code Specifications](#5-detailed-code-specifications)
6. [Configuration File Integration](#6-configuration-file-integration)
7. [Testing Strategy](#7-testing-strategy)
8. [API Compatibility](#8-api-compatibility)
9. [Expected Results & Validation](#9-expected-results--validation)
10. [Future Extensions](#10-future-extensions)
11. [References](#11-references)
12. [Appendix](#12-appendix)

---

## 1. Executive Summary

### 1.1 Overview

Model (ii) extends Model (i) by replacing the rigid **daily cycle limit constraint** (Cst-5) with a flexible, **economically-aware cyclic degradation cost function**. This allows the optimizer to dynamically trade off revenue against battery lifetime, resulting in higher profitability while maintaining battery health.

### 1.2 Key Changes from Model (i)

| Aspect | Model (i) | Model (ii) |
|--------|-----------|------------|
| **Degradation Handling** | Hard constraint (≤ N cycles/day) | Flexible cost function in objective |
| **SOC Tracking** | Single aggregate SOC variable | 10 segment-based SOC variables |
| **Discharge Cost** | Zero (free) | Depth-dependent (€0.0052-€0.0990/kWh) |
| **Decision Variables** | ~70,000 continuous + 35,000 binary | ~770,000 continuous + 35,000 binary |
| **Optimization Goal** | Max revenue only | Max (revenue - α × degradation cost) |

### 1.3 Mathematical Foundation

Based on **Xu et al. (2017)** and the formulation in `doc/p2_model/p2_bi_model_ggdp.tex`, cyclic aging is modeled as a **convex piecewise-linear cost** function:

$$C^{\mathrm{cyc}} = \sum_{t \in T} \sum_{j \in J} \left( c^{\mathrm{cost}}_{j} \cdot \frac{p^{\mathrm{dis}}_{j}(t)}{\eta_{\mathrm{dis}}} \cdot \Delta t \right)$$

Where:
- $J = \{1, 2, ..., 10\}$: SOC segments (10% each, from 90-100% down to 0-10%)
- $c^{\mathrm{cost}}_{j}$: Marginal cost of discharging 1 kWh from segment $j$ (EUR/kWh)
- $p^{\mathrm{dis}}_{j}(t)$: Discharge power from segment $j$ at time $t$ (kW)
- Higher segment number → deeper discharge → higher marginal cost

**Key Insight:** The optimizer naturally discharges from shallower segments first (lower cost) before deeper segments (higher cost), perfectly modeling the non-linear degradation physics in a linear framework.

### 1.4 Implementation Strategy

Follow the **Subclass Inheritance Pattern**:

```python
class BESSOptimizerModelII(BESSOptimizerModelI):
    """
    Model (ii): Model (i) + Cyclic Aging Cost

    Extends the base Model (i) with segment-based SOC tracking and
    cyclic degradation cost modeling as per Xu et al. (2017).
    """
```

**Design Principles:**
1. **Preserve Model (i):** No modifications to existing `BESSOptimizerModelI` class
2. **Override Minimally:** Only `__init__` and `build_optimization_model` methods
3. **Reuse Infrastructure:** Keep all data loading, solving, and output methods
4. **Maintain Compatibility:** Provide backward-compatible aliases

### 1.5 Expected Outcomes

- **Higher Profitability:** 5-15% increase in 10-year NPV compared to rigid cycle limits
- **Better Battery Health:** Dynamic cost function prevents excessively deep cycling
- **Pareto Frontier:** Ability to tune `α` meta-parameter to explore profit vs. degradation trade-offs
- **Validation Metric:** Model (ii) should yield similar or better results than Model (i) when `α` is calibrated correctly

---

## 2. Technical Background

### 2.1 Current Model (i) Architecture

**File:** `py_script/core/optimizer.py`
**Class:** `BESSOptimizerModelI` (lines 49-1010)
**Status:** Fully implemented and validated

**Key Components:**

1. **Decision Variables (per 15-min interval $t$):**
   - Energy market: `p_ch[t]`, `p_dis[t]` (DA), `p_afrr_pos_e[t]`, `p_afrr_neg_e[t]` (aFRR-E)
   - Capacity market: `c_fcr[b]`, `c_afrr_pos[b]`, `c_afrr_neg[b]` (per 4-hour block $b$)
   - State tracking: `e_soc[t]` (single aggregate SOC)
   - Totals: `p_total_ch[t]`, `p_total_dis[t]` (DA + aFRR-E combined)

2. **Constraints (9 groups):**
   - Cst-1: SOC Dynamics (single equation)
   - Cst-2: SOC Limits (0-100%)
   - Cst-3: Simultaneous Operation Prevention
   - Cst-4: Market Co-optimization Power Limits
   - **Cst-5: Daily Cycle Limits** ← **TO BE REPLACED**
   - Cst-6: Ancillary Service Energy Reserve
   - Cst-7: AS Market Mutual Exclusivity
   - Cst-8: Cross-Market Mutual Exclusivity
   - Cst-9: Minimum/Maximum Bid Sizes

3. **Objective Function:**
   ```python
   maximize: P_DA + P_aFRR_E + P_ANCI
   ```
   Where:
   - $P^{DA}$: Day-ahead energy profit
   - $P^{aFRR\\_E}$: aFRR energy profit (Model i)
   - $P^{ANCI}$: Ancillary service capacity profit

### 2.2 Cyclic Aging Theory

**Literature Basis:**
- **Xu et al. (2017):** "Factoring the Cycle Aging Cost of Batteries Participating in Electricity Markets" (arXiv:1707.04567v2)
- **Power-Law Model:** $\text{CycleLife}(D) = a \cdot D^{-b}$

**Parameters (from `p2_bi_model_ggdp.tex`):**
- LFP battery: 6,000 cycles at 80% DoD (manufacturer spec)
- Derived parameter $a$: 3,840 cycles at 100% DoD (from $a = 6000 \times 0.8^{-2}$)
- Behavioral exponent $b$: 2 (strongly penalizes deep discharges)
- Total BESS investment: €894,400 (4,472 kWh × €200/kWh)
- Cost per full cycle: €232.92 (€894,400 ÷ 3,840 cycles)

**Segmentation Approach:**
- Divide 4,472 kWh capacity into **10 equal segments** of 447.2 kWh each
- Each segment represents 10% SOC range (e.g., Segment 1 = 90-100%, Segment 10 = 0-10%)
- Marginal cost increases with depth: $c^{\mathrm{cost}}_{1} < c^{\mathrm{cost}}_{2} < ... < c^{\mathrm{cost}}_{10}$

**Physical Interpretation:**
- Discharging from 100% → 90% is "cheap" (shallow cycling, long life)
- Discharging from 10% → 0% is "expensive" (deep cycling, short life)
- The optimizer will naturally prefer shallow cycles unless high revenue justifies deep cycles

### 2.3 Degradation Parameters

**Source File:** `data/phase2_aging_config/aging_config.json`

```json
{
  "cyclic_aging": {
    "description": "Marginal cost of discharging 1 kWh from different SOC segments",
    "unit": "EUR/kWh",
    "costs": [
      0.0052,  // Segment 1: 90-100% SOC (shallowest, cheapest)
      0.0156,  // Segment 2: 80-90%
      0.0260,  // Segment 3: 70-80%
      0.0364,  // Segment 4: 60-70%
      0.0469,  // Segment 5: 50-60%
      0.0573,  // Segment 6: 40-50%
      0.0677,  // Segment 7: 30-40%
      0.0781,  // Segment 8: 20-30%
      0.0885,  // Segment 9: 10-20%
      0.0990   // Segment 10: 0-10% (deepest, most expensive)
    ]
  }
}
```

**Validation Check:**
- Sum of costs × segment size should equal cost per full cycle:
  $$\sum_{j=1}^{10} c^{\mathrm{cost}}_{j} \times E^{\mathrm{seg}} = \text{Cost per Full Cycle}$$
  $$(0.0052 + 0.0156 + ... + 0.0990) \times 447.2 \approx 232.92 \text{ EUR}$$ 
  ✓

### 2.4 Mathematical Formulation (Model ii)

**From:** `doc/p2_model/p2_bi_model_ggdp.tex` (Section: Phase II - Model (ii))

**New Objective Function:**
$$\max \; Z = \mathbb{P}^{DA} + \mathbb{P}^{ANCI} + \mathbb{P}^{aFRR\\_E} - \alpha \cdot C^{\mathrm{cyc}}$$

**New Decision Variables:**
- $p^{\mathrm{ch}}_{j}(t)$: Charge power to segment $j$ at time $t$ (kW), $\forall t \in T, j \in J$
- $p^{\mathrm{dis}}_{j}(t)$: Discharge power from segment $j$ at time $t$ (kW), $\forall t \in T, j \in J$
- $e_{\mathrm{soc},j}(t)$: Energy stored in segment $j$ at time $t$ (kWh), $\forall t \in T, j \in J$

**Modified SOC Dynamics (replaces Cst-1):**
$$e_{\mathrm{soc},j}(t) = e_{\mathrm{soc},j}(t-1) + \left( p^{\mathrm{ch}}_{j}(t) \eta_{\mathrm{ch}} - \frac{p^{\mathrm{dis}}_{j}(t)}{\eta_{\mathrm{dis}}} \right) \Delta t \quad \forall t, \forall j$$

**Aggregation Constraints:**
$$e_{\mathrm{soc}}(t) = \sum_{j \in J} e_{\mathrm{soc},j}(t) \quad \forall t$$
$$p^{\mathrm{total}}_{\\mathrm{ch}}(t) = \sum_{j \in J} p^{\mathrm{ch}}_{j}(t) \quad \forall t$$
$$p^{\mathrm{total}}_{\\mathrm{dis}}(t) = \sum_{j \in J} p^{\mathrm{dis}}_{j}(t) \quad \forall t$$

**Segment Capacity Limits (new):**
$$0 \le e_{\mathrm{soc},j}(t) \le E^{\mathrm{seg}}_{j} \quad \forall t, \forall j$$

**Removal:**
- **DELETE Cst-5** (Daily Cycle Limits) - Replaced by cost-based approach

---

## 3. Implementation Architecture

### 3.1 Class Hierarchy

```
BESSOptimizerModelI (existing, lines 49-1010)
    │
    ├── __init__(country_data, config)
    ├── load_and_preprocess_data(jsonl_path, afrr_energy_path)
    ├── extract_country_data(preprocessed_df, country)
    ├── build_optimization_model(country_data, c_rate, daily_cycle_limit) ← OVERRIDE
    ├── solve_model(model, solver_name)
    ├── optimize(country_data, c_rate, daily_cycle_limit)
    └── [helper methods]

    ↓ INHERITANCE

BESSOptimizerModelII (new, to be added after line 1010)
    │
    ├── __init__(country_data, config, degradation_config_path) ← OVERRIDE
    ├── build_optimization_model(country_data, c_rate, daily_cycle_limit) ← OVERRIDE
    ├── _load_degradation_config(config_path) ← NEW
    ├── _validate_degradation_params() ← NEW
    └── [inherits all other methods from parent]
```

### 3.2 File Structure

**Modified Files:**
1. `py_script/core/optimizer.py`
   - Add `BESSOptimizerModelII` class after line 1010
   - Add new aliases after existing aliases (line 1089)
   - **No changes to existing Model (i) code**

**New/Referenced Files:**
2. `data/phase2_aging_config/aging_config.json` (existing, read-only)
3. `tests/test_model_ii.py` (new, to be created)
4. `doc/dev_plan/model_ii_implementation_plan.md` (this document)

### 3.3 Method Override Strategy

| Method | Action | Rationale |
|--------|--------|-----------|
| `__init__` | **Override** | Must load degradation config and add new params |
| `build_optimization_model` | **Override** | Must add segment variables and modify constraints |
| `solve_model` | **Reuse** (call `super()`) | Extraction logic can be extended via parent method |
| `load_and_preprocess_data` | **Inherit** | Data format unchanged |
| `extract_country_data` | **Inherit** | Country extraction logic unchanged |
| `optimize` | **Inherit** | High-level workflow unchanged |

### 3.4 Backward Compatibility

**Aliases (add after line 1089):**
```python
# Model (ii) Aliases
BESSOptimizer_Phase2_ModelII = BESSOptimizerModelII
BESSOptimizerV3 = BESSOptimizerModelII  # Version alias
```

**Migration Path:**
```python
# Old code (Model i)
optimizer = BESSOptimizerModelI(country_data, config)

# New code (Model ii) - minimal change
optimizer = BESSOptimizerModelII(
    country_data,
    config,
    degradation_config_path='data/phase2_aging_config/aging_config.json'
)
```

---

## 4. Step-by-Step Implementation Guide

### Step 1: Create Model II Class Structure

**File:** `py_script/core/optimizer.py`
**Location:** After line 1010 (end of `BESSOptimizerModelI` class)

**Task 1.1:** Add class definition and docstring

```python
class BESSOptimizerModelII(BESSOptimizerModelI):
    """
    Model (ii): BESS Optimizer with Cyclic Aging Cost

    Extends Model (i) by replacing the rigid daily cycle limit (Cst-5) with
    a flexible, economically-aware cyclic degradation cost function. This model
    uses segment-based SOC tracking to implement the piecewise-linear aging cost
    model from Xu et al. (2017).

    Key Enhancements:
    - 10 SOC segments for depth-dependent degradation modeling
    - Marginal cost function: €0.0052/kWh (shallow) to €0.0990/kWh (deep)
    - Meta-parameter α for tuning profit vs. degradation trade-off
    - Removes hard daily cycle constraint (Cst-5)

    Mathematical Formulation:
        Objective = P_DA + P_aFRR_E + P_ANCI - α × C_cyclic

        where C_cyclic = Σ_t Σ_j (c_cost_j × p_dis_j[t] / η_dis × Δt)

    References:
        - doc/p2_model/p2_bi_model_ggdp.tex (Model ii formulation)
        - Xu et al. (2017): "Factoring the Cycle Aging Cost of Batteries..."

    Args:
        country_data (pd.DataFrame): Same as Model (i)
        config (dict): Same as Model (i)
        degradation_config_path (str): Path to aging_config.json
        alpha (float): Degradation cost weight meta-parameter (default: 1.0)

    Example:
        >>> optimizer = BESSOptimizerModelII(
        ...     country_data=data,
        ...     config={'c_rate': 0.5, 'daily_cycle_limit': None},  # cycle limit ignored
        ...     degradation_config_path='data/phase2_aging_config/aging_config.json',
        ...     alpha=1.0
        ... )
        >>> results = optimizer.optimize(data, c_rate=0.5, daily_cycle_limit=1.5)
        >>> print(results['degradation_metrics'])
    """
```

### Step 2: Override `__init__` Method

**Task 2.1:** Define the constructor

```python
def __init__(self, country_data: pd.DataFrame = None, config: Dict = None,
             degradation_config_path: str = None, alpha: float = 1.0):
    """
    Initialize Model (ii) optimizer with cyclic aging cost parameters.

    Args:
        country_data: Market price data (same as Model i)
        config: Battery and market configuration (same as Model i)
        degradation_config_path: Path to aging_config.json file
        alpha: Degradation cost weight (0 = ignore aging, >0 = penalize aging)

    Raises:
        FileNotFoundError: If degradation config file not found
        ValueError: If aging parameters are invalid
    """
    # Step 2.1.1: Call parent constructor
    super().__init__(country_data, config)

    # Step 2.1.2: Set default config path if not provided
    if degradation_config_path is None:
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        degradation_config_path = project_root / 'data' / 'phase2_aging_config' / 'aging_config.json'

    # Step 2.1.3: Load degradation configuration
    self.degradation_config = self._load_degradation_config(degradation_config_path)

    # Step 2.1.4: Initialize degradation parameters dictionary
    cyclic_config = self.degradation_config['cyclic_aging']

    self.degradation_params = {
        'enabled': True,
        'model_type': 'cyclic_only',  # 'cyclic_only', 'calendar_only', 'full' (for future)
        'num_segments': len(cyclic_config['costs']),  # Should be 10
        'segment_capacity_kwh': self.battery_params['capacity_kwh'] / len(cyclic_config['costs']),
        'marginal_costs': cyclic_config['costs'],  # List of 10 costs (EUR/kWh)
        'alpha': alpha,  # Meta-parameter for degradation weight
        'config_file_path': str(degradation_config_path)
    }

    # Step 2.1.5: Validate parameters
    self._validate_degradation_params()

    # Step 2.1.6: Log initialization
    logger.info(f"Initialized BESSOptimizerModelII with:")
    logger.info(f"  - Segments: {self.degradation_params['num_segments']}")
    logger.info(f"  - Segment capacity: {self.degradation_params['segment_capacity_kwh']:.2f} kWh")
    logger.info(f"  - Alpha: {self.degradation_params['alpha']}")
    logger.info(f"  - Cost range: €{min(self.degradation_params['marginal_costs']):.4f} - "
                f"€{max(self.degradation_params['marginal_costs']):.4f} per kWh")
```

**Task 2.2:** Implement helper method `_load_degradation_config`

```python
def _load_degradation_config(self, config_path: str) -> Dict:
    """
    Load and parse the degradation configuration JSON file.

    Args:
        config_path: Path to aging_config.json

    Returns:
        Dictionary with cyclic_aging and calendar_aging parameters

    Raises:
        FileNotFoundError: If config file doesn't exist
        JSONDecodeError: If file is not valid JSON
        KeyError: If required keys are missing
    """
    import json
    from pathlib import Path

    config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(
            f"Degradation config file not found: {config_path}\n"
            f"Expected location: data/phase2_aging_config/aging_config.json"
        )

    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in degradation config file: {e}")

    # Validate required keys
    if 'cyclic_aging' not in config:
        raise KeyError("Missing 'cyclic_aging' key in degradation config")

    if 'costs' not in config['cyclic_aging']:
        raise KeyError("Missing 'costs' array in cyclic_aging config")

    logger.info(f"Loaded degradation config from: {config_path}")

    return config
```

**Task 2.3:** Implement validation method

```python
def _validate_degradation_params(self):
    """
    Validate degradation parameters for consistency and physical correctness.

    Checks:
        1. Number of segments is positive
        2. Marginal costs are strictly increasing (deeper = more expensive)
        3. All costs are non-negative
        4. Segment capacity equals total capacity / num_segments
        5. Alpha is non-negative

    Raises:
        ValueError: If any validation check fails
    """
    num_seg = self.degradation_params['num_segments']
    costs = self.degradation_params['marginal_costs']
    seg_cap = self.degradation_params['segment_capacity_kwh']
    total_cap = self.battery_params['capacity_kwh']
    alpha = self.degradation_params['alpha']

    # Check 1: Positive number of segments
    if num_seg <= 0:
        raise ValueError(f"Number of segments must be positive, got {num_seg}")

    # Check 2: Correct number of cost values
    if len(costs) != num_seg:
        raise ValueError(
            f"Marginal costs array length ({len(costs)}) must equal "
            f"number of segments ({num_seg})"
        )

    # Check 3: Costs are strictly increasing (convex cost function)
    for j in range(1, num_seg):
        if costs[j] <= costs[j-1]:
            logger.warning(
                f"Marginal costs should be strictly increasing for convex aging model. "
                f"Cost[{j}] = {costs[j]:.4f} is not greater than Cost[{j-1}] = {costs[j-1]:.4f}"
            )

    # Check 4: All costs are non-negative
    if any(c < 0 for c in costs):
        raise ValueError(f"All marginal costs must be non-negative, got {costs}")

    # Check 5: Segment capacity is consistent
    expected_seg_cap = total_cap / num_seg
    if abs(seg_cap - expected_seg_cap) > 0.01:  # 0.01 kWh tolerance
        raise ValueError(
            f"Segment capacity mismatch: {seg_cap:.2f} kWh != "
            f"{expected_seg_cap:.2f} kWh (total: {total_cap} / {num_seg})"
        )

    # Check 6: Alpha is non-negative
    if alpha < 0:
        raise ValueError(f"Alpha must be non-negative, got {alpha}")

    logger.info("Degradation parameters validated successfully")
```

### Step 3: Override `build_optimization_model` Method

**Task 3.1:** Define the override method signature

```python
def build_optimization_model(self, country_data: pd.DataFrame,
                              c_rate: float, daily_cycle_limit: float = None) -> pyo.ConcreteModel:
    """
    Build Pyomo optimization model with cyclic aging costs (Model ii).

    This method extends the parent Model (i) by:
    1. Adding SOC segment set J
    2. Replacing single SOC variable with per-segment tracking
    3. Adding segment-based charge/discharge variables
    4. Modifying SOC dynamics to per-segment equations
    5. Adding cyclic degradation cost to objective function
    6. IGNORING daily_cycle_limit parameter (replaced by cost function)

    Args:
        country_data: Market price DataFrame (same as Model i)
        c_rate: C-rate configuration (0.25, 0.33, or 0.5)
        daily_cycle_limit: IGNORED in Model (ii) - kept for API compatibility

    Returns:
        Pyomo ConcreteModel with segment-based degradation modeling

    Note:
        The daily_cycle_limit parameter is ignored because Model (ii) uses
        a flexible cost-based approach instead of a hard constraint.
    """
    # Task 3.1.1: Log warning if daily_cycle_limit is provided
    if daily_cycle_limit is not None:
        logger.warning(
            f"Model (ii) ignores daily_cycle_limit parameter ({daily_cycle_limit}). "
            f"Using cost-based degradation model instead."
        )

    # Task 3.1.2: Build base Model (i) - this gives us all the standard constraints
    # We pass daily_cycle_limit=None to bypass Cst-5 in parent
    model = super().build_optimization_model(country_data, c_rate, daily_cycle_limit=None)

    # Task 3.1.3: Now extend with cyclic aging components
    # From this point, we add new components to the existing model object

    # [Continue in Task 3.2...]
```

**Task 3.2:** Add segment set and parameters

```python
    # --- EXTENSION: Add Cyclic Aging Components ---

    # Task 3.2.1: Extract parameters for convenience
    num_segments = self.degradation_params['num_segments']
    segment_capacity = self.degradation_params['segment_capacity_kwh']
    marginal_costs = self.degradation_params['marginal_costs']
    alpha = self.degradation_params['alpha']

    # Task 3.2.2: Add segment index set
    model.J = pyo.Set(initialize=range(1, num_segments + 1),
                      doc="SOC segments (1=shallowest/90-100%, 10=deepest/0-10%)")

    # Task 3.2.3: Add segment parameters
    model.E_seg = pyo.Param(
        model.J,
        initialize={j: segment_capacity for j in model.J},
        doc="Energy capacity of each segment (kWh)"
    )

    model.c_cost = pyo.Param(
        model.J,
        initialize={j: marginal_costs[j-1] for j in model.J},  # j=1 → costs[0]
        doc="Marginal cyclic degradation cost per kWh discharged from segment j (EUR/kWh)"
    )

    model.alpha = pyo.Param(
        initialize=alpha,
        doc="Degradation cost weight meta-parameter"
    )

    logger.info(f"Added {len(model.J)} SOC segments with costs: {marginal_costs}")
```

**Task 3.3:** Add segment-based decision variables

```python
    # Task 3.3.1: Add per-segment charge power variables
    model.p_ch_j = pyo.Var(
        model.T, model.J,
        domain=pyo.NonNegativeReals,
        bounds=(0, model.P_max_config),  # Each segment limited by total power
        doc="Charge power to segment j at time t (kW)"
    )

    # Task 3.3.2: Add per-segment discharge power variables
    model.p_dis_j = pyo.Var(
        model.T, model.J,
        domain=pyo.NonNegativeReals,
        bounds=(0, model.P_max_config),
        doc="Discharge power from segment j at time t (kW)"
    )

    # Task 3.3.3: Add per-segment SOC variables
    model.e_soc_j = pyo.Var(
        model.T, model.J,
        domain=pyo.NonNegativeReals,
        bounds=lambda m, t, j: (0, m.E_seg[j]),
        doc="Energy stored in segment j at end of time t (kWh)"
    )

    logger.info(f"Added segment variables: {len(model.T) * len(model.J) * 3:,} new variables")
```

**Task 3.4:** Replace aggregate SOC and add aggregation expressions

```python
    # Task 3.4.0: Remove parent SOC dynamics to avoid double definitions
    if hasattr(model, 'soc_dynamics'):
        model.del_component(model.soc_dynamics)
        if hasattr(model, 'soc_dynamics_index'):
            model.del_component(model.soc_dynamics_index)
        logger.info("Removed parent SOC dynamics constraint (Cst-1) before adding segment-based dynamics")

    # Task 3.4.1: Replace aggregate SOC variable with expression derived from segments
    if hasattr(model, 'e_soc'):
        model.del_component(model.e_soc)
    model.e_soc = pyo.Expression(
        model.T,
        rule=lambda m, t: sum(m.e_soc_j[t, j] for j in m.J),
        doc="Total SOC computed directly from segment SOCs"
    )

    # Task 3.4.2: Define aggregation constraint for total charge power
    def total_charge_power_rule(m, t):
        """Sum of segment charge powers equals total charge power."""
        return m.p_total_ch[t] == sum(m.p_ch_j[t, j] for j in m.J)

    model.total_charge_aggregation = pyo.Constraint(
        model.T,
        rule=total_charge_power_rule,
        doc="Total charge power aggregation from all segments"
    )

    # Task 3.4.3: Define aggregation constraint for total discharge power
    def total_discharge_power_rule(m, t):
        """Sum of segment discharge powers equals total discharge power."""
        return m.p_total_dis[t] == sum(m.p_dis_j[t, j] for j in m.J)

    model.total_discharge_aggregation = pyo.Constraint(
        model.T,
        rule=total_discharge_power_rule,
        doc="Total discharge power aggregation from all segments"
    )

    logger.info("Aggregation complete: charge/discharge constraints added, total SOC now derived from segments")
```

**Task 3.5:** Add per-segment SOC dynamics and stacked-tank ordering

```python
    # Helper: deterministic top-down initial SOC allocation (LIFO-friendly)
    def initial_segment_soc(m, j):
        """
        Fill segments from the top (j=1) downward until the initial SOC is exhausted.
        Guarantees feasibility and matches the stacked-tank physical model.
        """
        capacity_per_segment = m.E_seg[j]
        higher_capacity = sum(m.E_seg[k] for k in m.J if k < j)
        remaining = max(0.0, m.E_soc_init - higher_capacity)
        return min(capacity_per_segment, remaining)

    # Task 3.5.1: Define segment SOC dynamics constraint with LIFO-consistent initial state
    def segment_soc_dynamics_rule(m, t, j):
        if t == m.T.first():
            initial_soc_j = initial_segment_soc(m, j)
            return (m.e_soc_j[t, j] ==
                    initial_soc_j +
                    (m.p_ch_j[t, j] * m.eta_ch - m.p_dis_j[t, j] / m.eta_dis) * m.dt)
        return (m.e_soc_j[t, j] ==
                m.e_soc_j[m.T.prev(t), j] +
                (m.p_ch_j[t, j] * m.eta_ch - m.p_dis_j[t, j] / m.eta_dis) * m.dt)

    model.segment_soc_dynamics = pyo.Constraint(
        model.T, model.J,
        rule=segment_soc_dynamics_rule,
        doc="Segment SOC dynamics with deterministic top-down initialization"
    )

    # Task 3.5.2: Enforce stacked-tank ordering so deeper segments never hold more energy
    def stacked_tank_rule(m, t, j):
        if j == max(m.J):
            return pyo.Constraint.Skip
        return m.e_soc_j[t, j] >= m.e_soc_j[t, j + 1]

    model.stacked_tank_ordering = pyo.Constraint(
        model.T, model.J,
        rule=stacked_tank_rule,
        doc="Monotonic SOC ordering across segments (LIFO enforcement)"
    )

    # Task 3.5.3: Optional binary gating to prevent bypassing shallow segments
    model.z_segment_active = pyo.Var(
        model.T, model.J, domain=pyo.Binary,
        doc="Binary indicator: 1 if segment j is active (charge/discharge allowed)"
    )

    def segment_activation_upper_rule(m, t, j):
        return m.e_soc_j[t, j] <= m.E_seg[j] * m.z_segment_active[t, j]

    model.segment_activation_upper = pyo.Constraint(model.T, model.J, rule=segment_activation_upper_rule)

    def segment_activation_cascade_rule(m, t, j):
        if j == 1:
            return pyo.Constraint.Skip
        return m.z_segment_active[t, j] <= m.z_segment_active[t, j - 1]

    model.segment_activation_cascade = pyo.Constraint(
        model.T, model.J,
        rule=segment_activation_cascade_rule,
        doc="Activation binaries ensure deeper segments only operate when shallower ones are active"
    )

    # Optional: bind segment charge/discharge to activation binary to avoid phantom flows
    if self.degradation_params.get('enforce_segment_binary', True):
        def segment_charge_activation_rule(m, t, j):
            return m.p_ch_j[t, j] <= m.P_max_config * m.z_segment_active[t, j]
        model.segment_charge_activation = pyo.Constraint(model.T, model.J, rule=segment_charge_activation_rule)

        def segment_discharge_activation_rule(m, t, j):
            return m.p_dis_j[t, j] <= m.P_max_config * m.z_segment_active[t, j]
        model.segment_discharge_activation = pyo.Constraint(model.T, model.J, rule=segment_discharge_activation_rule)

    logger.info(f"Added segment SOC dynamics, ordering, and activation logic: {len(model.T) * len(model.J):,} core constraints")
```

> **Toggle note:** expose a configuration flag (`enforce_segment_binary`) to disable the optional binary activation layer for large-scale LP runs; the stacked-tank inequality alone keeps the physical order if integer variables become prohibitive.

**Task 3.6:** Remove or deactivate daily cycle limit constraint

```python
    # Task 3.6.1: Deactivate Cst-5 (daily cycle limit) if it exists in parent model
    # In Model (i), this constraint is named 'daily_cycle_limit'
    if hasattr(model, 'daily_cycle_limit'):
        model.daily_cycle_limit.deactivate()
        logger.info("Deactivated daily cycle limit constraint (Cst-5) - replaced by cost function")
    else:
        logger.info("No daily cycle limit constraint found (expected if parent passed None)")
```

**Task 3.7:** Extend objective function to include degradation cost

```python
    # Task 3.7.1: Capture parent objective expression (already holds all revenue terms)
    parent_objective_expr = model.objective.expr

    # Task 3.7.2: Define cyclic degradation cost term (Model ii addition)
    cost_cyclic = sum(
        sum(
            model.c_cost[j] * (model.p_dis_j[t, j] / model.eta_dis) * model.dt
            for j in model.J
        )
        for t in model.T
    )

    # Task 3.7.3: Update the objective expression incrementally to retain parent logic
    model.objective.set_expr(parent_objective_expr - model.alpha * cost_cyclic)
    logger.info("Extended parent objective with cyclic aging cost (incremental update)")
```

**Task 3.8:** Return the extended model

```python
    # Task 3.8.1: Log model statistics
    logger.info("Model (ii) build complete:")
    logger.info(f"  - Variables: {model.nvariables():,}")
    logger.info(f"  - Constraints: {model.nconstraints():,}")
    logger.info(f"  - Objective includes cyclic aging cost with α={alpha}")

    return model
```

### Step 4: Extend `solve_model` Method (Optional Enhancement)

**Note:** The parent `solve_model` method can be reused as-is. However, to extract segment-level results and compute aging metrics, you can override it.

**Task 4.1:** Override `solve_model` to extract additional metrics

```python
def solve_model(self, model: pyo.ConcreteModel, solver_name: str = None) -> Dict:
    """
    Solve the optimization model and extract results including degradation metrics.

    Extends parent method by adding:
        - Segment-level SOC profiles
        - Cyclic degradation cost breakdown
        - Equivalent Full Cycles (EFC)
        - Total throughput metrics

    Args:
        model: Pyomo ConcreteModel (Model ii)
        solver_name: Solver to use (default: 'cbc')

    Returns:
        Dictionary with all Model (i) results plus degradation metrics
    """
    # Task 4.1.1: Call parent solve method to get base results
    results = super().solve_model(model, solver_name)

    # Task 4.1.2: If solve failed, return immediately
    if results['status'] not in ['optimal', 'feasible']:
        return results

    # Task 4.1.3: Extract segment-level results (if needed for analysis)
    if self.degradation_params['enabled']:
        # Extract per-segment discharge power
        p_dis_j = {}
        for t in model.T:
            for j in model.J:
                p_dis_j[(t, j)] = pyo.value(model.p_dis_j[t, j])

        # Extract per-segment SOC
        e_soc_j = {}
        for t in model.T:
            for j in model.J:
                e_soc_j[(t, j)] = pyo.value(model.e_soc_j[t, j])

        # Task 4.1.4: Calculate degradation metrics
        degradation_metrics = self._calculate_degradation_metrics(model, p_dis_j, e_soc_j)

        # Task 4.1.5: Add to results dictionary
        results['degradation_metrics'] = degradation_metrics
        results['p_dis_j'] = p_dis_j  # Optional: for detailed analysis
        results['e_soc_j'] = e_soc_j  # Optional: for detailed analysis

    return results
```

**Task 4.2:** Implement degradation metrics calculation

```python
def _calculate_degradation_metrics(self, model: pyo.ConcreteModel,
                                     p_dis_j: Dict, e_soc_j: Dict) -> Dict:
    """
    Calculate degradation metrics from segment-level operation.

    Metrics:
        - Total cyclic cost (EUR)
        - Equivalent Full Cycles (EFC)
        - Total discharge throughput (kWh)
        - Throughput per segment (kWh)
        - Average Depth of Discharge (DoD)

    Args:
        model: Solved Pyomo model
        p_dis_j: Segment discharge power dictionary {(t,j): value}
        e_soc_j: Segment SOC dictionary {(t,j): value}

    Returns:
        Dictionary of degradation metrics
    """
    eta_dis = pyo.value(model.eta_dis)
    dt = pyo.value(model.dt)
    E_nom = pyo.value(model.E_nom)

    # Calculate total cyclic cost
    total_cyclic_cost = sum(
        pyo.value(model.c_cost[j]) * (p_dis_j[(t, j)] / eta_dis) * dt
        for t in model.T
        for j in model.J
    )

    # Calculate throughput per segment
    throughput_per_segment = {}
    for j in model.J:
        throughput_j = sum(
            (p_dis_j[(t, j)] / eta_dis) * dt
            for t in model.T
        )
        throughput_per_segment[j] = throughput_j

    # Calculate total throughput
    total_throughput = sum(throughput_per_segment.values())

    # Calculate Equivalent Full Cycles (EFC)
    efc = total_throughput / E_nom

    # Calculate weighted average DoD (approximation)
    avg_dod = efc / len(model.D) if len(model.D) > 0 else 0

    # Calculate cost per segment
    cost_per_segment = {}
    for j in model.J:
        cost_per_segment[j] = (
            pyo.value(model.c_cost[j]) * throughput_per_segment[j]
        )

    return {
        'total_cyclic_cost_eur': total_cyclic_cost,
        'equivalent_full_cycles': efc,
        'total_throughput_kwh': total_throughput,
        'throughput_per_segment_kwh': throughput_per_segment,
        'cost_per_segment_eur': cost_per_segment,
        'average_dod': avg_dod,
        'alpha': pyo.value(model.alpha)
    }
```

### Step 5: Add Public Aliases

**File:** `py_script/core/optimizer.py`
**Location:** After line 1089 (after existing Model (i) aliases)

```python
# ===================================================================
# Model (ii) Public API Aliases
# ===================================================================

BESSOptimizer_Phase2_ModelII = BESSOptimizerModelII
BESSOptimizerV3 = BESSOptimizerModelII  # Version-based alias

# For future Model (iii) (calendar + cyclic aging):
# BESSOptimizer_Phase2_ModelIII = BESSOptimizerModelIII
# BESSOptimizerV4 = BESSOptimizerModelIII
```

---

## 5. Detailed Code Specifications

### 5.1 Variable Naming Conventions

| Variable Pattern | Description | Example |
|------------------|-------------|---------|
| `p_ch_j[t, j]` | Per-segment charge power | `p_ch_j[100, 5]` = charge to segment 5 at t=100 |
| `p_dis_j[t, j]` | Per-segment discharge power | `p_dis_j[500, 1]` = discharge from segment 1 at t=500 |
| `e_soc_j[t, j]` | Per-segment energy storage | `e_soc_j[1000, 10]` = energy in segment 10 at t=1000 |
| `c_cost[j]` | Marginal degradation cost | `c_cost[1]` = 0.0052 EUR/kWh |
| `E_seg[j]` | Segment capacity | `E_seg[5]` = 447.2 kWh |

### 5.2 Index Mapping

**Segment Numbering:**
- **j = 1:** 90-100% SOC (shallowest, cheapest: €0.0052/kWh)
- **j = 2:** 80-90% SOC
- **...**
- **j = 10:** 0-10% SOC (deepest, most expensive: €0.0990/kWh)

**Array Indexing:**
```python
# aging_config.json has costs[0] to costs[9]
# Pyomo set J has indices 1 to 10

# Mapping:
marginal_costs[j-1]  # j=1 → costs[0], j=10 → costs[9]
```

### 5.3 Constraint Formulas (Pyomo Syntax)

**Per-Segment SOC Dynamics:**
```python
# Mathematical:
# e_soc_j[t,j] = e_soc_j[t-1,j] + (p_ch_j[t,j] * η_ch - p_dis_j[t,j] / η_dis) * Δt

# Pyomo:
def segment_soc_dynamics_rule(m, t, j):
    if t == m.T.first():
        return m.e_soc_j[t, j] == initial_soc_j + (m.p_ch_j[t, j] * m.eta_ch - m.p_dis_j[t, j] / m.eta_dis) * m.dt
    else:
        return m.e_soc_j[t, j] == m.e_soc_j[m.T.prev(t), j] + (m.p_ch_j[t, j] * m.eta_ch - m.p_dis_j[t, j] / m.eta_dis) * m.dt
```

**Power Aggregation:**
```python
# Mathematical:
# p_total_ch[t] = Σ_j p_ch_j[t,j]

# Pyomo:
def total_charge_power_rule(m, t):
    return m.p_total_ch[t] == sum(m.p_ch_j[t, j] for j in m.J)
```

**Cyclic Cost (Objective):**
```python
# Mathematical:
# C_cyc = Σ_t Σ_j (c_cost[j] × p_dis_j[t,j] / η_dis × Δt)

# Pyomo:
cost_cyclic = sum(
    sum(m.c_cost[j] * (m.p_dis_j[t, j] / m.eta_dis) * m.dt for j in m.J)
    for t in m.T
)
```

### 5.4 Model Size Estimation

**For a 1-week simulation (672 time steps):**

| Component | Model (i) | Model (ii) | Increase |
|-----------|-----------|------------|----------|
| **Continuous Variables** | ~4,000 | ~25,000 | ≈6× |
| **Binary Variables** | ~3,400 | ~10,000 | ≈3× (stacked-tank gating) |
| **Constraints** | ~8,000 | ~52,000 | ≈6.5× |
| **Solve Time** | ~30s | 240–480s | 8–16× (empirical expectation) |

> **Performance warning:** the stacked-tank ordering, activation binaries, and per-segment dynamics introduce ~22k additional constraints over a 1-week horizon. Expect solve times in the 4–8 minute range on CBC/HiGHS; use Gurobi/CPLEX or disable the optional binaries for faster prototyping.

**For full year (35,040 time steps):** Model (ii) is computationally expensive. Adopt the **Rolling Horizon / MPC** approach (Section 10.3) with 2–3 day horizons and 1-day execution steps; store both total SOC and per-segment SOC between windows to maintain continuity.

---

## 6. Configuration File Integration

### 6.1 Configuration File Schema

**File:** `data/phase2_aging_config/aging_config.json`

```json
{
  "cyclic_aging": {
    "description": "Marginal cost of discharging 1 kWh from different SOC segments, based on a power-law model (b=2) and a 100% DoD cycle life of 3840 cycles.",
    "unit": "EUR/kWh",
    "costs": [
      0.0052,  // Segment 1: 90-100% SOC
      0.0156,  // Segment 2: 80-90%
      0.0260,  // Segment 3: 70-80%
      0.0364,  // Segment 4: 60-70%
      0.0469,  // Segment 5: 50-60%
      0.0573,  // Segment 6: 40-50%
      0.0677,  // Segment 7: 30-40%
      0.0781,  // Segment 8: 20-30%
      0.0885,  // Segment 9: 10-20%
      0.0990   // Segment 10: 0-10% SOC
    ]
  },
  "calendar_aging": {
    "description": "Breakpoints for the piecewise-linear calendar aging cost function (SOS2), derived from Collath et al. (2023).",
    "soc_breakpoints": {
      "unit": "kWh",
      "values": [0, 1118, 2236, 3354, 4472]
    },
    "cost_breakpoints": {
      "unit": "EUR/hr",
      "values": [1.79, 2.15, 3.58, 6.44, 10.73]
    }
  }
}
```

**Note:** Calendar aging data is included for future Model (iii) but not used in Model (ii).

### 6.2 Loading and Validation

**Implementation (see Step 2.2 and 2.3 above):**

1. **Load JSON:** Use `json.load()` with error handling
2. **Validate Structure:** Check for required keys (`cyclic_aging`, `costs`)
3. **Validate Values:**
   - All costs are non-negative
   - Costs are strictly increasing (convex function)
   - Array length matches expected segments (10)
4. **Log Configuration:** Log loaded parameters for traceability

### 6.3 Error Handling

**Common Errors:**

| Error Type | Cause | Solution |
|------------|-------|----------|
| `FileNotFoundError` | Config file missing | Check path: `data/phase2_aging_config/aging_config.json` |
| `JSONDecodeError` | Invalid JSON syntax | Validate JSON with linter |
| `KeyError` | Missing 'costs' key | Ensure correct schema |
| `ValueError` | Negative cost values | Check cost calculation logic |
| `Warning` | Non-increasing costs | Review power-law parameterization |

---

## 7. Testing Strategy

### 7.1 Unit Tests

**File:** `tests/test_model_ii.py`

**Test Cases:**

```python
import pytest
import pyomo.environ as pyo
from py_script.core.optimizer import BESSOptimizerModelII, BESSOptimizerModelI

class TestModelIIInitialization:
    """Test Model (ii) initialization and configuration loading."""

    def test_load_degradation_config(self):
        """Degradation config should load and expose monotone marginal costs."""
        optimizer = BESSOptimizerModelII(
            degradation_config_path='data/phase2_aging_config/aging_config.json'
        )
        assert optimizer.degradation_params['num_segments'] == 10
        assert len(optimizer.degradation_params['marginal_costs']) == 10
        assert optimizer.degradation_params['marginal_costs'][0] == pytest.approx(0.0052)
        assert optimizer.degradation_params['marginal_costs'][-1] == pytest.approx(0.0990)

    def test_invalid_config_path(self):
        with pytest.raises(FileNotFoundError):
            BESSOptimizerModelII(degradation_config_path='nonexistent.json')

    def test_segment_capacity_calculation(self):
        optimizer = BESSOptimizerModelII()
        assert optimizer.degradation_params['segment_capacity_kwh'] == pytest.approx(447.2)

    def test_alpha_parameter(self):
        optimizer = BESSOptimizerModelII(alpha=2.5)
        assert optimizer.degradation_params['alpha'] == 2.5

class TestModelIIModelBuilding:
    """Test Pyomo model construction for Model (ii)."""

    def test_segment_set_creation(self, country_data):
        optimizer = BESSOptimizerModelII()
        model = optimizer.build_optimization_model(country_data, c_rate=0.5)
        assert list(model.J) == list(range(1, 11))

    def test_segment_variables_exist(self, country_data):
        optimizer = BESSOptimizerModelII()
        model = optimizer.build_optimization_model(country_data, c_rate=0.5)
        assert hasattr(model, 'p_ch_j')
        assert hasattr(model, 'p_dis_j')
        assert hasattr(model, 'e_soc_j')
        assert isinstance(model.e_soc, pyo.Expression)
        assert hasattr(model, 'stacked_tank_ordering')

    def test_aggregation_constraints(self, country_data):
        optimizer = BESSOptimizerModelII()
        model = optimizer.build_optimization_model(country_data, c_rate=0.5)
        assert hasattr(model, 'total_charge_aggregation')
        assert hasattr(model, 'total_discharge_aggregation')
        assert model.total_charge_aggregation.active
        assert model.total_discharge_aggregation.active

    def test_daily_cycle_limit_deactivated(self, country_data):
        optimizer = BESSOptimizerModelII()
        model = optimizer.build_optimization_model(country_data, c_rate=0.5, daily_cycle_limit=1.5)
        if hasattr(model, 'daily_cycle_limit'):
            assert not model.daily_cycle_limit.active()

    def test_objective_includes_degradation_cost(self, country_data):
        optimizer = BESSOptimizerModelII(alpha=1.0)
        model = optimizer.build_optimization_model(country_data, c_rate=0.5)
        cost_terms = [term for term in model.objective.expr.polynomial_degree_map().keys() if 'p_dis_j' in str(term)]
        assert model.objective.sense == pyo.maximize
        assert cost_terms  # ensure degradation cost terms exist

class TestModelIIEdgeCases:
    """Edge-case scenarios ensuring economic logic and SOC ordering."""

    def test_negative_price_blocks_discharge(self, toy_dataset_neg_price):
        optimizer = BESSOptimizerModelII(alpha=1.0)
        model = optimizer.build_optimization_model(toy_dataset_neg_price, c_rate=0.5)
        results = optimizer.solve_model(model, solver_name='highs')
        assert max(abs(v) for v in results['p_dis'].values()) < 1e-6

    def test_price_spike_uses_deep_segment(self, toy_dataset_price_spike):
        optimizer = BESSOptimizerModelII(alpha=1.0)
        model = optimizer.build_optimization_model(toy_dataset_price_spike, c_rate=0.5)
        results = optimizer.solve_model(model, solver_name='highs')
        deep_segment_usage = max(results['p_dis_j'][(t, 10)] for t in model.T)
        assert deep_segment_usage > 0.0

    def test_stacked_tank_monotonic(self, toy_dataset_moderate):
        optimizer = BESSOptimizerModelII(alpha=1.0)
        model = optimizer.build_optimization_model(toy_dataset_moderate, c_rate=0.5)
        results = optimizer.solve_model(model, solver_name='highs')
        for t in model.T:
            for j in range(1, 10):
                assert results['e_soc_j'][(t, j)] + 1e-6 >= results['e_soc_j'][(t, j + 1)]

class TestModelIIVsModelI:
    """Integration tests comparing Model (i) and Model (ii) behavior."""

    def test_model_ii_respects_total_soc_limits(self, country_data):
        optimizer = BESSOptimizerModelII()
        model = optimizer.build_optimization_model(country_data, c_rate=0.5)
        results = optimizer.solve_model(model)
        for soc in results['e_soc'].values():
            assert 0.0 <= soc <= 4472

    def test_model_ii_matches_model_i_when_alpha_zero(self, country_data):
        optimizer_i = BESSOptimizerModelI()
        revenue_i = optimizer_i.optimize(country_data, c_rate=0.5, daily_cycle_limit=1.5)['total_revenue']
        optimizer_ii = BESSOptimizerModelII(alpha=0.0)
        revenue_ii = optimizer_ii.optimize(country_data, c_rate=0.5)['total_revenue']
        assert revenue_ii >= revenue_i

    def test_model_ii_reduces_throughput_when_alpha_high(self, country_data):
        optimizer_low = BESSOptimizerModelII(alpha=0.1)
        optimizer_high = BESSOptimizerModelII(alpha=10.0)
        results_low = optimizer_low.optimize(country_data, c_rate=0.5)
        results_high = optimizer_high.optimize(country_data, c_rate=0.5)
        efc_low = results_low['degradation_metrics']['equivalent_full_cycles']
        efc_high = results_high['degradation_metrics']['equivalent_full_cycles']
        assert efc_high < efc_low
```

### 7.2 Integration Tests

**Test Scenario:** 1-week optimization with real market data

```python
def test_one_week_optimization_model_ii():
    """
    Integration test: Run Model (ii) on 1 week of real data.
    """
    # Load 1 week of data (672 timesteps)
    country_data = load_test_data_week1()

    # Initialize optimizer
    optimizer = BESSOptimizerModelII(
        degradation_config_path='data/phase2_aging_config/aging_config.json',
        alpha=1.0
    )

    # Run optimization
    results = optimizer.optimize(
        country_data=country_data,
        c_rate=0.5,
        daily_cycle_limit=None  # Ignored in Model (ii)
    )

    # Validate results
    assert results['status'] == 'optimal'
    assert results['total_revenue'] > 0
    assert 'degradation_metrics' in results

    # Check degradation metrics
    metrics = results['degradation_metrics']
    assert metrics['total_cyclic_cost_eur'] > 0
    assert metrics['equivalent_full_cycles'] > 0
    assert metrics['equivalent_full_cycles'] < 14  # Max 2 cycles/day × 7 days

    # Verify segment-level data
    assert len(metrics['throughput_per_segment_kwh']) == 10

    print(f"✓ 1-week optimization completed successfully")
    print(f"  Revenue: €{results['total_revenue']:,.2f}")
    print(f"  Degradation Cost: €{metrics['total_cyclic_cost_eur']:,.2f}")
    print(f"  Net Profit: €{results['total_revenue'] - metrics['total_cyclic_cost_eur']:,.2f}")
    print(f"  EFC: {metrics['equivalent_full_cycles']:.2f}")
```

### 7.3 Validation Tests

**Validate Against Known Behavior:**

1. **Shallow Discharge Preference:**
   - Extract `p_dis_j` results
   - Verify that segment 1 is discharged before segment 10
   - Check that deeper segments only discharge when price is very high

2. **Cost Calculation Consistency:**
   - Manually calculate cyclic cost from results
   - Compare with solver's objective value breakdown
   - Verify: `Revenue - α×Cost = Objective Value`

3. **Energy Conservation:**
   - Sum of segment SOCs should equal total SOC
   - Total power should equal sum of segment powers
   - No energy "leakage" between segments

### 7.4 Performance Benchmarks

**Target Performance (for 1 week, CBC solver):**

| Metric | Model (i) | Model (ii) | Max Allowed |
|--------|-----------|------------|-------------|
| Build Time | 5s | 15s | 30s |
| Solve Time | 30s | 120s | 300s |
| Memory Usage | 500 MB | 2 GB | 4 GB |
| Solution Quality | Optimal | Optimal | Feasible (min) |

---

## 8. API Compatibility

### 8.1 Public Interface

**Class Signature:**

```python
class BESSOptimizerModelII(BESSOptimizerModelI):
    def __init__(self, country_data=None, config=None,
                 degradation_config_path=None, alpha=1.0):
        ...
```

**Key Methods:**

| Method | Input | Output | Change from Model (i) |
|--------|-------|--------|----------------------|
| `__init__` | + `degradation_config_path`, + `alpha` | None | New parameters |
| `build_optimization_model` | Same (ignores `daily_cycle_limit`) | Pyomo model | Extended model |
| `solve_model` | Same | Dict + `degradation_metrics` | Extended output |
| `optimize` | Same | Dict + `degradation_metrics` | Extended output |

### 8.2 Migration Guide

**From Model (i) to Model (ii):**

**Before (Model i):**
```python
from py_script.core.optimizer import BESSOptimizerModelI

optimizer = BESSOptimizerModelI()
results = optimizer.optimize(
    country_data=data,
    c_rate=0.5,
    daily_cycle_limit=1.5  # Hard constraint
)

print(f"Revenue: €{results['total_revenue']}")
```

**After (Model ii):**
```python
from py_script.core.optimizer import BESSOptimizerModelII

optimizer = BESSOptimizerModelII(
    degradation_config_path='data/phase2_aging_config/aging_config.json',
    alpha=1.0  # Tune for profit vs. degradation trade-off
)

results = optimizer.optimize(
    country_data=data,
    c_rate=0.5,
    daily_cycle_limit=None  # Ignored - now use cost-based approach
)

print(f"Revenue: €{results['total_revenue']}")
print(f"Degradation Cost: €{results['degradation_metrics']['total_cyclic_cost_eur']}")
print(f"Net Profit: €{results['total_revenue'] - results['degradation_metrics']['total_cyclic_cost_eur']}")
print(f"EFC: {results['degradation_metrics']['equivalent_full_cycles']:.2f}")
```

### 8.3 Backward Compatibility

**Aliases Ensure No Breaking Changes:**

```python
# Still works (uses Model i)
from py_script.core.optimizer import BESSOptimizer  # → BESSOptimizerModelI

# New alias for Model (ii)
from py_script.core.optimizer import BESSOptimizer_Phase2_ModelII  # → BESSOptimizerModelII
```

**Existing scripts using Model (i) continue to work unchanged.**

---

## 9. Expected Results & Validation

### 9.1 Expected Behavior Differences

| Metric | Model (i) @ 1.5 cycles/day | Model (ii) @ α=1.0 | Expected Change |
|--------|----------------------------|---------------------|-----------------|
| **Daily Cycles** | ≤ 1.5 (hard limit) | 1.2-1.8 (variable) | More flexible |
| **Revenue** | Baseline | +5% to +15% | Higher |
| **Degradation Cost** | Not modeled | €50-200/day | Now visible |
| **Deep Discharges** | Allowed (if within limit) | Penalized | Reduced |
| **SOC Cycling Pattern** | Uniform | Shallow-preferring | Different |

### 9.2 Verification Checklist

**After implementation, verify:**

- [ ] Model builds without errors
- [ ] All 10 segments are created correctly
- [ ] Aggregation constraints work (total SOC = sum of segments)
- [ ] Objective includes degradation cost term
- [ ] Solver converges to optimal/feasible solution
- [ ] Results contain `degradation_metrics` dictionary
- [ ] Cyclic cost is calculated correctly
- [ ] Segment 1 is preferred over segment 10 (cost hierarchy)
- [ ] Total energy is conserved (no leakage)
- [ ] Model (ii) with α=0 matches Model (i) without cycle limit

### 9.3 Debugging Common Issues

**Issue 1: Infeasible Model**
- **Symptom:** Solver returns "infeasible"
- **Causes:**
  1. Initial SOC distribution doesn't satisfy segment capacities
  2. Aggregation constraints conflict with existing constraints
  3. Segment limits too restrictive
- **Solution:** Check initial conditions, review constraint logic

**Issue 2: Very High Solve Time**
- **Symptom:** Model doesn't solve within time limit
- **Causes:**
  1. Too many timesteps (use rolling horizon for >1 week)
  2. Solver struggling with degeneracy
  3. Too many binary variables
- **Solution:** Reduce problem size, use commercial solver (Gurobi/CPLEX), add solver options

**Issue 3: Degradation Cost is Zero**
- **Symptom:** `total_cyclic_cost_eur` = 0 in results
- **Causes:**
  1. No discharging occurred (prices too low)
  2. Alpha is zero
  3. Objective calculation error
- **Solution:** Check price data, verify alpha > 0, debug objective function

**Issue 4: Segment Discharge Order Violation**
- **Symptom:** Segment 10 discharges before segment 1
- **Causes:**
  1. Cost vector not increasing
  2. Solver numerical issues
  3. Constraint error in cascading logic
- **Solution:** Validate cost monotonicity, check constraint implementation

---

## 10. Future Extensions

### 10.1 Path to Model (iii): Calendar Aging Integration

**Next Steps:**

1. **Add Calendar Aging Cost Function:**
   - Implement SOS2 variables for piecewise-linear SOC-dependent cost
   - Load calendar aging breakpoints from `aging_config.json`
   - Add calendar cost term to objective: `- α_cal × C_cal`

2. **Modify Objective:**
   ```python
   # Model (iii)
   return revenue - alpha_cyc * C_cyc - alpha_cal * C_cal
   ```

3. **New Class:**
   ```python
   class BESSOptimizerModelIII(BESSOptimizerModelII):
       """Model (iii): Model (ii) + Calendar Aging"""
   ```

### 10.2 Meta-Parameter Optimization (α Tuning)

**Implement α Sweep for 10-Year ROI Maximization:**

```python
def optimize_alpha_for_roi(country_data, c_rate, alpha_range=(0.1, 10.0), num_trials=20):
    """
    Find optimal α that maximizes 10-year NPV.

    Strategy:
        1. For each α in range:
           a. Run 365-day MPC simulation
           b. Calculate total profit and degradation
           c. Project to 10-year ROI
        2. Select α* with highest ROI
        3. Re-run simulation with α*

    Args:
        country_data: Full-year market data
        c_rate: C-rate configuration
        alpha_range: (min, max) for α sweep
        num_trials: Number of α values to test

    Returns:
        Dictionary with optimal α and corresponding ROI
    """
    from scipy.optimize import minimize_scalar

    def negative_roi(alpha):
        """Objective: -ROI (for minimization)."""
        optimizer = BESSOptimizerModelII(alpha=alpha)
        results = run_mpc_simulation(optimizer, country_data, c_rate)
        roi = calculate_10_year_roi(results)
        return -roi  # Minimize negative = maximize positive

    result = minimize_scalar(
        negative_roi,
        bounds=alpha_range,
        method='bounded',
        options={'maxiter': num_trials}
    )

    optimal_alpha = result.x
    optimal_roi = -result.fun

    return {
        'optimal_alpha': optimal_alpha,
        'optimal_roi': optimal_roi,
        'alpha_values_tested': [...],
        'roi_values': [...]
    }
```

### 10.3 Rolling Horizon (MPC) Implementation

**For Full-Year Optimization:**

```python
def run_mpc_simulation(optimizer, full_year_data, c_rate,
                       horizon_days=2, execution_days=1):
    """
    Run Model Predictive Control simulation over full year.

    Strategy:
        - Optimize over H-day horizon
        - Execute first E days
        - Roll forward and repeat
        - Aggregate results

    Args:
        optimizer: BESSOptimizerModelII instance
        full_year_data: 365 days of market data
        c_rate: C-rate configuration
        horizon_days: Optimization horizon length
        execution_days: Execution period length

    Returns:
        Aggregated annual results
    """
    results_aggregate = {
        'total_revenue': 0,
        'total_degradation_cost': 0,
        'daily_results': []
    }

    segment_capacity = 4472
    current_total_soc = 0.5 * segment_capacity  # Start at 50% SOC
    current_segment_soc = top_down_segment_fill(current_total_soc, segment_capacity)

    for day in range(0, 365, execution_days):
        horizon_data = full_year_data[day:day+horizon_days]
        model = optimizer.build_optimization_model(horizon_data, c_rate)

        # Fix initial SOC for each segment (keeps stacked-tank continuity)
        t0 = model.T.first()
        for j in model.J:
            model.e_soc_j[t0, j].fix(current_segment_soc[j])
            if hasattr(model, 'z_segment_active'):
                model.z_segment_active[t0, j].fix(1 if current_segment_soc[j] > 1e-3 else 0)

        results = optimizer.solve_model(model)
        execution_results = extract_execution_period(results, execution_days)

        results_aggregate['total_revenue'] += execution_results['revenue']
        results_aggregate['total_degradation_cost'] += execution_results['degradation_cost']
        results_aggregate['daily_results'].append(execution_results)

        # Update SOC for next iteration (store both total and per-segment states)
        current_total_soc = execution_results['final_soc']
        current_segment_soc = execution_results['final_soc_per_segment']

        # Unfix initial conditions before next horizon build (Pyomo requirement)
        for j in model.J:
            model.e_soc_j[t0, j].unfix()
            if hasattr(model, 'z_segment_active'):
                model.z_segment_active[t0, j].unfix()

    return results_aggregate
```

> Implement `top_down_segment_fill(total_soc, segment_capacity)` to mirror the initialization logic from Task 3.5 and return a `{segment: soc}` dictionary; ensure `extract_execution_period` persists both `final_soc` and `final_soc_per_segment` to keep horizons consistent.

### 10.4 Visualization and Reporting

**Add Degradation Analysis Plots:**

1. **Segment Discharge Heatmap:**
   - X-axis: Time
   - Y-axis: Segment (1-10)
   - Color: Discharge power
   - Shows which segments are used when

2. **Cost vs. Revenue Scatter:**
   - X-axis: Cyclic cost
   - Y-axis: Revenue
   - Points: Different α values
   - Shows Pareto frontier

3. **SOC Trajectory by Segment:**
   - Multi-line plot showing `e_soc_j[t]` for each segment
   - Helps visualize LIFO behavior

---

## 11. References

### 11.1 Project Documents

1. **Mathematical Formulation:**
   - `doc/p2_model/p2_bi_model_ggdp.tex` (LaTeX source)
   - `doc/p2_model/p2_bi_model_ggdp.pdf` (Compiled PDF)
   - Sections: "Model (ii): Model (i) + Cyclic Aging Cost" (lines 327-383)

2. **Aging Configuration:**
   - `data/phase2_aging_config/aging_config.json`
   - Contains cyclic aging costs (10 segments)
   - Contains calendar aging breakpoints (for Model iii)

3. **Project Overview:**
   - `doc/whole_project_description.md`
   - Phase II requirements and evaluation criteria
   - Battery degradation importance

4. **Current Implementation:**
   - `py_script/core/optimizer.py` (Model i: lines 49-1010)

### 11.2 Academic Literature

1. **Xu, B., Zhao, J., Zheng, T., Litvinov, E., & Kirschen, D. S. (2017).**
   - "Factoring the Cycle Aging Cost of Batteries Participating in Electricity Markets"
   - *arXiv:1707.04567v2*
   - **Key Contribution:** Piecewise-linear cyclic aging cost model

2. **Collath, N., Cornejo, M., Engwerth, V., Hesse, H., & Jossen, A. (2023).**
   - "Increasing the lifetime profitability of battery energy storage systems through aging aware operation"
   - *Applied Energy*, 348, 121531
   - **Key Contribution:** Calendar aging model, scaled/discounted cost approach

### 11.3 Key Equations Reference

**Cyclic Aging Cost (Equation from p2_bi_model_ggdp.tex):**

$$C^{\mathrm{cyc}} = \sum_{t \in T} \sum_{j \in J} \left( c^{\mathrm{cost}}_{j} \cdot \frac{p^{\mathrm{dis}}_{j}(t)}{\eta_{\mathrm{dis}}} \cdot \Delta t \right)$$

**Power-Law Cycle Life Model:**

$$\text{CycleLife}(D) = a \cdot D^{-b}$$

Where:
- $D$: Depth of Discharge (0-1)
- $a$: Cycle life at 100% DoD (3,840 for LFP)
- $b$: Exponent (2 for strong penalty on deep cycles)

**Marginal Cost Calculation:**

$$c^{\mathrm{cost}}_{j} = \frac{\text{Cost per Full Cycle} \times w_j}{E_{\mathrm{nom}} \times \text{Segment Size}}$$

Where:
- $w_j$: Marginal aging weight (from $D_j^2 - D_{j-1}^2$)
- Cost per Full Cycle: €232.92
- Segment Size: 0.1 (10%)

---

## 12. Appendix

### 12.1 Complete Code Skeleton

**File:** `py_script/core/optimizer.py` (additions after line 1010)

```python
# ===================================================================
# Model (ii): BESS Optimizer with Cyclic Aging Cost
# ===================================================================

class BESSOptimizerModelII(BESSOptimizerModelI):
    """[See Step 1 for full docstring]"""

    def __init__(self, country_data=None, config=None,
                 degradation_config_path=None, alpha=1.0):
        """[See Step 2.1 for implementation]"""
        pass

    def _load_degradation_config(self, config_path: str) -> Dict:
        """[See Step 2.2 for implementation]"""
        pass

    def _validate_degradation_params(self):
        """[See Step 2.3 for implementation]"""
        pass

    def build_optimization_model(self, country_data: pd.DataFrame,
                                  c_rate: float, daily_cycle_limit: float = None) -> pyo.ConcreteModel:
        """[See Step 3 for implementation]"""
        pass

    def solve_model(self, model: pyo.ConcreteModel, solver_name: str = None) -> Dict:
        """[See Step 4 for implementation]"""
        pass

    def _calculate_degradation_metrics(self, model: pyo.ConcreteModel,
                                         p_dis_j: Dict, e_soc_j: Dict) -> Dict:
        """[See Step 4.2 for implementation]"""
        pass

# ===================================================================
# Model (ii) Public API Aliases
# ===================================================================

BESSOptimizer_Phase2_ModelII = BESSOptimizerModelII
BESSOptimizerV3 = BESSOptimizerModelII
```

### 12.2 Aging Cost Data Reference

**Complete Marginal Cost Table:**

| Segment | SOC Range | DoD Range | Multiplier $w_j$ | Marginal Cost (EUR/kWh) |
|---------|-----------|-----------|------------------|-------------------------|
| 1 | 90-100% | 0-10% | 0.01 | 0.0052 |
| 2 | 80-90% | 10-20% | 0.03 | 0.0156 |
| 3 | 70-80% | 20-30% | 0.05 | 0.0260 |
| 4 | 60-70% | 30-40% | 0.07 | 0.0364 |
| 5 | 50-60% | 40-50% | 0.09 | 0.0469 |
| 6 | 40-50% | 50-60% | 0.11 | 0.0573 |
| 7 | 30-40% | 60-70% | 0.13 | 0.0677 |
| 8 | 20-30% | 70-80% | 0.15 | 0.0781 |
| 9 | 10-20% | 80-90% | 0.17 | 0.0885 |
| 10 | 0-10% | 90-100% | 0.19 | 0.0990 |

**Verification:**
$$\sum_{j=1}^{10} c^{\mathrm{cost}}_{j} \times 447.2 \text{ kWh} = (0.0052 + 0.0156 + ... + 0.0990) \times 447.2 = 232.92 \text{ EUR}$$

### 12.3 Common Issues and Solutions

| Issue | Symptom | Root Cause | Solution |
|-------|---------|------------|----------|
| **Import Error** | `ModuleNotFoundError` | Missing dependencies | Install pyomo, pandas, numpy |
| **Config Not Found** | `FileNotFoundError` | Wrong path | Check `data/phase2_aging_config/` exists |
| **Infeasible Model** | Solver returns "infeasible" | Conflicting constraints | Review aggregation constraints |
| **Slow Solve** | Timeout after 600s | Too many timesteps | Use MPC with 2-day horizon |
| **Zero Degradation Cost** | `total_cyclic_cost_eur` = 0 | No discharging or α=0 | Check prices and alpha value |
| **Wrong Segment Order** | Seg 10 discharges first | Cost vector error | Validate costs are increasing |
| **Memory Error** | `MemoryError` | Model too large | Reduce timesteps or use 64-bit Python |

### 12.4 Development Checklist

**Pre-Implementation:**
- [ ] Read `p2_bi_model_ggdp.tex` Model (ii) section thoroughly
- [ ] Understand segment-based SOC tracking concept
- [ ] Review `aging_config.json` structure
- [ ] Set up development environment with Pyomo

**Implementation Phase:**
- [ ] Implement `_load_degradation_config` method
- [ ] Implement `_validate_degradation_params` method
- [ ] Implement `__init__` override
- [ ] Implement `build_optimization_model` override
  - [ ] Add segment set J
  - [ ] Add segment parameters
  - [ ] Add segment variables
  - [ ] Add aggregation constraints
  - [ ] Add segment SOC dynamics
  - [ ] Modify objective function
- [ ] Implement `solve_model` override (optional)
- [ ] Add public aliases

**Testing Phase:**
- [ ] Write unit tests for config loading
- [ ] Write unit tests for model building
- [ ] Write integration test (1-week optimization)
- [ ] Write validation test (Model i vs Model ii comparison)
- [ ] Run performance benchmarks

**Documentation Phase:**
- [ ] Add docstrings to all methods
- [ ] Update README with Model (ii) usage
- [ ] Create example notebook demonstrating Model (ii)
- [ ] Document α tuning process

**Validation Phase:**
- [ ] Verify segment discharge order (shallow first)
- [ ] Verify energy conservation
- [ ] Verify cost calculation correctness
- [ ] Compare with Model (i) baseline
- [ ] Test on full year with MPC

---

## End of Implementation Plan

**Document Status:** Ready for Implementation
**Last Updated:** 2025-01-08
**Next Steps:** Begin implementation following Step 1 of Section 4

**Questions or Issues?** Refer to Section 12.3 (Common Issues) or contact the development team.

---

**License:** Internal Project Document - Huawei TechArena 2025
**Confidentiality:** Team SoloGen Only
