"""Avaliação cronológica pré-especificada do WINZ26 em pregões inéditos.

Não certifica preços nem promete retorno. Não cria ordens ou dados.
A amostra anterior serve só de aquecimento dos indicadores; métricas e
relatórios excluem operações anteriores à primeira sessão de avaliação.
"""

from __future__ import annotations

import hashlib

import pandas as pd

from backtest import backtest
from engine import analyze, validate_win_candles
from provenance import inspect_historical_csv, missing_trading_days

# Parâmetros pré-registrados na versão 2.0; não reajustar após olhar o holdout.
RISK_LIMITS = (125, 175, 250, 500)
BASE_COST_POINTS = 2.0
SLIPPAGE_SCENARIOS = (1, 2, 3)  # ticks ADVERSOS por lado, tick = 5 pts
MAX_TRADES_PER_DAY = 3
MAX_HOLD_BARS = 12
MAX_DAILY_REALIZED_LOSS = 200.0
MAX_CONSECUTIVE_LOSSES = 2
MIN_THEORETICAL_RR = 1.0
SUMMARY_COLUMNS = (
    'Limite (pts)', 'Operações', 'Saldo líquido (pts)',
    'Rebaixamento máximo (pts)', 'Dias com operação', 'Dias avaliados',
    'Taxa de acerto (%)',
)
DETAIL_COLUMNS = ('Limite (pts)', 'Cenário', *(
    'sinal_candle', 'entrada_candle', 'saida_candle', 'direcao',
    'entrada', 'stop', 'alvo', 'saida', 'motivo',
    'gross_points', 'cost_points', 'slippage_points', 'net_points',
    'entrada_data', 'saida_data', 'tipo_horario_saida',
    'risco_stop_estimado_pts', 'rr_teorico',
))


def _drawdown(values) -> float:
    gains = pd.to_numeric(pd.Series(values, dtype='float64'), errors='raise')
    equity = pd.concat([pd.Series([0.0]), gains.cumsum()], ignore_index=True)
    return round(float((equity.cummax() - equity).max()), 2)


def _simulate(analyzed: pd.DataFrame, contract: str, *, limit: int,
              slip: int, evaluation_start: pd.Timestamp) -> pd.DataFrame:
    trades = backtest(
        analyzed, cost_points=BASE_COST_POINTS, slippage_ticks=slip,
        max_daily_trades=MAX_TRADES_PER_DAY, max_hold=MAX_HOLD_BARS,
        max_daily_loss_points=MAX_DAILY_REALIZED_LOSS, contract=contract,
        max_trade_risk_points=limit,
        max_consecutive_losses=MAX_CONSECUTIVE_LOSSES,
        min_reward_risk=MIN_THEORETICAL_RR,
    )
    # Backtest do histórico inteiro para conservar o aquecimento, mas a análise
    # jamais soma operações da amostra de 10 a 19/11.
    return trades.loc[pd.to_datetime(trades['entrada_data']) >= evaluation_start].copy()


def _stats(trades: pd.DataFrame, sessions: int) -> dict:
    net = trades['net_points'].astype(float)
    days = pd.to_datetime(trades['entrada_data']).dt.date
    return {
        'Operações': int(len(trades)),
        'Saldo líquido (pts)': round(float(net.sum()), 2),
        'Rebaixamento máximo (pts)': _drawdown(net),
        'Dias com operação': int(days.nunique()),
        'Dias avaliados': int(sessions),
        'Taxa de acerto (%)': round(float(net.gt(0).mean() * 100), 1) if len(net) else None,
    }



def sample_stress(history: pd.DataFrame, contract: str) -> pd.DataFrame:
    """Estresse SOMENTE exploratório da amostra interna: não há holdout aqui."""
    baseline = validate_win_candles(
        history, require_complete_sessions=True, contract=contract,
    )
    analyzed = analyze(baseline, contract=contract, profile='seletivo')
    dates = int(baseline['datetime'].dt.date.nunique())
    rows = []
    for limit in RISK_LIMITS:
        for slip in SLIPPAGE_SCENARIOS:
            trades = _simulate(analyzed, contract, limit=limit, slip=slip,
                               evaluation_start=baseline['datetime'].min())
            stats = _stats(trades, dates)
            rows.append({
                'Limite (pts)': limit,
                'Slippage (ticks por lado)': slip,
                'Operações': stats['Operações'],
                'Saldo líquido (pts)': stats['Saldo líquido (pts)'],
                'Rebaixamento máximo (pts)': stats['Rebaixamento máximo (pts)'],
            })
    return pd.DataFrame(rows)


def evaluate_forward(history: pd.DataFrame, payload: bytes, provider: str, contract: str,
                     filename: str, as_of=None) -> dict:
    """Valida dados posteriores e calcula cenários INALTERADOS e estresse.

    Retorna resumo, operações, por-dia, estresse e recibo rastreável. Os cenários
    de estresse são novos backtests: risco/RR e elegibilidade podem mudar.
    """
    baseline = validate_win_candles(
        history, require_complete_sessions=True, contract=contract,
    )
    future, source = inspect_historical_csv(payload, provider, contract, filename, as_of=as_of)
    if not source['ticker_presente_no_csv']:
        raise ValueError('Validação de pregões novos exige a coluna contrato/symbol/ticker em cada candle.')
    start = future['datetime'].min().normalize()
    if start <= baseline['datetime'].max().normalize():
        raise ValueError('O arquivo de avaliação deve conter apenas pregões posteriores à amostra inicial.')
    combined = pd.concat([baseline, future], ignore_index=True)
    missing = missing_trading_days(combined)
    if missing:
        raise ValueError('Existem pregões faltando entre amostra e avaliação: '
                         + ', '.join(missing[:6]))

    dates = sorted(future['datetime'].dt.date.unique())
    analyzed = analyze(combined, contract=contract, profile='seletivo')
    summaries, details, daily, stresses = [], [], [], []

    for limit in RISK_LIMITS:
        for slip in SLIPPAGE_SCENARIOS:
            trades = _simulate(analyzed, contract, limit=limit, slip=slip,
                               evaluation_start=start)
            stats = _stats(trades, len(dates))
            row = {'Limite (pts)': limit, **stats}
            if slip == SLIPPAGE_SCENARIOS[0]:
                summaries.append(row)
                day_index = pd.to_datetime(trades['entrada_data']).dt.date
                for day in dates:
                    day_trades = trades.loc[day_index.eq(day)]
                    values = day_trades['net_points'].astype(float)
                    daily.append({
                        'Limite (pts)': limit,
                        'Dia': day.isoformat(),
                        'Operações': len(day_trades),
                        'Saldo líquido (pts)': round(float(values.sum()), 2),
                    })
                if not trades.empty:
                    labeled = trades.copy()
                    labeled.insert(0, 'Cenário', 'Base · 1 tick/lado')
                    labeled.insert(0, 'Limite (pts)', limit)
                    details.append(labeled)
            stresses.append({
                'Limite (pts)': limit,
                'Slippage (ticks por lado)': slip,
                'Operações': stats['Operações'],
                'Saldo líquido (pts)': stats['Saldo líquido (pts)'],
                'Rebaixamento máximo (pts)': stats['Rebaixamento máximo (pts)'],
            })

    receipt = {
        'versao': '2.2',
        'classificacao': 'FORWARD_EXPLORATORIO_NAO_AUTENTICADO',
        'origem_verificada_independentemente': False,
        'ordens_liberadas': False,
        'arquivo': source['nome_arquivo'],
        'fonte_declarada': source['fonte_declarada'],
        'contrato': source['contrato_declarado'],
        'sha256_csv_avaliacao': source['sha256'],
        'sha256_amostra_normalizada': hashlib.sha256(
            baseline.to_csv(index=False).encode('utf-8'),
        ).hexdigest(),
        'amostra_inicio': str(baseline['datetime'].min()),
        'amostra_fim': str(baseline['datetime'].max()),
        'avaliacao_inicio': str(future['datetime'].min()),
        'avaliacao_fim': str(future['datetime'].max()),
        'pregoes_avaliados': len(dates),
        'candles_avaliados': len(future),
        'parametros_congelados': {
            'perfil': 'seletivo', 'limites_de_risco_pts': list(RISK_LIMITS),
            'custo_pts_por_operacao_completa': BASE_COST_POINTS,
            'slippage_base_ticks_por_lado': SLIPPAGE_SCENARIOS[0],
            'slippage_estresse_ticks_por_lado': list(SLIPPAGE_SCENARIOS[1:]),
            'max_operacoes_por_dia': MAX_TRADES_PER_DAY,
            'max_candles_por_operacao': MAX_HOLD_BARS,
            'limite_perda_realizada_dia_pts': MAX_DAILY_REALIZED_LOSS,
            'perdas_consecutivas_para_pausa': MAX_CONSECUTIVE_LOSSES,
            'rr_minimo_teorico': MIN_THEORETICAL_RR,
        },
        'alertas': [
            'Uma declaração de origem ou hash SHA-256 não autentica os preços da B3.',
            'A amostra de 10–19/11 é usada para aquecimento, não integra métricas futuras.',
            'Comparação entre quatro limites é exploratória; não eleger o maior saldo como ótimo.',
            'Estresse refaz entradas e saídas; mudar slippage muda risco/RR e número de operações.',
            'O risco realizado pode ultrapassar stop e limite diário por gaps/slippage.',
            'Mesmo resultados positivos não constituem evidência suficiente de rentabilidade futura.',
        ],
    }
    return {
        'resumo': pd.DataFrame(summaries, columns=SUMMARY_COLUMNS),
        'operacoes': pd.concat(details, ignore_index=True) if details
                    else pd.DataFrame(columns=DETAIL_COLUMNS),
        'por_dia': pd.DataFrame(daily),
        'estresse': pd.DataFrame(stresses),
        'recibo': receipt,
    }
