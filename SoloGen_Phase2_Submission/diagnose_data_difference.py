"""
Diagnostic script to compare Excel vs. Parquet data loading paths.
Identifies differences that may cause optimization result discrepancies.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from py_script.core.optimizer import BESSOptimizerModelIII
from py_script.data.load_process_market_data import load_preprocessed_country_data

def compare_data_sources(country='DE_LU', test_days=3):
    """Compare data from Excel vs. Parquet loading paths."""

    print("=" * 80)
    print("DATA SOURCE COMPARISON DIAGNOSTIC")
    print("=" * 80)
    print(f"Country: {country}")
    print(f"Duration: {test_days} days ({test_days * 96} timesteps)")
    print("=" * 80)

    # 1. Load via Excel path (as in submission)
    print("\n[1/2] Loading via EXCEL path...")
    excel_path = project_root / "Input" / "TechArena2025_Phase2_data.xlsx"

    optimizer_excel = BESSOptimizerModelIII(alpha=1.0)
    full_data = optimizer_excel.load_and_preprocess_data(str(excel_path))
    data_excel = optimizer_excel.extract_country_data(full_data, country)

    # Slice to test duration
    duration_timesteps = test_days * 96
    data_excel = data_excel.iloc[:duration_timesteps].copy()
    print(f"  [OK] Loaded: {len(data_excel)} rows, {len(data_excel.columns)} columns")

    # 2. Load via Parquet path (development fast path)
    print("\n[2/2] Loading via PARQUET path...")
    preprocessed_dir = project_root / "data" / "parquet" / "preprocessed"
    data_parquet = load_preprocessed_country_data(country, data_dir=preprocessed_dir)
    data_parquet = data_parquet.iloc[:duration_timesteps].copy()
    print(f"  [OK] Loaded: {len(data_parquet)} rows, {len(data_parquet.columns)} columns")

    # 3. Compare structure
    print("\n" + "=" * 80)
    print("STRUCTURAL COMPARISON")
    print("=" * 80)

    print(f"\nRow count:")
    print(f"  Excel:   {len(data_excel)}")
    print(f"  Parquet: {len(data_parquet)}")
    print(f"  Match:   {len(data_excel) == len(data_parquet)}")

    print(f"\nColumn count:")
    print(f"  Excel:   {len(data_excel.columns)}")
    print(f"  Parquet: {len(data_parquet.columns)}")
    print(f"  Match:   {len(data_excel.columns) == len(data_parquet.columns)}")

    print(f"\nColumn names:")
    print(f"  Excel columns:   {sorted(data_excel.columns.tolist())}")
    print(f"  Parquet columns: {sorted(data_parquet.columns.tolist())}")

    excel_cols = set(data_excel.columns)
    parquet_cols = set(data_parquet.columns)

    missing_in_parquet = excel_cols - parquet_cols
    missing_in_excel = parquet_cols - excel_cols

    if missing_in_parquet:
        print(f"\n  [!] Missing in Parquet: {missing_in_parquet}")
    if missing_in_excel:
        print(f"\n  [!] Missing in Excel: {missing_in_excel}")

    common_cols = excel_cols & parquet_cols
    print(f"\n  Common columns: {len(common_cols)}")

    # 4. Compare values for common columns
    print("\n" + "=" * 80)
    print("VALUE COMPARISON (Common Columns)")
    print("=" * 80)

    differences = []

    for col in sorted(common_cols):
        excel_vals = data_excel[col]
        parquet_vals = data_parquet[col]

        # Check for NaN differences
        excel_nans = excel_vals.isna().sum()
        parquet_nans = parquet_vals.isna().sum()

        # For numeric comparison, ignore NaN positions
        excel_numeric = pd.to_numeric(excel_vals, errors='coerce')
        parquet_numeric = pd.to_numeric(parquet_vals, errors='coerce')

        # Compare where both are not NaN
        both_valid = ~(excel_numeric.isna() | parquet_numeric.isna())

        if both_valid.sum() > 0:
            excel_valid = excel_numeric[both_valid]
            parquet_valid = parquet_numeric[both_valid]

            # Check for exact equality
            exact_match = (excel_valid == parquet_valid).all()

            # Check for numerical closeness (handle floating point)
            close_match = np.allclose(excel_valid, parquet_valid, rtol=1e-9, atol=1e-12)

            max_diff = abs(excel_valid - parquet_valid).max()
            mean_diff = abs(excel_valid - parquet_valid).mean()

            if not close_match or excel_nans != parquet_nans:
                differences.append({
                    'column': col,
                    'exact_match': exact_match,
                    'close_match': close_match,
                    'excel_nans': excel_nans,
                    'parquet_nans': parquet_nans,
                    'max_diff': max_diff,
                    'mean_diff': mean_diff
                })

                print(f"\n[!] DIFFERENCE in '{col}':")
                print(f"    NaN count - Excel: {excel_nans}, Parquet: {parquet_nans}")
                print(f"    Max difference: {max_diff:.6e}")
                print(f"    Mean difference: {mean_diff:.6e}")

                # Show first few differing values
                diff_mask_series = pd.Series(~np.isclose(excel_valid, parquet_valid, rtol=1e-9, atol=1e-12), index=excel_valid.index)
                if diff_mask_series.any():
                    diff_indices = diff_mask_series[diff_mask_series].index[:5]
                    print(f"    First differing rows (index: excel, parquet):")
                    for idx in diff_indices:
                        print(f"      {idx}: {excel_valid.loc[idx]:.6f}, {parquet_valid.loc[idx]:.6f}")
        else:
            # Check if NaN patterns match
            if excel_nans != parquet_nans:
                differences.append({
                    'column': col,
                    'excel_nans': excel_nans,
                    'parquet_nans': parquet_nans,
                    'note': 'Different NaN patterns, no valid numeric values'
                })
                print(f"\n[!] DIFFERENCE in '{col}' (NaN pattern only):")
                print(f"    Excel NaN count: {excel_nans}")
                print(f"    Parquet NaN count: {parquet_nans}")

    # 5. Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    if len(differences) == 0:
        print("\n✓ NO DIFFERENCES FOUND - Data sources are identical!")
    else:
        print(f"\n✗ FOUND {len(differences)} COLUMN(S) WITH DIFFERENCES:")
        for diff in differences:
            print(f"  - {diff['column']}")

        print("\n" + "=" * 80)
        print("DIAGNOSIS")
        print("=" * 80)

        # Check specific known issues
        afrr_energy_cols = [c for c in differences if 'afrr_energy' in c['column']]
        if afrr_energy_cols:
            print("\n[POTENTIAL ISSUE] aFRR energy columns differ:")
            print("  This could be due to 0→NaN conversion differences.")
            print("  Check if parquet has pre-converted values while Excel converts on-the-fly.")

        weight_cols = [c for c in differences if 'w_afrr' in c['column']]
        if weight_cols:
            print("\n[POTENTIAL ISSUE] aFRR weight columns differ:")
            print("  This could be due to activation weight calculation differences.")
            print("  Check afrr_ev_weights_config.json vs. preprocessed data generation.")

    print("\n" + "=" * 80)

    return data_excel, data_parquet, differences


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Compare Excel vs Parquet data loading')
    parser.add_argument('--country', default='DE_LU', choices=['DE_LU', 'AT', 'CH', 'HU', 'CZ'])
    parser.add_argument('--days', type=int, default=3, help='Number of days to compare')

    args = parser.parse_args()

    data_excel, data_parquet, differences = compare_data_sources(
        country=args.country,
        test_days=args.days
    )

    # Save comparison for detailed inspection
    output_file = project_root / f"data_comparison_{args.country}.csv"
    all_cols = sorted(set(data_excel.columns) | set(data_parquet.columns))
    comparison_data = {}
    for col in all_cols:
        comparison_data[f'{col}_excel'] = data_excel[col] if col in data_excel.columns else np.nan
        comparison_data[f'{col}_parquet'] = data_parquet[col] if col in data_parquet.columns else np.nan

    comparison_df = pd.DataFrame(comparison_data)
    comparison_df.to_csv(output_file, index=False)
    print(f"\nDetailed comparison saved to: {output_file}")
