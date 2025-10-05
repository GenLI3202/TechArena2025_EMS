#!/usr/bin/env python3
"""
DCF Validation Script
====================

This script validates the DCF calculations by showing the step-by-step
computation for the best investment scenario (Austria C0.5_Cyc2.0).
"""

def validate_dcf_calculation():
    """
    Validate DCF calculation for Austria C0.5_Cyc2.0 configuration
    Following the methodology from investment_opt.tex
    """
    
    print("DCF Validation: Austria C0.5_Cyc2.0 Configuration")
    print("=" * 60)
    
    # Input parameters
    initial_profit_2024 = 637840  # EUR (from our analysis)
    wacc = 8.3 / 100  # 8.3% converted to decimal
    inflation = 3.30 / 100  # 3.30% converted to decimal
    capacity_mwh = 2.0  # MWh
    capex_per_kwh = 200  # EUR/kWh
    project_lifetime = 10  # years
    
    capex = capex_per_kwh * capacity_mwh * 1000  # Convert MWh to kWh
    
    print(f"Initial Parameters:")
    print(f"  Annual Profit (2024): €{initial_profit_2024:,.0f}")
    print(f"  WACC: {wacc*100:.1f}%")
    print(f"  Inflation Rate: {inflation*100:.2f}%")
    print(f"  BESS Capacity: {capacity_mwh} MWh")
    print(f"  CAPEX: €{capex:,.0f}")
    print()
    
    # Step 1: Project nominal profits using inflation
    print("Step 1: Project Nominal Profits")
    print("-" * 35)
    print(f"{'Year':<5} {'Formula':<25} {'Nominal Profit (EUR)':<20}")
    print("-" * 60)
    
    nominal_profits = []
    for year in range(1, project_lifetime + 1):
        # Formula: Π_y = Π_2024 * (1 + π)^(y-1)
        nominal_profit = initial_profit_2024 * ((1 + inflation) ** (year - 1))
        nominal_profits.append(nominal_profit)
        
        formula = f"€{initial_profit_2024:,.0f} × (1.033)^{year-1}"
        print(f"{year:<5} {formula:<25} €{nominal_profit:<19,.0f}")
    
    print()
    
    # Step 2: Calculate present values
    print("Step 2: Calculate Present Values")
    print("-" * 35)
    print(f"{'Year':<5} {'Nominal Profit':<15} {'Discount Factor':<15} {'Present Value':<15}")
    print("-" * 60)
    
    present_values = []
    total_pv = 0
    
    for year in range(1, project_lifetime + 1):
        nominal_profit = nominal_profits[year - 1]
        discount_factor = 1 / ((1 + wacc) ** year)
        present_value = nominal_profit * discount_factor
        present_values.append(present_value)
        total_pv += present_value
        
        print(f"{year:<5} €{nominal_profit:<14,.0f} {discount_factor:<15.4f} €{present_value:<14,.0f}")
    
    print("-" * 60)
    print(f"{'Total':<5} {'PV(Profits):':<15} {'€':<14}{total_pv:<15,.0f}")
    print()
    
    # Step 3: Calculate NPV and ROI
    print("Step 3: Calculate NPV and Levelized ROI")
    print("-" * 40)
    
    npv = total_pv - capex
    levelized_roi = (total_pv / (capex * project_lifetime)) * 100
    
    print(f"PV(Total Profits): €{total_pv:,.0f}")
    print(f"Initial CAPEX:     €{capex:,.0f}")
    print(f"NPV:               €{npv:,.0f}")
    print()
    print(f"Levelized ROI Calculation:")
    print(f"  = PV(Total Profits) / (CAPEX × Lifetime) × 100")
    print(f"  = €{total_pv:,.0f} / (€{capex:,.0f} × {project_lifetime}) × 100")
    print(f"  = €{total_pv:,.0f} / €{capex * project_lifetime:,.0f} × 100")
    print(f"  = {levelized_roi:.2f}%")
    print()
    
    # Validation against our analysis results
    expected_npv = 4405094
    expected_roi = 120.1
    
    print("Validation Check:")
    print("-" * 17)
    print(f"Calculated NPV:  €{npv:,.0f}")
    print(f"Expected NPV:    €{expected_npv:,.0f}")
    print(f"Difference:      €{abs(npv - expected_npv):,.0f}")
    print()
    print(f"Calculated ROI:  {levelized_roi:.2f}%")
    print(f"Expected ROI:    {expected_roi:.1f}%")
    print(f"Difference:      {abs(levelized_roi - expected_roi):.2f}%")
    
    # Check if within acceptable tolerance
    npv_tolerance = 0.05  # 5%
    roi_tolerance = 0.05  # 5%
    
    npv_match = abs(npv - expected_npv) / expected_npv < npv_tolerance
    roi_match = abs(levelized_roi - expected_roi) / expected_roi < roi_tolerance
    
    print()
    print("Validation Result:")
    print(f"NPV Match (±5%): {'✓ PASS' if npv_match else '✗ FAIL'}")
    print(f"ROI Match (±5%): {'✓ PASS' if roi_match else '✗ FAIL'}")
    
    if npv_match and roi_match:
        print("\n🎉 DCF Calculation VALIDATED!")
    else:
        print("\n⚠️  DCF Calculation needs review")
    
    return {
        'npv': npv,
        'levelized_roi': levelized_roi,
        'pv_total_profits': total_pv,
        'capex': capex,
        'nominal_profits': nominal_profits,
        'present_values': present_values
    }

def compare_countries():
    """Compare DCF metrics across different countries"""
    
    print("\n" + "=" * 60)
    print("Country Comparison Analysis")
    print("=" * 60)
    
    countries = {
        'Austria': {'wacc': 8.3, 'inflation': 3.30},
        'Germany': {'wacc': 8.3, 'inflation': 2.0},
        'Switzerland': {'wacc': 8.3, 'inflation': 0.10},
        'Czech Republic': {'wacc': 12.0, 'inflation': 2.90},
        'Hungary': {'wacc': 15.0, 'inflation': 4.60}
    }
    
    base_profit = 500000  # EUR baseline annual profit
    capacity_mwh = 2.0
    capex = 200 * capacity_mwh * 1000
    
    print(f"{'Country':<15} {'WACC':<6} {'Inflation':<10} {'NPV (EUR)':<12} {'ROI (%)':<8}")
    print("-" * 60)
    
    for country, params in countries.items():
        wacc = params['wacc'] / 100
        inflation = params['inflation'] / 100
        
        # Calculate PV of profits
        pv_total = 0
        for year in range(1, 11):
            nominal_profit = base_profit * ((1 + inflation) ** (year - 1))
            discount_factor = 1 / ((1 + wacc) ** year)
            pv_total += nominal_profit * discount_factor
        
        npv = pv_total - capex
        roi = (pv_total / (capex * 10)) * 100
        
        print(f"{country:<15} {params['wacc']:<6.1f} {params['inflation']:<10.2f} {npv:<12,.0f} {roi:<8.1f}")
    
    print("\nKey Insights:")
    print("• Lower WACC = higher NPV (better discount rate)")
    print("• Higher inflation = higher nominal profits but also higher discount effects")
    print("• Czech Republic and Hungary have high WACC (higher risk)")

if __name__ == "__main__":
    # Run DCF validation
    result = validate_dcf_calculation()
    
    # Run country comparison
    compare_countries()
    
    print(f"\n📊 Analysis complete. All calculations follow the DCF methodology")
    print(f"   specified in investment_opt.tex document.")