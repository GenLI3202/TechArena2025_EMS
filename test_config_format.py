"""
Quick test to verify calendar aging config format parsing
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent / 'py_script'))

from core.optimizer import BESSOptimizerModelIII

def test_calendar_config_parsing():
    """Test that the new calendar aging config format is parsed correctly."""

    print("=" * 80)
    print("Testing Calendar Aging Config Format Parsing")
    print("=" * 80)

    try:
        # Initialize optimizer (this will load and parse the config)
        optimizer = BESSOptimizerModelIII(alpha=1.0)

        print("\n[OK] Config loaded successfully!")

        # Verify extracted values
        calendar_params = optimizer.calendar_params

        print("\nExtracted Calendar Aging Parameters:")
        print(f"  Number of breakpoints: {calendar_params['num_breakpoints']}")
        print(f"  SOC breakpoints (kWh): {calendar_params['soc_breakpoints_kwh']}")
        print(f"  Cost breakpoints (EUR/hr): {calendar_params['cost_breakpoints_eur_hr']}")
        print(f"  SOC unit: {calendar_params['soc_unit']}")
        print(f"  Cost unit: {calendar_params['cost_unit']}")

        # Verify expected values
        expected_soc = [0, 1118, 2236, 3354, 4472]
        expected_cost = [1.79, 2.15, 3.58, 6.44, 10.73]

        print("\nValidation:")

        if calendar_params['soc_breakpoints_kwh'] == expected_soc:
            print("  [PASS] SOC breakpoints match expected values")
        else:
            print(f"  [FAIL] SOC mismatch! Expected {expected_soc}")
            return False

        if calendar_params['cost_breakpoints_eur_hr'] == expected_cost:
            print("  [PASS] Cost breakpoints match expected values")
        else:
            print(f"  [FAIL] Cost mismatch! Expected {expected_cost}")
            return False

        if calendar_params['num_breakpoints'] == 5:
            print("  [PASS] Correct number of breakpoints (5)")
        else:
            print(f"  [FAIL] Expected 5 breakpoints, got {calendar_params['num_breakpoints']}")
            return False

        print("\n" + "=" * 80)
        print("SUCCESS: All calendar aging config tests passed!")
        print("=" * 80)

        return True

    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_calendar_config_parsing()
    sys.exit(0 if success else 1)
