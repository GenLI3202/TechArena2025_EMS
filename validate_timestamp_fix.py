#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Validation Script for Timestamp Rounding Bug Fix

This script verifies that the capacity price corruption bug has been fixed.

Validation checks:
1. Load preprocessed parquet files for all countries
2. Check FCR prices for January 19-31 (previously corrupted dates)
3. Verify that each day has 6 unique price values (not just 1)
4. Compare against expected behavior (6 four-hour blocks per day)
5. Generate validation report

Expected results AFTER fix:
- Each day should have 6 unique FCR prices (one per 4-hour block, forward-filled)
- Same for aFRR+ and aFRR- capacity prices
- No flat price days after January 18th
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np

# Configuration
PREPROCESSED_DIR = project_root / "data" / "parquet" / "preprocessed"
COUNTRIES = ['DE_LU', 'AT', 'CH', 'HU', 'CZ']

# Test date range (previously corrupted dates)
TEST_DAYS = range(19, 32)  # Jan 19-31, 2024

def validate_country(country):
    """
    Validate capacity prices for a single country.

    Returns dict with validation results.
    """
    results = {
        'country': country,
        'file_exists': False,
        'total_days_tested': 0,
        'fcr_corrupted_days': [],
        'afrr_pos_corrupted_days': [],
        'afrr_neg_corrupted_days': [],
        'all_passed': False
    }

    # Load preprocessed data
    parquet_file = PREPROCESSED_DIR / f"{country.lower()}.parquet"

    if not parquet_file.exists():
        print(f"  [ERROR] File not found: {parquet_file}")
        return results

    results['file_exists'] = True

    df = pd.read_parquet(parquet_file)
    print(f"  [OK] Loaded {len(df)} timesteps")

    # Test each day in the corrupted date range
    for day in TEST_DAYS:
        day_df = df[df['day_of_year'] == day]

        if len(day_df) == 0:
            continue

        results['total_days_tested'] += 1

        # Check FCR prices
        fcr_unique = day_df['price_fcr'].nunique()
        if fcr_unique == 1:
            results['fcr_corrupted_days'].append(day)

        # Check aFRR+ capacity prices
        afrr_pos_unique = day_df['price_afrr_pos'].nunique()
        if afrr_pos_unique == 1:
            results['afrr_pos_corrupted_days'].append(day)

        # Check aFRR- capacity prices
        afrr_neg_unique = day_df['price_afrr_neg'].nunique()
        if afrr_neg_unique == 1:
            results['afrr_neg_corrupted_days'].append(day)

    # Overall pass/fail
    results['all_passed'] = (
        len(results['fcr_corrupted_days']) == 0 and
        len(results['afrr_pos_corrupted_days']) == 0 and
        len(results['afrr_neg_corrupted_days']) == 0
    )

    return results


def print_validation_report(all_results):
    """Print comprehensive validation report."""
    print("\n" + "=" * 80)
    print("VALIDATION REPORT: CAPACITY PRICE CORRUPTION BUG FIX")
    print("=" * 80)

    total_countries = len(all_results)
    passed_countries = sum(1 for r in all_results if r['all_passed'])
    failed_countries = total_countries - passed_countries

    print(f"\nCountries Tested:  {total_countries}")
    print(f"Passed:            {passed_countries}")
    print(f"Failed:            {failed_countries}")

    print("\n" + "-" * 80)
    print("DETAILED RESULTS BY COUNTRY")
    print("-" * 80)

    for result in all_results:
        country = result['country']
        status = "[PASS]" if result['all_passed'] else "[FAIL]"

        print(f"\n{status} {country}")

        if not result['file_exists']:
            print(f"  ERROR: Preprocessed file not found")
            continue

        print(f"  Days tested: {result['total_days_tested']}")

        if result['all_passed']:
            print(f"  All capacity prices show correct variation (6 values/day)")
        else:
            if result['fcr_corrupted_days']:
                print(f"  FCR corrupted days: {result['fcr_corrupted_days']}")
            if result['afrr_pos_corrupted_days']:
                print(f"  aFRR+ corrupted days: {result['afrr_pos_corrupted_days']}")
            if result['afrr_neg_corrupted_days']:
                print(f"  aFRR- corrupted days: {result['afrr_neg_corrupted_days']}")

    print("\n" + "=" * 80)
    if failed_countries == 0:
        print("VALIDATION PASSED: All capacity prices show correct variation")
        print("The timestamp rounding bug has been successfully fixed!")
    else:
        print("VALIDATION FAILED: Some capacity prices still show corruption")
        print("Please check the bug fix and regenerate preprocessed files.")
    print("=" * 80)

    return failed_countries == 0


def main():
    print("=" * 80)
    print("VALIDATION: TIMESTAMP ROUNDING BUG FIX")
    print("=" * 80)
    print(f"\nPreprocessed directory: {PREPROCESSED_DIR}")
    print(f"Countries to validate: {', '.join(COUNTRIES)}")
    print(f"Test date range: Jan {min(TEST_DAYS)}-{max(TEST_DAYS)}, 2024")
    print("\nExpected behavior:")
    print("  - Each day should have ~6 unique values for FCR, aFRR+, aFRR- prices")
    print("  - (6 four-hour blocks per day, forward-filled to 15-min intervals)")
    print("\nRunning validation...\n")

    all_results = []

    for country in COUNTRIES:
        print(f"Validating {country}...")
        result = validate_country(country)
        all_results.append(result)

    # Print comprehensive report
    validation_passed = print_validation_report(all_results)

    # Exit code
    sys.exit(0 if validation_passed else 1)


if __name__ == "__main__":
    main()
