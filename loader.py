import pandas as pd
import numpy as np

# get swap data on block by block basis
def get_swap_data_per_block(path):
    out = pd.read_csv(path)
    out.BLOCK_TIMESTAMP = pd.to_datetime(out.BLOCK_TIMESTAMP) 
    fee_map = {'60': 3000, '200':10000, '10':500}
    fee = fee_map[out['POOL_NAME'].iloc[0].split(' ')[-1]]/1e6
    out = out.drop(columns=['Unnamed: 0', 'BLOCKCHAIN', 'RECIPIENT', 'SENDER','POOL_ADDRESS','POOL_NAME',
                    'TOKEN0_ADDRESS','TOKEN1_ADDRESS', 'TOKEN1_SYMBOL', 'TOKEN0_SYMBOL'])
    out = out.groupby('BLOCK_ID').agg({'LIQUIDITY_ADJUSTED': np.mean, 'TOKEN0_PRICE': np.mean, 'TOKEN1_PRICE':np.mean, 'AMOUNT0_ADJUSTED':np.sum,
                                            'AMOUNT0_USD':np.sum, 'AMOUNT1_ADJUSTED':np.sum, 'AMOUNT1_USD':np.sum, 'TICK':np.mean, 'BLOCK_TIMESTAMP': 'first'})
    out['FEE_AMOUNT0'] = fee*out['AMOUNT0_ADJUSTED'].apply(lambda x: 0 if x<0 else x)
    out['FEE_AMOUNT1'] = fee*out['AMOUNT1_ADJUSTED'].apply(lambda x: 0 if x<0 else x)
    out.columns = list(map(str.lower, out.columns))
    return out

# get price of pool on block by block basis
def get_pricing_per_block(path, decimals_diff):
    out = get_swap_data_per_block(path)
    price_data = pd.DataFrame(index=np.arange(out.index[0], out.index[-1]+1))
    price_data['tick'] = np.nan
    price_data.loc[out.index ,'tick'] = out['tick'].values
    price_data = price_data.fillna(method='ffill')
    price_data['price'] = price_data.tick.apply(lambda x: 1.0001**x/10**decimals_diff)
    return price_data

# get average gas price in wei on block by block basis 
def get_gas_price_per_block(eth_path, gas_path):
    eth_price = pd.read_csv(eth_path)
    out = eth_price.groupby(['BLOCK_ID']).TOKEN1_PRICE.mean()
    gas_price = pd.read_csv(gas_path).set_index(['BLOCK_ID'])
    out_price = pd.DataFrame(index=np.arange(gas_price.index[0], gas_price.index[-1]+1))
    out_price['price'] = np.nan
    common = gas_price[gas_price.index.isin(out.index)]
    out_price.loc[common.index, 'price'] = out.loc[common.index]*gas_price.loc[common.index, 'GAS_PRICE']*1e-18
    out_price = out_price.fillna(method='ffill').dropna()
    return out_price