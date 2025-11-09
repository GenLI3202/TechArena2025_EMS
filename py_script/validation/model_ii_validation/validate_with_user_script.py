"""
User-provided validation script (modified to work with available data)
Validates Cst-3, Cst-8, and Cst-9 constraints
"""
import json
import pandas as pd
from pathlib import Path
from typing import Dict, Any
import logging

# --- CONFIGURATION ---
# Set the minimum bid sizes in kW (as per whole_project_description.md)
# DA (Cst-9) = 0.1 MW
MIN_BID_DA_KW = 100.0
# aFRR-E (Cst-9) = 0.1 MW (Note: metadata.json says 1MW, but .tex and optimizer.py use 0.1)
MIN_BID_AFRR_E_KW = 100.0
# We use a small tolerance for floating point comparisons
TOLERANCE = 1e-6

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- HELPER FUNCTION ---

def get_time_to_block_map(num_days: int) -> Dict[int, str]:
    """
    Generates a map from a 15-min time index (t) to a block index (b).
    This replicates the logic from optimizer.py's preprocessing.
    """
    time_to_block = {}
    num_intervals = num_days * 96
    for t in range(num_intervals):
        day = t // 96
        # (t % 96) gives the 15-min interval number within the day (0-95)
        # // 16 gives the 4-hour block number (0-5)
        block_of_day = (t % 96) // 16
        # Block ID (b) is 0-indexed, matching the solver output keys
        block_id = (day * 6) + block_of_day
        time_to_block[t] = str(block_id)
    return time_to_block

# --- VALIDATION FUNCTION ---

def validate_solution(json_file_path: str):
    """
    Loads a solution JSON and validates it against the
    three "commented-out" constraint categories.
    """
    logger.info(f"--- Starting Validation for: {json_file_path} ---")

    try:
        with open(json_file_path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Could not load or parse JSON file: {e}")
        return

    # --- 1. Load Data & Prepare Environment ---
    try:
        num_days = int(data.get('num_days', 0))
        if num_days == 0:
            logger.error("Could not determine 'num_days' from JSON. Aborting.")
            return

        num_intervals = num_days * 96
        logger.info(f"Validating {num_days} days ({num_intervals} intervals)...")

        # Generate the t -> b mapping for Cst-8 check
        time_to_block_map = get_time_to_block_map(num_intervals)

        # Load all necessary variables from JSON
        p_total_ch = data.get('p_total_ch', {})
        p_total_dis = data.get('p_total_dis', {})
        p_ch = data.get('p_ch', {})
        p_dis = data.get('p_dis', {})
        p_afrr_pos_e = data.get('p_afrr_pos_e', {})
        p_afrr_neg_e = data.get('p_afrr_neg_e', {})
        p_afrr_pos = data.get('p_afrr_pos', {})
        p_afrr_neg = data.get('p_afrr_neg', {})
        c_fcr = data.get('c_fcr', {})
        c_afrr_pos = data.get('c_afrr_pos', {})
        c_afrr_neg = data.get('c_afrr_neg', {})

        # Check if T-indexed variables are present
        if not p_total_ch or not p_total_dis:
            logger.error("JSON is missing required 'p_total_ch' or 'p_total_dis' data.")
            return

        # Check if capacity variables are available
        has_capacity_vars = bool(c_fcr or c_afrr_pos or c_afrr_neg)
        if not has_capacity_vars:
            logger.warning("Capacity variables (c_fcr, c_afrr_pos, c_afrr_neg) not found.")
            logger.warning("Will use alternative Cst-8 validation with time-indexed power variables.")

    except Exception as e:
        logger.error(f"Error during data preparation: {e}")
        return

    # --- 2. Initialize Violation Counters ---
    violations = {
        'Cst_3_Simultaneous_Ops': 0,
        'Cst_8_Cross_Market_Discharge_vs_ChargeAS': 0,
        'Cst_8_Cross_Market_Charge_vs_DischargeAS': 0,
        'Cst_8_Alternative_DA_Dis_AFRR_Pos': 0,  # Using time-indexed powers
        'Cst_8_Alternative_DA_Ch_AFRR_Neg': 0,   # Using time-indexed powers
        'Cst_8_Alternative_AFRR_Both': 0,         # Using time-indexed powers
        'Cst_9_MinBid_p_ch': 0,
        'Cst_9_MinBid_p_dis': 0,
        'Cst_9_MinBid_p_afrr_pos_e': 0,
        'Cst_9_MinBid_p_afrr_neg_e': 0,
    }

    # --- 3. Run Validation Loops ---
    logger.info("Running validation checks for Cst-3 and Cst-8...")

    # Loop 1: T-indexed constraints (Cst-3 & Cst-8)
    for t in range(num_intervals):
        t_str = str(t)
        b_str = time_to_block_map.get(t)

        if b_str is None:
            logger.warning(f"Could not find block for time {t}. Skipping Cst-8 check for this interval.")
            continue

        # Get power values, default to 0.0 if key is missing
        val_total_ch = p_total_ch.get(t_str, 0.0)
        val_total_dis = p_total_dis.get(t_str, 0.0)

        # Get AS capacity values, default to 0.0
        val_c_fcr = c_fcr.get(b_str, 0.0)
        val_c_afrr_pos = c_afrr_pos.get(b_str, 0.0)
        val_c_afrr_neg = c_afrr_neg.get(b_str, 0.0)

        # --- Check Cst-3: Simultaneous Operation ---
        # y_total_ch[t] + y_total_dis[t] <= 1
        # This is violated if both powers are positive
        if val_total_ch > TOLERANCE and val_total_dis > TOLERANCE:
            violations['Cst_3_Simultaneous_Ops'] += 1
            logger.warning(f"Cst-3 VIOLATION @ t={t_str}: p_total_ch={val_total_ch:.2f}, p_total_dis={val_total_dis:.2f}")

        # --- Check Cst-8: Cross-Market Exclusivity ---
        if has_capacity_vars:
            # Original validation using capacity variables
            # Rule 1: y_total_dis(t) + y_fcr(b) + y_afrr_neg(b) <= 1
            # Violated if (discharging) AND (bidding FCR or Neg-aFRR)
            if val_total_dis > TOLERANCE and (val_c_fcr > TOLERANCE or val_c_afrr_neg > TOLERANCE):
                violations['Cst_8_Cross_Market_Discharge_vs_ChargeAS'] += 1

            # Rule 2: y_total_ch(t) + y_fcr(b) + y_afrr_pos(b) <= 1
            # Violated if (charging) AND (bidding FCR or Pos-aFRR)
            if val_total_ch > TOLERANCE and (val_c_fcr > TOLERANCE or val_c_afrr_pos > TOLERANCE):
                violations['Cst_8_Cross_Market_Charge_vs_DischargeAS'] += 1
        else:
            # Alternative validation using time-indexed power variables
            val_p_dis = p_dis.get(t_str, 0.0)
            val_p_ch = p_ch.get(t_str, 0.0)
            val_p_afrr_pos = p_afrr_pos.get(t_str, 0.0)
            val_p_afrr_neg = p_afrr_neg.get(t_str, 0.0)

            # Rule: Cannot discharge in DA while providing positive aFRR
            if val_p_dis > TOLERANCE and val_p_afrr_pos > TOLERANCE:
                violations['Cst_8_Alternative_DA_Dis_AFRR_Pos'] += 1

            # Rule: Cannot charge in DA while providing negative aFRR
            if val_p_ch > TOLERANCE and val_p_afrr_neg > TOLERANCE:
                violations['Cst_8_Alternative_DA_Ch_AFRR_Neg'] += 1

            # Rule: Cannot provide both positive and negative aFRR simultaneously
            if val_p_afrr_pos > TOLERANCE and val_p_afrr_neg > TOLERANCE:
                violations['Cst_8_Alternative_AFRR_Both'] += 1

    logger.info("Running validation checks for Cst-9 (MinBid)...")

    # Loop 2: Cst-9 (MinBid) Validation
    power_vars_to_check = {
        'p_ch': (p_ch, MIN_BID_DA_KW),
        'p_dis': (p_dis, MIN_BID_DA_KW),
        'p_afrr_pos_e': (p_afrr_pos_e, MIN_BID_AFRR_E_KW),
        'p_afrr_neg_e': (p_afrr_neg_e, MIN_BID_AFRR_E_KW),
    }

    for var_name, (power_data, min_bid) in power_vars_to_check.items():
        if not power_data:
            logger.warning(f"Variable '{var_name}' not found in JSON. Skipping MinBid check.")
            continue

        count = 0
        for t in range(num_intervals):
            t_str = str(t)
            val = power_data.get(t_str, 0.0)

            # Check for violation: 0 < value < MinBid
            if (val > TOLERANCE) and (val < (min_bid - TOLERANCE)):
                count += 1
                if count <= 5:  # Show first 5 violations
                    logger.warning(f"Cst-9 MinBid VIOLATION @ t={t}: {var_name}={val:.2f} kW < {min_bid} kW")
        violations[f'Cst_9_MinBid_{var_name}'] = count

    # --- 4. Report Results ---
    logger.info(f"\n{'='*80}")
    logger.info(f"VALIDATION REPORT: {Path(json_file_path).name}")
    logger.info(f"{'='*80}")
    logger.info("Cst-3 (Simultaneous Ops) Violations: %d", violations['Cst_3_Simultaneous_Ops'])

    if has_capacity_vars:
        logger.info("Cst-8 (Cross-Market Dis+ChargeAS) Violations: %d", violations['Cst_8_Cross_Market_Discharge_vs_ChargeAS'])
        logger.info("Cst-8 (Cross-Market Charge+DisAS) Violations: %d", violations['Cst_8_Cross_Market_Charge_vs_DischargeAS'])
    else:
        logger.info("Cst-8 (DA Dis + aFRR Pos) Violations: %d", violations['Cst_8_Alternative_DA_Dis_AFRR_Pos'])
        logger.info("Cst-8 (DA Ch + aFRR Neg) Violations: %d", violations['Cst_8_Alternative_DA_Ch_AFRR_Neg'])
        logger.info("Cst-8 (aFRR Pos + Neg) Violations: %d", violations['Cst_8_Alternative_AFRR_Both'])

    logger.info("Cst-9 (MinBid) Violations:")
    logger.info(f"  p_ch: {violations['Cst_9_MinBid_p_ch']}")
    logger.info(f"  p_dis: {violations['Cst_9_MinBid_p_dis']}")
    logger.info(f"  p_afrr_pos_e: {violations['Cst_9_MinBid_p_afrr_pos_e']}")
    logger.info(f"  p_afrr_neg_e: {violations['Cst_9_MinBid_p_afrr_neg_e']}")

    total_violations = sum(violations.values())
    logger.info(f"\nTOTAL VIOLATIONS: {total_violations}")

    if total_violations == 0:
        logger.info("[PASS] All constraints satisfied!")
    else:
        logger.info(f"[FAIL] {total_violations} constraint violations detected")

    logger.info(f"{'='*80}\n")

    return violations

# --- SCRIPT EXECUTION ---
if __name__ == "__main__":
    # Define the paths to your solution files
    results_dir = Path("results/model_ii_validation/july_november/decision_variables")

    july_file = results_dir / "July_31days_vars.json"
    nov_file = results_dir / "November_30days_vars.json"

    print("="*80)
    print("USER-PROVIDED VALIDATION SCRIPT")
    print("Checking July and November full-month results")
    print("="*80)
    print()

    # Validate July
    if july_file.exists():
        july_violations = validate_solution(str(july_file))
    else:
        logger.error(f"File not found: {july_file}")

    print("\n")

    # Validate November
    if nov_file.exists():
        nov_violations = validate_solution(str(nov_file))
    else:
        logger.error(f"File not found: {nov_file}")

    # Final summary
    print("="*80)
    print("FINAL SUMMARY")
    print("="*80)
    if july_violations and nov_violations:
        total = sum(july_violations.values()) + sum(nov_violations.values())
        print(f"Total violations across both months: {total}")
        if total == 0:
            print("\n[PASS] Both July and November solutions are FULLY COMPLIANT!")
        else:
            print(f"\n[FAIL] {total} violations detected")
    print("="*80)
