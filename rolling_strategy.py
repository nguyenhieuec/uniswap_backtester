import math
import univ3_funcs
import numpy as np


class RollingStrategy:
    def __init__(self, duration_param, percentage_param):
        self.duration  = duration_param
        self.percentage = percentage_param
        self.position_status = None
 #####################################
    # Check if a rebalance is necessary. 
    # If it is, remove the liquidity and set new ranges
    #####################################
        
    def check_strategy(self,current_strat_obs,strategy_info):
        
        #####################################
        #
        # This strategy rebalances in one scenarios:
        # 1. When position timestamp has passed duration
        #
        #####################################
        FIRST_POSITION_DURATION = (current_strat_obs.timestamp - strategy_info['first_position_timestamp'])/pd.Timedelta(self.duration)
        SECOND_POSITION_DURATION = (current_strat_obs.timestamp - strategy_info['second_position_timestamp'])/pd.Timedelta(self.duration)
        if FIRST_POSITION_DURATION > 1:
            # Remove liquidity from first position
            current_strat_obs.remove_liquidity([0])
            # Check removed position     
            self.check_position_initialized(current_strat_obs)
            # TODO: Clean up returns
            liq_range,strategy_info = self.set_liquidity_ranges(current_strat_obs)
            # update the postion ranges
            liq_ranges = [liq_range, current_strat_obs.liquidity_ranges[1]]

        if SECOND_POSITION_DURATION > 1:
            # Remove liquidity from first position
            current_strat_obs.remove_liquidity([1])
            # Check removed position     
            self.check_position_initialized(current_strat_obs)
            
            liq_range,strategy_info = self.set_liquidity_ranges(current_strat_obs)
            # update the postion ranges
            liq_ranges = [current_strat_obs.liquidity_ranges[0], liq_range]

        return liq_ranges,strategy_info        



    def check_position_initialized(self, current_strat_obs):
        # if position isn't initialized liquidity is zero
        first_not_initialized = int(current_strat_obs.liquidity_ranges[0]['position_liquidity']==0)
        second_not_initialized = int(current_strat_obs.liquidity_ranges[1]['position_liquidity']==0)
        self.position_status =  first_not_initialized + 2*second_not_initialized

        
    def set_liquidity_ranges(self, current_strat_obs):
        ###########################################################
        # STEP 1: Do calculations required to determine base liquidity bounds
        ###########################################################
        strategy_info = dict()
        # Calculate the ticks
        tick_lower      = current_strat_obs.price
        tick_upper      = (1+self.percentage)*current_strat_obs.price

        TICK_A_PRE         = int(math.log(current_strat_obs.decimal_adjustment*tick_lower,1.0001))
        TICK_A             = int(round(TICK_A_PRE/current_strat_obs.tickSpacing)*current_strat_obs.tickSpacing)

        TICK_B_PRE        = int(math.log(current_strat_obs.decimal_adjustment*tick_upper,1.0001))
        TICK_B            = int(round(TICK_B_PRE/current_strat_obs.tickSpacing)*current_strat_obs.tickSpacing)


        # check if position is there
        if self.position_status == 3:
            # Just use half the amount if position isn't initialized.
            limit_amount_0 = current_strat_obs.liquidity_in_0/2.0
            limit_amount_1 = current_strat_obs.liquidity_in_1/2.0
        else:
            # Store each token amount supplied to pool
            limit_amount_0 = current_strat_obs.liquidity_in_0
            limit_amount_1 = current_strat_obs.liquidity_in_1



        liquidity_placed_limit        = int(univ3_funcs.get_liquidity(current_strat_obs.price_tick,TICK_A,TICK_B, \
                                                                    limit_amount_0,limit_amount_1,current_strat_obs.decimals_0,current_strat_obs.decimals_1))
        limit_0_amount,limit_1_amount =     univ3_funcs.get_amounts(current_strat_obs.price_tick,TICK_A,TICK_B,\
                                                                    liquidity_placed_limit,current_strat_obs.decimals_0,current_strat_obs.decimals_1)      
        # Update token amount supplied to pool
        limit_amount_0  -= limit_0_amount
        limit_amount_1  -= limit_1_amount
        
        # Check we didn't allocate more liquidiqity than available
        assert current_strat_obs.liquidity_in_0 >= limit_amount_0
        assert current_strat_obs.liquidity_in_1 >= limit_amount_1

        pos_liq_range = {'price'              : current_strat_obs.price,
                        'lower_bin_tick'     : TICK_A,
                        'upper_bin_tick'     : TICK_B,
                        'lower_bin_price'    : tick_lower,
                        'upper_bin_price'    : tick_upper,
                        'time'               : current_strat_obs.time,
                        'token_0'            : limit_0_amount,
                        'token_1'            : limit_1_amount,
                        'position_liquidity' : liquidity_placed_limit,
                        'reset_time'         : current_strat_obs.time}

        liq_ranges = []
        # check if position is there
        if self.position_status==1: 
            liq_ranges = [pos_liq_range, current_strat_obs.liquidity_ranges[1]]
        elif self.position_status==2:
            liq_ranges = [current_strat_obs.liquidity_ranges[0], pos_liq_range]
        elif self.position_status==3:
            none_position = {'price'              : current_strat_obs.price,
                            'lower_bin_tick'     : TICK_A,
                            'upper_bin_tick'     : TICK_B,
                            'lower_bin_price'    : tick_lower,
                            'upper_bin_price'    : tick_upper,
                            'time'               : current_strat_obs.time,
                            'token_0'            : 0,
                            'token_1'            : 0,
                            'position_liquidity' : 0,
                            'reset_time'         : current_strat_obs.time}
            liq_ranges = [pos_liq_range, none_position]
        return liq_ranges, strategy_info