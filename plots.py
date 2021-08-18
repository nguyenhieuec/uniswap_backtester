import matplotlib.pyplot as plt
from metrics import sharpe, max_drawdown

def plot_with_hodl(result, swap_data,pool_name, save_path=None):
        holdings = result['holdings']
        filter_range, filter_move = result['range_percent'], result['move_percent']
        holdings['usd'].plot(figsize=(10, 5))
        hold_portfolio_5050 = (holdings.reserve0.iloc[0]*swap_data['token0_price']) + (holdings.reserve1.iloc[0]*swap_data['token1_price'])
        hold_portfolio_5050.plot(color='orange')
        # holdings_eth = (holdings['usd'].iloc[0]/swap_data.token1_price.iloc[0])*swap_data['token1_price']
        # holdings_eth.plot(color='orange')
        sharpe_holdings = sharpe(holdings.usd.pct_change().dropna())
        sharpe_hold_port = sharpe(hold_portfolio_5050.pct_change().dropna())
        # sharpe_hold_eth = sharpe(holdings_eth.pct_change().dropna())
        plt.legend([f'{filter_range} range, {filter_move} move sharpe: {round(sharpe_holdings,4)}', 
                    f'50 ETH USDC sharpe: {round(sharpe_hold_port,4)}' ])
        plt.xlabel('Block Number')
        plt.ylabel('Portfolio in USD')
        plt.title(f'{pool_name} comaprision with hodl')
        if save_path:
            plt.savefig(save_path)
        plt.show()


def plot_rebalances(holdings,pool_name,save_path=None):
    holdings.ub.plot(figsize=(10,5), color='red')
    holdings.cp.plot(color='orange')
    holdings.lb.plot(color='blue')
    plt.title(f'{pool_name} rebalance plot')
    plt.xlabel('Block Number')
    plt.ylabel('Price')
    plt.legend(['Upper Tick', 'Current Price', 'Lower Tick'])
    plt.twinx()
    holdings.rebalance.plot(color='yellow')
    if save_path:
        plt.savefig(save_path)
    plt.show()


def plot_all(out, pool_name, save_path=None):
    for i in range(len(out)):
        out[i]['holdings']['usd'].plot(figsize=(20, 15))
    L = plt.legend(loc='upper right')
    count = 0
    for i in range(len(out)):
        L.get_texts()[count].set_text(f'move_percentage: {out[i]["move_percent"]}, range: {out[i]["range_percent"]}')
        count+=1
    plt.title(f'{pool_name} backtest')
    plt.xlabel('Block Number')
    plt.ylabel('Portfolio in USD')
    if save_path:
        plt.savefig(save_path)
    plt.show()