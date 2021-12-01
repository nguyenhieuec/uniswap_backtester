# Uniswap v3 Strategy Backtester


## Introduction

This repository contains python scripts that are used by [Brahma Finance](https://brahma.fi/) to simulate and backtest strategies on concentrated amm's like uniswap v3. The repo is structured as follows:

[data/](data/) folder contains the csv files related to swap data of `ETH-USDC 0.3%` pool and average gas cost per block.

[notebooks/](notebooks/) folder contains the jupyter notebook files used for simulation and backtesting the put selling strategy.

Coming to python files:

1. [strategy_state.py](strategy_state.py) base code for ```strategy```, conducting either back-testing for put selling or range selection strategies (```run_put_strategy``` function and passing in historical swap data)
2. [big_query.py](big_query.py) contains all functions for downloading  the swap data from [block chain etl](https://github.com/blockchain-etl/ethereum-etl)  
2. [transformers.py](transformers.py) contains all the transformation functions used calculating metrics on swap data.
3. [univ3_funcs.py](univ3_funcs.py) a modified python implementation of Uniswap v3's [liquidity math](https://github.com/Uniswap/uniswap-v3-periphery/blob/main/contracts/libraries/LiquidityAmounts.sol) built by [JNP](https://github.com/JNP777).

## Backtesting
The new backtester has its main parts forked from (active-strategy-framework)[https://github.com/GammaStrategies/active-strategy-framework] by (GammaStrategies)[https://www.gammastrategies.org/]. The main difference is that the data is downloaded in programmatic way from [block chain etl](https://github.com/blockchain-etl/ethereum-etl) and backtesting is done on block by block basis.

In order to run the backtest for sample strategy provided :
- [backtest.ipynb](backtest.ipynb) runs the rolling strategy with two lp positions. 
- [rolling_strategy.py](rolling_strategy.py) contains the main code for rolling put selling strategy.

## TO DO

The current backtester doesn't incorperate the following features:
1. Swap Costs
2. Gast Costs
3. Improving the running time of the backtest
4. Metrics Integration
5. HODL factor based on (Prof.Lambert's work)[https://lambert-guillaume.medium.com/pricing-uniswap-v3-lp-positions-towards-a-new-options-paradigm-dce3e3b50125]
6. Cleaning up the previous backtest code base. 
