# Bug: Capacity Market Revenue Calculation Error

## Issue Summary
**Type:** Bug - Critical
**Component:** Phase II Model (i) - Objective Function
**Severity:** High (causes 4x underestimation of capacity market revenue)
**Status:** Confirmed
**Discovered:** 2025-11-08
**Affects:** BESSOptimizerModelI (all versions prior to fix)

---

## Problem Description

The objective function in Model (i) **incorrectly calculates capacity market revenue** by failing to multiply capacity prices by block duration. This results in a **4× underestimation** of FCR and aFRR capacity market revenues, causing the optimizer to systematically avoid bidding in capacity markets.

### Root Cause

**Data Unit Ambiguity:**
- Official Huawei CSV headers label capacity prices as: `"FCR Settlement price [EUR/MW]"` and `"aFRR capacity settlement prices [EUR/MW]"`
- **Missing unit component:** The correct unit should be `[EUR/MW/h]` (per megawatt per hour)
- Model implemented calculation assuming prices are "per block" when they are actually "per hour"

**Code Location:** `py_script/core/optimizer.py:719-723`

```python
# INCORRECT IMPLEMENTATION (current):
# Line 719-723
# Ancillary service capacity profit (prices are per block, so no db multiplication)
as_profit = sum(model.P_FCR[b] * model.c_fcr[b] +
                model.P_aFRR_pos[b] * model.c_afrr_pos[b] +
                model.P_aFRR_neg[b] * model.c_afrr_neg[b]
                for b in model.B)
```

The comment explicitly states "prices are per block, so no db multiplication" — this assumption is **WRONG**.

---

## Evidence from Validation Results

### Observed Behavior (Model i Seasonal Validation - Hungary):
- **aFRR Energy Revenue:** 79-95% of total profit
- **DA Energy Revenue:** 5-21% of total profit
- **FCR Capacity Revenue:** ~0.0% (effectively zero)
- **aFRR Capacity Revenue:** ~0.0% (often negative due to numerical precision: -3.39e-11)

**Expected behavior:** Capacity markets should contribute 10-30% of revenue in balanced market participation.

### Data Verification

**Sample prices from `data/phase2_processed/json/`:**

| Market | Country | Sample Price | Unit (Labeled) | Unit (Actual) | Time Interval |
|--------|---------|--------------|----------------|---------------|---------------|
| FCR | HU | 3.185 | EUR/MW | EUR/MW/h | 4-hour blocks |
| FCR | DE | 68.8 - 114.8 | EUR/MW | EUR/MW/h | 4-hour blocks |
| aFRR Cap | HU | 0.0 - 13.3 | EUR/MW | EUR/MW/h | 4-hour blocks |
| Day-Ahead | HU | 0.1 - 250 | EUR/MWh | EUR/MWh | 15-min intervals |
| aFRR Energy | HU | 0 - 3000 | EUR/MWh | EUR/MWh | 15-min intervals |

**Key observation:** Energy market prices are already time-integrated (EUR/MWh), while capacity market prices are rates (EUR/MW/h).

---

## Impact Analysis

### Revenue Underestimation Example (Hungary FCR):

**Scenario:** 1 MW FCR capacity bid, price = 3.185 EUR/MW/h, 4-hour block

**Current (WRONG) Calculation:**
```python
revenue_per_block = 3.185 EUR/MW × 1 MW = 3.185 EUR
```

**Correct Calculation:**
```python
revenue_per_block = 3.185 EUR/MW/h × 1 MW × 4 h = 12.74 EUR
```

**Error:** 4× underestimation (missing factor of `model.db = 4.0`)

### Optimizer Behavior Consequence:
With 4× underestimation, capacity markets appear economically unviable:
- Opportunity cost of reserving capacity for FCR/aFRR > perceived revenue
- Optimizer rationally chooses to focus on energy markets (DA + aFRR-E)
- Cross-market exclusivity constraints prevent capacity bidding when energy bidding is active

---

## Proposed Fix

### Code Change

**File:** `py_script/core/optimizer.py`
**Lines:** 719-723

```python
# CORRECTED IMPLEMENTATION:
# Ancillary service capacity profit (prices in EUR/MW/h, multiply by block duration)
as_profit = sum((model.P_FCR[b] * model.c_fcr[b] +
                 model.P_aFRR_pos[b] * model.c_afrr_pos[b] +
                 model.P_aFRR_neg[b] * model.c_afrr_neg[b]) * model.db
                for b in model.B)
```

**Key change:** Add `* model.db` to multiply by block duration (already defined in model at line 431).

### Updated Comment

```python
# Ancillary service capacity profit
# Prices are in EUR/MW/h (hourly rate), multiply by block duration to get total revenue
# model.db = 4.0 hours (defined at line 431)
```

---

## Validation Impact Assessment

### Expected Changes After Fix:

**Revenue Mix (Hungary, Baseline Scenario):**

| Season | Current DA % | Current aFRR-E % | Current Capacity % | Expected Capacity % (post-fix) |
|--------|--------------|------------------|--------------------|---------------------------------|
| Q1 Winter | 14.4% | 85.4% | 0.2% | 10-20% |
| Q2 Spring | 5.3% | 94.6% | 0.1% | 5-15% |
| Q3 Summer | 13.2% | 86.8% | 0.0% | 5-10% |
| Q4 Fall | 21.2% | 78.7% | 0.1% | 15-25% |

**Note:** Hungary's capacity prices are still low compared to other countries (e.g., CZ: 390-416 EUR/MW/h vs HU: 3.185 EUR/MW/h), so even with the fix, capacity contribution may remain modest for HU.

### Re-validation Required:
- [ ] Re-run seasonal validation (4 weeks × 3 scenarios = 12 tests)
- [ ] Compare revenue mix before/after fix
- [ ] Verify capacity market participation increases
- [ ] Check if cross-market exclusivity constraints become more binding

---

## Additional Notes

### Why This Bug Wasn't Caught Earlier:
1. **Unit ambiguity in source data:** Official CSV headers don't specify "/h"
2. **Comment misleading:** Code comment at line 719 reinforced incorrect assumption
3. **Parameter exists but unused:** `model.db` was correctly defined but not used in objective
4. **Validation focused on constraints:** All 15 constraints passed, but revenue distribution anomaly was not flagged as critical

### Related Components:
- Revenue breakdown calculation in validation metrics (`run_seasonal_validation.py`)
- Documentation in `doc/p2_model/p2_bi_model_ggdp.tex` (objective function formulation)
- `IMPLEMENTATION_STATUS.md` (should be updated after fix)

---

## Acceptance Criteria for Fix

- [x] Code change implements `* model.db` multiplication
- [x] Comment updated to reflect correct unit interpretation
- [ ] All 12 validation tests still pass (must-pass criteria)
- [ ] Capacity market revenue > 0 in at least 50% of test scenarios
- [ ] Total profit increases (capacity revenue adds to, not substitutes, energy revenue in some scenarios)
- [ ] Documentation updated (formulation docs, implementation status)

---

## Related Files

**Code:**
- `py_script/core/optimizer.py` (lines 719-723, 431)

**Data:**
- `data/phase2_processed/json/fcr_wide.json`
- `data/phase2_processed/json/afrr_capacity_wide.json`

**Validation:**
- `run_seasonal_validation.py`
- `results/model_i_validation/HU_seasonal/VALIDATION_REPORT.md`

**Documentation:**
- `doc/p2_model/p2_bi_model_ggdp.tex` (objective function)
- `IMPLEMENTATION_STATUS.md`

---

## Timeline

- **Discovered:** 2025-11-08 (during Model i validation review)
- **Issue Created:** 2025-11-08
- **Target Fix:** Next model iteration (before Model ii implementation)
- **Re-validation:** Required after fix

---

## Labels
`bug`, `critical`, `model-i`, `objective-function`, `phase-2`, `validation-failed`

---

## Author
Gen Li (@SoloGen)
TechArena 2025 - Round 2
