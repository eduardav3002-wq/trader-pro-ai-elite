"""Trader Pro AI Elite v2.6: avaliação prospectiva dupla, sem seleção de vencedor.

A v2.2 é o protocolo original (pré-registrado); a proteção v2.5 foi
concebida após observar o histórico e é um protocolo COMPLEMENTAR.
Sem dados genuínos posteriores ao último pregão de aquecimento, não há métricas.
"""
from __future__ import annotations

import hashlib
import json

import pandas as pd

from daily_budget_v25 import compare_daily_budget
from engine import validate_win_candles
from forward_validation import (
    evaluate_forward, RISK_LIMITS, SLIPPAGE_SCENARIOS, BASE_COST_POINTS,
    MAX_TRADES_PER_DAY, MAX_HOLD_BARS, MAX_DAILY_REALIZED_LOSS,
    MAX_CONSECUTIVE_LOSSES, MIN_THEORETICAL_RR,
)
from provenance import inspect_historical_csv

BASELINE_SHA256 = '1c60f464372f30af9571b5ae9e43f09642fbd8e2eb09dcd230d623421b8e42c9'
CONTRACT = 'WINZ26'
ORIGINAL_START = '2026-11-23'
PROTOCOL_V22 = {
    'contrato': CONTRACT, 'perfil': 'seletivo',
    'limites_risco_pontos': [125, 175, 250, 500],
    'taxa_pontos_operacao_completa': 2.0,
    'slippage_ticks_por_lado': [1, 2, 3],
    'max_operacoes_dia': 3, 'max_candles_posicao': 12,
    'limite_perda_realizada_dia_pontos': 200.0,
    'pausa_apos_perdas_seguidas': 2, 'rr_minimo': 1.0,
    'versao_origem': '2.2',
}
PROTOCOL_V25 = {
    'base': 'v2.2', 'versao_origem': '2.5',
    'regra_adicional': 'pretrade_budget', 'orcamento_inicial_pontos': 200.0,
    'orcamento_resta': '200 + min(0, pnl_liquido_realizado_dia)',
    'lucros_nao_aumentam_orcamento': True,
}


def _sha_protocol(protocol: dict) -> str:
    return hashlib.sha256(json.dumps(protocol, sort_keys=True, ensure_ascii=False,
                                      separators=(',', ':')).encode('utf-8')).hexdigest()


def _baseline(history: pd.DataFrame) -> pd.DataFrame:
    checked = validate_win_candles(history, require_complete_sessions=True,
                                   contract=CONTRACT)
    actual = hashlib.sha256(checked.to_csv(index=False).encode('utf-8')).hexdigest()
    if actual != BASELINE_SHA256:
        raise ValueError('Amostra de aquecimento não corresponde à base congelada. '
                         'Restaure WINZ26_B3_2026-11-10_a_19_M5.csv da versão oficial do projeto.')
    if str(checked.datetime.max().date()) != '2026-11-19' or len(checked) != 904:
        raise ValueError('Amostra congelada com período ou contagem inválida.')
    return checked


def evaluate_prospective_v26(history: pd.DataFrame, payload: bytes, provider: str,
                             filename: str, as_of=None) -> dict:
    """Valida INTEGRALMENTE o holdout antes de computar os dois protocolos.

    Um único arquivo de pregões novos, com ticker explícito, horas fechadas e
    sem lacunas cronológicas. Nunca autentica a origem externamente.
    """
    actual_settings = (
        list(RISK_LIMITS), BASE_COST_POINTS, list(SLIPPAGE_SCENARIOS),
        MAX_TRADES_PER_DAY, MAX_HOLD_BARS, MAX_DAILY_REALIZED_LOSS,
        MAX_CONSECUTIVE_LOSSES, MIN_THEORETICAL_RR,
    )
    protocol_settings = (
        PROTOCOL_V22['limites_risco_pontos'],
        PROTOCOL_V22['taxa_pontos_operacao_completa'],
        PROTOCOL_V22['slippage_ticks_por_lado'],
        PROTOCOL_V22['max_operacoes_dia'], PROTOCOL_V22['max_candles_posicao'],
        PROTOCOL_V22['limite_perda_realizada_dia_pontos'],
        PROTOCOL_V22['pausa_apos_perdas_seguidas'], PROTOCOL_V22['rr_minimo'],
    )
    if actual_settings != protocol_settings:
        raise ValueError('Parâmetros do motor não correspondem ao protocolo congelado. '
                         'Restaure os arquivos originais antes de avaliar dados novos.')
    old = _baseline(history)
    future, source = inspect_historical_csv(
        payload, provider, CONTRACT, filename, as_of=as_of)
    if not source['ticker_presente_no_csv']:
        raise ValueError('CSV futuro precisa de coluna contrato, symbol ou ticker '
                         'com WINZ26 em TODAS as linhas.')
    if str(future.datetime.min().date()) < ORIGINAL_START:
        raise ValueError('O primeiro pregão precisa ser posterior a 19/11/2026.')
    # Refaz a validação v2.2 sem modificar UMA regra ou valor do protocolo.
    original = evaluate_forward(old, payload, provider, CONTRACT, filename, as_of=as_of)
    receipt = original['recibo']
    if (receipt['sha256_csv_avaliacao'] != source['sha256'] or
            receipt['sha256_amostra_normalizada'] != BASELINE_SHA256):
        raise ValueError('Recibos de entrada divergentes. Avaliação bloqueada.')
    both = pd.concat([old, future], ignore_index=True)
    guarded = compare_daily_budget(both, CONTRACT,
                                   evaluation_start=future.datetime.min().normalize())
    summary = guarded['resumo'].copy()
    expected_scenarios = {(int(l), int(s)) for l in RISK_LIMITS for s in SLIPPAGE_SCENARIOS}
    for mode in ('LEGADO_V22', 'PROTEGIDO_V25'):
        subset = summary.loc[summary['Modo'].eq(mode)]
        observed = set(zip(subset['Limite (pts)'].astype(int), subset['Slippage (ticks/lado)'].astype(int)))
        if len(subset) != len(expected_scenarios) or observed != expected_scenarios:
            raise ValueError('Faltam cenários congelados da avaliação. Nenhum relatório liberado.')
    # Reconcilia o lado legado do estudo novo com a versão 2.2 PRE-REGISTRADA.
    legacy = summary.loc[summary['Modo'].eq('LEGADO_V22')]
    expected = original['estresse'].rename(columns={
        'Slippage (ticks por lado)': 'Slippage (ticks/lado)',
    })
    check = legacy.merge(expected, on=['Limite (pts)', 'Slippage (ticks/lado)'],
                         how='outer', validate='one_to_one', suffixes=('_v26', '_v22'),
                         indicator=True)
    if (not check['_merge'].eq('both').all() or
            not check['Operações_v26'].eq(check['Operações_v22']).all() or
            not (check['Saldo líquido (pts)_v26'] - check['Saldo líquido (pts)_v22']).abs().le(.011).all() or
            not (check['Rebaixamento máximo (pts)_v26'] - check['Rebaixamento máximo (pts)_v22']).abs().le(.011).all()):
        raise ValueError('Divergência entre o motor legado v2.2 e a reexecução v2.6. '
                         'Resultados bloqueados para auditoria.')
    # Conciliação dia a dia, inclusive pregões sem operações.
    for record in summary.to_dict('records'):
        d = guarded['por_dia']
        mask = (d['Modo'].eq(record['Modo']) &
                d['Limite (pts)'].eq(record['Limite (pts)']) &
                d['Slippage (ticks/lado)'].eq(record['Slippage (ticks/lado)']))
        if not mask.any() or round(float(d.loc[mask, 'Resultado realizado (pts)'].sum()), 2) != record['Saldo líquido (pts)']:
            raise ValueError('Conciliação diária falhou. Resultado não será exibido.')
    selected = summary.loc[summary['Modo'].eq('PROTEGIDO_V25')].copy()
    joined = legacy.merge(selected,
                          on=['Limite (pts)', 'Slippage (ticks/lado)'],
                          validate='one_to_one', suffixes=('_original', '_protegido'))
    comp = joined[['Limite (pts)', 'Slippage (ticks/lado)',
                   'Operações_original', 'Operações_protegido',
                   'Saldo líquido (pts)_original', 'Saldo líquido (pts)_protegido',
                   'Rebaixamento máximo (pts)_original',
                   'Rebaixamento máximo (pts)_protegido',
                   'Sinais bloqueados pelo orçamento_protegido']].copy()
    comp['Diferença saldo (protegido − original) pts'] = (
        comp['Saldo líquido (pts)_protegido'] - comp['Saldo líquido (pts)_original']).round(2)
    comp = comp.sort_values(['Limite (pts)', 'Slippage (ticks/lado)']).reset_index(drop=True)
    new_days = sorted(future.datetime.dt.date.unique())
    for day in guarded['por_dia']['Pregão'].unique():
        if day not in [d.isoformat() for d in new_days]:
            raise ValueError('Relatório contém pregão da amostra de aquecimento.')
    protocol_receipt = {
        'versao_interface': '2.6',
        'estado': 'AVALIACAO_FORA_AMOSTRA_EXPLORATORIA_SE_ORIGEM_GENUINA',
        'execucao_real': False, 'ia_treinada': False,
        'fonte_verificada_independentemente': False,
        'data_primeiro_pregao_elegivel': ORIGINAL_START,
        'qtd_pregoes_novos': len(new_days),
        'datas_novas': [d.isoformat() for d in new_days],
        'candles_novos': int(len(future)),
        'contrato': CONTRACT,
        'arquivo': source['nome_arquivo'], 'fonte_declarada': source['fonte_declarada'],
        'sha256_csv_novos': source['sha256'],
        'sha256_base_congelada': BASELINE_SHA256,
        'protocolo_v22': PROTOCOL_V22,
        'sha256_protocolo_v22': _sha_protocol(PROTOCOL_V22),
        'protocolo_v25': PROTOCOL_V25,
        'sha256_protocolo_v25': _sha_protocol(PROTOCOL_V25),
        'recibo_original_v22': receipt,
        'checagem_conciliacao_v22': '12 cenários e resultados idênticos',
        'alertas': [
            'Dados com origem declarada, NÃO autenticada independentemente.',
            'Amostra inicial serve SOMENTE de aquecimento dos indicadores.',
            'Protocolo v2.5 surgiu após análise dos oito pregões iniciais; avaliar sem reajustá-lo.',
            'A avaliação de apenas poucos pregões NÃO valida rentabilidade, nem uma IA.',
            'Cenários alternativos NÃO são uma escolha de vencedor; não selecionar o maior saldo.',
            'Resultados hipotéticos: OHLC M5 não identifica a sequência real de execuções intrabar.',
            'Proteção de orçamento não limita com certeza perdas reais.',
            'O SHA-256 identifica bytes; não comprova autenticidade dos negócios.',
        ],
    }
    return {'comparativo': comp, 'resumo_completo': summary,
            'por_dia': guarded['por_dia'], 'bloqueios': guarded['bloqueios'],
            'operacoes': guarded['operacoes'], 'recibo': protocol_receipt}
