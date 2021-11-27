import math
import copy
import univ3_funcs
import numpy as np
import pandas as pd
import plotly.graph_objects as go

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
        # For every swap in this time period
        for lr in self.liquidity_ranges:
            in_range = np.logical_and(relevant_swaps['tick'] >= lr['lower_bin_tick'],relevant_swaps['tick'] <= lr['upper_bin_tick'])
            token_0_in = relevant_swaps['token_in'] == 'token0'
            # Low liquidity tokens can have zero liquidity after swap
            fraction_fees_earned_position = np.where(relevant_swaps['liquidity']<1e-9, 1, lr['position_liquidity']/(lr['position_liquidity'] + relevant_swaps['liquidity'])) 
            fees_earned_token_0 += np.sum(np.logical_and(in_range, token_0_in)* self.fee_tier * relevant_swaps['traded_in'] * fraction_fees_earned_position)
            fees_earned_token_1 += np.sum(np.logical_and(in_range, 1-token_0_in)* self.fee_tier * relevant_swaps['traded_in'] * fraction_fees_earned_position)
            
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

def simulate_strategy(price_data:pd.Series,swap_data:pd.DataFrame,strategy_in,
                       liquidity_in_0,liquidity_in_1,fee_tier,decimals_0,decimals_1):
    print('Initializing strategy...')
    strategy_results = [StrategyObservation(price_data.index[0],
                                              price_data[0],
                                              strategy_in,
                                              liquidity_in_0,liquidity_in_1,
                                              fee_tier,decimals_0,decimals_1)]    
  
    # Go through every time period in the data that was passet
    for i in range(1,len(price_data)): 
        # After initialization
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
    
    token_0_initial                  = simulations[0].liquidity_ranges[0]['token_0'] + simulations[0].liquidity_ranges[1]['token_0'] + simulations[0].liquidity_in_0
    token_1_initial                  = simulations[0].liquidity_ranges[0]['token_1'] + simulations[0].liquidity_ranges[1]['token_1'] + simulations[0].liquidity_in_1
    
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



def plot_strategy(data_strategy,y_axis_label,base_color = '#ff0000'):
    CHART_SIZE = 300

    fig_strategy = go.Figure()
    fig_strategy.add_trace(go.Scatter(
        x=data_strategy['time'], 
        y=1/data_strategy['first_position_lower'],
        fill=None,
        mode='lines',
        showlegend = False,
        line_color=base_color,
        ))
    fig_strategy.add_trace(go.Scatter(
        x=data_strategy['time'], 
        y=1/data_strategy['first_position_upper'],
        name='First Position',
        fill='tonexty', # fill area between trace0 and trace1
        mode='lines', line_color=base_color))

    fig_strategy.add_trace(go.Scatter(
        x=data_strategy['time'], 
        y=1/data_strategy['second_position_lower'],
        fill=None,
        mode='lines',
        showlegend = False,
        line_color='#6f6f6f'))

    fig_strategy.add_trace(go.Scatter(
        x=data_strategy['time'], 
        y=1/data_strategy['second_position_upper'],
        name='Second Position',
        fill='tonexty', # fill area between trace0 and trace1
        mode='lines', line_color='#6f6f6f',))

    fig_strategy.add_trace(go.Scatter(
        x=data_strategy['time'], 
        y=1/data_strategy['price'],
        name='Price',
        line=dict(width=2,color='black')))

    fig_strategy.update_layout(
        margin=dict(l=20, r=20, t=40, b=20),
        height= CHART_SIZE,
        title = 'Strategy Simulation',
        xaxis_title="Date",
        yaxis_title=y_axis_label,
    )

    fig_strategy.show(renderer="png")
    
    
def plot_position_value(data_strategy):
    CHART_SIZE = 300

    fig_strategy = go.Figure()
    fig_strategy.add_trace(go.Scatter(
        x=data_strategy['time'], 
        y=data_strategy['value_position_usd'],
        name='Value of LP Position',
        line=dict(width=2,color='red')))

    fig_strategy.add_trace(go.Scatter(
        x=data_strategy['time'], 
        y=data_strategy['value_hold_usd'],
        name='Value of Holding',
        line=dict(width=2,color='blue')))

    fig_strategy.update_layout(
        margin=dict(l=20, r=20, t=40, b=20),
        height= CHART_SIZE,
        title = 'Strategy Simulation — LP Position vs. Holding',
        xaxis_title="Date",
        yaxis_title='Position Value',
    )

    fig_strategy.show(renderer="png")
    
    
def plot_asset_composition(data_strategy,token_0_name,token_1_name):
    CHART_SIZE = 300
    # 3 - Asset Composition
    fig_composition = go.Figure()
    fig_composition.add_trace(go.Scatter(
        x=data_strategy['time'], y=data_strategy['token_0_total'],
        mode='lines',
        name=token_0_name,
        line=dict(width=0.5, color='blue'),
        stackgroup='one', # define stack group
        groupnorm='percent'
    ))
    fig_composition.add_trace(go.Scatter(
        x=data_strategy['time'], y=data_strategy['token_1_total']/data_strategy['price'],
        mode='lines',
        name=token_1_name,
        line=dict(width=0.5, color='#f4f4f4'),
        stackgroup='one'
    ))

    fig_composition.update_layout(
        showlegend=True,
        xaxis_type='date',
        yaxis=dict(
            type='linear',
            range=[1, 100],
            ticksuffix='%'))

    fig_composition.update_layout(
        margin=dict(l=20, r=20, t=40, b=20),
        height= CHART_SIZE,
        title = 'Position Asset Composition',
        xaxis_title="Date",
        yaxis_title="Position %",
        legend_title='Token'
    )

    fig_composition.show(renderer="png")
