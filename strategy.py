import sys 
import numpy as np
import pandas as pd
from tqdm import tqdm
from utils import signal, initialize_holdings, update_row, update_fees, get_signal
from liquidity import get_liquidity_based_usd



def run_backtest_onpercent(amount_invested, swap_path, decimal_diff,swap_cost, 
                            range_percent, move_percent, gas_price, disable_costs): 

    swap_data, gas_price = signal(swap_path, gas_price, range_percent, decimal_diff)

    holdings, liquidity, current_range = initialize_holdings(swap_data, amount_invested)
    start_price = swap_data['cp'].iloc[0]
    fees_earned_sofar = [0,0]
    GAS_COST = 4.7e5

    for i,row in tqdm(swap_data.iterrows(), total=len(swap_data)):
        cp = row['cp']
        #copy current row
        hold_row = holdings.loc[i]
        hold_row = update_row(hold_row, current_range, liquidity, row)
        
        # swap fee calculation:
        ratio = liquidity/(row['liquidity_adjusted']+liquidity)
        hold_row['percentage_tick'] = ratio
        # condition to check we are in range to earn fees.
        if cp<=current_range[1] or cp>=current_range[0]:
            ratio = 0

        # calculate the fees and update the row    
        hold_row['fee_amount0']=ratio*row['fee_amount0']
        hold_row['fee_amount1']=ratio*row['fee_amount1']
        fees_earned_sofar[0] +=(hold_row['fee_amount0'])
        fees_earned_sofar[1] +=(hold_row['fee_amount1'])

        # update the fees of holdings
        hold_row = update_fees(hold_row, fees_earned_sofar, row)
        # calculate percentage_change
        percentage_change = 100*abs(cp-start_price)/start_price
        # check to rebalance
        if percentage_change > move_percent:
            current_range = [row['ub'], row['lb']]
            start_price = cp
            hold_row['rebalance'] = 1
            usd_amount = hold_row['usd']
            hold_row['gas_cost'] = gas_price.loc[i, 'price']*GAS_COST
            hold_row['swap_cost'] = usd_amount*(swap_cost)
            fees_usd=  (fees_earned_sofar[0]*row['token0_price']) + (fees_earned_sofar[1]*row['token1_price'])
            hold_row['fee_usd'] = fees_usd
            if disable_costs:
                hold_row['swap_cost'] = 0
                hold_row['gas_cost'] = 0
            usd_amount = usd_amount+fees_usd -hold_row['gas_cost'] -hold_row['swap_cost'] 
            fees_earned_sofar = [0,0]
            liquidity =  get_liquidity_based_usd(usd_amount, [row['token0_price'], row['token1_price']], *current_range)
            hold_row = update_row(hold_row, current_range, liquidity, row)

        # paste updated row
        holdings.loc[i] = hold_row
    return {'range_percent': range_percent, 'move_percent': move_percent, 'holdings': holdings}




def run_put_strategy(amount_invested, swap_path, decimal_diff,swap_cost,get_range, 
                            duration, gas_price, disable_costs, params): 

    swap_data, gas_price = get_signal(swap_path, gas_price, decimal_diff=decimal_diff, get_range=get_range, params=params)
    holdings, liquidity, current_range = initialize_holdings(swap_data, amount_invested)
    fees_earned_sofar = [0,0]
    GAS_COST = 4.7e5
    start_time = swap_data['block_timestamp'].iloc[0]
    for i,row in tqdm(swap_data.iterrows(), total=len(swap_data)):
        cp = row['cp']
        #copy current row
        hold_row = holdings.loc[i]
        hold_row = update_row(hold_row, current_range, liquidity, row)
        
        # swap fee calculation:
        ratio = liquidity/(row['liquidity_adjusted']+liquidity)
        # condition to check we are in range to earn fees.
        if cp<=current_range[1] or cp>=current_range[0]:
            ratio = 0
        hold_row['percentage_tick'] = ratio
        # calculate the fees and update the row    
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
            start_time = row['block_timestamp']
            hold_row['rebalance'] = 1
            usd_amount = hold_row['usd']
            hold_row['gas_cost'] = gas_price.loc[i, 'price']*GAS_COST
            hold_row['swap_cost'] = usd_amount*(swap_cost)
            fees_usd=  (fees_earned_sofar[0]*row['token0_price']) + (fees_earned_sofar[1]*row['token1_price'])
            hold_row['fee_usd'] = fees_usd
            if disable_costs:
                hold_row['swap_cost'] = 0
                hold_row['gas_cost'] = 0
            usd_amount = usd_amount+fees_usd -hold_row['gas_cost'] -hold_row['swap_cost'] 
            fees_earned_sofar = [0,0]
            liquidity =  get_liquidity_based_usd(usd_amount, [row['token0_price'], row['token1_price']], *current_range)
            hold_row = update_row(hold_row, current_range, liquidity, row)

        # paste updated row
        holdings.loc[i] = hold_row
        if holdings.loc[i, 'usd_with_fees']==np.nan:
            print('something problem', i)
    holdings.set_index(swap_data['block_timestamp'], inplace=True)
    return {'range_percent': params['range_percent'], 'duration': duration, 'holdings': holdings}
