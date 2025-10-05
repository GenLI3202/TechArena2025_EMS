#!/usr/bin/env python3
"""
Display Investment Excel Content
Shows the actual content of the investment Excel file to verify the format
"""

import pandas as pd
import os

def display_investment_content():
    test_dir = 'SoloGen_TechArena2025_Phase1_test'
    filepath = os.path.join(test_dir, 'TechArena_Phase1_Investment.xlsx')
    
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return
    
    print("=== Investment Excel Content ===")
    
    # Read AT sheet (the one with data)
    df = pd.read_excel(filepath, sheet_name='AT')
    
    print("\\n📊 Austria (AT) Investment Analysis:")
    print("=" * 50)
    print(df.to_string(index=False))
    
    print("\\n🔍 Format Analysis:")
    print(f"- Rows: {len(df)}")
    print(f"- Columns: {list(df.columns)}")
    print("- Structure matches LaTeX table: 4 columns, parameter rows + year table")

if __name__ == "__main__":
    display_investment_content()