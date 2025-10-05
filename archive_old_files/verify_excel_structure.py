#!/usr/bin/env python3
"""
Verify Excel File Structure
Checks if the generated Excel files have the required country sheets
"""

import pandas as pd
import os

def verify_excel_files():
    test_dir = 'SoloGen_TechArena2025_Phase1_test'
    required_countries = ['DE', 'AT', 'CH', 'HU', 'CZ']
    required_files = [
        'TechArena_Phase1_Configuration.xlsx',
        'TechArena_Phase1_Investment.xlsx', 
        'TechArena_Phase1_Operation.xlsx'
    ]
    
    print("=== Verifying Excel File Structure ===")
    
    for filename in required_files:
        filepath = os.path.join(test_dir, filename)
        if not os.path.exists(filepath):
            print(f"❌ File not found: {filepath}")
            continue
            
        print(f"\\n📁 Checking: {filename}")
        try:
            # Read Excel file and get sheet names
            excel_file = pd.ExcelFile(filepath)
            sheet_names = excel_file.sheet_names
            
            print(f"   Sheets found: {sheet_names}")
            
            # Check if all required countries are present
            for country in required_countries:
                if country in sheet_names:
                    # Try to read the sheet
                    df = pd.read_excel(filepath, sheet_name=country)
                    print(f"   ✅ {country}: {len(df)} rows, columns: {list(df.columns)}")
                else:
                    print(f"   ⚠️ {country}: Sheet missing")
                    
        except Exception as e:
            print(f"   ❌ Error reading file: {e}")
    
    print("\\n=== Verification Complete ===")

if __name__ == "__main__":
    verify_excel_files()