"""Compara cenários fixos em pregões de WIN."""
import pandas as pd

from backtest import backtest
from engine import analyze
from provenance import inspect_historical_csv, missing_trading_days


def compare_risk_limits(candles, contract, evaluation_start=None):
    analyzed = analyze(candles, contract=contract, profile='seletivo')
    rows = []
    for limit in (125, 175, 250, 500):
        trades = backtest(
            analyzed, cost_points=2.0, slippage_ticks=1, max_daily_trades=3,
            max_hold=12, max_daily_loss_points=200.0, contract=contract,
            max_trade_risk_points=limit, max_consecutive_losses=2,
            min_reward_risk=1.0,
        )
        if evaluation_start is not None:
            trades = trades.loc[pd.to_datetime(trades['entrada_data']).ge(evaluation_start)]
        net = trades['net_points'].astype(float)
        equity = pd.concat([pd.Series([0.0]), net.cumsum()], ignore_index=True)
        rows.append({
            'Limite (pts)': limit,
            'Operações': len(trades),
            'Saldo líquido (pts)': round(net.sum(), 2),
            'Rebaixamento máximo (pts)': round((equity.cummax() - equity).max(), 2),
        })
    return pd.DataFrame(rows)


def evaluate_later_sessions(history, payload, provider, contract, filename, as_of=None):
    """Usa o histórico anterior para os indicadores e mede só as novas entradas."""
    later, provenance = inspect_historical_csv(
        payload, provider, contract, filename, as_of=as_of,
    )
    start = later['datetime'].min().normalize()
    if start <= history['datetime'].max().normalize():
        raise ValueError('Envie somente pregões posteriores à amostra de 10 a 19/11/2026.')
    combined = pd.concat([history, later], ignore_index=True)
    missing = missing_trading_days(combined)
    if missing:
        raise ValueError(
            'Há pregões ausentes entre a amostra e a avaliação: ' + ', '.join(missing[:6]) + '.'
        )
    return compare_risk_limits(combined, contract, evaluation_start=start), provenance
