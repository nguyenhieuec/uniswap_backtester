import math
import pandas as pd
import univ3_funcs
import copy

class StrategyObservation:
    def __init__(self,timepoint,
                     current_price,
                     strategy_in,
                     liquidity_in_0,
                     liquidity_in_1,
                     fee_tier,
                     decimals_0,
                     decimals_1,
                     token_0_left_over        = 0.0,
                     token_1_left_over        = 0.0,
                     token_0_fees_uncollected = 0.0,
                     token_1_fees_uncollected = 0.0,
                     liquidity_ranges         = None,
                     strategy_info            = None,
                     swaps                    = None,
                     simulate_strat           = True):
        
        ######################################
        # 1. Store current values
        ######################################
        
        self.time                        = timepoint
        self.price                       = current_price
        self.liquidity_in_0              = liquidity_in_0
        self.liquidity_in_1              = liquidity_in_1
        self.fee_tier                    = fee_tier
        self.decimals_0                  = decimals_0
        self.decimals_1                  = decimals_1
        self.token_0_left_over           = token_0_left_over
        self.token_1_left_over           = token_1_left_over
        self.token_0_fees_uncollected    = token_0_fees_uncollected
        self.token_1_fees_uncollected    = token_1_fees_uncollected
        self.reset_point                 = False
        self.reset_reason                = ''
        self.decimal_adjustment          = 10**(self.decimals_1  - self.decimals_0)
        self.tickSpacing                 = int(self.fee_tier*2*10000)   
        self.token_0_fees                = 0.0
        self.token_1_fees                = 0.0
        self.simulate_strat              = simulate_strat
        
        TICK_P_PRE                       = int(math.log(self.decimal_adjustment*self.price,1.0001))        
        self.price_tick                  = round(TICK_P_PRE/self.tickSpacing)*self.tickSpacing
            
        ######################################
        # 2. Execute the strategy
        #    If this is the first observation, need to generate ranges 
        #    Otherwise, check if a rebalance is required and execute.
        #    If swaps data has been fed in, it will be used to estimate fee income (for backtesting simulations)
        #    Otherwise just the ranges will be updated (for a live environment)
        ######################################
        if liquidity_ranges is None and strategy_info is None:
            self.liquidity_ranges,self.strategy_info  = strategy_in.set_liquidity_ranges(self)

        else: 
            self.liquidity_ranges         = copy.deepcopy(liquidity_ranges)
            
            # Update amounts in each position according to current pool price
            for i in range(len(self.liquidity_ranges)):
                self.liquidity_ranges[i]['time'] = self.time
                
                if self.simulate_strat:
                    amount_0, amount_1 = univ3_funcs.get_amounts(self.price_tick,
                                                                self.liquidity_ranges[i]['lower_bin_tick'],
                                                                self.liquidity_ranges[i]['upper_bin_tick'],
                                                                self.liquidity_ranges[i]['position_liquidity'],
                                                                self.decimals_0,
                                                                self.decimals_1)

                    self.liquidity_ranges[i]['token_0'] = amount_0
                    self.liquidity_ranges[i]['token_1'] = amount_1

            # If backtesting swaps, accrue the fees in the provided period
            if swaps is not None:
                fees_token_0,fees_token_1           = self.accrue_fees(swaps)
                self.token_0_fees                   = fees_token_0
                self.token_1_fees                   = fees_token_1
                
            # Check strategy and potentially reset the ranges
            self.liquidity_ranges,self.strategy_info     = strategy_in.check_strategy(self,strategy_info) # self is current strategy observation.
                
    ########################################################
    # Accrue earned fees (not supply into LP yet)
    ########################################################               
    def accrue_fees(self,relevant_swaps):   
        
        fees_earned_token_0 = 0.0
        fees_earned_token_1 = 0.0
                
        if len(relevant_swaps) > 0:
            
            # For every swap in this time period
            for s in range(len(relevant_swaps)):
                for i in range(len(self.liquidity_ranges)):
                    in_range   = (self.liquidity_ranges[i]['lower_bin_tick'] <= relevant_swaps.iloc[s]['tick']) and \
                                 (self.liquidity_ranges[i]['upper_bin_tick'] >= relevant_swaps.iloc[s]['tick'])

                    token_0_in = relevant_swaps.iloc[s]['token_in'] == 'token0'
                    
                    # Low liquidity tokens can have zero liquidity after swap
                    if relevant_swaps.iloc[s]['liquidity'] < 1e-9:
                        fraction_fees_earned_position = 1
                    else:
                        fraction_fees_earned_position = self.liquidity_ranges[i]['position_liquidity']/(self.liquidity_ranges[i]['position_liquidity'] + relevant_swaps.iloc[s]['liquidity'])

                    fees_earned_token_0 += in_range * token_0_in     * self.fee_tier * fraction_fees_earned_position * relevant_swaps.iloc[s]['traded_in']
                    fees_earned_token_1 += in_range * (1-token_0_in) * self.fee_tier * fraction_fees_earned_position * relevant_swaps.iloc[s]['traded_in']
        
        self.token_0_fees_uncollected += fees_earned_token_0
        self.token_1_fees_uncollected += fees_earned_token_1
        
        return fees_earned_token_0,fees_earned_token_1            
     
    ########################################################
    # Rebalance: Remove all liquidity positions
    # Not dependent on strategy
    ########################################################   
    def remove_liquidity(self, positions):
    
        removed_amount_0    = 0.0
        removed_amount_1    = 0.0
        
        # For every bin, get the amounts you currently have and withdraw
        for i in positions:
            
            position_liquidity = self.liquidity_ranges[i]['position_liquidity']
            
            TICK_A             = self.liquidity_ranges[i]['lower_bin_tick']
            TICK_B             = self.liquidity_ranges[i]['upper_bin_tick']
            
            token_amounts      = univ3_funcs.get_amounts(self.price_tick,TICK_A,TICK_B,
                                                    position_liquidity,self.decimals_0,self.decimals_1)   
            removed_amount_0   += token_amounts[0]
            removed_amount_1   += token_amounts[1]
            # update removed liqudity
            self.liquidity_ranges[i]['position_liquidity'] = 0
        self.liquidity_in_0 = removed_amount_0 + self.token_0_left_over + self.token_0_fees_uncollected
        self.liquidity_in_1 = removed_amount_1 + self.token_1_left_over + self.token_1_fees_uncollected
        
        self.token_0_left_over = 0.0
        self.token_1_left_over = 0.0
        
        self.token_0_fees_uncollected = 0.0
        self.token_1_fees_uncollected = 0.0
        
########################################################
# Simulate reset strategy using a Pandas series called price_data, which has as an index
# the time point, and contains the pool price (token 1 per token 0)
########################################################

def simulate_strategy(price_data,swap_data,strategy_in,
                       liquidity_in_0,liquidity_in_1,fee_tier,decimals_0,decimals_1):

    strategy_results = []    
  
    # Go through every time period in the data that was passet
    for i in range(len(price_data)): 
        # Strategy Initialization
        if i == 0:
            print('Initializing strategy...')
            strategy_results.append(StrategyObservation(price_data.index[i],
                                              price_data[i],
                                              strategy_in,
                                              liquidity_in_0,liquidity_in_1,
                                              fee_tier,decimals_0,decimals_1))
        # After initialization
        else:
            relevant_swaps = swap_data[price_data.index[i-1]:price_data.index[i]]
            strategy_results.append(StrategyObservation(price_data.index[i],
                                              price_data[i],
                                              strategy_in,
                                              strategy_results[i-1].liquidity_in_0,
                                              strategy_results[i-1].liquidity_in_1,
                                              strategy_results[i-1].fee_tier,
                                              strategy_results[i-1].decimals_0,
                                              strategy_results[i-1].decimals_1,
                                              strategy_results[i-1].token_0_left_over,
                                              strategy_results[i-1].token_1_left_over,
                                              strategy_results[i-1].token_0_fees_uncollected,
                                              strategy_results[i-1].token_1_fees_uncollected,
                                              strategy_results[i-1].liquidity_ranges,
                                              strategy_results[i-1].strategy_info,
                                              relevant_swaps))
            
    return strategy_results

########################################################
# Extract Strategy Data
########################################################
def generate_simulation_series(simulations,strategy_in,token_0_usd_data = None):
    data_strategy                    = pd.DataFrame([strategy_in.dict_components(i) for i in simulations])
    data_strategy                    = data_strategy.set_index('time',drop=False)
    data_strategy                    = data_strategy.sort_index()
    
    token_0_initial                  = simulations[0].liquidity_ranges[0]['token_0'] + simulations[0].liquidity_ranges[1]['token_0']
    token_1_initial                  = simulations[0].liquidity_ranges[0]['token_1'] + simulations[0].liquidity_ranges[1]['token_1']
    
    if token_0_usd_data is None:
        data_strategy['value_position_usd'] = data_strategy['value_position']
        data_strategy['cum_fees_usd']       = data_strategy['token_0_fees'].cumsum() + (data_strategy['token_1_fees'] / data_strategy['price']).cumsum()
        data_strategy['token_0_hold_usd']   = token_0_initial
        data_strategy['token_1_hold_usd']   = token_1_initial / data_strategy['price']
        data_strategy['value_hold_usd']     = data_strategy['token_0_hold_usd'] + data_strategy['token_1_hold_usd']
        data_return = data_strategy
    else:
        # Merge in usd price data
        token_0_usd_data['price_0_usd']    = 1/token_0_usd_data['quotePrice']
        token_0_usd_data                   = token_0_usd_data.sort_index()
        data_strategy['time_pd']           = pd.to_datetime(data_strategy['time'],utc=True)
        data_strategy                      = data_strategy.set_index('time_pd')
        data_return                        = pd.merge_asof(data_strategy,token_0_usd_data['price_0_usd'],on='time_pd',direction='backward',allow_exact_matches = True)
        data_return['value_position_usd']  = data_return['value_position']*data_return['price_0_usd']
        data_return['cum_fees_0']          = data_return['token_0_fees'].cumsum() + (data_return['token_1_fees'] / data_return['price']).cumsum()
        data_return['cum_fees_usd']        = data_return['cum_fees_0']*data_return['price_0_usd']
        data_return['token_0_hold_usd']    = token_0_initial * data_return['price_0_usd']
        data_return['token_1_hold_usd']    = token_1_initial * data_return['price_0_usd'] / data_return['price']
        data_return['value_hold_usd']      = data_return['token_0_hold_usd'] + data_return['token_1_hold_usd']
        
    return data_return


def analyze_strategy(data_usd,initial_position_value,frequency = 'M'):

    
    if   frequency == 'M':
            annualization_factor = 365*24*60
    elif frequency == 'H':
            annualization_factor = 365*24
    elif frequency == 'D':
            annualization_factor = 365

    days_strategy           = (data_usd['time'].max()-data_usd['time'].min()).days    
    strategy_last_obs       = data_usd.tail(1)
    strategy_last_obs       = strategy_last_obs.reset_index(drop=True)
    net_apr                 = float((strategy_last_obs['value_position_usd']/initial_position_value - 1) * 365 / days_strategy)

    summary_strat = {
                        'days_strategy'        : days_strategy,
                        'gross_fee_apr'        : float((strategy_last_obs['cum_fees_usd']/initial_position_value) * 365 / days_strategy),
                        'gross_fee_return'     : float(strategy_last_obs['cum_fees_usd']/initial_position_value),
                        'net_apr'              : net_apr,
                        'net_return'           : float(strategy_last_obs['value_position_usd']/initial_position_value  - 1),
                        'rebalances'           : data_usd['reset_point'].sum(),
                        'max_drawdown'         : ( data_usd['value_position_usd'].max() - data_usd['value_position_usd'].min() ) / data_usd['value_position_usd'].max(),
                        'volatility'           : ((data_usd['value_position_usd'].pct_change().var())**(0.5)) * ((annualization_factor)**(0.5)),
                        'sharpe_ratio'         : float(net_apr / (((data_usd['value_position_usd'].pct_change().var())**(0.5)) * ((annualization_factor)**(0.5)))),
                        'impermanent_loss'     : ((strategy_last_obs['value_position_usd'] - strategy_last_obs['value_hold_usd']) / strategy_last_obs['value_hold_usd'])[0],
                        'mean_first_position'   : (data_usd['first_position_value']/ \
                                                  (data_usd['first_position_value']+data_usd['second_position_value']+data_usd['value_left_over'])).mean(),
        
                        'median_first_position' : (data_usd['first_position_value']/ \
                                                  (data_usd['first_position_value']+data_usd['second_position_value']+data_usd['value_left_over'])).median(),
        
                        'final_value'          : data_usd['value_position_usd'].iloc[-1]
                    }
    
    return summary_strat


