# Archive Location Notice

## Phase 1 Files Archive

All Phase 1 development files, test scripts, and legacy code that were previously located in the `archive/` directory have been preserved in the project's git history.

**To access archived Phase 1 files:**

1. **Main Phase 1 submission code**: Branch `r1-static-battery`
   ```bash
   git checkout r1-static-battery
   ```

2. **Historical archive directory**: Available in git history before reorganization
   ```bash
   # View files from before reorganization (commit before this one)
   git log --oneline  # Find the reorganization commit
   git checkout <commit-hash-before-reorganization> -- py_script/archive/
   ```

## Archive Removal Date
- **Date**: November 1, 2025
- **Reason**: Repository cleanup and reorganization for Phase 2
- **Current branch**: `r2-with-bat-config`

## Archived Content Summary

The removed `archive/` directory contained approximately 45 files including:
- Legacy test scripts (e.g., `test_*.py`, `quick_test_*.py`)
- Old model versions (e.g., `model_3009.py`)
- Validation scripts (e.g., `validation_test_october.py`)
- Analysis tools (e.g., `investment_analysis_old.py`, `revenue_analysis.py`)
- Documentation files (e.g., `*.md` files)
- Test results (e.g., `*.json`, `*.csv` files)

All these files were development artifacts from Phase 1 and are no longer needed for Phase 2 development.

## Current Structure

The repository has been reorganized into a professional package structure. See the main `README.md` for the current organization.
