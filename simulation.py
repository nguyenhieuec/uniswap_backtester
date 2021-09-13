import numpy as np
import pandas as pd
from tqdm import tqdm
from liquidity import get_liquidity_based_usd
from utils import initialize_holdings, update_row, update_fees


def format_prices(price, block, block_timestamp):
    prices = pd.DataFrame(index=[i for i in range(block[0], block[-1]+1)])
    prices['price'] = price
    swap_price = prices.loc[block].copy()
    swap_price['block_timestamp'] = block_timestamp
    return swap_price

def run_simulation(amount_invested, prices, decimal_diff, get_range,
                duration,  params, token_volumes, tick_percent, fee_teir): 

    lb, ub  = get_range(prices, params)
    swap_data = pd.DataFrame(index=prices.index)
    swap_data['fee_amount0'] = fee_teir*token_volumes[0]
    swap_data['fee_amount1'] = fee_teir*token_volumes[1]
    swap_data['cp'] = prices.price
    swap_data['lb'] = lb
    swap_data['ub'] = ub
    swap_data['block_timestamp'] = prices['block_timestamp']
    swap_data['token0_price'] = 1
    swap_data['token1_price'] = 1/prices.price
    
    holdings, liquidity, current_range = initialize_holdings(swap_data, amount_invested)
    start_price = swap_data['cp'].iloc[0]
    fees_earned_sofar = [0,0]
    start_time = swap_data['block_timestamp'].iloc[0]
    for i,row in tqdm(swap_data.iterrows(), total=len(swap_data)):
        cp = row['cp']
        #copy current row
        hold_row = holdings.loc[i]
        hold_row = update_row(hold_row, current_range, liquidity, row)
        
        ratio = tick_percent
        # swap fee calculation:
        if cp<=current_range[1] or cp>=current_range[0]:
            ratio = 0
        hold_row['percentage_tick'] = ratio
        hold_row['fee_amount0']=ratio*row['fee_amount0']
        hold_row['fee_amount1']=ratio*row['fee_amount1']
        fees_earned_sofar[0] +=(hold_row['fee_amount0'])
        fees_earned_sofar[1] +=(hold_row['fee_amount1'])

        # update the fees of holdings
        hold_row = update_fees(hold_row, fees_earned_sofar, row)
        # calculate time_fiff
        time_since = (row['block_timestamp'] - start_time)/pd.Timedelta(duration)
        if time_since >= 1:
            current_range = [row['ub'], row['lb']]
            start_price = cp
            start_time = row['block_timestamp']
            hold_row['rebalance'] = 1
            usd_amount = hold_row['usd']

            fees_usd=  (fees_earned_sofar[0]*row['token0_price']) + (fees_earned_sofar[1]*row['token1_price'])
            hold_row['fee_usd'] = fees_usd
            usd_amount = usd_amount+fees_usd 
            fees_earned_sofar = [0,0]
            liquidity =  get_liquidity_based_usd(usd_amount, [row['token0_price'], row['token1_price']], *current_range)
            hold_row = update_row(hold_row, current_range, liquidity, row)

        # paste updated row
        holdings.loc[i] = hold_row
        if holdings.loc[i, 'usd_with_fees']==np.nan:
            print('something problem', i)
    holdings.set_index(swap_data['block_timestamp'], inplace=True)
    return {'range_percent': params['range_percent'], 'duration': duration, 'holdings': holdings}
