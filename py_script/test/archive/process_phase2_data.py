#!/usr/bin/env python3
"""
Process TechArena Phase 2 Data from Excel to JSON/Parquet
==========================================================

This script loads the Phase 2 Excel data, validates it, and saves processed
outputs in both JSON (for dashboard) and Parquet (for Python analysis) formats.

Usage:
    python py_script/process_phase2_data.py

Outputs:
    - data/phase2_processed/json/*.json (for web dashboard)
    - data/phase2_processed/parquet/*.parquet (for Python analysis)
    - data/phase2_processed/metadata.json (validation report + stats)

Author: SoloGen Team
Date: October 2025
"""

from pathlib import Path
import json
import sys
from datetime import datetime
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.market_data import (
    load_phase2_market_tables,
    validate_phase2_data,
    wide_to_tidy_day_ahead,
    wide_to_tidy_fcr,
    wide_to_tidy_afrr,
)
from core.exceptions import DataLoadingError, DataValidationError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def save_to_json(df, output_path: Path):
    """Save DataFrame to JSON in records format (better for JS)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_json(output_path, orient='records', date_format='iso', indent=2)
    logger.info(f"Saved JSON: {output_path.name} ({output_path.stat().st_size / 1024:.1f} KB)")


def save_to_parquet(df, output_path: Path):
    """Save DataFrame to Parquet format (faster, smaller)."""
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(output_path, index=False, compression='snappy')
        logger.info(f"Saved Parquet: {output_path.name} ({output_path.stat().st_size / 1024:.1f} KB)")
    except ImportError:
        logger.warning("pyarrow not installed, skipping Parquet output")
    except Exception as e:
        logger.error(f"Failed to save Parquet: {e}")


def main():
    """Main data processing pipeline."""
    print("=" * 70)
    print("TechArena 2025 Phase 2 Data Processing Pipeline")
    print("=" * 70)

    # Paths
    project_root = Path(__file__).parent.parent
    excel_path = project_root / "data" / "TechArena2025_Phase2_data.xlsx"
    output_dir = project_root / "data" / "phase2_processed"
    json_dir = output_dir / "json"
    parquet_dir = output_dir / "parquet"

    # Check if input file exists
    if not excel_path.exists():
        logger.error(f"Excel file not found: {excel_path}")
        logger.error("Please ensure TechArena2025_Phase2_data.xlsx is in the data/ folder")
        sys.exit(1)

    try:
        # Step 1: Load data
        print("\nStep 1/4: Loading Phase 2 market data...")
        logger.info(f"Loading from: {excel_path}")
        tables = load_phase2_market_tables(excel_path)

        print(f"[OK] Loaded {len(tables)} market tables:")
        for market, df in tables.items():
            print(f"  - {market:15s}: {len(df):6d} rows x {len(df.columns):2d} columns")

        # Step 2: Validate data
        print("\nStep 2/4: Validating data quality...")
        validation_report = validate_phase2_data(tables)

        if not validation_report["passed"]:
            logger.error("Data validation failed!")
            for error in validation_report["errors"]:
                logger.error(f"  ERROR: {error}")

            # Save error report
            error_file = output_dir / "validation_errors.json"
            error_file.parent.mkdir(parents=True, exist_ok=True)
            with open(error_file, 'w') as f:
                json.dump(validation_report, f, indent=2)
            logger.error(f"Validation report saved to: {error_file}")

            raise DataValidationError(validation_report)

        # Log warnings
        if validation_report["warnings"]:
            print(f"\n[WARNING] {len(validation_report['warnings'])} warnings:")
            for warning in validation_report["warnings"]:
                logger.warning(f"  {warning}")

        print(f"[OK] Validation passed with {len(validation_report['warnings'])} warning(s)")

        # Step 3: Save wide format (for dashboard)
        print("\nStep 3/4: Saving data in multiple formats...")

        # 3a. Save JSON (wide format)
        print("  Saving JSON (wide format)...")
        for market, df in tables.items():
            json_file = json_dir / f"{market}_wide.json"
            save_to_json(df, json_file)

        # 3b. Save Parquet (wide format - faster loading)
        print("  Saving Parquet (wide format)...")
        for market, df in tables.items():
            parquet_file = parquet_dir / f"{market}.parquet"
            save_to_parquet(df, parquet_file)

        # Step 4: Save metadata
        print("\nStep 4/4: Generating metadata...")
        metadata = {
            "processing_timestamp": datetime.now().isoformat(),
            "source_file": str(excel_path.name),
            "data_counts": {
                market: len(df) for market, df in tables.items()
            },
            "date_range": {
                "start": tables["day_ahead"]["timestamp"].min().isoformat(),
                "end": tables["day_ahead"]["timestamp"].max().isoformat()
            },
            "columns": {
                market: list(df.columns) for market, df in tables.items()
            },
            "validation": {
                "passed": validation_report["passed"],
                "errors_count": len(validation_report["errors"]),
                "warnings_count": len(validation_report["warnings"]),
                "errors": validation_report["errors"],
                "warnings": validation_report["warnings"]
            },
            "statistics": validation_report["stats"]
        }

        metadata_path = output_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"Saved metadata: {metadata_path.name}")

        # Success summary
        print("\n" + "=" * 70)
        print("[SUCCESS] Data processing complete!")
        print("=" * 70)
        print(f"\nOutput directory: {output_dir}")
        print(f"  JSON files:    {json_dir}")
        print(f"  Parquet files: {parquet_dir}")
        print(f"  Metadata:      {metadata_path.name}")

        print(f"\nData summary:")
        print(f"  Time range: {metadata['date_range']['start'][:10]} to {metadata['date_range']['end'][:10]}")
        print(f"  Total rows:")
        for market, count in metadata['data_counts'].items():
            print(f"    {market:15s}: {count:6d}")

        if validation_report["warnings"]:
            print(f"\n[WARNING] Review {len(validation_report['warnings'])} warning(s) in metadata.json")

        print("\nNext steps:")
        print("  1. Review validation warnings in metadata.json")
        print("  2. Run visualization scripts to create McKinsey-style plots")
        print("  3. Build the dashboard using processed data")

        return 0

    except DataValidationError as e:
        print("\n" + "=" * 70)
        print("[FAILED] Data validation failed!")
        print("=" * 70)
        print(f"\nErrors: {len(e.get_errors())}")
        for i, error in enumerate(e.get_errors(), 1):
            print(f"  {i}. {error}")
        print(f"\nSee {output_dir}/validation_errors.json for details")
        return 1

    except DataLoadingError as e:
        print("\n" + "=" * 70)
        print("[FAILED] Data loading failed!")
        print("=" * 70)
        print(f"\nError: {e}")
        return 1

    except Exception as e:
        logger.exception("Unexpected error during processing")
        print("\n" + "=" * 70)
        print("[FAILED] Unexpected error!")
        print("=" * 70)
        print(f"\nError: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
