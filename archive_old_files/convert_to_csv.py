#!/usr/bin/env python3
"""
Convert Excel files to CSV format for TechArena 2025 Phase 1 submission
Creates both multi-sheet Excel files and individual CSV files per country
"""

import pandas as pd
import os

def convert_excel_to_csv():
    """Convert Excel files to CSV format, creating separate files for each country"""
    
    input_dir = 'SoloGen_TechArena2025_Phase1/output'
    countries = ['DE', 'AT', 'CH', 'HU', 'CZ']
    
    file_types = [
        'TechArena_Phase1_Configuration',
        'TechArena_Phase1_Investment', 
        'TechArena_Phase1_Operation'
    ]
    
    print("=== Converting Excel files to CSV format ===")
    
    for file_type in file_types:
        excel_file = os.path.join(input_dir, f'{file_type}.xlsx')
        
        if os.path.exists(excel_file):
            print(f"\nProcessing {file_type}.xlsx...")
            
            # Read all sheets from Excel file
            excel_data = pd.read_excel(excel_file, sheet_name=None)
            
            # Create individual CSV files for each country
            for country in countries:
                if country in excel_data:
                    csv_filename = f'{file_type}_{country}.csv'
                    csv_path = os.path.join(input_dir, csv_filename)
                    
                    # Save as CSV
                    excel_data[country].to_csv(csv_path, index=False)
                    print(f"  Created: {csv_filename}")
                else:
                    print(f"  Warning: Sheet '{country}' not found in {file_type}.xlsx")
            
            # Also create a combined CSV file with country identifier
            print(f"  Creating combined CSV file...")
            combined_data = []
            
            for country in countries:
                if country in excel_data:
                    df = excel_data[country].copy()
                    df.insert(0, 'Country', country)  # Add country column at the beginning
                    combined_data.append(df)
            
            if combined_data:
                combined_df = pd.concat(combined_data, ignore_index=True)
                combined_csv_path = os.path.join(input_dir, f'{file_type}.csv')
                combined_df.to_csv(combined_csv_path, index=False)
                print(f"  Created combined: {file_type}.csv")
        else:
            print(f"Error: {excel_file} not found")
    
    print("\n=== Conversion Complete ===")
    print("Files created in SoloGen_TechArena2025_Phase1/output/:")
    
    # List all files in output directory
    if os.path.exists(input_dir):
        files = sorted(os.listdir(input_dir))
        for file in files:
            print(f"  - {file}")

if __name__ == "__main__":
    convert_excel_to_csv()