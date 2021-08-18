import numpy as np 

def get_liquidity(amountToken0, amountToken1, current_price, upper_limit, lower_limit):
    sqrC = np.sqrt(current_price)
    sqrL = np.sqrt(lower_limit)
    sqrU = np.sqrt(upper_limit)
    if current_price <= lower_limit:
        liquidity = float(amountToken0)*sqrL*sqrU/(sqrU-sqrL)
    elif current_price <= upper_limit:
        liquidity0 = float(amountToken0)*(sqrU*sqrC)/(sqrU-sqrC)
        liquidity1 = float(amountToken1)/(sqrC-sqrL)
        liquidity = min(liquidity0,liquidity1)
    else:
        liquidity = float(amountToken1)/(sqrU-sqrL)
    return liquidity


def get_amounts(liquidity, current_price, upper_limit, lower_limit):
    sqrC = np.sqrt(current_price)
    sqrL = np.sqrt(lower_limit)
    sqrU = np.sqrt(upper_limit)
    if current_price <= lower_limit:
        amountToken0 = liquidity*(sqrU-sqrL)/(sqrL*sqrU)
        amountToken1 = 0
    elif current_price <= upper_limit:
        amountToken0 = liquidity*(sqrU-sqrC)/(sqrU*sqrC)
        amountToken1 = liquidity*(sqrC-sqrL)
    else:
        amountToken0 = 0
        amountToken1 = liquidity*(sqrU-sqrL)
    
    return [amountToken0, amountToken1]


def get_liquidity_based_usd(usd_amount,  prices, upper_limit, lower_limit):
    priceToken0, priceToken1 = prices
    current_price = priceToken0/priceToken1
    sqrC = np.sqrt(current_price)
    sqrL = np.sqrt(lower_limit)
    sqrU = np.sqrt(upper_limit)

    if current_price <= lower_limit:
        liquidity = float(usd_amount/priceToken0)*sqrL*sqrU/(sqrU-sqrL)
    elif current_price <= upper_limit:
        amounts_ratio = (sqrC-sqrL)*(sqrU*sqrC)/(sqrU-sqrC)
        amount0 = float(usd_amount)/((amounts_ratio*priceToken1)+priceToken0)
        amount1 = amount0*amounts_ratio
        liquidity =  get_liquidity(amount0, amount1, current_price, upper_limit, lower_limit)
    else:
        liquidity = float(usd_amount/priceToken1)/(sqrU-sqrL)
    return liquidity 








    