# Model Update Prompt: Fix Capacity Market Revenue Calculation

## Task Overview
Fix a critical bug in the Phase II Model (i) objective function where capacity market revenue is underestimated by 4× due to missing block duration multiplication.

---

## Background

During seasonal validation of Model (i), we discovered that capacity markets (FCR, aFRR capacity) contribute nearly 0% of revenue, while they should contribute 10-30%. Root cause analysis revealed:

**Problem:** The objective function multiplies capacity prices by capacity variables but fails to account for block duration. Capacity prices are in **EUR/MW/h** (hourly rates), not EUR/MW (per-block rates). Since each capacity market block is 4 hours long, the current implementation underestimates revenue by 4×.

**Evidence:**
- Validation results show capacity revenue ≈ 0% across all 12 test scenarios
- Official data headers label prices as "EUR/MW" but actually mean "EUR/MW/h"
- The parameter `model.db` (block duration = 4.0 hours) is defined but not used in the objective function

---

## Required Changes

### 1. Fix Objective Function (PRIMARY CHANGE)

**File:** `py_script/core/optimizer.py`

**Current Implementation (Lines 719-723):**
```python
# Ancillary service capacity profit (prices are per block, so no db multiplication)
as_profit = sum(model.P_FCR[b] * model.c_fcr[b] +
                model.P_aFRR_pos[b] * model.c_afrr_pos[b] +
                model.P_aFRR_neg[b] * model.c_afrr_neg[b]
                for b in model.B)
```

**Corrected Implementation:**
```python
# Ancillary service capacity profit (prices in EUR/MW/h, multiply by block duration)
as_profit = sum((model.P_FCR[b] * model.c_fcr[b] +
                 model.P_aFRR_pos[b] * model.c_afrr_pos[b] +
                 model.P_aFRR_neg[b] * model.c_afrr_neg[b]) * model.db
                for b in model.B)
```

**Key Changes:**
- Add parentheses around the sum of three capacity revenue terms
- Multiply the entire sum by `model.db` (block duration = 4.0 hours)
- Update comment to reflect correct unit interpretation

**Verification:** Ensure `model.db` is already defined earlier in the file (should be at line ~431).

---

### 2. Update Mathematical Formulation Documentation (SECONDARY CHANGE)

**File:** `doc/p2_model/p2_bi_model_ggdp.tex`, `doc/p2_model/p2_3models_formulation.tex` and `doc/whole_project_description.md`

**Locate the objective function sections** and ensure the capacity revenue term is documented as:

Where:
- $P^{\text{FCR}}_{b}$ = FCR capacity price in EUR/MW/h (not EUR/MW)
- $\Delta t_{\text{block}}$ = block duration = 4 hours

**If the documentation currently states:** "Prices are in EUR/MW per block"
**Change to:** "Prices are in EUR/MW/h (hourly rates), multiplied by block duration $\Delta b = 4$ hours"

HINT: can refer to our old model version `doc\archived_tex\chapters\3_a_modeling.tex` where $\Delta b$ is used to fix this issue. 


---
## Important Notes

### Do NOT:
- ❌ Run any tests or validation scripts (we'll do that separately)
- ❌ Modify data files (prices are correct, interpretation was wrong)
- ❌ Change energy market calculations (DA and aFRR energy are already correct)
- ❌ Alter constraint definitions (all 15 constraints are correct)
- ❌ Modify the definition of `model.db` (it's already correct at line 431)

### DO:
- ✅ Only modify the objective function calculation (one line addition of `* model.db`)
- ✅ Check if LaTeX documentation needs updating (optional but recommended)
- ✅ Add entry to implementation status log

---


## Verification Checklist (for you to confirm after making changes)

- [ ] Modified `py_script/core/optimizer.py` lines 719-723
- [ ] Added `* model.db` multiplication to capacity profit calculation
- [ ] Updated comment to say "prices in EUR/MW/h, multiply by block duration"
- [ ] Verified `model.db` parameter exists (should be defined around line 431)
- [ ] Updated LaTeX documentation if applicable
- [ ] Added entry to `IMPLEMENTATION_STATUS.md`
- [ ] Did NOT run tests or modify data files
- [ ] Code passes basic syntax check (no import needed, just visual inspection)

---

## Context for Your Reference

**Model Structure:**
- Time intervals: 15-minute granularity (96 per day)
- Capacity blocks: 4-hour duration (6 per day)
- `model.dt` = 0.25 hours (for energy markets)
- `model.db` = 4.0 hours (for capacity markets)

**Current Objective Function Components:**
1. DA Energy profit: `sum((P_DA * p_dis - P_DA * p_ch) * dt)` ✅ Correct
2. aFRR Energy profit: `sum((P_aFRR_E_pos * p_afrr_pos_e - ...) * dt)` ✅ Correct
3. Capacity profit: `sum(P_FCR * c_fcr + ...)` ❌ WRONG (missing `* db`)

**After fix:**
3. Capacity profit: `sum((P_FCR * c_fcr + ...) * db)` ✅ Correct

---

## Questions to Ask If Unclear

1. Is `model.db` already defined in the code? (Should be yes, around line 431)
2. Should I modify the revenue breakdown calculation in validation scripts? (No, just the optimizer)
3. Do we need to update test files? (No, tests will be re-run separately later)

---

**Priority:** High
**Complexity:** Low (single line change + documentation)
**Testing Required:** No (not in this task)
**Expected Time:** 10-15 minutes

Good luck! Let me know if you need any clarification on the changes.
