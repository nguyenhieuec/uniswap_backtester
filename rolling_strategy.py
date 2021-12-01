import math
import univ3_funcs
import pandas as pd


class RollingStrategy:
    def __init__(self, duration_param, buffer_param, percentage_param):
        self.duration  = duration_param
        self.buffer = buffer_param
        self.percentage = percentage_param
        # as both positions are undefined position_status is three
        self.first_position_timestamp = None
        self.second_position_timestamp = None 
    #####################################
    # Check if a rebalance is necessary. 
    # If it is, remove the liquidity and set new ranges
    #####################################
    def check_strategy(self,current_strat_obs,strategy_info):
        
        #####################################
        # This strategy rebalances, when position timestamp has passed duration
        #####################################
        FIRST_POSITION_DURATION = (current_strat_obs.time - strategy_info['first_position_timestamp'])/pd.Timedelta(self.duration)
        
        if FIRST_POSITION_DURATION > 1:
            current_strat_obs.reset_point = True
            current_strat_obs.reset_reason = 'first_position_rebalance'
            # Remove liquidity from first position
            current_strat_obs.remove_liquidity([0])
            liq_range,strategy_info = self.set_liquidity_ranges(current_strat_obs)

        elif 'second_position_timestamp' in strategy_info.keys():
            SECOND_POSITION_DURATION = (current_strat_obs.time - strategy_info['second_position_timestamp'])/pd.Timedelta(self.duration)
            if SECOND_POSITION_DURATION > 1:
                current_strat_obs.reset_point = True
                current_strat_obs.reset_reason = 'second_position_rebalance'
                # Remove liquidity from first position
                current_strat_obs.remove_liquidity([1])
                liq_range,strategy_info = self.set_liquidity_ranges(current_strat_obs)
            else:
                liq_range = current_strat_obs.liquidity_ranges

        # If it right time to initialized second position
        elif strategy_info['first_position_timestamp']+pd.Timedelta(self.buffer) < current_strat_obs.time:
            current_strat_obs.reset_point = True
            current_strat_obs.reset_reason = 'second_position_initialization'
            liq_range,strategy_info = self.set_liquidity_ranges(current_strat_obs)
        else:
            liq_range = current_strat_obs.liquidity_ranges
        return liq_range,strategy_info        


        
    def set_liquidity_ranges(self, current_strat_obs):
        ###########################################################
        # STEP 1: Do calculations required to determine base liquidity bounds
        ###########################################################
        strategy_info = dict()
        # Calculate the ticks
        tick_lower      = current_strat_obs.price/1.0001
        tick_upper      = (1+self.percentage)*current_strat_obs.price

        TICK_A_PRE         = int(math.log(current_strat_obs.decimal_adjustment*tick_lower,1.0001))
        TICK_A             = int(round(TICK_A_PRE/current_strat_obs.tickSpacing)*current_strat_obs.tickSpacing)

        TICK_B_PRE        = int(math.log(current_strat_obs.decimal_adjustment*tick_upper,1.0001))
        TICK_B            = int(round(TICK_B_PRE/current_strat_obs.tickSpacing)*current_strat_obs.tickSpacing)

        ###########################################################
        # TODO Add gas costs
        ###########################################################
        # print("before:", current_strat_obs.token_0_left_over, current_strat_obs.token_1_left_over)
        current_strat_obs.token_0_left_over,  current_strat_obs.token_1_left_over = univ3_funcs.swap_tokens( current_strat_obs.token_0_left_over,  current_strat_obs.token_1_left_over, TICK_A, TICK_B, current_strat_obs.price_tick, current_strat_obs.decimal_adjustment)
        # print("after:", current_strat_obs.token_0_left_over, current_strat_obs.token_1_left_over)
        # check if position is there
        if current_strat_obs.reset_reason == '':
            # Just use half the amount if position isn't initialized.
            limit_amount_0 = current_strat_obs.token_0_left_over/2.0
            limit_amount_1 = current_strat_obs.token_1_left_over/2.0
        else:
            # Store each token amount supplied to pool
            limit_amount_0 = current_strat_obs.token_0_left_over
            limit_amount_1 = current_strat_obs.token_1_left_over

        liquidity_placed_limit        = int(univ3_funcs.get_liquidity(current_strat_obs.price_tick,TICK_A,TICK_B, \
                                                                    limit_amount_0,limit_amount_1,current_strat_obs.decimals_0,current_strat_obs.decimals_1))
        limit_0_amount,limit_1_amount =     univ3_funcs.get_amounts(current_strat_obs.price_tick,TICK_A,TICK_B,\
                                                                    liquidity_placed_limit,current_strat_obs.decimals_0,current_strat_obs.decimals_1)      
        # Update token amount supplied to pool
        limit_amount_0  -= limit_0_amount
        limit_amount_1  -= limit_1_amount
        
        # Check we didn't allocate more liquidiqity than available
        assert current_strat_obs.token_0_left_over >= limit_amount_0
        assert current_strat_obs.token_0_left_over >= limit_amount_1

        pos_liq_range = {'price'             : current_strat_obs.price,
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
        if current_strat_obs.reset_reason == 'first_position_rebalance':
            liq_ranges = [pos_liq_range, current_strat_obs.liquidity_ranges[1]]
            strategy_info['first_position_timestamp'] = current_strat_obs.time
            self.first_position_timestamp = strategy_info['first_position_timestamp']

        elif 'second_position' in current_strat_obs.reset_reason:
            liq_ranges = [current_strat_obs.liquidity_ranges[0], pos_liq_range]
            strategy_info['second_position_timestamp'] = current_strat_obs.time
            self.second_position_timestamp = strategy_info['second_position_timestamp']

        elif current_strat_obs.reset_reason=='':
            current_strat_obs.reset_reason = 'first_position_initialization'
            current_strat_obs.reset_point = True
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
            strategy_info['first_position_timestamp'] = current_strat_obs.time
            self.first_position_timestamp = strategy_info['first_position_timestamp']
        if self.first_position_timestamp:
            strategy_info['first_position_timestamp'] = self.first_position_timestamp
        if self.second_position_timestamp:
            strategy_info['second_position_timestamp'] = self.second_position_timestamp

        current_strat_obs.token_0_left_over -= limit_0_amount
        current_strat_obs.token_1_left_over -= limit_1_amount
        return liq_ranges, strategy_info


        
    ########################################################
    # Extract strategy parameters
    ########################################################
    def dict_components(self,strategy_observation):
            this_data = dict()
            
            # General variables
            this_data['time']                   = strategy_observation.time
            this_data['price']                  = strategy_observation.price
            this_data['reset_point']            = strategy_observation.reset_point
            this_data['reset_reason']           = strategy_observation.reset_reason
            
            # Range Variables
            this_data['first_position_lower']       = strategy_observation.liquidity_ranges[0]['lower_bin_price']
            this_data['first_position_upper']       = strategy_observation.liquidity_ranges[0]['upper_bin_price']
            this_data['second_position_lower']      = strategy_observation.liquidity_ranges[1]['lower_bin_price']
            this_data['second_position_upper']      = strategy_observation.liquidity_ranges[1]['upper_bin_price']
            # this_data['reset_range_lower']      = strategy_observation.strategy_info['reset_range_lower']
            # this_data['reset_range_upper']      = strategy_observation.strategy_info['reset_range_upper']
            
            # Fee Varaibles
            this_data['token_0_fees']           = strategy_observation.token_0_fees 
            this_data['token_1_fees']           = strategy_observation.token_1_fees 
            this_data['token_0_fees_uncollected']     = strategy_observation.token_0_fees_uncollected
            this_data['token_1_fees_uncollected']     = strategy_observation.token_1_fees_uncollected
            
            # Asset Variables
            this_data['token_0_left_over']      = strategy_observation.token_0_left_over
            this_data['token_1_left_over']      = strategy_observation.token_1_left_over
            
            total_token_0 = 0.0
            total_token_1 = 0.0
            for i in range(len(strategy_observation.liquidity_ranges)):
                total_token_0 += strategy_observation.liquidity_ranges[i]['token_0']
                total_token_1 += strategy_observation.liquidity_ranges[i]['token_1']
                
            this_data['token_0_allocated']      = total_token_0
            this_data['token_1_allocated']      = total_token_1
            this_data['token_0_total']          = total_token_0 + strategy_observation.token_0_left_over + strategy_observation.token_0_fees_uncollected 
            this_data['token_1_total']          = total_token_1 + strategy_observation.token_1_left_over + strategy_observation.token_1_fees_uncollected 

            # Value Variables
            this_data['value_position']         = this_data['token_0_total'] + this_data['token_1_total']         / this_data['price']
            this_data['value_allocated']        = this_data['token_0_allocated'] + this_data['token_1_allocated'] / this_data['price']
            this_data['value_left_over']        = this_data['token_0_left_over'] + this_data['token_1_left_over'] / this_data['price']
            
            this_data['first_position_value']    = strategy_observation.liquidity_ranges[0]['token_0'] + strategy_observation.liquidity_ranges[0]['token_1'] / this_data['price']
            this_data['second_position_value']   = strategy_observation.liquidity_ranges[1]['token_0'] + strategy_observation.liquidity_ranges[1]['token_1'] / this_data['price']
            
            return this_data
        