#!/usr/bin/env python3
"""
Verify the investment Excel file fixes
"""

import pandas as pd
import os

def verify_investment_fixes():
    """Verify that the investment Excel file has the correct format"""
    
    file_path = r'SoloGen_TechArena2025_Phase1_test\TechArena_Phase1_Investment.xlsx'
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    
    try:
        # Read the Austria sheet
        df = pd.read_excel(file_path, sheet_name='AT')
        
        print("✅ Investment Excel File Verification")
        print(f"File: {file_path}")
        print(f"Sheet: AT (Austria)")
        print(f"Dimensions: {df.shape[0]} rows × {df.shape[1]} columns")
        print()
        
        # Check specific fixes
        print("🔍 Checking fixes:")
        
        # Fix 1: Cell B2 should be "Value"
        cell_b2_value = df.iloc[0, 1]  # Row 1 (0-indexed), Column B (1-indexed)
        print(f"1. Cell B2 (WACC Value): '{cell_b2_value}'")
        if cell_b2_value == "Value":
            print("   ✅ CORRECT: Cell B2 shows 'Value'")
        else:
            print("   ❌ ERROR: Cell B2 should show 'Value'")
        
        # Fix 2: Years should be in column A (Col1)
        print("\n2. Year placement in column A:")
        years_found = []
        for i, row in df.iterrows():
            col_a_value = str(row['Col1']).strip()
            if col_a_value.isdigit() and len(col_a_value) == 4:  # Check if it's a 4-digit year
                years_found.append((i+1, col_a_value))
        
        print(f"   Found {len(years_found)} years in column A:")
        for row_num, year in years_found:
            print(f"   - Row {row_num}: {year}")
        
        if len(years_found) >= 10:  # Should have 2023 + 10 years (2024-2033)
            print("   ✅ CORRECT: Years are in column A")
        else:
            print("   ❌ ERROR: Years should be in column A")
        
        # Show the corrected structure
        print("\n📊 Current structure:")
        print(df.head(15).to_string(index=False))
        
        return True
        
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False

if __name__ == "__main__":
    verify_investment_fixes()