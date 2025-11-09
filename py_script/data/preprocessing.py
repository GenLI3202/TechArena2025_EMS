"""
This module contains functions for preprocessing market data for the EMS optimizer.
"""
import pandas as pd
import numpy as np

def preprocess_market_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Preprocesses market data to handle non-activated aFRR energy markets.

    When aFRR energy prices are 0, it signifies that the market was not activated.
    This function replaces these zero prices with NaN to prevent the optimizer
    from incorrectly treating them as free energy.

    Args:
        df: A DataFrame containing market data with columns
            'price_afrr_energy_pos' and 'price_afrr_energy_neg'.

    Returns:
        The DataFrame with zero aFRR energy prices replaced by np.nan.
    """
    df_processed = df.copy()
    
    # Replace 0 with NaN for aFRR energy prices
    if 'price_afrr_energy_pos' in df_processed.columns:
        df_processed['price_afrr_energy_pos'] = df_processed['price_afrr_energy_pos'].replace(0, np.nan)
    
    if 'price_afrr_energy_neg' in df_processed.columns:
        df_processed['price_afrr_energy_neg'] = df_processed['price_afrr_energy_neg'].replace(0, np.nan)
        
    return df_processed
