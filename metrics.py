import numpy as np
import pandas as pd

def sharpe(returns, risk_free=0):
    """
    Calculates the Sharpe Ratio for the strategy, based on a
    benchmark of zero (i.e. no risk-free rate information).

    Parameters:
    returns - A pandas Series representing period percentage returns.
    risk_free - A number representing the risk-free rate of return.
                This defaults to 0 to match the Excel implementation.
    """
    sharpe = (np.mean(returns)- risk_free)/np.std(returns)
    return sharpe


def max_drawdown(returns):
    """
    Calculates the maximum drawdown for the strategy.
    Parameters:
    returns  -  A pandas Series representing period percentage returns.
    """
    cum_returns = (1+returns).cumprod()
    max_so_far = cum_returns.cummax()
    max_drawdown = max(max_so_far-cum_returns)
    return max_drawdown