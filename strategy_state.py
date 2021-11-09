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
                    amount_0, amount_1 = UNI_v3_funcs.get_amounts(self.price_tick,
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
            self.liquidity_ranges,self.strategy_info     = strategy_in.check_strategy(self,strategy_info)
                
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
                    in_range   = (self.liquidity_ranges[i]['lower_bin_tick'] <= relevant_swaps.iloc[s]['tick_swap']) and \
                                 (self.liquidity_ranges[i]['upper_bin_tick'] >= relevant_swaps.iloc[s]['tick_swap'])

                    token_0_in = relevant_swaps.iloc[s]['token_in'] == 'token0'
                    
                    # Low liquidity tokens can have zero liquidity after swap
                    if relevant_swaps.iloc[s]['virtual_liquidity'] < 1e-9:
                        fraction_fees_earned_position = 1
                    else:
                        fraction_fees_earned_position = self.liquidity_ranges[i]['position_liquidity']/(self.liquidity_ranges[i]['position_liquidity'] + relevant_swaps.iloc[s]['virtual_liquidity'])

                    fees_earned_token_0 += in_range * token_0_in     * self.fee_tier * fraction_fees_earned_position * relevant_swaps.iloc[s]['traded_in']
                    fees_earned_token_1 += in_range * (1-token_0_in) * self.fee_tier * fraction_fees_earned_position * relevant_swaps.iloc[s]['traded_in']
        
        self.token_0_fees_uncollected += fees_earned_token_0
        self.token_1_fees_uncollected += fees_earned_token_1
        
        return fees_earned_token_0,fees_earned_token_1            
     
    ########################################################
    # Rebalance: Remove all liquidity positions
    # Not dependent on strategy
    ########################################################   
    def remove_liquidity(self):
    
        removed_amount_0    = 0.0
        removed_amount_1    = 0.0
        
        # For every bin, get the amounts you currently have and withdraw
        for i in range(len(self.liquidity_ranges)):
            
            position_liquidity = self.liquidity_ranges[i]['position_liquidity']
           
            TICK_A             = self.liquidity_ranges[i]['lower_bin_tick']
            TICK_B             = self.liquidity_ranges[i]['upper_bin_tick']
            
            token_amounts      = UNI_v3_funcs.get_amounts(self.price_tick,TICK_A,TICK_B,
                                                     position_liquidity,self.decimals_0,self.decimals_1)   
            removed_amount_0   += token_amounts[0]
            removed_amount_1   += token_amounts[1]
        
        self.liquidity_in_0 = removed_amount_0 + self.token_0_left_over + self.token_0_fees_uncollected
        self.liquidity_in_1 = removed_amount_1 + self.token_1_left_over + self.token_1_fees_uncollected
        
        self.token_0_left_over = 0.0
        self.token_1_left_over = 0.0
        
        self.token_0_fees_uncollected = 0.0
        self.token_1_fees_uncollected = 0.0
        
  