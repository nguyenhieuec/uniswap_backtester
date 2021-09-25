# Uniswap v3 Strategy Backtester


## Introduction

This repository contains python scripts that are used by [Brahma Finance](https://brahma.fi/) to simulate the performance of synthetic short put option strategies and evaluate risks. The repo is structured as follows:

[data/](data/) folder contains the csv files related to swap data of `ETH-USDC 0.3%` pool and average gas cost per block.

[notebooks/](notebooks/) folder contains the jupyter notebook files used for simulation and backtesting the put selling strategy.

Coming to python files:

1. [strategy.py](strategy.py) base code for ```strategy```, conducting either back-testing for put selling or range selection strategies (```run_put_strategy``` function and passing in historical swap data)
2. [loader.py](loader.py) contains all functions for processing the swap data gathered from [flipside crypto](https://www.flipsidecrypto.com/)  
2. [simulation.py](simulation.py) contains all the helper functions used for monte calro simulations.
3. [utils.py](utils.py) contains all the helper functions used for updating the state of holdings during backtest.
4. [liquidity.py](liquidity.py) a modified python implementation of Uniswap v3's [liquidity math](https://github.com/Uniswap/uniswap-v3-periphery/blob/main/contracts/libraries/LiquidityAmounts.sol). 

In order to run the backtest for put selling option :
- [backtest.ipynb](backtest.ipynb) runs the analysis explained in the [Aastra  article](). 
- [monte_carlo_simulation.ipynb](monte_carlo_simulation.ipynb) runs the simulations and backtest the put selling strategy on the simulated prices

We have developed a good strategy framework for eth-put selling strategy which backtests on **the real Uniswap v3 swap history with gas prices** in order to improve accurracy of yield's generated. Thefore simulations are ensured to be as realistic as possible considering real time gas fees of the network for the operations used by strategy and slippage costs for any swap involved with available time period since Unsiwap v3 was released (May 5th 2021 is when swap data starts to show up consistently). 


## Potential Sources of inaccurracy

There are several potential sources for imprecision, as for example gas fees are averaged, and can have a significant impact on performance in particular for small positions in high fee regimes.
