# Data Pipeline Improvement Plan

**Date**: 2025-11-13
**Status**: Approved - Ready for Implementation

## Problem Statement

The current optimizer data pipeline is confusing and mixes legacy Phase 1 (JSONL) with Phase 2 (Excel/Parquet) data formats. This causes:
- Unclear data flow with multiple format conversions
- Difficulty in validation testing (must load full Excel each time)
- Disconnect between data extraction scripts and optimizer input requirements

## Solution Overview

Create a dual-path pipeline:
1. **Submission path**: Excel → optimizer (matches Huawei requirements)
2. **Validation path**: Pre-processed country parquets → optimizer (fast testing)

Both paths must produce identical results.

---

## Implementation Plan

### Current State (Already Done)
1. ✅ `load_phase2_market_tables()` in `load_process_market_data.py` loads Phase 2 Excel → returns wide-format dict
2. ✅ Wide-format market data saved to `data/parquet/*.parquet` and `data/json/*.json`

---

### Step 3: Create Preprocessed Country Data

**Directory Structure**:
```
data/
  parquet/
    # Original wide-format (existing)
    day_ahead.parquet       # Columns: timestamp, DE_LU, AT, CH, HU, CZ
    fcr.parquet             # Columns: timestamp, DE, AT, CH, HU, CZ
    afrr_capacity.parquet   # Columns: timestamp, DE_Pos, DE_Neg, AT_Pos, ...
    afrr_energy.parquet     # Columns: timestamp, DE_Pos, DE_Neg, AT_Pos, ...

    # New: Preprocessed country-specific data
    preprocessed/
      de_lu.parquet         # All 4 markets for Germany
      at.parquet            # All 4 markets for Austria
      ch.parquet            # All 4 markets for Switzerland
      hu.parquet            # All 4 markets for Hungary
      cz.parquet            # All 4 markets for Czechia
```

**Critical Notes**:
- **Germany naming**: Day-ahead uses "DE_LU", other markets use "DE"
- **aFRR energy preprocessing**: ONLY aFRR energy prices need 0→NaN conversion (price=0 means "not activated", not "free energy")
- Other markets: Keep original values including zeros

**Implementation**: Add to `load_process_market_data.py`:

```python
def save_preprocessed_country_data(
    market_tables: Dict[str, pd.DataFrame],
    output_dir: Path = Path("data/parquet/preprocessed")
) -> None:
    """Extract and save each country's preprocessed data.

    This mimics optimizer.extract_country_data() logic:
    - Extracts country-specific columns from wide format
    - Handles DE/DE_LU naming inconsistency
    - Applies 0→NaN conversion ONLY for aFRR energy prices
    - Combines all markets into single DataFrame per country

    Args:
        market_tables: Dict from load_phase2_market_tables()
        output_dir: Output directory for preprocessed files
    """


def load_preprocessed_country_data(
    country: str,
    data_dir: Path = Path("data/parquet/preprocessed")
) -> pd.DataFrame:
    """Load pre-processed country data for validation testing.

    This is a fast path that bypasses:
    - Excel loading
    - Wide-format to MultiIndex conversion
    - Country extraction

    Use this for rapid validation testing only.
    For submission, use optimizer.load_and_preprocess_data().

    Args:
        country: Country code (DE_LU, AT, CH, HU, CZ)
        data_dir: Directory containing preprocessed files

    Returns:
        DataFrame ready for optimizer.build_optimization_model()
    """
```

---

### Step 4: Update Optimizer for Submission

**Submission Flow** (matching Phase 1 structure):
```
main.py (submission script)
  ↓
  input/TechArena2025_Phase2_data.xlsx
  ↓
  optimizer.load_and_preprocess_data(xlsx_path)
  ↓
  internally: load_phase2_market_tables(xlsx_path)
  ↓
  builds MultiIndex DataFrame
  ↓
  extract_country_data(country) with aFRR-E preprocessing
  ↓
  build_optimization_model()
  ↓
  solve()
  ↓
  output/results.csv
```

**Phase 1 Submission Structure** (from Huawei instructions):
```
your_team_submission.zip
├─ main.py                 # Main execution script (REQUIRED)
├─ requirements.txt        # Python dependencies (if needed)
├─ README.md              # Documentation (RECOMMENDED)
├─ input/                 # Input data directory
│  └─ {phase_1_data_name}.xlsx
├─ [additional files/folders] # Your implementation files
└─ output/                # Output data directory
```

**Updated Optimizer Method**:
```python
def load_and_preprocess_data(self, workbook_path: Path) -> pd.DataFrame:
    """Load Phase 2 market data from Excel workbook.

    This method is designed for Huawei submission compatibility.
    It loads the official Excel workbook and converts it to the internal
    MultiIndex DataFrame format expected by extract_country_data().

    Args:
        workbook_path: Path to TechArena2025_Phase2_data.xlsx

    Returns:
        MultiIndex DataFrame with columns:
        - Level 0: country (DE_LU, AT, CH, HU, CZ)
        - Level 1: market prices (price_da, price_fcr, etc.)
    """
    from py_script.data.load_process_market_data import load_phase2_market_tables

    # Load wide-format tables
    market_tables = load_phase2_market_tables(workbook_path)

    # Convert to MultiIndex (replace existing JSONL logic)
    # ... implementation
```

**Key Changes**:
- Remove JSONL loading logic
- Use `load_phase2_market_tables()` instead
- Maintain same MultiIndex output format
- Ensure `extract_country_data()` still works identically

---

### Step 5: Validation Fast Path

**For Local Testing** (bypass Excel loading):

```python
# Example usage in validation scripts
from py_script.data.load_process_market_data import load_preprocessed_country_data

# Fast path - loads from preprocessed parquet
country_data = load_preprocessed_country_data('DE_LU')

# Use directly with optimizer
optimizer = BESSOptimizerModelIII()
optimizer.build_optimization_model(country_data)
optimizer.solve()
```

**Benefits**:
- No Excel parsing overhead
- No wide→MultiIndex→country extraction
- Direct load of final preprocessed data
- 10-100x faster for repeated testing

---

### Step 6: Cleanup Legacy Code

**After validation confirms both paths produce identical results:**

1. **Remove from `optimizer.py`**:
   - JSONL loading logic in `load_and_preprocess_data()`
   - Any Phase 1 specific code paths

2. **Remove from `load_process_market_data.py`**:
   - `load_data()` function (lines 171-191)
   - Any Phase 1 JSONL parsing utilities not used elsewhere

3. **Update documentation**:
   - `CLAUDE.md`: Remove Phase 1 data references
   - `optimizer_data_model_pipeline.md`: Update with new pipeline
   - README files: Clarify Phase 2 data requirements

---

## Implementation Order

1. ✅ Save this plan document
2. **Create preprocessing functions** in `load_process_market_data.py`:
   - `save_preprocessed_country_data()`
   - `load_preprocessed_country_data()`
   - Internal helper: `_extract_country_from_wide_tables()`
3. **Generate preprocessed files**: Run on current Phase 2 data
4. **Update `optimizer.load_and_preprocess_data()`**: Replace JSONL with Excel loading
5. **Test submission flow**: Excel → optimizer → solution
6. **Test validation flow**: Preprocessed parquet → optimizer → solution
7. **Compare results**: Verify both paths produce identical solutions
8. **Delete legacy code** and update documentation

---

## Critical Implementation Details

### Germany Country Code Mapping
- Day-ahead market: `DE_LU` (combined German-Luxembourg market)
- Other markets: `DE` (Germany only)
- Preprocessing must handle both when extracting Germany data

### aFRR Energy Zero Handling
- **ONLY aFRR energy**: Convert price=0 to NaN
- **Reason**: 0 means "market not activated", not "free energy"
- **Other markets**: Keep zeros as-is (they are valid prices)

### Data Validation
Before saving preprocessed files, verify:
- Row counts match across markets (35,040 for 15-min data)
- No unexpected NaN values (except aFRR energy activation)
- Column naming consistent with optimizer expectations
- Germany data correctly merged from DE/DE_LU sources

---

## Expected Benefits

✅ **Submission-ready**: Matches Huawei's expected input format (Excel file)
✅ **Fast validation**: Pre-processed country data for quick testing (10-100x faster)
✅ **Backward compatible**: Existing `extract_country_data()` logic preserved
✅ **Clear separation**: Submission path vs validation path well-defined
✅ **Testable**: Can verify both paths produce identical results
✅ **Maintainable**: Single source of truth for preprocessing logic
✅ **Documented**: Clear pipeline flow for future development

---

## Rollback Plan

If issues arise:
1. Keep old `load_and_preprocess_data()` as `load_and_preprocess_data_legacy()`
2. Test new implementation thoroughly in parallel
3. Only remove legacy code after 100% validation confidence
4. Git branch: `p2-data-pipeline-refactor` (can revert if needed)

---

## Testing Checklist

Before considering this done:
- [ ] Preprocessed files generated for all 5 countries
- [ ] Submission path works: Excel → optimizer → solution
- [ ] Validation path works: Parquet → optimizer → solution
- [ ] Both paths produce bit-identical results (same objective value)
- [ ] All existing validation tests still pass
- [ ] Documentation updated
- [ ] Legacy code removed
- [ ] No performance regression in submission path
- [ ] Validation path is measurably faster (>10x)

---

## Notes

- This refactor does NOT change optimization model logic
- Only changes HOW data is loaded and preprocessed
- Output solutions must be identical to current implementation
- Priority: Submission compatibility > Validation speed > Code cleanliness
