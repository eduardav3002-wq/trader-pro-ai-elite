"""Pesquisa offline: compara protocolo legado e trava de orçamento ANTES da entrada.

IMPORTANTE: protocolo futuro v2.2 permanece intocado; a trava v2.5 é uma
hipótese experimental posterior, nunca deve ser confundida com seu holdout.
"""
from __future__ import annotations

import pandas as pd

from backtest import backtest
from engine import analyze, validate_win_candles
from forward_validation import (
    BASE_COST_POINTS, SLIPPAGE_SCENARIOS, RISK_LIMITS, MAX_TRADES_PER_DAY,
    MAX_HOLD_BARS, MAX_DAILY_REALIZED_LOSS, MAX_CONSECUTIVE_LOSSES,
    MIN_THEORETICAL_RR, _drawdown,
)

SUMMARY_COLS = (
    'Limite (pts)', 'Slippage (ticks/lado)', 'Modo', 'Operações',
    'Saldo líquido (pts)', 'Rebaixamento máximo (pts)',
    'Sinais bloqueados pelo orçamento', 'Dias com saldo final inferior a -200 pts',
    'Operações com perda maior que 200 pts', 'Saídas com tempo intrabar incerto',
)
BLOCK_COLS = (
    'Limite (pts)', 'Slippage (ticks/lado)', 'Modo',
    'sinal_candle', 'sinal_data', 'direcao', 'decisao',
    'risco_stop_estimado_pts', 'orcamento_restante_antes_entrada_pts',
)
DAY_COLS = (
    'Limite (pts)', 'Slippage (ticks/lado)', 'Modo', 'Pregão',
    'Operações', 'Resultado realizado (pts)', 'Ultrapassou -200 pts',
)


def compare_daily_budget(history: pd.DataFrame, contract: str,
                         evaluation_start=None) -> dict:
    """Reexecuta os mesmos cenários, com/s/sem novo filtro pre-entrada.

    Não é otimização; resultados do cenário antigo reproduzem o legado.
    A auditoria de riscos de stop nao garante preço de preenchimento ou perda máxima.
    """
    checked = validate_win_candles(
        history, require_complete_sessions=True, contract=contract)
    analyzed = analyze(checked, contract=contract, profile='seletivo')
    dates = sorted(checked['datetime'].dt.date.unique())
    if evaluation_start is not None:
        start = pd.Timestamp(evaluation_start)
        if start != start.normalize():
            raise ValueError('Data de início precisa ser meia-noite do pregão.')
        dates = [d for d in dates if d >= start.date()]
        if not dates:
            raise ValueError('Não há pregões para avaliação após a data selecionada.')
    else:
        start = None
    rows, blocks, days, trades_all = [], [], [], []
    for limit in RISK_LIMITS:
        for slip in SLIPPAGE_SCENARIOS:
            for guarded in (False, True):
                trades, decisions = backtest(
                    analyzed, cost_points=BASE_COST_POINTS,
                    slippage_ticks=slip, max_daily_trades=MAX_TRADES_PER_DAY,
                    max_hold=MAX_HOLD_BARS, max_daily_loss_points=MAX_DAILY_REALIZED_LOSS,
                    contract=contract, max_trade_risk_points=limit,
                    max_consecutive_losses=MAX_CONSECUTIVE_LOSSES,
                    min_reward_risk=MIN_THEORETICAL_RR, return_audit=True,
                    enforce_pretrade_daily_budget=guarded,
                )
                if start is not None:
                    trades = trades.loc[pd.to_datetime(trades['entrada_data']).ge(start)].copy()
                    decisions = decisions.loc[pd.to_datetime(decisions['sinal_data']).ge(start)].copy()
                label = 'PROTEGIDO_V25' if guarded else 'LEGADO_V22'
                index = pd.to_datetime(trades['entrada_data']).dt.date
                day_profit = trades.groupby(index)['net_points'].sum() if len(trades) else pd.Series(dtype=float)
                blocked = decisions.loc[decisions['decisao'].eq('ORCAMENTO_DIARIO_INSUFICIENTE')].copy()
                for day in dates:
                    subset = trades.loc[index.eq(day)]
                    net = round(float(day_profit.get(day, 0)), 2)
                    days.append({
                        'Limite (pts)': limit, 'Slippage (ticks/lado)': slip,
                        'Modo': label, 'Pregão': day.isoformat(),
                        'Operações': len(subset), 'Resultado realizado (pts)': net,
                        'Ultrapassou -200 pts': net < -MAX_DAILY_REALIZED_LOSS,
                    })
                rows.append({
                    'Limite (pts)': limit, 'Slippage (ticks/lado)': slip,
                    'Modo': label, 'Operações': len(trades),
                    'Saldo líquido (pts)': round(float(trades['net_points'].sum()), 2),
                    'Rebaixamento máximo (pts)': _drawdown(trades['net_points']),
                    'Sinais bloqueados pelo orçamento': len(blocked),
                    'Dias com saldo final inferior a -200 pts': int((day_profit < -MAX_DAILY_REALIZED_LOSS).sum()),
                    'Operações com perda maior que 200 pts': int((trades['net_points'] < -MAX_DAILY_REALIZED_LOSS).sum()),
                    'Saídas com tempo intrabar incerto': int(trades['tipo_horario_saida'].eq('INICIO_CANDLE_SAIDA_INTRA_5M_TEMPO_INCERTO').sum()),
                })
                if not blocked.empty:
                    stamped = blocked.reindex(columns=['sinal_candle','sinal_data','direcao','decisao',
                        'risco_stop_estimado_pts','orcamento_restante_antes_entrada_pts']).copy()
                    stamped.insert(0, 'Modo', label)
                    stamped.insert(0, 'Slippage (ticks/lado)', slip)
                    stamped.insert(0, 'Limite (pts)', limit)
                    blocks.append(stamped)
                if len(trades):
                    stamped = trades.copy()
                    stamped.insert(0,'Modo',label)
                    stamped.insert(0,'Slippage (ticks/lado)',slip)
                    stamped.insert(0,'Limite (pts)',limit)
                    trades_all.append(stamped)
    summary = pd.DataFrame(rows, columns=SUMMARY_COLS)
    daily = pd.DataFrame(days, columns=DAY_COLS)
    blocked_df = pd.concat(blocks, ignore_index=True) if blocks else pd.DataFrame(columns=BLOCK_COLS)
    trade_df = pd.concat(trades_all, ignore_index=True) if trades_all else pd.DataFrame(
        columns=['Limite (pts)','Slippage (ticks/lado)','Modo'])
    for rec in summary.to_dict('records'):
        selected = daily.loc[
            daily['Limite (pts)'].eq(rec['Limite (pts)']) &
            daily['Slippage (ticks/lado)'].eq(rec['Slippage (ticks/lado)']) &
            daily['Modo'].eq(rec['Modo'])]
        assert round(float(selected['Resultado realizado (pts)'].sum()), 2) == rec['Saldo líquido (pts)'], 'Resultado por dia não concilia.'
    return {
        'resumo': summary,
        'bloqueios': blocked_df,
        'por_dia': daily,
        'operacoes': trade_df,
        'protocolo': {
            'versao': '2.5', 'modo': 'EXPERIMENTO_DE_ORCAMENTO_PRE_ENTRADA',
            'protocolo_v22_alterado': False, 'execucao_real': False,
            'limites_predefinidos_pts': list(RISK_LIMITS),
            'slippage_ticks_por_lado': list(SLIPPAGE_SCENARIOS),
            'limite_diario_pts': MAX_DAILY_REALIZED_LOSS,
            'regra': 'Orçamento disponível = 200 + min(0, resultado líquido realizado no dia); ganhos não ampliam orçamento. Bloqueia risco de stop projetado > orçamento disponível.',
            'alerta': 'Stop e slippage simulados; gaps, liquidez, movimentos intrabar e custos reais podem gerar perdas além de 200 pontos.',
        },
    }


def compare_guarded_future(history: pd.DataFrame, payload: bytes, provider: str,
                           contract: str, filename: str, as_of=None) -> dict:
    """Só permite comparar a nova trava depois de validar o holdout pelo protocolo antigo.

    A avaliação OFICIAL original continua sendo `evaluate_forward` da v2.2.
    Este resultado é um estudo adicional v2.5, não substitui o original.
    """
    from forward_validation import evaluate_forward
    from provenance import inspect_historical_csv
    official = evaluate_forward(history, payload, provider, contract, filename, as_of=as_of)
    new, _ = inspect_historical_csv(payload, provider, contract, filename, as_of=as_of)
    combined = pd.concat([history, new], ignore_index=True)
    extra = compare_daily_budget(combined, contract, evaluation_start=new['datetime'].min().normalize())
    extra['protocolo']['recibo_validacao_v22'] = {
        'sha256_csv_avaliacao': official['recibo']['sha256_csv_avaliacao'],
        'pregoes_avaliados': official['recibo']['pregoes_avaliados'],
        'avaliacao_inicio': official['recibo']['avaliacao_inicio'],
        'avaliacao_fim': official['recibo']['avaliacao_fim'],
    }
    return extra
