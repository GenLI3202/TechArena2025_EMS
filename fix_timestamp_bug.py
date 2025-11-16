#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Automated Fix for Critical Timestamp Rounding Bug

This script fixes the capacity price corruption bug that caused flat prices after Jan 18th.

Root cause: Asymmetric timestamp rounding (round() vs floor()) broke reindex alignment.
Fix: Change all .dt.round('s') to .dt.floor('s') for consistent alignment.

Files to fix:
1. py_script/data/load_process_market_data.py (lines 729, 744, 756)
2. py_script/core/optimizer.py (lines 318-320, 334)
"""

from pathlib import Path
import re

# Project root
project_root = Path(__file__).resolve().parent

# Files to fix
files_to_fix = [
    project_root / "py_script" / "data" / "load_process_market_data.py",
    project_root / "py_script" / "core" / "optimizer.py"
]

def fix_file(file_path):
    """
    Replace all occurrences of .dt.round('s') with .dt.floor('s')
    in timestamp alignment code.
    """
    print(f"\nProcessing: {file_path.name}")

    # Read file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # Pattern 1: .dt.round('s') - main pattern
    pattern1 = r"\.dt\.round\('s'\)"
    replacement1 = ".dt.floor('s')"
    content, n1 = re.subn(pattern1, replacement1, content)

    # Pattern 2: Update comments mentioning "Round" to "Floor"
    pattern2 = r"# Round timestamps"
    replacement2 = "# Floor timestamps"
    content, n2 = re.subn(pattern2, replacement2, content)

    if content != original_content:
        # Backup original
        backup_path = file_path.with_suffix(file_path.suffix + '.backup')
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(original_content)
        print(f"  [OK] Created backup: {backup_path.name}")

        # Write fixed version
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"  [OK] Applied fixes:")
        print(f"     - Changed {n1} instances of .dt.round('s') to .dt.floor('s')")
        print(f"     - Updated {n2} comment(s)")
        return True
    else:
        print(f"  [INFO] No changes needed (already fixed or pattern not found)")
        return False

def main():
    print("=" * 80)
    print("TIMESTAMP ROUNDING BUG FIX")
    print("=" * 80)
    print("\nThis script fixes the critical capacity price corruption bug.")
    print("It will replace .dt.round('s') with .dt.floor('s') in data loading functions.\n")

    files_fixed = 0

    for file_path in files_to_fix:
        if not file_path.exists():
            print(f"\n⚠ WARNING: File not found: {file_path}")
            continue

        if fix_file(file_path):
            files_fixed += 1

    print("\n" + "=" * 80)
    print("FIX SUMMARY")
    print("=" * 80)
    print(f"Files processed: {len(files_to_fix)}")
    print(f"Files fixed:     {files_fixed}")
    print("\nBackup files created with .backup extension")
    print("\nNext steps:")
    print("1. Review the changes in the fixed files")
    print("2. Run: python py_script/data/generate_preprocessed_country_data.py")
    print("3. Run: python validate_timestamp_fix.py")
    print("=" * 80)

if __name__ == "__main__":
    main()
