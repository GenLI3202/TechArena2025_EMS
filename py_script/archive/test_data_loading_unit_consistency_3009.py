#!/usr/bin/env python3
"""
Test script to verify unit consistency fixes in market_da.py.
"""

import sys
import os
from pathlib import Path

# Add the script directory to Python path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from market_da import load_market_tables, PRICE_COL_MWH, PRICE_COL_MW
from market_da import wide_to_tidy_day_ahead, wide_to_tidy_fcr, wide_to_tidy_afrr

def test_unit_consistency():
    """Test that different market types use correct price columns."""
    print("Testing unit consistency in market data processing...")
    
    # Load market data
    data_path = script_dir.parent / "data" / "TechArena2025_data.xlsx"
    if not data_path.exists():
        print(f"Data file not found: {data_path}")
        return False
    
    try:
        # Load market tables (returns dictionary)
        tables = load_market_tables(data_path)
        day_ahead = tables['day_ahead']
        fcr = tables['fcr'] 
        afrr = tables['afrr']
        
        print(f"✓ Loaded all market tables")
        print(f"  - Day-ahead shape: {day_ahead.shape}")
        print(f"  - FCR shape: {fcr.shape}")
        print(f"  - aFRR shape: {afrr.shape}")
        
        # Convert to tidy format to test column names
        print("\nTesting tidy format conversions...")
        day_ahead_tidy = wide_to_tidy_day_ahead(day_ahead)
        fcr_tidy = wide_to_tidy_fcr(fcr)
        afrr_tidy = wide_to_tidy_afrr(afrr)
        
        # Verify day-ahead data uses EUR/MWh column
        if PRICE_COL_MWH in day_ahead_tidy.columns:
            print(f"✓ Day-ahead correctly uses {PRICE_COL_MWH} (EUR/MWh)")
        else:
            print(f"✗ Day-ahead missing {PRICE_COL_MWH} column")
            return False
        
        # Verify FCR data uses EUR/MW column
        if PRICE_COL_MW in fcr_tidy.columns:
            print(f"✓ FCR correctly uses {PRICE_COL_MW} (EUR/MW)")
        else:
            print(f"✗ FCR missing {PRICE_COL_MW} column")
            return False
        
        # Verify aFRR data uses EUR/MW column  
        if PRICE_COL_MW in afrr_tidy.columns:
            print(f"✓ aFRR correctly uses {PRICE_COL_MW} (EUR/MW)")
        else:
            print(f"✗ aFRR missing {PRICE_COL_MW} column")
            return False
        
        # Test sample values
        print("\nSample price value ranges in tidy format:")
        print(f"  Day-ahead {PRICE_COL_MWH}: min={day_ahead_tidy[PRICE_COL_MWH].min():.2f}, max={day_ahead_tidy[PRICE_COL_MWH].max():.2f}")
        print(f"  FCR {PRICE_COL_MW}: min={fcr_tidy[PRICE_COL_MW].min():.2f}, max={fcr_tidy[PRICE_COL_MW].max():.2f}")
        print(f"  aFRR {PRICE_COL_MW}: min={afrr_tidy[PRICE_COL_MW].min():.2f}, max={afrr_tidy[PRICE_COL_MW].max():.2f}")
        
        print("\n✓ All unit consistency tests passed!")
        print("  - Day-ahead prices use EUR/MWh units")
        print("  - FCR and aFRR prices use EUR/MW units")
        return True
        
    except Exception as e:
        print(f"✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_integration():
    """Test that the main model can import and use the updated market functions."""
    print("\nTesting integration with main model...")
    
    try:
        from model import BESSOptimizer
        print("✓ BESSOptimizer imported successfully")
        
        # Verify the optimizer can be instantiated
        optimizer = BESSOptimizer()
        print("✓ BESSOptimizer instance created successfully")
        
        print("✓ Integration tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Error during integration testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success1 = test_unit_consistency()
    success2 = test_integration()
    
    if success1 and success2:
        print("\n🎉 All tests passed! Unit consistency fixes are working correctly.")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
    
    sys.exit(0 if (success1 and success2) else 1)