"""
Generate a validation summary table showing constraint violations
"""
import json
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# Load validation results
# Get project root (3 levels up from this script)
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent.parent
results_dir = project_root / "results/model_ii_validation/july_november/decision_variables"

july_file = results_dir / "July_31days_vars.json"
november_file = results_dir / "November_30days_vars.json"

# Run validation for both files
from validate_with_user_script import validate_solution

print("Running validation...")
july_violations = validate_solution(str(july_file))
november_violations = validate_solution(str(november_file))

if july_violations is None or november_violations is None:
    print("ERROR: Validation failed")
    exit(1)

# Create summary table
data = {
    'Constraint We Commented Out': [
        'Cst-3: Simultaneous Ops',
        'Cst-8: Cross-Market (Dis+ChargeAS)',
        'Cst-8: Cross-Market (Charge+DisAS)',
        'Cst-8: Cross-Market (aFRR Pos+Neg)',
        'Cst-9: MinBid p_ch',
        'Cst-9: MinBid p_dis',
        'Cst-9: MinBid p_afrr_pos_e',
        'Cst-9: MinBid p_afrr_neg_e',
        'TOTAL',
    ],
    'July_31days_vars.json': [],
    'November_30days_vars.json': []
}

# Fill July column
data['July_31days_vars.json'] = [
    july_violations['Cst_3_Simultaneous_Ops'],
    july_violations.get('Cst_8_Cross_Market_Discharge_vs_ChargeAS',
                       july_violations.get('Cst_8_Alternative_DA_Dis_AFRR_Pos', 0)),
    july_violations.get('Cst_8_Cross_Market_Charge_vs_DischargeAS',
                       july_violations.get('Cst_8_Alternative_DA_Ch_AFRR_Neg', 0)),
    july_violations.get('Cst_8_Alternative_AFRR_Both', 0),
    july_violations['Cst_9_MinBid_p_ch'],
    july_violations['Cst_9_MinBid_p_dis'],
    july_violations['Cst_9_MinBid_p_afrr_pos_e'],
    july_violations['Cst_9_MinBid_p_afrr_neg_e'],
    sum([v for k, v in july_violations.items() if isinstance(v, int)])
]

# Fill November column
data['November_30days_vars.json'] = [
    november_violations['Cst_3_Simultaneous_Ops'],
    november_violations.get('Cst_8_Cross_Market_Discharge_vs_ChargeAS',
                           november_violations.get('Cst_8_Alternative_DA_Dis_AFRR_Pos', 0)),
    november_violations.get('Cst_8_Cross_Market_Charge_vs_DischargeAS',
                           november_violations.get('Cst_8_Alternative_DA_Ch_AFRR_Neg', 0)),
    november_violations.get('Cst_8_Alternative_AFRR_Both', 0),
    november_violations['Cst_9_MinBid_p_ch'],
    november_violations['Cst_9_MinBid_p_dis'],
    november_violations['Cst_9_MinBid_p_afrr_pos_e'],
    november_violations['Cst_9_MinBid_p_afrr_neg_e'],
    sum([v for k, v in november_violations.items() if isinstance(v, int)])
]

# Create figure
fig, ax = plt.subplots(figsize=(12, 6))
ax.axis('tight')
ax.axis('off')

# Create table
cell_text = []
for i, constraint in enumerate(data['Constraint We Commented Out']):
    july_val = data['July_31days_vars.json'][i]
    nov_val = data['November_30days_vars.json'][i]

    # Format with "Violations" suffix
    july_str = f"{july_val:,} Violations" if i < len(data['Constraint We Commented Out']) - 1 else f"{july_val:,}"
    nov_str = f"{nov_val:,} Violations" if i < len(data['Constraint We Commented Out']) - 1 else f"{nov_val:,}"

    cell_text.append([constraint, july_str, nov_str])

# Create table with colors
table = ax.table(cellText=cell_text,
                colLabels=['Constraint We Commented Out', 'July_31days_vars.json', 'November_30days_vars.json'],
                cellLoc='left',
                loc='center',
                colWidths=[0.45, 0.275, 0.275])

# Style the table
table.auto_set_font_size(False)
table.set_fontsize(10)
table.scale(1, 2.5)

# Color cells based on violations
for i in range(1, len(cell_text) + 1):
    for j in range(3):
        cell = table[(i, j)]

        if j == 0:  # Constraint name column
            cell.set_facecolor('#f0f0f0')
            cell.set_text_props(weight='bold')
        else:  # Violation columns
            # Get violation count
            val_str = cell_text[i-1][j]
            if 'Violations' in val_str:
                val = int(val_str.split()[0].replace(',', ''))
            else:
                val = int(val_str.replace(',', ''))

            # Color based on severity
            if val == 0:
                cell.set_facecolor('#d4edda')  # Green for no violations
            elif val < 50:
                cell.set_facecolor('#fff3cd')  # Yellow for minor violations
            elif val < 1000:
                cell.set_facecolor('#f8d7da')  # Light red for moderate violations
            else:
                cell.set_facecolor('#f5c6cb')  # Red for major violations

# Style header row
for j in range(3):
    cell = table[(0, j)]
    cell.set_facecolor('#4a6fa5')
    cell.set_text_props(weight='bold', color='white')

# Style total row
for j in range(3):
    cell = table[(len(cell_text), j)]
    cell.set_facecolor('#e9ecef')
    cell.set_text_props(weight='bold', size=11)

plt.title('Constraint Violation Summary - Model (ii) Full-Month Validation',
          fontsize=14, fontweight='bold', pad=20)

# Save figure
output_path = project_root / 'results/model_ii_validation/july_november/validation_summary_table.png'
plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
print(f"\nTable saved to: {output_path}")

plt.show()

# Also print text summary
print("\n" + "="*80)
print("VALIDATION SUMMARY TABLE")
print("="*80)
print(f"{'Constraint We Commented Out':<50} {'July':<20} {'November':<20}")
print("-"*80)
for i, constraint in enumerate(data['Constraint We Commented Out']):
    july_val = data['July_31days_vars.json'][i]
    nov_val = data['November_30days_vars.json'][i]
    print(f"{constraint:<50} {july_val:<20,} {nov_val:<20,}")
print("="*80)
