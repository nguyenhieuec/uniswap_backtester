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


def initialize_holdings(swap_data, amount_invested):
    # dataframe to keep track of holdings
    holdings = pd.DataFrame(index=swap_data.index)
    holdings['rebalance'] = 0
    holdings['usd'] = 0
    holdings['fees'] = 0
    holdings['gas_cost'] = 0
    holdings['swap_cost'] = 0
    holdings['percentage_tick'] = 0
    holdings['return_on_swap'] = 0
    holdings['fee_usd'] = 0
    holdings['reserve0'] = 0
    holdings['reserve1'] = 0
    holdings['ub'] = 0
    holdings['lb'] = 0
    holdings['cp'] = 0
    holdings['fee_amount0'] = 0
    holdings['fee_amount1'] = 0
    holdings['liquidity'] = 0
    # initialize the values for starting backtest
    current_range = [swap_data['ub'].iloc[0], swap_data['lb'].iloc[0]]
    liquidity = get_liquidity_based_usd(amount_invested, [swap_data['token0_price'].iloc[0], swap_data['token1_price'].iloc[0]], *current_range)
    reserves = get_amounts(liquidity, swap_data.cp.iloc[0], swap_data.ub.iloc[0], swap_data.lb.iloc[0])
    return holdings, liquidity, current_range, reserves

def update_row(hold_row, current_range, liquidity, row):
    hold_row['ub'] = current_range[0]
    hold_row['lb'] = current_range[1]
    hold_row['cp'] = row['cp']
    hold_row['liquidity'] = liquidity
    # calculate the new reserves 
    hold_row['reserve0'], hold_row['reserve1'] = get_amounts(liquidity, row['cp'],*current_range)
    hold_row['usd'] = hold_row['reserve0']*row['token0_price'] + hold_row['reserve1']*row['token1_price']
    return hold_row
