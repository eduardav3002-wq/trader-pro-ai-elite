"""Auditoria DESCRITIVA de concentração da amostra de negócios do WIN.

Não altera parâmetros do motor nem avalia dados futuros por conta própria.
Um resultado ao remover a melhor operação/dia é contrafactual aritmético:
o backtest não é reexecutado após retirar uma operação (travas de risco
poderiam alterar os sinais subsequentes).
"""
from __future__ import annotations

import math
import pandas as pd

from forward_validation import RISK_LIMITS, SLIPPAGE_SCENARIOS, _drawdown

REQUIRED = {
    'Limite (pts)', 'Slippage (ticks por lado)', 'sinal_candle',
    'entrada_data', 'net_points', 'tipo_horario_saida',
}
SUMMARY_COLUMNS = [
    'Limite (pts)', 'Slippage (ticks por lado)', 'Operações',
    'Dias com operação', 'Pregões na amostra', 'Saldo líquido (pts)',
    'Melhor operação (pts)', 'Pior operação (pts)',
    'Saldo menos melhor operação (pts)', 'Melhor pregão (pts)',
    'Saldo menos melhor pregão (pts)', 'Rebaixamento máximo (pts)',
    'Saídas intrabar com tempo incerto', 'Percentual de saídas incertas (%)',
    'Maior operação / ganhos positivos (%)',
    'Lucro depende da melhor operação',
]
DAY_COLUMNS = [
    'Limite (pts)', 'Slippage (ticks por lado)', 'Dia',
    'Operações', 'Saldo líquido (pts)',
]


def _round(value: float) -> float:
    return round(float(value), 2)


def analyze_fragility(trades: pd.DataFrame, *, sample_sessions: int = 8) -> dict:
    """Retorna métricas por cenário e por pregão, sem previsão de acerto.

    Operações são distintas por cenário; nunca se somam 1, 2 e 3 ticks.
    Para melhorar a rastreabilidade, rejeita duplicatas por candle de sinal.
    """
    if sample_sessions < 1:
        raise ValueError('Amostra deve conter pelo menos um pregão.')
    missing = REQUIRED.difference(trades.columns)
    if missing:
        raise ValueError('Campos ausentes na auditoria: ' + ', '.join(sorted(missing)))
    src = trades.copy()
    if not src.empty:
        for col in ('Limite (pts)', 'Slippage (ticks por lado)', 'net_points'):
            src[col] = pd.to_numeric(src[col], errors='raise')
        if not src['net_points'].map(math.isfinite).all():
            raise ValueError('Resultado líquido não finito na auditoria.')
        src['entrada_data'] = pd.to_datetime(src['entrada_data'], errors='raise')
        if src['entrada_data'].isna().any():
            raise ValueError('Horário de entrada inválido.')
        src['Dia'] = src['entrada_data'].dt.date.astype(str)
        src = src.sort_values(['Limite (pts)', 'Slippage (ticks por lado)', 'entrada_data', 'sinal_candle'])
        if src.duplicated(['Limite (pts)','Slippage (ticks por lado)','sinal_candle']).any():
            raise ValueError('Sinal duplicado no mesmo cenário.')
        valid = set((limit, slip) for limit in RISK_LIMITS for slip in SLIPPAGE_SCENARIOS)
        observed = set(zip(src['Limite (pts)'], src['Slippage (ticks por lado)']))
        if not observed.issubset(valid):
            raise ValueError('A auditoria contém um limite/slippage fora do protocolo congelado.')

    summaries = []
    days_rows = []
    for limit in RISK_LIMITS:
        for slip in SLIPPAGE_SCENARIOS:
            mask = src['Limite (pts)'].eq(limit) & src['Slippage (ticks por lado)'].eq(slip)
            selected = src.loc[mask]
            n = len(selected)
            if n:
                net = selected['net_points'].astype(float)
                balance = _round(net.sum())
                best = _round(net.max())
                worst = _round(net.min())
                daily = selected.groupby('Dia', sort=True)['net_points'].agg(['sum','size'])
                best_day = _round(daily['sum'].max())
                for day, row in daily.iterrows():
                    days_rows.append({
                        'Limite (pts)':limit, 'Slippage (ticks por lado)':slip, 'Dia':day,
                        'Operações':int(row['size']), 'Saldo líquido (pts)':_round(row['sum']),
                    })
                uncertain = int(selected['tipo_horario_saida'].eq(
                    'INICIO_CANDLE_SAIDA_INTRA_5M_TEMPO_INCERTO').sum())
                positives = net[net.gt(0)]
                share = _round(100 * max(best, 0) / positives.sum()) if len(positives) else None
                reduced = _round(balance - best)
                reduced_day = _round(balance - best_day)
                dependency = bool(balance > 0 and reduced <= 0)
            else:
                balance = best = worst = best_day = reduced = reduced_day = 0.0
                uncertain = 0
                share = None
                dependency = False
            summaries.append({
                'Limite (pts)':limit,
                'Slippage (ticks por lado)':slip,
                'Operações':n,
                'Dias com operação':int(selected['Dia'].nunique()) if n else 0,
                'Pregões na amostra':sample_sessions,
                'Saldo líquido (pts)':balance,
                'Melhor operação (pts)':best,
                'Pior operação (pts)':worst,
                'Saldo menos melhor operação (pts)':reduced,
                'Melhor pregão (pts)':best_day,
                'Saldo menos melhor pregão (pts)':reduced_day,
                'Rebaixamento máximo (pts)':_drawdown(selected['net_points']) if n else 0.0,
                'Saídas intrabar com tempo incerto':uncertain,
                'Percentual de saídas incertas (%)':_round(100*uncertain/n) if n else None,
                'Maior operação / ganhos positivos (%)':share,
                'Lucro depende da melhor operação':dependency,
            })
    return {
        'resumo':pd.DataFrame(summaries, columns=SUMMARY_COLUMNS),
        'por_dia':pd.DataFrame(days_rows, columns=DAY_COLUMNS),
    }
