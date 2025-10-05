"""
Quick script to extract validation results highlights
"""
import pandas as pd
import os

validation_dir = r"h:\TUM-PC\TUM_CEM_PhD\a_tech_arena_hw\TechArena2025_EMS\ValidationTest_full_20251001_223452"

print("=" * 80)
print("VALIDATION RESULTS EXTRACTION")
print("=" * 80)

# Read Investment results
inv_file = os.path.join(validation_dir, 'TechArena_Phase1_Investment.xlsx')
if os.path.exists(inv_file):
    inv = pd.read_excel(inv_file)
    
    print("\n📊 INVESTMENT ANALYSIS RESULTS\n")
    print(inv.to_string(index=False))
    
    print("\n" + "=" * 80)
    print("KEY HIGHLIGHTS")
    print("=" * 80)
    
    countries = inv['Country'].unique()
    print(f"\n✅ Countries Analyzed: {', '.join(countries)}")
    
    # Best overall scenario
    best_idx = inv['NPV [EUR]'].idxmax()
    best_npv = inv.loc[best_idx, 'NPV [EUR]']
    best_roi = inv.loc[best_idx, 'ROI [%]']
    best_country = inv.loc[best_idx, 'Country']
    best_crate = inv.loc[best_idx, 'Battery C-rate [C]']
    best_cycles = inv.loc[best_idx, 'Battery Cycling Limit [cycles/day]']
    
    print(f"\n🏆 BEST OVERALL SCENARIO:")
    print(f"   Country: {best_country}")
    print(f"   Configuration: {best_crate}C / {best_cycles} cycles/day")
    print(f"   NPV: {best_npv:,.2f} EUR")
    print(f"   ROI: {best_roi:.2f}%")
    
    # Best per country
    print(f"\n📍 BEST CONFIGURATION PER COUNTRY:")
    for country in countries:
        country_data = inv[inv['Country'] == country]
        best_country_idx = country_data['NPV [EUR]'].idxmax()
        npv = country_data.loc[best_country_idx, 'NPV [EUR]']
        roi = country_data.loc[best_country_idx, 'ROI [%]']
        crate = country_data.loc[best_country_idx, 'Battery C-rate [C]']
        cycles = country_data.loc[best_country_idx, 'Battery Cycling Limit [cycles/day]']
        print(f"   {country}: {crate}C / {cycles} cycles | NPV: {npv:,.2f} EUR | ROI: {roi:.2f}%")
    
    # Statistics
    print(f"\n📈 STATISTICS:")
    print(f"   NPV Range: {inv['NPV [EUR]'].min():,.2f} to {inv['NPV [EUR]'].max():,.2f} EUR")
    print(f"   ROI Range: {inv['ROI [%]'].min():.2f}% to {inv['ROI [%]'].max():.2f}%")
    print(f"   Average NPV: {inv['NPV [EUR]'].mean():,.2f} EUR")
    print(f"   Average ROI: {inv['ROI [%]'].mean():.2f}%")

# Read Configuration results
config_file = os.path.join(validation_dir, 'TechArena_Phase1_Configuration.xlsx')
if os.path.exists(config_file):
    config = pd.read_excel(config_file)
    
    print("\n" + "=" * 80)
    print("CONFIGURATION SUMMARY")
    print("=" * 80)
    print(f"\n✅ Total Scenarios: {len(config)}")
    print(f"✅ Countries: {config['Country'].nunique()}")
    print(f"✅ C-rate options: {sorted(config['Battery C-rate [C]'].unique())}")
    print(f"✅ Cycling limits: {sorted(config['Battery Cycling Limit [cycles/day]'].unique())}")

print("\n" + "=" * 80)
print("EXTRACTION COMPLETE")
print("=" * 80)
