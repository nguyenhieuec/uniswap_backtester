import sys 
import numpy as np
import pandas as pd
from tqdm import tqdm
from utils import signal, initialize_holdings, update_row, update_fees, get_signal, get_multi_signal, initialize_multi_holdings
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


def run_put_strategy_multi(amount_invested, swap_path, decimal_diff,swap_cost,get_range, 
                            duration, gas_price, disable_costs, params): 

    swap_data, gas_price = get_multi_signal(swap_path, gas_price, decimal_diff=decimal_diff, get_range=get_range, params=params)
    holdings, liquidity, current_range, holdings_2, liquidity_2, current_range_2 = initialize_multi_holdings(swap_data, amount_invested)
    holdings_2['idle_usd'] = 0
    fees_earned_sofar = [0,0]
    fees_earned_sofar_2 = [0,0]
    GAS_COST = 4.7e5
    start_time = swap_data['block_timestamp'].iloc[0]
    start_price = swap_data['token1_price'].iloc[0]
    amount1, amount2 = amount_invested/2, amount_invested/2

    for i,row in tqdm(swap_data.iterrows(), total=len(swap_data)):
        cp = row['cp']
        #copy current row
        hold_row = holdings.loc[i]
        hold_row = update_row(hold_row, current_range, liquidity, row)
        
        # swap fee calculation:
        ratio = liquidity/(row['liquidity_adjusted']+liquidity)
        # condition to check we are in range to earn fees.
        if (cp<=current_range[1] or cp>=current_range[0]):
            ratio = 0
        hold_row['percentage_tick'] = ratio

        # update the fees of holdings
        # calculate the fees and update the row    
        hold_row['fee_amount0']=ratio*row['fee_amount0']
        hold_row['fee_amount1']=ratio*row['fee_amount1']
        fees_earned_sofar[0] +=(hold_row['fee_amount0'])
        fees_earned_sofar[1] +=(hold_row['fee_amount1'])
        hold_row = update_fees(hold_row, fees_earned_sofar, row)



        # repeat for position 2
        #copy current row
        hold_row_2 = holdings_2.loc[i]
        hold_row_2 = update_row(hold_row_2, current_range_2, liquidity_2, row)
        
        # swap fee calculation:
        ratio_2 = liquidity_2/(row['liquidity_adjusted']+liquidity_2)
        # condition to check we are in range to earn fees.
        if cp<=current_range_2[1] or cp>=current_range_2[0]  or amount2!=0:
            ratio_2 = 0
        hold_row_2['percentage_tick'] = ratio_2
        # calculate the fees and update the row    
        hold_row_2['fee_amount0']=ratio_2*row['fee_amount0']
        hold_row_2['fee_amount1']=ratio_2*row['fee_amount1']
        fees_earned_sofar_2[0] +=(hold_row_2['fee_amount0'])
        fees_earned_sofar_2[1] +=(hold_row_2['fee_amount1'])
        # update the fees of holdings
        hold_row_2 = update_fees(hold_row_2, fees_earned_sofar_2, row)
#         print(hold_row_2['usd_with_fees'], hold_row_2['usd'], fees_earned_sofar_2, ratio_2)
        # calculate time
        
        
        time_since = (row['block_timestamp'] - start_time)/pd.Timedelta(duration)
        if time_since >= 1:
            # update position 1
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

            # update lp position 2
            if amount2==0:
                start_price = row['token1_price']
                hold_row_2['rebalance'] = 1
                usd_amount += hold_row_2['usd']
                hold_row_2['gas_cost'] = gas_price.loc[i, 'price']*GAS_COST
                hold_row_2['swap_cost'] = usd_amount*(swap_cost)
                fees_usd_2=  (fees_earned_sofar_2[0]*row['token0_price']) + (fees_earned_sofar_2[1]*row['token1_price'])
                hold_row_2['fee_usd'] = fees_usd_2
                if disable_costs:
                    hold_row['swap_cost'] = 0
                    hold_row['gas_cost'] = 0
                usd_amount = usd_amount+fees_usd_2 -hold_row_2['gas_cost'] -hold_row_2['swap_cost'] 
                fees_earned_sofar_2 = [0,0]

                amount1, amount2 = usd_amount/2, usd_amount/2

                 # reset position 2
                current_range_2 = [row['ub1'],row['lb1']]
                liquidity_2 =  get_liquidity_based_usd(0, [row['token0_price'], row['token1_price']], *current_range_2)
                hold_row_2['usd_with_fees'] = 0
                hold_row_2 = update_row(hold_row_2, current_range_2, liquidity_2, row)
                
            else:
                amount1 = usd_amount
            # restart position 1
            liquidity =  get_liquidity_based_usd(amount1, [row['token0_price'], row['token1_price']], *current_range)
            hold_row = update_row(hold_row, current_range, liquidity, row)
            


        # rebalance condition for second position
        pct_change = 100*(row['token1_price'] - start_price)/start_price
        if pct_change < -1*params['range_percent2'] and amount2 !=0:
            lb = current_range[1]
            ub = current_range[1]*(1+params['range_percent2']/100)*(1/1.0001)
            current_range_2 = [ub, lb]
            liquidity_2 =  get_liquidity_based_usd(amount2*(1-3e-3), [row['token0_price'], row['token1_price']], *current_range_2)
            # update usd state
            hold_row_2 = update_row(hold_row_2, current_range_2, liquidity_2, row)
            hold_row_2['usd_with_fees'] = hold_row_2['usd'] 
            # move the capital to lp position
            amount2 = 0
            hold_row_2['rebalance'] = -1


        # paste updated row
        holdings.loc[i] = hold_row
        holdings_2.loc[i] = hold_row_2
        holdings_2.loc[i, 'idle_usd'] = amount2 
        if holdings.loc[i, 'usd_with_fees']==np.nan or holdings_2.loc[i, 'usd_with_fees']==np.nan:
            print('something problem', i)

    holdings.set_index(swap_data['block_timestamp'], inplace=True)
    holdings_2.set_index(swap_data['block_timestamp'], inplace=True)

    return {'range_percent': params['range_percent'], 'duration': duration, 'holdings': holdings, 'holdings_2':holdings_2}
