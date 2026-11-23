"""Compara cenários fixos na amostra exploratória de WIN."""
import pandas as pd

from backtest import backtest
from engine import analyze


def compare_risk_limits(candles, contract):
    analyzed = analyze(candles, contract=contract, profile='seletivo')
    rows = []
    for limit in (125, 175, 250, 500):
        trades = backtest(
            analyzed, cost_points=2.0, slippage_ticks=1, max_daily_trades=3,
            max_hold=12, max_daily_loss_points=200.0, contract=contract,
            max_trade_risk_points=limit, max_consecutive_losses=2,
            min_reward_risk=1.0,
        )
        net = trades['net_points'].astype(float)
        equity = pd.concat([pd.Series([0.0]), net.cumsum()], ignore_index=True)
        rows.append({
            'Limite (pts)': limit,
            'Operações': len(trades),
            'Saldo líquido (pts)': round(net.sum(), 2),
            'Rebaixamento máximo (pts)': round((equity.cummax() - equity).max(), 2),
        })
    return pd.DataFrame(rows)
