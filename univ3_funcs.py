import numpy as np
"""
Created on Mon Jun 14 18:53:09 2021

@author: JNP
"""



'''liquitidymath'''
'''Python library to emulate the calculations done in liquiditymath.sol of UNI_V3 peryphery contract'''

#sqrtP: format X96 = int(1.0001**(tick/2)*(2**96))
#liquidity: int
#sqrtA = price for lower tick
#sqrtB = price for upper tick
'''get_amounts function'''
#Use 'get_amounts' function to calculate amounts as a function of liquitidy and price range
def get_amount0(sqrtA,sqrtB,liquidity,decimals):
    
    if (sqrtA > sqrtB):
          (sqrtA,sqrtB)=(sqrtB,sqrtA)
    
    amount0=((liquidity*2**96*(sqrtB-sqrtA)/sqrtB/sqrtA)/10**decimals)
    
    return amount0

def get_amount1(sqrtA,sqrtB,liquidity,decimals):
    
    if (sqrtA > sqrtB):
        (sqrtA,sqrtB)=(sqrtB,sqrtA)
    
    amount1=liquidity*(sqrtB-sqrtA)/2**96/10**decimals
    
    return amount1

def get_amounts(tick,tickA,tickB,liquidity,decimal0,decimal1):

    sqrt  = int(1.0001**(tick/2)*(2**96))
    sqrtA = int(1.0001**(tickA/2)*(2**96))
    sqrtB = int(1.0001**(tickB/2)*(2**96))

    if (sqrtA > sqrtB):
        (sqrtA,sqrtB)=(sqrtB,sqrtA)

    if sqrt<=sqrtA:

        amount0 = get_amount0(sqrtA,sqrtB,liquidity,decimal0)
        return amount0,0
   
    elif sqrt<sqrtB and sqrt>sqrtA:
        amount0 = get_amount0(sqrt,sqrtB,liquidity,decimal0)
        amount1 = get_amount1(sqrtA,sqrt,liquidity,decimal1)
        return amount0,amount1
    
    else:
        amount1=get_amount1(sqrtA,sqrtB,liquidity,decimal1)
        return 0,amount1

'''get token amounts relation'''
#Use this formula to calculate amount of t0 based on amount of t1 (required before calculate liquidity)
#relation = t1/t0      
def amounts_relation (tick,tickA,tickB,decimals0,decimals1):
    
    sqrt=(1.0001**tick/10**(decimals1-decimals0))**(1/2)
    sqrtA=(1.0001**tickA/10**(decimals1-decimals0))**(1/2)
    sqrtB=(1.0001**tickB/10**(decimals1-decimals0))**(1/2)
    
    if sqrt==sqrtA or sqrt==sqrtB:
        relation=0
#         print("There is 0 tokens on one side")

    relation=(sqrt-sqrtA)/((1/sqrt)-(1/sqrtB))     
    return relation       



'''get_liquidity function'''
#Use 'get_liquidity' function to calculate liquidity as a function of amounts and price range
def get_liquidity0(sqrtA,sqrtB,amount0,decimals):
    
    if (sqrtA > sqrtB):
          (sqrtA,sqrtB)=(sqrtB,sqrtA)
    
    liquidity = int(amount0/((2**96*(sqrtB-sqrtA)/sqrtB/sqrtA)/10**decimals))
    return liquidity

def get_liquidity1(sqrtA,sqrtB,amount1,decimals):
    
    if (sqrtA > sqrtB):
        (sqrtA,sqrtB)=(sqrtB,sqrtA)
    
    liquidity = int(amount1/((sqrtB-sqrtA)/2**96/10**decimals))
    return liquidity

def get_liquidity(tick,tickA,tickB,amount0,amount1,decimal0,decimal1):
    
        sqrt  = int(1.0001**(tick/2)*(2**96))
        sqrtA = int(1.0001**(tickA/2)*(2**96))
        sqrtB = int(1.0001**(tickB/2)*(2**96))
        
        if (sqrtA > sqrtB):
            (sqrtA,sqrtB)=(sqrtB,sqrtA)
    
        if sqrt<=sqrtA:
            liquidity0=get_liquidity0(sqrtA,sqrtB,amount0,decimal0)            
            return liquidity0        
        elif sqrt<sqrtB and sqrt>sqrtA:
            liquidity0 = get_liquidity0(sqrt,sqrtB,amount0,decimal0)
            
            liquidity1 = get_liquidity1(sqrtA,sqrt,amount1,decimal1)
            
            liquidity  = liquidity0 if liquidity0<liquidity1 else liquidity1
            return liquidity
        else:
            liquidity1 = get_liquidity1(sqrtA,sqrtB,amount1,decimal1)
            return liquidity1


def swap_tokens(amount0, amount1, lower_tick, upper_tick, current_tick, decimal_adjustment):
    token0, token1  = 0.0, 0.0
    price = decimal_adjustment/(1.0001**current_tick)
    total_amount = amount0 + amount1*price

    if upper_tick <= current_tick:
        # convert amount1 to amount0. 
        token0 = total_amount
        token1 = 0.0
    elif lower_tick >= current_tick:
        # convert amount0 to amount1.
        token1 = total_amount/price
        token0 = 0.0
    else:
        price_lower = decimal_adjustment/(1.0001**lower_tick)
        price_upper = decimal_adjustment/(1.0001**upper_tick)
        sqrC = np.sqrt(price)
        sqrL = np.sqrt(price_lower)
        sqrU = np.sqrt(price_upper)
        amounts_ratio = (sqrC-sqrL)*(sqrU*sqrC)/(sqrU-sqrC)
        token0 = float(total_amount)/(amounts_ratio*price+1)
        token1 = token0*amounts_ratio

    return token0, token1
        