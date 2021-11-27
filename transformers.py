import numpy as np
import pandas as pd

def get_iv(swap_data:pd.DataFrame, FEE_TIER:float, DECIMALS_0: int,DECIMALS_1:int, TICK_SPACING:int):
    price = 10**(DECIMALS_1-DECIMALS_0)/(1.0001**swap_data.tick)
    volume = (abs(swap_data['amount0']) + abs(swap_data['amount1']*price))/2
    daily_volume = volume.rolling('24h').sum()
    tickA = np.ceil(swap_data['tick']/TICK_SPACING)*TICK_SPACING
    tickB = tickA - TICK_SPACING
    # get liquidity in one tick spacing
    amount1_current_price_spacing = swap_data['liquidity']*((1.0001**(tickA/2))-(1.0001**(tickB/2)))*price/10**DECIMALS_1
    IV = 2*FEE_TIER*np.sqrt(daily_volume/amount1_current_price_spacing)*np.sqrt(365)
    return IV