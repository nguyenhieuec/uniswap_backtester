import sys
import pandas as pd
from loader  import get_swap_data_per_block, get_pricing_per_block
from liquidity import  get_amounts, get_liquidity_based_usd

def signal(swap_path, gas_price, range_percent, decimal_diff):
    swap_data = get_swap_data_per_block(swap_path)
    price_df = get_pricing_per_block(path=swap_path, decimals_diff=decimal_diff)

    lb = (price_df.price*(1 - range_percent/100)).dropna()
    ub = (price_df.price*(1 + range_percent/100)).dropna()
    # intialize the params and load the data
    swap_data = get_swap_data_per_block(swap_path)  
    common = lb[lb.index.isin(swap_data.index)]
    common = common[common.index.isin(gas_price.index)]
    swap_data = swap_data.loc[common.index]
    swap_data['lb'] = lb.loc[swap_data.index]
    swap_data['cp'] = price_df.price.loc[swap_data.index]
    swap_data['ub'] = ub.loc[swap_data.index]
    swap_data['token1_price'] = swap_data['token0_price']/swap_data['cp']
    gas_price = gas_price.loc[swap_data.index]
    return swap_data, gas_price


def put_signal(swap_path, gas_price, decimal_diff, is_complete, range_percent):
    swap_data = get_swap_data_per_block(swap_path)
    price_df = get_pricing_per_block(path=swap_path, decimals_diff=decimal_diff)
    ub = (price_df.price*(1 + range_percent/100)).dropna()
    if is_complete:
        lb = price_df.price*(1.0001)
    else:
        lb = ub/1.0001

    swap_data = get_swap_data_per_block(swap_path)  
    common = lb[lb.index.isin(swap_data.index)]
    common = common[common.index.isin(gas_price.index)]
    swap_data = swap_data.loc[common.index]
    swap_data['lb'] = lb.loc[swap_data.index]
    swap_data['cp'] = price_df.price.loc[swap_data.index]
    swap_data['ub'] = ub.loc[swap_data.index]
    swap_data['token1_price'] = swap_data['token0_price']/swap_data['cp']
    gas_price = gas_price.loc[swap_data.index]
    return swap_data, gas_price


def get_signal(swap_path, gas_price, get_range, decimal_diff, params):
    price_df = get_pricing_per_block(path=swap_path, decimals_diff=decimal_diff)
    lb, ub = get_range(price_df = price_df, params=params)
    # intialize the params and load the data
    swap_data = get_swap_data_per_block(swap_path)  
    common = lb[lb.index.isin(swap_data.index)]
    common = common[common.index.isin(gas_price.index)]
    swap_data = swap_data.loc[common.index]
    swap_data['lb'] = lb.loc[swap_data.index]
    swap_data['cp'] = price_df.price.loc[swap_data.index]
    swap_data['ub'] = ub.loc[swap_data.index]
    swap_data['token1_price'] = swap_data['token0_price']/swap_data['cp']
    gas_price = gas_price.loc[swap_data.index]
    return swap_data, gas_price


def get_multi_signal(swap_path, gas_price, get_range, decimal_diff, params):
    price_df = get_pricing_per_block(path=swap_path, decimals_diff=decimal_diff)
    lb, ub, lb1, ub1 = get_range(price_df = price_df, params=params)
    # intialize the params and load the data
    swap_data = get_swap_data_per_block(swap_path)  
    common = lb[lb.index.isin(swap_data.index)]
    common = common[common.index.isin(gas_price.index)]
    swap_data = swap_data.loc[common.index]
    swap_data['lb'] = lb.loc[swap_data.index]
    swap_data['cp'] = price_df.price.loc[swap_data.index]
    swap_data['ub'] = ub.loc[swap_data.index]
    swap_data['lb1'] = lb1.loc[swap_data.index]
    swap_data['ub1'] = ub1.loc[swap_data.index]
    swap_data['token1_price'] = swap_data['token0_price']/swap_data['cp']
    gas_price = gas_price.loc[swap_data.index]
    return swap_data, gas_price

def initialize_holdings(swap_data, amount_invested):
    # dataframe to keep track of holdings
    columns = ['rebalance', 'usd', 'gas_cost', 'swap_cost', 'percentage_tick', 'fee_usd', 
                'reserve0', 'reserve1','ub', 'lb', 'cp', 'fee_amount0', 'fee_amount1', 'liquidity', 'usd_with_fees']
    holdings = pd.DataFrame(0.0,index=swap_data.index, columns=columns, dtype=float)
    # initialize the values for starting backtest

    current_range = list(swap_data.iloc[0][['ub', 'lb']].values)
    liquidity = get_liquidity_based_usd(amount_invested, list(swap_data.iloc[0][['token0_price', 'token1_price']].values), *current_range)
    return holdings, liquidity, current_range


def initialize_multi_holdings(swap_data, amount_invested):
    # dataframe to keep track of holdings
    columns = ['rebalance', 'usd', 'gas_cost', 'swap_cost', 'percentage_tick', 'fee_usd', 
                'reserve0', 'reserve1','ub', 'lb', 'cp', 'fee_amount0', 'fee_amount1', 'liquidity', 'usd_with_fees']
    holdings_1 = pd.DataFrame(0.0,index=swap_data.index, columns=columns, dtype=float)
    holdings_2 = pd.DataFrame(0.0,index=swap_data.index, columns=columns, dtype=float)
    
    # initialize the values for starting backtest
    current_range_1 = list(swap_data.iloc[0][['ub', 'lb']].values)
    liquidity_1 = get_liquidity_based_usd(amount_invested/2, list(swap_data.iloc[0][['token0_price', 'token1_price']].values), *current_range_1)

    current_range_2 = list(swap_data.iloc[0][['ub1', 'lb1']].values)
    liquidity_2 = get_liquidity_based_usd(0, list(swap_data.iloc[0][['token0_price', 'token1_price']].values), *current_range_2)

    return holdings_1, liquidity_1, current_range_1, holdings_2, liquidity_2, current_range_2




def update_row(hold_row, current_range, liquidity, row):
    hold_row['ub'] = current_range[0]
    hold_row['lb'] = current_range[1]
    hold_row['cp'] = row['cp']
    hold_row['liquidity'] = liquidity
    # calculate the new reserves 
    hold_row['reserve0'], hold_row['reserve1'] = get_amounts(liquidity, row['cp'],*current_range)
    hold_row['usd'] = hold_row['reserve0']*row['token0_price'] + hold_row['reserve1']*row['token1_price']
    return hold_row


def update_fees(hold_row, fees_earned_sofar, row):
    hold_row['usd_with_fees'] = hold_row['usd'] + (fees_earned_sofar[0]*row['token0_price']) + (fees_earned_sofar[1]*row['token1_price'])
    return hold_row
