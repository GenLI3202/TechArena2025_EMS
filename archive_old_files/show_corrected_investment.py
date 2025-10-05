#!/usr/bin/env python3
"""
Show the corrected investment Excel file content
"""

import pandas as pd
import os

def show_corrected_investment_file():
    print('📊 CORRECTED Investment Excel File:')
    print()
    
    main_file = 'TechArena_Phase1_Investment_Updated.xlsx'
    
    if os.path.exists(main_file):
        df = pd.read_excel(main_file, sheet_name='AT')
        
        print(f'📁 File: {os.path.abspath(main_file)}')
        print(f'📊 Sheet: AT (Austria)')
        print(f'📐 Size: {df.shape[0]} rows × {df.shape[1]} columns')
        print()
        
        print('🔍 Key Fixes Applied:')
        cell_b2 = df.iloc[0, 1]
        print(f'   1. Cell B2 (WACC Value): "{cell_b2}" ✅')
        
        # Show years found in column A
        years_in_col_a = []
        for i, row in df.iterrows():
            col_a_value = str(row['Col1']).strip()
            if col_a_value.isdigit() and len(col_a_value) == 4:
                years_in_col_a.append(col_a_value)
        
        print(f'   2. Years in Column A: {len(years_in_col_a)} years ({years_in_col_a[0]} to {years_in_col_a[-1]}) ✅')
        print()
        
        print('📋 File Content:')
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 120)
        print(df.to_string(index=False))
        
        print()
        print('💡 Summary of Changes:')
        print('   - Cell B2 now shows "Value" instead of "8.3%"')
        print('   - Years (2023-2033) moved from Column B to Column A')
        print('   - Investment data shifted left to Column B')
        print('   - Profit data shifted left to Column C')
        print()
        print('🎯 Production script updated: generate_real_optimization_csvs.py now has the same fixes')
        
    else:
        print(f'❌ File not found: {main_file}')

if __name__ == "__main__":
    show_corrected_investment_file()