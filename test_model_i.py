"""
Quick test script for Phase II Model (i): Base Model + aFRR Energy Market

This script tests the newly implemented Model (i) with a small dataset
to verify all components are working correctly.
"""

import sys
from pathlib import Path

# Add py_script to path
sys.path.insert(0, str(Path(__file__).parent / 'py_script'))

from core.optimizer import BESSOptimizerModelI
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_model_i():
    """Test Model (i) with 1 day of data"""

    logger.info("="*80)
    logger.info("Testing Phase II Model (i): Base Model + aFRR Energy Market")
    logger.info("="*80)

    # Initialize optimizer
    optimizer = BESSOptimizerModelI()

    # Load data
    data_file = "data/TechArena2025_data_tidy.jsonl"
    logger.info(f"\n1. Loading data from {data_file}")
    data = optimizer.load_and_preprocess_data(data_file)

    logger.info(f"   Data shape: {data.shape}")
    logger.info(f"   Columns: {data.columns.tolist()[:5]}...")  # Show first 5 columns

    # Check if aFRR energy data was loaded
    afrr_energy_cols = [col for col in data.columns if 'afrr_energy' in str(col)]
    logger.info(f"   aFRR energy columns found: {len(afrr_energy_cols)}")

    # Limit to 1 day for quick test
    from datetime import timedelta
    end_time = data.index[0] + timedelta(days=1)
    data_1day = data[data.index < end_time]
    logger.info(f"\n2. Limited to 1 day: {len(data_1day)} intervals")

    # Extract country data (Germany - using DE_LU for coupled market)
    logger.info("\n3. Extracting data for Germany (DE_LU)")
    country_data = optimizer.extract_country_data(data_1day, 'DE_LU')

    # Verify aFRR energy columns exist
    required_cols = ['price_day_ahead', 'price_fcr', 'price_afrr_pos', 'price_afrr_neg',
                    'price_afrr_energy_pos', 'price_afrr_energy_neg']
    missing = [col for col in required_cols if col not in country_data.columns]
    if missing:
        logger.error(f"   Missing columns: {missing}")
        return False
    else:
        logger.info(f"   ✓ All required columns present")

    # Check aFRR energy prices
    logger.info(f"   aFRR energy pos price range: [{country_data['price_afrr_energy_pos'].min():.2f}, {country_data['price_afrr_energy_pos'].max():.2f}] EUR/MWh")
    logger.info(f"   aFRR energy neg price range: [{country_data['price_afrr_energy_neg'].min():.2f}, {country_data['price_afrr_energy_neg'].max():.2f}] EUR/MWh")

    # Build and solve model
    logger.info("\n4. Building Model (i) optimization model")
    c_rate = 0.5
    daily_cycle_limit = 1.5

    model = optimizer.build_optimization_model(country_data, c_rate, daily_cycle_limit)

    # Check model statistics
    logger.info(f"   Model variables: {model.nvariables()}")
    logger.info(f"   Model constraints: {model.nconstraints()}")

    # Verify new variables exist
    logger.info("\n5. Verifying Model (i) specific variables exist:")
    model_i_vars = ['p_afrr_pos_e', 'p_afrr_neg_e', 'p_total_ch', 'p_total_dis',
                    'y_afrr_pos_e', 'y_afrr_neg_e', 'y_total_ch', 'y_total_dis']
    for var_name in model_i_vars:
        if hasattr(model, var_name):
            logger.info(f"   ✓ {var_name} exists")
        else:
            logger.error(f"   ✗ {var_name} MISSING")
            return False

    # Verify new constraints exist
    logger.info("\n6. Verifying Model (i) specific constraints exist:")
    model_i_constraints = ['total_ch_def', 'total_dis_def', 'afrr_pos_e_min_bid',
                          'total_ch_binary_link1', 'total_dis_binary_link1']
    for cst_name in model_i_constraints:
        if hasattr(model, cst_name):
            logger.info(f"   ✓ {cst_name} exists")
        else:
            logger.error(f"   ✗ {cst_name} MISSING")
            return False

    # Solve model
    logger.info("\n7. Solving Model (i)")
    solution = optimizer.solve_model(model)

    if solution['status'] in ['optimal', 'feasible']:
        logger.info(f"   ✓ Solution status: {solution['status']}")
        logger.info(f"   Objective value: {solution['objective_value']:.2f} EUR")
        logger.info(f"   Solve time: {solution['solve_time']:.2f} seconds")

        # Check if new variables have non-zero values
        logger.info("\n8. Checking Model (i) solution values:")

        # aFRR energy bids
        afrr_e_pos_sum = sum(solution.get('p_afrr_pos_e', {}).values())
        afrr_e_neg_sum = sum(solution.get('p_afrr_neg_e', {}).values())
        logger.info(f"   Total aFRR-E positive bids: {afrr_e_pos_sum:.2f} kW")
        logger.info(f"   Total aFRR-E negative bids: {afrr_e_neg_sum:.2f} kW")

        # Total power
        total_ch_sum = sum(solution.get('p_total_ch', {}).values())
        total_dis_sum = sum(solution.get('p_total_dis', {}).values())
        logger.info(f"   Total charge power sum: {total_ch_sum:.2f} kW")
        logger.info(f"   Total discharge power sum: {total_dis_sum:.2f} kW")

        logger.info("\n" + "="*80)
        logger.info("✓ Model (i) Test PASSED!")
        logger.info("="*80)
        return True
    else:
        logger.error(f"   ✗ Solution failed: {solution['status']}")
        return False

if __name__ == "__main__":
    success = test_model_i()
    sys.exit(0 if success else 1)
