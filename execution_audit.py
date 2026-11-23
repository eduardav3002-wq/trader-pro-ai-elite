"""Diagnóstico pareado de cenários de slippage do backtest de pesquisa.

Compara explicitamente trades por índice do candle-sinal, atribui divergências
à seleção de operações, à mudança do caminho de saída e ao custo puro.
NÃO altera o backtest, o perfil ou os parâmetros congelados da v2.2.
"""
from __future__ import annotations

import pandas as pd

from backtest import backtest, COLUMNS
from engine import analyze, validate_win_candles
from forward_validation import (
    BASE_COST_POINTS, MAX_CONSECUTIVE_LOSSES, MAX_DAILY_REALIZED_LOSS,
    MAX_HOLD_BARS, MAX_TRADES_PER_DAY, MIN_THEORETICAL_RR,
    RISK_LIMITS, SLIPPAGE_SCENARIOS, _drawdown,
)

COMPARISON_COLUMNS = (
    'Limite (pts)', 'Slippage base (ticks/lado)', 'Slippage comparado (ticks/lado)',
    'Operações base', 'Operações comparadas', 'Operações em comum',
    'Só na base', 'Só no comparado', 'Mudaram saída',
    'Saldo base (pts)', 'Saldo comparado (pts)', 'Variação líquida (pts)',
    'Variação do resultado bruto (pts)', 'Variação dos custos (pts)',
    'Rebaixamento base (pts)', 'Rebaixamento comparado (pts)',
)
DETAIL_COLUMNS = (
    'Limite (pts)', 'Slippage base (ticks/lado)', 'Slippage comparado (ticks/lado)',
    'Candle sinal', 'Data entrada', 'Direção', 'Correspondência',
    'Motivo sem operação', 'Saída base', 'Saída comparada',
    'Candle saída base', 'Candle saída comparada',
    'Saldo base (pts)', 'Saldo comparado (pts)', 'Variação líquida (pts)',
    'Variação bruta (pts)', 'Variação de custos (pts)', 'Categoria da mudança',
)


def audit_slippage_scenarios(history: pd.DataFrame, contract: str,
                             evaluation_start=None) -> dict:
    """Retorna auditoria por cenário, pares e trade; apenas pesquisa offline.

    Se evaluation_start foi especificado, resultados excluem entradas anteriores.
    O aquecimento continua no histórico integral. Em produção, o filtro deve ser
    primeiro candle de uma sessão NOVA, conforme a validação futura v2.2.
    """
    baseline = validate_win_candles(history, require_complete_sessions=True, contract=contract)
    analyzed = analyze(baseline, contract=contract, profile='seletivo')
    if evaluation_start is not None:
        evaluation_start = pd.Timestamp(evaluation_start)
        if evaluation_start != evaluation_start.normalize():
            raise ValueError('O início da avaliação deve ser a abertura de um dia, sem hora.')
    runs = {}
    summary = []
    details = []
    raw = []

    for limit in RISK_LIMITS:
        for slip in SLIPPAGE_SCENARIOS:
            trades, decisions = backtest(
                analyzed, cost_points=BASE_COST_POINTS, slippage_ticks=slip,
                max_daily_trades=MAX_TRADES_PER_DAY, max_hold=MAX_HOLD_BARS,
                max_daily_loss_points=MAX_DAILY_REALIZED_LOSS, contract=contract,
                max_trade_risk_points=limit,
                max_consecutive_losses=MAX_CONSECUTIVE_LOSSES,
                min_reward_risk=MIN_THEORETICAL_RR, return_audit=True,
            )
            if evaluation_start is not None:
                trades = trades.loc[pd.to_datetime(trades['entrada_data']).ge(evaluation_start)].copy()
                decisions = decisions.loc[pd.to_datetime(decisions['sinal_data']).ge(evaluation_start)].copy()
            assert not trades['sinal_candle'].duplicated().any(), 'Um candle sinal não pode criar duas operações.'
            runs[limit, slip] = (trades.set_index('sinal_candle', drop=False),
                                 decisions.set_index('sinal_candle', drop=False))
            if not trades.empty:
                stamped = trades.copy()
                stamped.insert(0, 'Slippage (ticks por lado)', slip)
                stamped.insert(0, 'Limite (pts)', limit)
                raw.append(stamped)
        base, base_decisions = runs[limit, SLIPPAGE_SCENARIOS[0]]
        for other_slip in SLIPPAGE_SCENARIOS[1:]:
            other, other_decisions = runs[limit, other_slip]
            common = base.index.intersection(other.index)
            only_base = base.index.difference(other.index)
            only_other = other.index.difference(base.index)
            changed = 0
            for signal in sorted(base.index.union(other.index)):
                b = base.loc[signal] if signal in base.index else None
                o = other.loc[signal] if signal in other.index else None
                both = b is not None and o is not None
                if both:
                    exit_changed = (b['motivo'] != o['motivo'] or
                                    b['saida_candle'] != o['saida_candle'] or
                                    round(float(b['saida']) + (1 if b['direcao']=='COMPRA' else -1) * 5 * SLIPPAGE_SCENARIOS[0], 6) !=
                                    round(float(o['saida']) + (1 if o['direcao']=='COMPRA' else -1) * 5 * other_slip, 6))
                    # exit_mid, not the slip-adjusted fill, determines path changes.
                    if exit_changed:
                        changed += 1
                    label = 'SAIDA_OU_CAMINHO_ALTERADO' if exit_changed else 'MESMA_SAIDA_CUSTO_MAIOR'
                    match = 'AMBOS'
                    missing_reason = ''
                elif b is not None:
                    label, match = 'OPERACAO_BLOQUEADA', 'SO_BASE'
                    missing_reason = (other_decisions.at[signal,'decisao']
                                      if signal in other_decisions.index else 'SEM_DECISAO')
                else:
                    label, match = 'OPERACAO_ADICIONADA', 'SO_COMPARADO'
                    missing_reason = (base_decisions.at[signal,'decisao']
                                      if signal in base_decisions.index else 'SEM_DECISAO')
                bnet, onet = (round(float(r['net_points']),2) if r is not None else 0.0 for r in (b,o))
                bgross, ogross = (round(float(r['gross_points']),2) if r is not None else 0.0 for r in (b,o))
                btotal, ototal = ((float(r['cost_points']) + float(r['slippage_points']))
                                  if r is not None else 0.0 for r in (b,o))
                details.append({
                    'Limite (pts)': limit,
                    'Slippage base (ticks/lado)': SLIPPAGE_SCENARIOS[0],
                    'Slippage comparado (ticks/lado)': other_slip,
                    'Candle sinal': int(signal),
                    'Data entrada': (b if b is not None else o)['entrada_data'],
                    'Direção': (b if b is not None else o)['direcao'],
                    'Correspondência': match,
                    'Motivo sem operação': missing_reason,
                    'Saída base': b['motivo'] if b is not None else '—',
                    'Saída comparada': o['motivo'] if o is not None else '—',
                    'Candle saída base': int(b['saida_candle']) if b is not None else None,
                    'Candle saída comparada': int(o['saida_candle']) if o is not None else None,
                    'Saldo base (pts)': bnet, 'Saldo comparado (pts)': onet,
                    'Variação líquida (pts)': round(onet-bnet,2),
                    'Variação bruta (pts)': round(ogross-bgross,2),
                    'Variação de custos (pts)': round(-(ototal-btotal),2),
                    'Categoria da mudança': label,
                })
            summary.append({
                'Limite (pts)': limit,
                'Slippage base (ticks/lado)': SLIPPAGE_SCENARIOS[0],
                'Slippage comparado (ticks/lado)': other_slip,
                'Operações base': len(base), 'Operações comparadas': len(other),
                'Operações em comum': len(common), 'Só na base': len(only_base),
                'Só no comparado': len(only_other), 'Mudaram saída': changed,
                'Saldo base (pts)': round(float(base.net_points.sum()), 2),
                'Saldo comparado (pts)': round(float(other.net_points.sum()), 2),
                'Variação líquida (pts)': round(float(other.net_points.sum()-base.net_points.sum()), 2),
                'Variação do resultado bruto (pts)': round(float(other.gross_points.sum()-base.gross_points.sum()), 2),
                'Variação dos custos (pts)': round(-float(
                    (other.cost_points+other.slippage_points).sum() -
                    (base.cost_points+base.slippage_points).sum()), 2),
                'Rebaixamento base (pts)': _drawdown(base.net_points),
                'Rebaixamento comparado (pts)': _drawdown(other.net_points),
            })

    paired = pd.DataFrame(summary, columns=COMPARISON_COLUMNS)
    per_trade = pd.DataFrame(details, columns=DETAIL_COLUMNS)
    if not paired.empty:
        if not (paired['Variação líquida (pts)'].round(2) ==
                (paired['Variação do resultado bruto (pts)'] + paired['Variação dos custos (pts)']).round(2)).all():
            raise AssertionError('Decomposição de P&L inconsistente.')
        for record in paired.itertuples(index=False):
            subset = per_trade.loc[(per_trade['Limite (pts)'] == record[0]) &
                                   (per_trade['Slippage comparado (ticks/lado)'] == record[2])]
            if round(subset['Variação líquida (pts)'].sum(),2) != record[11]:
                raise AssertionError('Pareamento de operações inconsistente.')
    return {
        'comparacoes': paired,
        'operacoes_pareadas': per_trade,
        'operacoes_por_cenario': pd.concat(raw, ignore_index=True) if raw else pd.DataFrame(
            columns=['Limite (pts)','Slippage (ticks por lado)',*COLUMNS]),
    }
