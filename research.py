"""Diagnósticos transparentes de estabilidade para Trader Pro AI Elite v0.8.

Não calibra regras, não treina IA e não fornece estimativa de retorno futuro.
A divisão temporal é DESCRITIVA dentro da mesma amostra, não um out-of-sample.
"""
from __future__ import annotations

import math
import pandas as pd


def _safe_float(value):
    try:
        f = float(value)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def summarize_trades(trades: pd.DataFrame) -> dict:
    """Resumo líquido estritamente da amostra; não é uma previsão."""
    if 'net_points' not in trades:
        raise ValueError('Tabela de operações precisa conter net_points.')
    vals = pd.to_numeric(trades['net_points'], errors='coerce')
    if vals.isna().any() or (~vals.map(math.isfinite)).any():
        raise ValueError('Há resultados de operações inválidos.')
    wins = int(vals.gt(0).sum())
    losses = int(vals.lt(0).sum())
    count = len(vals)
    equity = pd.concat([pd.Series([0.0]), vals.cumsum().reset_index(drop=True)], ignore_index=True)
    drawdown = float((equity - equity.cummax()).min())
    gross_gains = float(vals[vals.gt(0)].sum())
    gross_losses = -float(vals[vals.lt(0)].sum())
    return {
        'operacoes': count,
        'positivas': wins,
        'negativas': losses,
        'neutras': count-wins-losses,
        'taxa_acerto': wins/count if count else None,
        'saldo_pts': float(vals.sum()),
        'drawdown_pts': drawdown,
        'profit_factor': (gross_gains/gross_losses if gross_losses else None),
        'media_pts': float(vals.mean()) if count else None,
    }


def robustness_report(trades: pd.DataFrame, candles: pd.DataFrame,
                      additional_costs=(0, 5, 10)) -> dict:
    """Análise retrospectiva por metades cronológicas e custos adicionais.

    Não altera os preços ou as condições de entrada originais; custos adicionais
    são subtraídos de cada negociação já simulada. A divisão é feita entre DIAS
    inteiros, não no meio da sessão, e reutiliza o mesmo backtest.
    """
    if 'datetime' not in candles or 'entrada_data' not in trades:
        raise ValueError('Dados sem datetime de candle ou entrada_data de operação.')
    overall = summarize_trades(trades)
    ts = pd.to_datetime(candles['datetime'], errors='coerce')
    if ts.isna().any():
        raise ValueError('Datas de candles inválidas.')
    ordered_days = sorted(set(ts.dt.date))
    safe_costs = []
    for amount in additional_costs:
        cost = _safe_float(amount)
        if cost is None or cost < 0:
            raise ValueError('Custos adicionais devem ser números não negativos.')
        safe_costs.append(cost)
    cost_rows = []
    for additional in safe_costs:
        adjusted = trades.copy()
        adjusted['net_points'] = pd.to_numeric(adjusted['net_points']) - additional
        row = summarize_trades(adjusted)
        cost_rows.append({'Custo extra por operação (pts)': additional,
                          'Saldo líquido (pts)': round(row['saldo_pts'],2),
                          'Acerto líquido': row['taxa_acerto'],
                          'Drawdown (pts)': round(row['drawdown_pts'],2)})
    halves = []
    if len(ordered_days) >= 2:
        cut = len(ordered_days)//2
        if cut > 0 and cut < len(ordered_days):
            entry_dt = pd.to_datetime(trades['entrada_data'], errors='coerce')
            if entry_dt.isna().any():
                raise ValueError('Datas de entrada inválidas.')
            for name, days in [('Primeira metade',ordered_days[:cut]),('Segunda metade',ordered_days[cut:])]:
                mask=entry_dt.dt.date.isin(days)
                part=summarize_trades(trades.loc[mask])
                halves.append({'Período':name,
                               'De':str(days[0]),'Até':str(days[-1]),
                               'Pregões':len(days),
                               'Operações':part['operacoes'],
                               'Acerto líquido':part['taxa_acerto'],
                               'Saldo (pts)':round(part['saldo_pts'],2),
                               'Drawdown (pts)':round(part['drawdown_pts'],2)})
    limitations = []
    if overall['operacoes'] < 100:
        limitations.append('Menos de 100 operações: amostra pequena; qualquer porcentagem é instável.')
    if len(ordered_days) < 10:
        limitations.append('Menos de 10 pregões: comparação por períodos é insuficiente para conclusões.')
    if any(c > 0 for c in safe_costs):
        limitations.append('Custo adicional é uma análise de sensibilidade; não recalcula stops, entradas ou liquidez.')
    limitations.append('As duas metades fazem parte da MESMA amostra. Não são teste fora da amostra nem validação em dados novos.')
    return {'resumo':overall,'pregoes':len(ordered_days),'periodos':pd.DataFrame(halves),
            'custos':pd.DataFrame(cost_rows),'alertas':limitations}
