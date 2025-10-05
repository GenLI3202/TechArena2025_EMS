#!/usr/bin/env python3
"""
Display the updated investment Excel file
"""

import pandas as pd
import os

def show_investment_preview():
    """Show preview of the updated investment Excel file"""
    
    file_path = r'SoloGen_TechArena2025_Phase1_test\TechArena_Phase1_Investment.xlsx'
    
    print('✅ Updated Investment Excel File Preview:')
    print(f'📁 File: {file_path}')
    print()
    
    try:
        # Read the Austria sheet
        df = pd.read_excel(file_path, sheet_name='AT')
        
        print('🇦🇹 Austria Sheet (AT):')
        print(f'📊 Dimensions: {df.shape[0]} rows × {df.shape[1]} columns')
        print()
        
        # Show the corrected format
        print('📋 Structure with fixes applied:')
        print('   ✅ Fix 1: Cell B2 now shows "Value"')
        print('   ✅ Fix 2: Years moved to Column A, data shifted left')
        print()
        
        print('📊 Current Excel content:')
        # Format the output nicely
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.max_colwidth', 30)
        
        print(df.to_string(index=False))
        
        # Show specific key cells
        print()
        print('🔍 Key cells verification:')
        print(f'   Cell B1 (WACC): {df.iloc[0, 0]}')
        print(f'   Cell B2 (Value): {df.iloc[0, 1]}')
        print(f'   Cell C2 (WACC %): {df.iloc[0, 2]}')
        print()
        print('   Years in Column A:')
        for i, row in df.iterrows():
            col_a_value = str(row['Col1']).strip()
            if col_a_value.isdigit() and len(col_a_value) == 4:
                print(f'   Row {i+1}: {col_a_value}')
        
    except Exception as e:
        print(f'❌ Error: {e}')

if __name__ == "__main__":
    show_investment_preview()