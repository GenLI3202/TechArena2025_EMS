# Critical Bug Fix Report: Capacity Price Corruption

**Date:** 2025-11-16
**Issue:** Capacity market prices (FCR, aFRR+, aFRR-) corrupted after January 18, 2024
**Status:** ✅ FIXED

---

## Executive Summary

A critical data corruption bug was discovered where **capacity market prices became flat/constant after January 18, 2024**, despite the source Excel file containing correct time-varying data. The bug affected all 15 submission scenarios and would have invalidated optimization results.

**Root Cause:** Inconsistent timestamp precision in Excel source data (some timestamps have milliseconds, others are exact seconds like `04:00:01`) caused misalignment between Day-Ahead and FCR/aFRR timestamps, breaking the `reindex()` operation.

**Fix:** Changed all timestamp processing to `.dt.floor('min')` to normalize to minute-level precision, eliminating second-level inconsistencies.

**Impact:** All preprocessed parquet files regenerated with clean data. Ready for re-running batch submission.

---

## Bug Details

### Symptoms
- **Before Jan 19:** Capacity prices show correct variation (6 values/day for 4-hour blocks)
- **After Jan 18:** Capacity prices become flat (1 value repeated for entire day)
- **Example:** CH Jan 19 FCR should be `[30.08, 38.00, 40.00, 24.80, 45.91, 24.03]` but was `[30.08, 30.08, ..., 30.08]`

### Root Cause Analysis

**Timestamp Precision Inconsistency in Excel Source:**

The Excel file `TechArena2025_Phase2_data.xlsx` contains timestamps with **mixed precision**:
- Some timestamps: `2024-02-06 03:45:00.999` (milliseconds)
- Other timestamps: `2024-02-06 03:45:01` (exact seconds, no milliseconds)
- Other timestamps: `2024-02-06 04:00:01` (exact seconds with +1s offset)

**Initial Attempted Fix (FAILED):**
1. Changed `.dt.round('s')` to `.dt.floor('s')`
2. **Problem:** Timestamps already at exact seconds (e.g., `04:00:01`) have nothing to floor
3. Day-Ahead at `04:00:01` still doesn't match FCR at `04:00:00`
4. User validation showed Day 37 (Feb 6) still had constant prices (all 56.0)

**Final Working Fix:**
1. Changed to `.dt.floor('min')` for **minute-level normalization**
2. `2024-02-06 04:00:01` → `2024-02-06 04:00:00`
3. `2024-02-06 04:00:00.999` → `2024-02-06 04:00:00`
4. All timestamps align at minute precision, enabling correct `reindex()` operation

**Consequence of Bug:**
- `reindex(timestamps)` failed to match timestamps due to second-level misalignment
- Created NaN gaps that `ffill()` couldn't fill properly
- Only first capacity price value of each day propagated across all 96 timesteps

### Affected Code

**File:** `py_script/data/load_process_market_data.py`

**Lines 730, 745, 757** (BEFORE):
```python
timestamps = pd.to_datetime(...).dt.round('s')  # ❌ BUG
fcr_df[TIMESTAMP_COL] = pd.to_datetime(...).dt.round('s')  # ❌ BUG
afrr_cap_df[TIMESTAMP_COL] = pd.to_datetime(...).dt.round('s')  # ❌ BUG
```

**Lines 730, 745, 757** (AFTER - FINAL FIX):
```python
timestamps = pd.to_datetime(...).dt.floor('min')  # ✅ FIXED
fcr_df[TIMESTAMP_COL] = pd.to_datetime(...).dt.floor('min')  # ✅ FIXED
afrr_cap_df[TIMESTAMP_COL] = pd.to_datetime(...).dt.floor('min')  # ✅ FIXED
```

**Why `floor('min')` works:** Normalizes ALL timestamps to minute precision, eliminating inconsistent second-level offsets from Excel source. Both `04:00:01` and `04:00:00.999` become `04:00:00`, enabling proper alignment for `reindex()`.

---

## Fix Implementation

### Step 1: Apply Code Fix

**Initial Attempt (FAILED):**
- Used `fix_timestamp_bug.py` to change `.dt.round('s')` → `.dt.floor('s')`
- Regenerated parquets
- User validation showed **bug still present** (Day 37 had constant prices)

**Final Fix (SUCCESSFUL):**
- **Manual edit** of `py_script/data/load_process_market_data.py`
- Changed lines 730, 745, 757: `.dt.floor('s')` → `.dt.floor('min')`
- Key insight: Must normalize to **minute precision** to handle inconsistent second-level offsets in Excel
- ✅ Backup files created (`.backup` extension)

### Step 2: Regenerate Preprocessed Parquet Files
**Tool:** `py_script/data/generate_preprocessed_country_data.py`

```bash
python py_script/data/generate_preprocessed_country_data.py
```

**Results (First Generation - with bug):**
- ⚠️ DE_LU: 985.0 KB (35,136 timesteps) - Generated at 16:14:37 before code fix
- ⚠️ AT: 612.6 KB (35,136 timesteps)
- ⚠️ CH: 599.4 KB (35,136 timesteps)
- ⚠️ HU: 581.4 KB (35,136 timesteps)
- ⚠️ CZ: 636.0 KB (35,136 timesteps)

**Results (Second Generation - FIXED):**
- ✅ DE_LU: 1018.1 KB (35,136 timesteps) - Generated at 16:36:35 after `floor('min')` fix
- ✅ AT: 643.3 KB (35,136 timesteps)
- ✅ CH: 632.5 KB (35,136 timesteps)
- ✅ HU: 585.5 KB (35,136 timesteps)
- ✅ CZ: 688.1 KB (35,136 timesteps)

**Note:** File sizes increased after fix due to storing correct time-varying prices instead of repeated constant values.

### Step 3: Validation
**Tool:** `validate_timestamp_fix.py`

```bash
python validate_timestamp_fix.py
```

**Results:**

| Country | Status | Details |
|---------|--------|---------|
| DE_LU | ✅ PASS | All capacity prices show correct variation (6 values/day) |
| AT | ✅ PASS | All capacity prices show correct variation (6 values/day) |
| CH | ✅ PASS | All capacity prices show correct variation (6 values/day) |
| HU | ⚠️ NOTE | Some days have legitimate constant prices in source data |
| CZ | ✅ PASS | All capacity prices show correct variation (6 values/day) |

**Note on HU:** Hungary actually has constant FCR/aFRR- prices on certain days in the original Excel file. This is **not a bug** - it's real market data. The validation script correctly identifies this as legitimate behavior (not corruption).

---

## Verification Example

### Before Fix (CORRUPTED)
```python
df = pd.read_parquet('data/parquet/preprocessed/de_lu.parquet')
day37 = df[df['day_of_year'] == 37]  # Feb 6, 2024
print(day37['price_fcr'].nunique())
# Output: 1 ❌ (BUG: only first value repeated - all 56.0)
```

### After `floor('s')` Fix (STILL CORRUPTED)
```python
df = pd.read_parquet('data/parquet/preprocessed/de_lu.parquet')
day37 = df[df['day_of_year'] == 37]  # Feb 6, 2024
print(day37['price_fcr'].nunique())
# Output: 1 ❌ (STILL BUG: all 56.0 - floor('s') didn't fix exact-second timestamps)
```

### After `floor('min')` Fix (CORRECT)
```python
df = pd.read_parquet('data/parquet/preprocessed/de_lu.parquet')
day37 = df[df['day_of_year'] == 37]  # Feb 6, 2024
print(day37['price_fcr'].nunique())
# Output: 6 ✅ (CORRECT: 6 four-hour blocks)
```

**DE_LU Feb 6 FCR Prices (Fixed):**
```
Hour 0-3:   56.00 EUR/MW
Hour 4-7:   56.40 EUR/MW
Hour 8-11:  38.40 EUR/MW
Hour 12-15: 36.00 EUR/MW
Hour 16-19: 40.31 EUR/MW
Hour 20-23: 32.11 EUR/MW
```

---

## Impact Assessment

### Files Affected
- ✅ `py_script/data/load_process_market_data.py` (fixed)
- ✅ All preprocessed parquet files (regenerated):
  - `data/parquet/preprocessed/de_lu.parquet`
  - `data/parquet/preprocessed/at.parquet`
  - `data/parquet/preprocessed/ch.parquet`
  - `data/parquet/preprocessed/hu.parquet`
  - `data/parquet/preprocessed/cz.parquet`

### Submission Impact
- ⚠️ **CRITICAL:** All 15 submission scenarios used corrupted capacity prices
- ⚠️ **ACTION REQUIRED:** Re-run `run_submission_batch.py` with clean data
- ✅ Optimizer code itself is correct (no changes needed)
- ✅ Excel loading path now produces clean data

---

## Next Steps

### Required Actions
1. ✅ **DONE:** Fix applied to `load_process_market_data.py`
2. ✅ **DONE:** Regenerate all preprocessed parquet files
3. ✅ **DONE:** Validate fix with `validate_timestamp_fix.py`
4. ⚠️ **TODO:** Re-run batch submission with clean data:
   ```bash
   python run_submission_batch.py
   ```
5. ⚠️ **TODO:** Re-analyze results with `p2d_results_ana.py`
6. ⚠️ **TODO:** Compare old (corrupted) vs new (clean) results

### Expected Changes in Results
- **Higher capacity market participation:** Optimizer can now see real price variation
- **Better profit optimization:** More opportunities for arbitrage in FCR/aFRR markets
- **Different market strategy:** Previously flat prices biased optimizer toward energy markets

---

## Files Created

1. **`fix_timestamp_bug.py`** - Automated fix application script
2. **`validate_timestamp_fix.py`** - Validation script to verify fix
3. **`BUG_FIX_REPORT.md`** - This comprehensive report
4. **Backup files:**
   - `py_script/data/load_process_market_data.py.backup` (original version)

---

## Lessons Learned

1. **Timestamp alignment is critical** - Even 1-second misalignments break pandas `reindex()` operation
2. **Check source data precision** - Excel files can have inconsistent timestamp formats (mixed milliseconds and exact seconds)
3. **Normalize to appropriate precision** - Use `floor('min')` for 15-min interval data, not `floor('s')` which doesn't fix exact-second timestamps
4. **Validate fixes thoroughly** - User validation caught that `floor('s')` didn't work, requiring deeper investigation
5. **Incremental file sizes matter** - Clean data files were larger (e.g., DE_LU: 985 KB → 1018 KB) because they stored varying prices instead of repeated constants
6. **Automate validation** - Scripts like `validate_timestamp_fix.py` catch regressions early
7. **Document fix iterations** - Recording failed attempts helps others avoid same mistakes

---

## Technical References

- **pandas.DataFrame.reindex()**: Requires exact timestamp matches (no tolerance for misalignment)
- **pandas.Series.dt.round()**: Asymmetric rounding can create misalignments when source data has mixed precision
- **pandas.Series.dt.floor('s')**: Rounds down to second precision - insufficient when source has exact-second timestamps
- **pandas.Series.dt.floor('min')**: Rounds down to minute precision - normalizes all sub-minute variations
- **Forward-fill (ffill)**: Propagates last valid value forward, but cannot fill across misaligned indices
- **Excel timestamp precision**: Can mix millisecond timestamps (`00:00.999`) with exact-second timestamps (`00:01`) in same file

---

**Report Generated:** 2025-11-16
**Author:** Claude Code (Automated Bug Fix)
**Status:** ✅ Bug Fixed & Validated
