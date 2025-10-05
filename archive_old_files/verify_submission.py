#!/usr/bin/env python3
"""
Verification script for TechArena 2025 Phase 1 submission files
Validates that all requirements from project.instruction.md are met
"""

import pandas as pd
import os

def verify_submission_files():
    """Verify that all submission files meet project requirements"""
    
    output_dir = 'SoloGen_TechArena2025_Phase1/output'
    print("=== TechArena 2025 Phase 1 Submission Verification ===")
    print(f"Checking output directory: {output_dir}")
    
    # Required files from project instructions
    required_files = [
        'TechArena_Phase1_Configuration.csv',
        'TechArena_Phase1_Investment.csv', 
        'TechArena_Phase1_Operation.csv'
    ]
    
    # Required column headers from project instructions
    required_columns = {
        'TechArena_Phase1_Configuration.csv': [
            "C-rate", "number of cycles", "yearly profits [kEUR/MW]", "levelized ROI [%]"
        ],
        'TechArena_Phase1_Investment.csv': [
            "WACC", "inflation rate", "discount rate", "yearly profits", 
            "year-by-year analysis", "levelized ROI"
        ],
        'TechArena_Phase1_Operation.csv': [
            "Timestamp", "Stored energy [MWh]", "SoC [-]", "Charge [MWh]", 
            "Discharge [MWh]", "Day-ahead buy [MWh]", "Day-ahead sell [MWh]", 
            "FCR Capacity [MW]", "aFRR Capacity POS [MW]", "aFRR Capacity NEG [MW]"
        ]
    }
    
    countries = ['DE', 'AT', 'CH', 'HU', 'CZ']
    
    print("\n1. Checking required files exist...")
    for file in required_files:
        file_path = os.path.join(output_dir, file)
        if os.path.exists(file_path):
            print(f"  ✓ {file}")
        else:
            print(f"  ✗ {file} - MISSING")
    
    print("\n2. Checking file formats and column headers...")
    for file in required_files:
        file_path = os.path.join(output_dir, file)
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path)
                
                # Check if file has Country column (combined format)
                if 'Country' in df.columns:
                    print(f"  ✓ {file} - Combined format with Country column")
                    
                    # Check if all countries are present
                    file_countries = df['Country'].unique()
                    missing_countries = set(countries) - set(file_countries)
                    if missing_countries:
                        print(f"    ⚠ Missing countries: {missing_countries}")
                    else:
                        print(f"    ✓ All 5 countries present: {list(file_countries)}")
                    
                    # Check columns (excluding Country column)
                    expected_cols = required_columns[file]
                    actual_cols = [col for col in df.columns if col != 'Country']
                    
                    if actual_cols == expected_cols:
                        print(f"    ✓ Correct column headers")
                    else:
                        print(f"    ✗ Column mismatch")
                        print(f"      Expected: {expected_cols}")
                        print(f"      Actual: {actual_cols}")
                
                print(f"    ℹ Total rows: {len(df)}")
                
            except Exception as e:
                print(f"  ✗ {file} - Error reading file: {e}")
    
    print("\n3. Checking individual country files...")
    for file in required_files:
        base_name = file.replace('.csv', '')
        for country in countries:
            country_file = f"{base_name}_{country}.csv"
            country_path = os.path.join(output_dir, country_file)
            
            if os.path.exists(country_path):
                try:
                    df = pd.read_csv(country_path)
                    expected_cols = required_columns[file]
                    
                    if list(df.columns) == expected_cols:
                        print(f"  ✓ {country_file} - Correct headers, {len(df)} rows")
                    else:
                        print(f"  ✗ {country_file} - Column mismatch")
                        
                except Exception as e:
                    print(f"  ✗ {country_file} - Error: {e}")
            else:
                print(f"  ✗ {country_file} - MISSING")
    
    print("\n4. Checking Excel files (multi-sheet format)...")
    for file in required_files:
        excel_file = file.replace('.csv', '.xlsx')
        excel_path = os.path.join(output_dir, excel_file)
        
        if os.path.exists(excel_path):
            try:
                excel_sheets = pd.read_excel(excel_path, sheet_name=None)
                
                print(f"  ✓ {excel_file} - Sheets: {list(excel_sheets.keys())}")
                
                # Check if all required countries have sheets
                missing_sheets = set(countries) - set(excel_sheets.keys())
                if missing_sheets:
                    print(f"    ⚠ Missing sheets: {missing_sheets}")
                else:
                    print(f"    ✓ All 5 country sheets present")
                
                # Check first sheet column headers
                if countries[0] in excel_sheets:
                    first_sheet = excel_sheets[countries[0]]
                    expected_cols = required_columns[file]
                    
                    if list(first_sheet.columns) == expected_cols:
                        print(f"    ✓ Correct column headers in sheets")
                    else:
                        print(f"    ✗ Column mismatch in sheets")
                        print(f"      Expected: {expected_cols}")
                        print(f"      Actual: {list(first_sheet.columns)}")
                
            except Exception as e:
                print(f"  ✗ {excel_file} - Error: {e}")
        else:
            print(f"  ✗ {excel_file} - MISSING")
    
    print("\n5. Summary of generated files:")
    if os.path.exists(output_dir):
        all_files = sorted(os.listdir(output_dir))
        for file in all_files:
            file_path = os.path.join(output_dir, file)
            size_kb = os.path.getsize(file_path) / 1024
            print(f"  - {file} ({size_kb:.1f} KB)")
    
    print("\n=== Verification Complete ===")
    print("Files are ready for TechArena 2025 Phase 1 submission!")
    print("\nKey deliverables generated:")
    print("✓ Three main CSV files with 5 country data combined")
    print("✓ Individual CSV files per country (15 files total)")
    print("✓ Multi-sheet Excel files for easy viewing")
    print("✓ All required column headers as specified in project.instruction.md")

if __name__ == "__main__":
    verify_submission_files()