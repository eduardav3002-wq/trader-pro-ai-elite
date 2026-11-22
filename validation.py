"""Trader Pro AI Elite v0.9 — verificação cronológica descritiva e evidências.

Nenhum conjunto aqui é considerado comprovadamente cego ou independente: o código
não acompanha a história de escolhas humanas de parâmetros nem autentica CSVs.
Não há calibração, aprendizado, previsão nem autorização de negociação real.
"""
from __future__ import annotations

import math

import pandas as pd

from research import summarize_trades


def _days_from_candles(candles: pd.DataFrame) -> list:
    if not isinstance(candles, pd.DataFrame) or 'datetime' not in candles:
        raise ValueError('Candles devem conter a coluna datetime.')
    stamps = pd.to_datetime(candles['datetime'], errors='coerce')
    if stamps.empty or stamps.isna().any() or not stamps.is_monotonic_increasing:
        raise ValueError('Candles precisam ter datas válidas e ordem cronológica.')
    return sorted(set(stamps.dt.date))


def chronological_validation(
    trades: pd.DataFrame,
    candles: pd.DataFrame,
    *,
    is_demo: bool,
    reserve_fraction: float = 0.30,
    extra_cost_points: float = 10.0,
) -> dict:
    """Descreve segmento inicial e segmento final de pregões INTEIROS.

    Os sinais e operações precisam ser calculados somente com informações
    disponíveis no instante histórico (responsabilidade do engine/backtest).
    O motor tem parâmetros fixos; a função NÃO escolhe os melhores parâmetros.
    Dados finais NÃO viram "fora da amostra de verdade" só por serem separados:
    o pesquisador pode já ter observado esses dias ou ajustado regras após vê-los.
    """
    if not isinstance(is_demo, bool):
        raise ValueError('is_demo deve ser booleano.')
    if not isinstance(reserve_fraction, (int, float)) or isinstance(reserve_fraction, bool) \
            or not math.isfinite(reserve_fraction) or not 0.1 <= reserve_fraction <= 0.5:
        raise ValueError('A proporção reservada deve estar entre 10% e 50%.')
    if not isinstance(extra_cost_points, (int, float)) or isinstance(extra_cost_points, bool) \
            or not math.isfinite(extra_cost_points) or extra_cost_points < 0:
        raise ValueError('O custo extra deve ser um número não negativo.')
    if not isinstance(trades, pd.DataFrame) or not {'entrada_data', 'net_points'} <= set(trades.columns):
        raise ValueError('Backtest precisa fornecer entrada_data e net_points.')

    days = _days_from_candles(candles)
    if len(days) < 2:
        raise ValueError('Necessários pelo menos dois pregões para dividir cronologicamente.')
    entry_dates = pd.to_datetime(trades['entrada_data'], errors='coerce')
    if entry_dates.isna().any() or not entry_dates.is_monotonic_increasing:
        raise ValueError('Operações precisam ter entradas válidas e cronológicas.')
    trade_days = entry_dates.dt.date
    if not set(trade_days).issubset(set(days)):
        raise ValueError('Existem entradas fora dos pregões fornecidos.')
    # Nunca divide o mesmo dia entre estudo e reserva.
    reserve_count = min(len(days) - 1, max(1, math.ceil(len(days) * reserve_fraction)))
    cut = len(days) - reserve_count
    study_days, reserve_days = days[:cut], days[cut:]
    study = trades.loc[trade_days.isin(study_days)].copy()
    reserved = trades.loc[trade_days.isin(reserve_days)].copy()
    study_summary = summarize_trades(study)
    reserve_summary = summarize_trades(reserved)
    stressed = reserved.copy()
    stressed['net_points'] = pd.to_numeric(stressed['net_points']) - extra_cost_points
    stress_summary = summarize_trades(stressed)

    messages = []
    if is_demo:
        messages.append('Dados 100% fictícios: resultados NÃO são evidência sobre o WIN real.')
    else:
        messages.append('Fonte histórica apenas DECLARADA: autenticidade, completude e execução real não foram verificadas.')
    if len(days) < 30:
        messages.append('Menos de 30 pregões completos no histórico inteiro: janela curta.')
    if reserve_count < 10:
        messages.append('Menos de 10 pregões no segmento final: amostra temporal insuficiente.')
    if reserve_summary['operacoes'] < 100:
        messages.append('Menos de 100 operações no segmento final: taxa de acerto instável ou indisponível.')
    if reserve_summary['operacoes'] == 0:
        messages.append('Não há operações no segmento final para avaliar o desempenho.')
    elif reserve_summary['saldo_pts'] <= 0:
        messages.append('O saldo líquido do segmento final não foi positivo.')
    if reserve_summary['operacoes'] > 0 and stress_summary['saldo_pts'] <= 0:
        messages.append(f'Com {extra_cost_points:g} pontos de custo extra por operação, o segmento final não ficou positivo.')
    messages.append('Separação temporal retrospectiva NÃO comprova teste cego: dados e regras podem já ter sido vistos.')
    messages.append('Nenhum resultado libera ordens reais; é preciso histórico independente, execução e custos verificados.')

    decision = (
        'SIMULAÇÃO — SEM EVIDÊNCIA DE MERCADO' if is_demo
        else 'EVIDÊNCIA INSUFICIENTE — SOMENTE PESQUISA'
    )
    period_rows = []
    for name, d, s in [('Estudo inicial', study_days, study_summary),
                       ('Reserva cronológica', reserve_days, reserve_summary)]:
        period_rows.append({
            'Segmento': name,
            'De': str(d[0]),
            'Até': str(d[-1]),
            'Pregões': len(d),
            'Operações': s['operacoes'],
            'Acerto líquido': s['taxa_acerto'],
            'Saldo (pts)': round(s['saldo_pts'], 2),
            'Drawdown (pts)': round(s['drawdown_pts'], 2),
        })
    day_rows = []
    for day in days:
        part = trades.loc[trade_days.eq(day)]
        summary = summarize_trades(part)
        day_rows.append({
            'Dia': str(day),
            'Grupo': 'Estudo inicial' if day in study_days else 'Reserva cronológica',
            'Operações': summary['operacoes'],
            'Saldo (pts)': round(summary['saldo_pts'], 2),
        })
    return {
        'classificacao': decision,
        'frac_reserva': reserve_fraction,
        'pregoes_estudo': len(study_days),
        'pregoes_reserva': reserve_count,
        'estudo': study_summary,
        'reserva': reserve_summary,
        'reserva_com_custo_extra': stress_summary,
        'custo_extra_pontos': extra_cost_points,
        'segmentos': pd.DataFrame(period_rows),
        'por_dia': pd.DataFrame(day_rows),
        'alertas': messages,
    }
