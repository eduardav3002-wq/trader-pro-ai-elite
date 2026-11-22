"""Trader Pro AI Elite v1.7 — comparação M1 entre dois arquivos declarados.

NÃO autentica origem, não valida tickers, não libera sinais, backtests ou ordens.
Compara SOMENTE preços ORIGINAIS em timestamps + contratos idênticos; sem
interpolação, fuso inferido, alinhamento por deslocamento ou ajuste de rolagem.
"""
from __future__ import annotations

import hashlib
from typing import Any

import pandas as pd

from source_lab import _read_content, inspect_ticker_m1

KEYS = ['datetime', 'contrato']
PRICES = ['open', 'high', 'low', 'close']
MAX_EVENTS = 500  # Limite para interface móvel; totais continuam completos.


def _validated(raw: bytes, label: str, tz: str, filename: str):
    if not isinstance(raw, bytes):
        raise ValueError('Os dois arquivos precisam ser enviados como bytes CSV/TSV.')
    # Reutiliza validação rigorosa: duplicidade, OHLC, grade 5 pontos,
    # cronologia, datas, formato, limite de arquivo.
    inspect_ticker_m1(raw, label, tz, filename)
    df = _read_content(raw)
    df['datetime'] = pd.to_datetime(df['datetime'], errors='raise')
    df['contrato'] = df['contrato'].astype(str).str.strip().str.upper()
    for key in PRICES:
        df[key] = pd.to_numeric(df[key], errors='raise')
    if 'volume' in df.columns:
        df['volume'] = pd.to_numeric(df['volume'], errors='raise')
    df = df[KEYS + PRICES + (['volume'] if 'volume' in df.columns else [])].copy()
    return df


def compare_independent_m1(
    raw_a: bytes, raw_b: bytes, source_a: str, source_b: str,
    tz_a: str, tz_b: str, filename_a: str = 'fonte_a.csv', filename_b: str = 'fonte_b.csv',
    ref_a: str = '', ref_b: str = '',
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    """Resumo, comparação por dia, divergências (até MAX_EVENTS linhas).

    Fonte e URLs são apenas DECLARAÇÕES. Se não houver provas externas, 0 dias
    são autenticados, independentemente do número de preços coincidentes.
    """
    source_a, source_b = source_a.strip(), source_b.strip()
    if not source_a or not source_b:
        raise ValueError('Informe a fonte declarada dos dois arquivos.')
    if (not isinstance(ref_a, str)) or (not isinstance(ref_b, str)) or len(ref_a) > 2048 or len(ref_b) > 2048:
        raise ValueError('Referências documentais precisam ter até 2048 caracteres.')
    a = _validated(raw_a, source_a, tz_a, filename_a)
    b = _validated(raw_b, source_b, tz_b, filename_b)
    sha_a = hashlib.sha256(raw_a).hexdigest()
    sha_b = hashlib.sha256(raw_b).hexdigest()
    same_bytes = sha_a == sha_b
    same_reference = bool(ref_a.strip() and ref_b.strip() and ref_a.strip().rstrip('/') == ref_b.strip().rstrip('/'))
    same_source_label = source_a.casefold() == source_b.casefold()
    same_timezone = tz_a == tz_b
    known_tz = tz_a != 'Desconhecido' and tz_b != 'Desconhecido'

    matched = a.merge(b, on=KEYS, how='outer', suffixes=('_a','_b'), indicator=True,
                      validate='one_to_one', sort=True)
    overlap = matched['_merge'].eq('both')
    both_have_volume = 'volume_a' in matched.columns and 'volume_b' in matched.columns
    if both_have_volume:
        matched['dif_volume'] = (matched['volume_b']-matched['volume_a']).where(overlap)
        volume_diff_count = int((overlap & matched['dif_volume'].abs().gt(1e-8)).sum())
    else:
        volume_diff_count = None
    only_a = int(matched['_merge'].eq('left_only').sum())
    only_b = int(matched['_merge'].eq('right_only').sum())
    for price in PRICES:
        # A comparação é exata na grade discreta de 5 pontos, sem tolerância inventada.
        matched[f'dif_{price}'] = (matched[f'{price}_b'] - matched[f'{price}_a']).where(overlap)
    diff = matched[[f'dif_{k}' for k in PRICES]].abs().gt(1e-8).any(axis=1) & overlap
    equal = overlap & ~diff
    dif_count = int(diff.sum())
    count_equal = int(equal.sum())
    common = int(overlap.sum())
    max_abs = (float(matched.loc[overlap,[f'dif_{c}' for c in PRICES]].abs().max().max())
               if common else None)
    same_original_content = bool(common == len(a) == len(b) and dif_count == 0)
    if same_bytes:
        classification = 'MESMO_ARQUIVO_NAO_INDEPENDENTE'
    elif not same_timezone:
        classification = 'FUSOS_DECLARADOS_INCOMPATIVEIS'
    elif common == 0:
        classification = 'SEM_SOBREPOSICAO_EXATA'
    elif dif_count:
        classification = 'PRECOS_DIVERGENTES'
    else:
        classification = 'PRECOS_COINCIDENTES_ORIGEM_NAO_COMPROVADA'

    matched['dia'] = matched['datetime'].dt.strftime('%Y-%m-%d')
    matched['ticker'] = matched['contrato']
    matched['em_ambos'] = overlap
    matched['precos_diferentes'] = diff
    matched['so_a'] = matched['_merge'].eq('left_only')
    matched['so_b'] = matched['_merge'].eq('right_only')
    daily = matched.groupby(['dia','ticker'],sort=True).agg(
        em_ambos=('em_ambos','sum'),
        divergencias_ohlc=('precos_diferentes','sum'),
        apenas_fonte_a=('so_a','sum'), apenas_fonte_b=('so_b','sum'),
    ).reset_index()
    daily['precos_identicos'] = daily['em_ambos'] - daily['divergencias_ohlc']
    daily['classificacao'] = 'NAO_AUTENTICADO'
    # Os dois relatórios principais exibem o que não coincide, sem misturar OHLC ajustados.
    selected = matched.loc[~equal, ['datetime','ticker','_merge']+
                           [f'{p}_{side}' for p in PRICES for side in ('a','b')]+
                           [f'dif_{p}' for p in PRICES]].copy()
    selected['motivo'] = selected['_merge'].map({'left_only':'AUSENTE_B','right_only':'AUSENTE_A','both':'OHLC_DIVERGENTE'}).astype(str)
    selected.drop(columns=['_merge'],inplace=True)
    total_events = len(selected)
    events = selected.head(MAX_EVENTS).reset_index(drop=True)
    alerts = []
    if same_bytes:
        alerts.append('Os hashes SHA-256 são idênticos: não são duas amostras independentes.')
    if same_original_content and not same_bytes:
        alerts.append('Todos os OHLC e horários dos dois arquivos coincidem; podem ser uma cópia ou reexportação, não duas origens independentes.')
    if same_source_label or same_reference:
        alerts.append('As fontes ou referências declaradas coincidem; não há evidência de fornecedor independente.')
    if not same_timezone:
        alerts.append('Fusos declarados diferentes. Timestamps NÃO foram convertidos nem alinhados; comparação temporal não certificada.')
    if not known_tz:
        alerts.append('Pelo menos um fuso é desconhecido. Mesmo timestamps iguais não provam simultaneidade.')
    if common == 0:
        alerts.append('Sem minutos com contrato e timestamp idênticos; não é possível comparar preços.')
    if only_a or only_b:
        alerts.append('Existem minutos presentes somente em uma fonte; não foram preenchidos nem interpolados.')
    if volume_diff_count is not None:
        alerts.append('Volumes comparados somente como números declarados; unidades, volume real e tick volume podem diferir e exigem documentação.')
    if dif_count:
        alerts.append('Preços originais divergentes; investigar fornecedor, fuso, série de ajuste e política de preços.')
    alerts.append('Mesmo preços coincidentes não confirmam independência, corretora, licença, fuso ou origem B3.')
    results = {
        'versao':'1.7', 'classificacao':classification,
        'arquivo_a':filename_a, 'arquivo_b':filename_b,
        'fonte_a_declarada':source_a, 'fonte_b_declarada':source_b,
        'referencia_a_declarada':ref_a.strip(), 'referencia_b_declarada':ref_b.strip(),
        'fuso_a_declarado':tz_a, 'fuso_b_declarado':tz_b,
        'sha256_a':sha_a, 'sha256_b':sha_b,
        'mesmos_bytes':same_bytes,'mesmo_conteudo_ohlc_e_minutos':same_original_content,'mesma_referencia_declarada':same_reference,
        'mesmo_rotulo_fonte':same_source_label,'fusos_compativeis_declarados':same_timezone,
        'fusos_conhecidos_declarados':known_tz,
        'candles_a':int(len(a)),'candles_b':int(len(b)),
        'candles_com_mesmo_ticker_e_minuto':common,
        'candles_ohlc_identicos':count_equal,
        'candles_ohlc_divergentes':dif_count,
        'candles_apenas_a':only_a,'candles_apenas_b':only_b,
        'volumes_comparaveis_numericamente':bool(both_have_volume),
        'candles_com_volume_diferente':volume_diff_count,
        'diferenca_absoluta_maxima_pontos':max_abs,
        'linhas_evento_total':int(total_events),
        'linhas_evento_exibidas':int(len(events)),
        'eventos_truncados':bool(total_events>MAX_EVENTS),
        'origem_confirmada_independentemente':False,
        'pregoes_certificados':0,'backtest_liberado':False,'ordens_liberadas':False,
        'avisos':alerts,
    }
    return results,daily,events
