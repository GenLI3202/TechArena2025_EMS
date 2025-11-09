# CRITICAL BUG FIX: aFRR Energy Market False Arbitrage

## Date: 2025-11-09
## Severity: CRITICAL
## Status: FIXED ✅

---

## Summary

**Bug:** The optimizer was treating `aFRR energy price = 0` as "free energy" and charging the battery, instead of treating it as "market not activated" (NaN).

**Root Cause:** Missing preprocessing step to convert `0 → NaN` in aFRR energy prices.

**Impact:** False arbitrage - battery would charge "for free" from inactive markets, leading to:
- Incorrect energy flows
- Overstated revenues
- Invalid optimization results

---

## Bug Details

### What Was Happening (BEFORE FIX):

```
aFRR Energy Data:
├─ price_afrr_energy_pos = 0.00 EUR/MWh (all 144 periods)
└─ price_afrr_energy_neg = 0.00 EUR/MWh (all 144 periods)
         ↓
Optimizer Interpretation: "Free energy available!"
         ↓
Optimization Result:
├─ p_afrr_neg_e = 23.92 MWh (charged battery at zero cost)
├─ p_afrr_pos_e = 0.00 MWh
└─ Revenue = €0.00 (price × energy = 0)
         ↓
Problem: Battery "charged" 23.92 MWh that doesn't exist!
```

### Key Indicators of the Bug:

1. **Non-zero bids with zero prices:** 23.92 MWh aFRR- bids despite all prices = 0
2. **False energy balance:** Battery charged from inactive market
3. **Constraint violation logic:** `no_bid_if_no_afrr_activation` constraint should have blocked this but wasn't triggered because prices were `0.0` not `NaN`

---

## Root Cause Analysis

### Code Flow (BROKEN):

```python
# optimizer.py line 1222-1224 (BEFORE FIX)
except KeyError:
    logger.warning(f"aFRR energy market data not available for {country}. Setting to 0 (Model (i) will be limited).")
    country_df['price_afrr_energy_pos'] = 0.0  # ❌ WRONG: Should be NaN
    country_df['price_afrr_energy_neg'] = 0.0  # ❌ WRONG: Should be NaN
```

### Missing Step:

The preprocessing function existed in `py_script/data/preprocessing.py`:

```python
def preprocess_market_data(df: pd.DataFrame) -> pd.DataFrame:
    """Replaces 0 → NaN for aFRR energy prices"""
    df['price_afrr_energy_pos'] = df['price_afrr_energy_pos'].replace(0, np.nan)
    df['price_afrr_energy_neg'] = df['price_afrr_energy_neg'].replace(0, np.nan)
    return df
```

**BUT IT WAS NEVER CALLED!**

---

## The Fix

### Modified Code (optimizer.py lines 1216-1232):

```python
# PHASE II Model (i): Extract aFRR energy market prices (15-min intervals)
try:
    country_df['price_afrr_energy_pos'] = data[(as_country, 'afrr_energy', 'positive')]
    country_df['price_afrr_energy_neg'] = data[(as_country, 'afrr_energy', 'negative')]
    logger.info(f"aFRR energy market data extracted for {country}")

    # CRITICAL: Preprocess aFRR energy prices (convert 0 → NaN)
    # Price = 0 means "market not activated", NOT "free energy"
    # This prevents false arbitrage opportunities
    country_df['price_afrr_energy_pos'] = country_df['price_afrr_energy_pos'].replace(0, np.nan)
    country_df['price_afrr_energy_neg'] = country_df['price_afrr_energy_neg'].replace(0, np.nan)
    logger.info(f"Preprocessed aFRR energy prices: 0 → NaN (prevents false arbitrage)")

except KeyError:
    logger.warning(f"aFRR energy market data not available for {country}. Setting to NaN (Model (i) will be limited).")
    country_df['price_afrr_energy_pos'] = np.nan  # ✅ FIXED: Now uses NaN
    country_df['price_afrr_energy_neg'] = np.nan  # ✅ FIXED: Now uses NaN
```

### Why This Works:

The constraint `no_bid_if_no_afrr_activation` (optimizer.py lines 617-629) checks for NaN:

```python
def no_bid_if_no_afrr_neg_activation_rule(model, t):
    if pd.isna(country_data['price_afrr_energy_neg'].iloc[t]):
        return model.p_afrr_neg_e[t] == 0  # Force bid to zero
    return pyo.Constraint.Skip
```

Now that prices are correctly set to `NaN`, this constraint activates and forces bids to zero.

---

## Verification Results

### BEFORE FIX (36h HU Winter):

| Metric | Value | Issue |
|--------|-------|-------|
| Objective Value | €1,025.62 | ❌ Inflated |
| aFRR+ Energy | 0.00 MWh | ✅ Correct |
| aFRR- Energy | **23.92 MWh** | ❌ **FALSE ARBITRAGE** |
| DA Discharge | 94.86 MWh | ❌ Distorted |
| DA Charge | 0.00 MWh | ❌ Should have charged |
| Total Revenue | €1,333.37 | ❌ Overstated |
| Solve Time | 25.84 sec | Slower (false feasible region) |
| Constraints | 5,112 | Missing active constraints |

### AFTER FIX (36h HU Winter):

| Metric | Value | Status |
|--------|-------|--------|
| Objective Value | €264.23 | ✅ Correct |
| aFRR+ Energy | **0.00 MWh** | ✅ **Correct** |
| aFRR- Energy | **0.00 MWh** | ✅ **Correct** |
| DA Discharge | 22.54 MWh | ✅ Realistic |
| DA Charge | 15.56 MWh | ✅ Balanced operation |
| Total Revenue | €434.75 | ✅ Realistic |
| Solve Time | 0.60 sec | ✅ Faster (correct feasible region) |
| Constraints | 5,400 | ✅ All constraints active |

### Key Changes:

1. **aFRR- false arbitrage eliminated:** 23.92 MWh → 0.00 MWh ✅
2. **Battery behavior realistic:** Now charges AND discharges in DA market
3. **Objective value corrected:** €1,025 → €264 (75% reduction)
4. **Solve time improved:** 25.8s → 0.6s (43× faster!)
5. **Constraints properly enforced:** +288 active constraints

---

## Impact Assessment

### Affected Models:
- ✅ Model I (Base + aFRR Energy)
- ✅ Model II (Model I + Cyclic Aging)
- ✅ Model III (Model II + Calendar Aging)

### Affected Scenarios:
- **All countries** when aFRR energy prices = 0 (market inactive)
- **All time periods** with stable grids (no balancing needed)
- **Particularly winter** periods (low renewable volatility)

### Data Sources Affected:
- Phase 2 parquet data (`data/phase2_processed/parquet/afrr_energy.parquet`)
- Any period where TSO didn't activate balancing markets

---

## Lessons Learned

1. **Zero vs. NaN semantic difference is critical**
   - `0` = "service available at zero price" (rare)
   - `NaN` = "service not available/not activated" (common)

2. **Preprocessing must be integrated, not optional**
   - Function existed but wasn't called
   - Need explicit integration in data loading pipeline

3. **Visualization can mislead without context**
   - Plots showed "bids" that weren't physically realized
   - Need clear distinction between "potential" and "actual" actions

4. **Constraint validation is essential**
   - The `no_bid_if_no_afrr_activation` constraint was correct
   - But it depended on NaN detection, which failed due to missing preprocessing

---

## Testing Checklist

- [x] 36h HU winter test case
- [x] Verify aFRR energy bids = 0 when prices = NaN
- [x] Verify constraint count increased (288 new constraints active)
- [x] Verify solve time improved significantly
- [x] Verify objective value realistic (not inflated)
- [x] Verify battery charges AND discharges (balanced behavior)
- [ ] Test with non-zero aFRR energy prices (future validation)
- [ ] Test all countries (DE, AT, CH, HU, CZ)
- [ ] Test all seasons (winter, spring, summer, autumn)

---

## Recommendation

**This fix should be immediately deployed to all optimization runs.**

The bug created **systematically incorrect results** whenever aFRR energy markets were inactive (which is common). All previous results using Model I/II/III should be:

1. **Re-validated** with the fix applied
2. **Compared** before/after to assess impact
3. **Documented** with corrected metrics

---

## File Modified

- `py_script/core/optimizer.py` (lines 1216-1232)
  - Added inline preprocessing: `replace(0, np.nan)`
  - Changed fallback value: `0.0` → `np.nan`
  - Added logging for transparency

---

## Status: ✅ RESOLVED

The fix has been implemented and validated. The optimizer now correctly handles inactive aFRR energy markets and prevents false arbitrage opportunities.

---

**End of Report**
