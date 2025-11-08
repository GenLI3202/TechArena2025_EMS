# Phase II Model Naming Scheme

## Overview

Phase II consists of three progressive models, each building upon the previous one. This document defines the naming conventions used throughout the codebase.

**IMPORTANT**: *Math Model documents* `doc/p2_model/p2_bi_model_ggdp.tex` and 
`doc/p2_model/p2_3models_formulation.tex`

## Model Hierarchy

```
Phase I Base Model (3 markets)
    ↓
Model (i): Base + aFRR Energy Market (4 markets)
    ↓
Model (ii): Model (i) + Cyclic Aging Cost
    ↓
Model (iii): Model (ii) + Calendar Aging Cost [FULL PHASE II MODEL]
```

## Python Class Names

### Model (i): Base Model + aFRR Energy Market ✓ IMPLEMENTED

**Primary Class Name:**
```python
from core.optimizer import BESSOptimizerModelI
```

**Aliases (for backward compatibility):**
```python
BESSOptimizer                    # Main alias
BESSOptimizerV2                  # Old V2 naming
BESSOptimizer_Phase2_ModelI      # Explicit naming
```

**Key Features:**
- 4-market co-optimization: DA energy, aFRR energy, FCR capacity, aFRR capacity
- New variables: p_afrr_pos_e, p_afrr_neg_e, p_total_ch, p_total_dis
- Objective: max(P_DA + P_ANCI + P_aFRR_E)
- No degradation modeling

---

### Model (ii): Model (i) + Cyclic Aging Cost [PLANNED]


**Primary Class Name:**
```python
from core.optimizer import BESSOptimizerModelII  # To be implemented
```

**Aliases:**
```python
BESSOptimizer_Phase2_ModelII     # Explicit naming
```

**Key Features:**
- All features from Model (i)
- Piecewise-linear cyclic aging cost (Xu et al., 2017)
- Segment-based SOC tracking: e_soc_j[t] for j ∈ J
- Objective: max(P_DA + P_ANCI + P_aFRR_E - α·C_cyc)
- Replaces rigid daily cycle limit with economic cost

---

### Model (iii): Model (ii) + Calendar Aging Cost [PLANNED]

**Primary Class Name:**
```python
from core.optimizer import BESSOptimizerModelIII  # To be implemented
```

**Aliases:**
```python
BESSOptimizer_Phase2_Full        # Full Phase II model
BESSOptimizer_Phase2_ModelIII    # Explicit naming
```

**Key Features:**
- All features from Model (ii)
- SOS2-based calendar aging cost (Collath et al., 2023)
- SOC-dependent degradation: λ_{t,i} weights
- Objective: max(P_DA + P_ANCI + P_aFRR_E - α·(C_cyc + C_cal))
- Complete Phase II formulation

---

## Usage Examples

### Current: Model (i)

```python
from core.optimizer import BESSOptimizerModelI

# Initialize
optimizer = BESSOptimizerModelI()

# Load data (includes aFRR energy automatically)
data = optimizer.load_and_preprocess_data("data/TechArena2025_data_tidy.jsonl")

# Extract and optimize
country_data = optimizer.extract_country_data(data, 'DE_LU')
model = optimizer.build_optimization_model(country_data, c_rate=0.5, daily_cycle_limit=1.5)
solution = optimizer.solve_model(model)
```

### Future: Model (ii)

```python
from core.optimizer import BESSOptimizerModelII

# Initialize with degradation parameters
optimizer = BESSOptimizerModelII(
    num_segments=10,           # J = 10 SOC segments
    degradation_price_alpha=1.0  # α meta-parameter
)

# Same workflow as Model (i)
# ...
```

### Future: Model (iii)

```python
from core.optimizer import BESSOptimizerModelIII

# Initialize with full degradation modeling
optimizer = BESSOptimizerModelIII(
    num_segments=10,              # J = 10 SOC segments
    num_breakpoints=20,           # I = 20 calendar cost breakpoints
    degradation_price_alpha=1.0   # α meta-parameter
)

# Same workflow as Model (i) and (ii)
# ...
```

---

## File Organization

```
py_script/core/
├── optimizer.py                 # Contains BESSOptimizerModelI ✓
├── optimizer_model_ii.py        # Will contain BESSOptimizerModelII
└── optimizer_model_iii.py       # Will contain BESSOptimizerModelIII

test_model_i.py                  # Tests Model (i) ✓
test_model_ii.py                 # Will test Model (ii)
test_model_iii.py                # Will test Model (iii)
```

---

## References

- **Mathematical Formulation:** `doc/p2_model/p2_bi_model_ggdp.tex`
- **Clean Model Definitions:** `doc/p2_model/p2_3models_formulation.tex`
- **Phase I Documentation:** See branch `r1-static-battery`

---

## Migration Guide

If you have existing code using the old naming:

```python
# Old (still works via aliases)
from core.optimizer import BESSOptimizerV2
optimizer = BESSOptimizerV2()

# New (recommended)
from core.optimizer import BESSOptimizerModelI
optimizer = BESSOptimizerModelI()
```

All old code will continue to work due to backward compatibility aliases.

---

Last Updated: 2025-11-08
Model (i) Status: ✓ Implemented and Tested
