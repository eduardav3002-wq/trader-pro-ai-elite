"""Trader Pro AI Elite v1.8 - diagnóstico adicional para comparação M1 A/B.

Pesquisa exclusivamente. Não corrige dados, não desloca relógios, não converte
fusos, não infere rolagens, não certifica pregões e não libera negociações.
Os exemplos sintéticos gerados por este módulo NÃO são dados de mercado.
"""
from __future__ import annotations

import hashlib
from typing import Any

import pandas as pd

from independent_lab import KEYS, PRICES, MAX_EVENTS, _validated


def _runs(frame: pd.DataFrame, missing_in: str) -> list[dict]:
    """Agrupa minutos exclusivos contíguos, sem cruzar contrato ou data."""
    if frame.empty:
        return []
    result = []
    frame = frame.sort_values(['contrato', 'datetime'])
    for (ticker, day), group in frame.groupby(['contrato', frame['datetime'].dt.date], sort=True):
        start = end = None
        total = 0
        for ts in group['datetime']:
            if start is None:
                start = end = ts
                total = 1
            elif ts - end == pd.Timedelta(minutes=1):
                end = ts
                total += 1
            else:
                result.append({
                    'dia': str(day), 'contrato': ticker,
                    'ausente_em': missing_in, 'primeiro_minuto': start,
                    'ultimo_minuto': end, 'minutos_exclusivos': total,
                })
                start = end = ts
                total = 1
        if start is not None:
            result.append({
                'dia': str(day), 'contrato': ticker,
                'ausente_em': missing_in, 'primeiro_minuto': start,
                'ultimo_minuto': end, 'minutos_exclusivos': total,
            })
    return result


def diagnose_m1_differences(
    raw_a: bytes, raw_b: bytes, source_a: str, source_b: str,
    tz_a: str, tz_b: str, filename_a: str = 'fonte_a.csv', filename_b: str = 'fonte_b.csv',
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Relatório, diferenças por OHLC, faixas exclusivas e eventos (prévia).

    Todos os números são DESCRITIVOS da comparação exata em (datetime,ticker).
    Para avaliar o contrato ou negociar é necessário validação externa separada.
    """
    if not source_a.strip() or not source_b.strip():
        raise ValueError('Informe a origem declarada dos dois arquivos.')
    a = _validated(raw_a, source_a, tz_a, filename_a)
    b = _validated(raw_b, source_b, tz_b, filename_b)
    combined = a.merge(b, on=KEYS, how='outer', suffixes=('_a', '_b'),
                       indicator=True, validate='one_to_one', sort=True)
    overlap = combined['_merge'].eq('both')
    common = combined.loc[overlap].copy()
    row_diff = pd.Series(False, index=common.index)
    by_field = []
    for p in PRICES:
        delta = common[f'{p}_b'] - common[f'{p}_a']
        changed = delta.abs().gt(1e-8)
        row_diff |= changed
        by_field.append({
            'campo': p.upper(),
            'minutos_com_diferenca': int(changed.sum()),
            'maior_diferenca_absoluta_pts': float(delta.abs().max()) if len(delta) else None,
            'mediana_diferenca_absoluta_pts': float(delta.abs().median()) if len(delta) else None,
            'diferenca_minima_assinada_pts': float(delta.min()) if len(delta) else None,
            'diferenca_maxima_assinada_pts': float(delta.max()) if len(delta) else None,
        })
    by_field_df = pd.DataFrame(by_field)
    volume_available = 'volume_a' in common and 'volume_b' in common
    vol_changed = ((common['volume_b'] - common['volume_a']).abs().gt(1e-8)
                   if volume_available else pd.Series(False, index=common.index))

    same_hash = hashlib.sha256(raw_a).hexdigest() == hashlib.sha256(raw_b).hexdigest()
    # Detecção descritiva: todos os OHLC dos minutos compartilhados precisam
    # ter exatamente a mesma diferença não nula. Não ajusta nem alinha nada.
    uniform_shift = None
    if len(common) >= 2 and not same_hash:
        values = pd.concat([(common[f'{p}_b'] - common[f'{p}_a']) for p in PRICES])
        first = float(values.iloc[0])
        if abs(first) > 1e-8 and (values - first).abs().le(1e-8).all():
            uniform_shift = first

    only_a = combined.loc[combined['_merge'].eq('left_only'), KEYS]
    only_b = combined.loc[combined['_merge'].eq('right_only'), KEYS]
    ranges = _runs(only_a, 'B') + _runs(only_b, 'A')
    range_cols = ['dia', 'contrato', 'ausente_em', 'primeiro_minuto', 'ultimo_minuto', 'minutos_exclusivos']
    ranges_df = pd.DataFrame(ranges, columns=range_cols)
    if not ranges_df.empty:
        ranges_df = ranges_df.sort_values(['primeiro_minuto','contrato','ausente_em']).reset_index(drop=True)

    # Prévia de eventos inclui exclusivamente divergências OU volume distinto,
    # sem incluir linhas idênticas. Totais não dependem do limite de prévia.
    selected = combined.loc[~overlap].copy()
    both_changed = common.loc[row_diff | vol_changed].copy()
    selected = pd.concat([selected, both_changed], ignore_index=True)
    if not selected.empty:
        selected = selected.sort_values(['datetime','contrato']).reset_index(drop=True)
    event_rows = []
    for rec in selected.head(MAX_EVENTS).to_dict('records'):
        kind = rec['_merge']
        record = {'datetime': rec['datetime'], 'contrato': rec['contrato']}
        if kind == 'left_only':
            record.update({'tipo': 'AUSENTE_B', 'campos_diferentes': '', 'maior_diferenca_abs_pts': None})
        elif kind == 'right_only':
            record.update({'tipo': 'AUSENTE_A', 'campos_diferentes': '', 'maior_diferenca_abs_pts': None})
        else:
            changes = [p.upper() for p in PRICES if abs(rec[f'{p}_b']-rec[f'{p}_a']) > 1e-8]
            volume_change = bool(volume_available and abs(rec['volume_b'] - rec['volume_a']) > 1e-8)
            record.update({
                'tipo': 'OHLC_DIVERGENTE' if changes else 'VOLUME_DIVERGENTE',
                'campos_diferentes': ', '.join(changes),
                'maior_diferenca_abs_pts': max([abs(rec[f'{p}_b']-rec[f'{p}_a']) for p in PRICES]) if changes else 0.0,
            })
            if volume_change:
                record['volume_diferente'] = True
        for p in PRICES:
            record[f'{p}_a'] = rec.get(f'{p}_a')
            record[f'{p}_b'] = rec.get(f'{p}_b')
            record[f'dif_{p}'] = (rec[f'{p}_b'] - rec[f'{p}_a']) if kind == 'both' else None
        event_rows.append(record)
    event_cols = ['datetime','contrato','tipo','campos_diferentes','maior_diferenca_abs_pts','volume_diferente'] + [f'{s}_{x}' for s in PRICES for x in ('a','b')] + [f'dif_{x}' for x in PRICES]
    events_df = pd.DataFrame(event_rows).reindex(columns=event_cols)

    total = int(len(only_a) + len(only_b) + (row_diff | vol_changed).sum())
    report = {
        'versao': '1.8',
        'tipo': 'DIAGNOSTICO_EXPLORATORIO_NAO_CERTIFICADO',
        'arquivo_a': filename_a, 'arquivo_b': filename_b,
        'sha256_a': hashlib.sha256(raw_a).hexdigest(),
        'sha256_b': hashlib.sha256(raw_b).hexdigest(),
        'mesmo_arquivo': same_hash,
        'fonte_a_declarada': source_a.strip(), 'fonte_b_declarada': source_b.strip(),
        'fuso_a_declarado': tz_a, 'fuso_b_declarado': tz_b,
        'fusos_declarados_iguais': tz_a == tz_b,
        'minutos_em_comum': int(len(common)),
        'minutos_com_divergencia_ohlc': int(row_diff.sum()),
        'minutos_somente_a': int(len(only_a)),
        'minutos_somente_b': int(len(only_b)),
        'minutos_com_diferenca_volume': int(vol_changed.sum()) if volume_available else None,
        'campos_ohlc': by_field,
        'deslocamento_uniforme_pts_na_sobreposicao': uniform_shift,
        'deslocamento_uniforme_comprovado_como_rolagem': False,
        'faixas_exclusivas_total': int(len(ranges_df)),
        'eventos_total': total, 'eventos_exibidos': int(len(events_df)),
        'eventos_truncados': total > MAX_EVENTS,
        'dias_certificados': 0, 'backtest_liberado': False, 'ordens_liberadas': False,
        'observacoes': [
            'Diagnóstico aritmético entre fontes DECLARADAS, não confirmação de independência.',
            'Nenhuma diferença de preços foi corrigida ou interpolada.',
            'Os fusos NÃO foram convertidos. Minutos iguais não comprovam simultaneidade.',
            'Faixas exclusivas indicam falta em um arquivo RELATIVA ao outro, não ausência comprovada de negociação.',
            'Um deslocamento uniforme NÃO comprova rolagem nem legitima ajustar cotações.',
            'O limite de 500 eventos afeta apenas a prévia exportada, não os totais.',
        ],
    }
    return report, by_field_df, ranges_df, events_df


def controlled_demo_pair() -> tuple[bytes, bytes]:
    """Dois CSVs INVENTADOS com diferenças conhecidas; NUNCA dados B3."""
    header = 'Datetime,Contrato,Open,High,Low,Close,Volume\n'
    rows_a, rows_b = [], []
    for minute in range(21):
        timestamp = f'2022-10-31 09:{minute:02d}:00'
        p = 110000 + minute * 5
        row = [timestamp, 'WINZ22', p, p+10, p-5, p+5, 100]
        if minute < 20:
            rows_a.append(','.join(map(str, row)))
        if minute == 5:
            continue  # faltante em B, presente em A
        if minute == 9:
            for i in range(2, 6):
                row[i] += 5  # todos OHLC deslocados em 5 pontos
        if minute == 12:
            row[3] += 10  # apenas máxima
        if minute == 14:
            row[6] = 140  # apenas volume
        rows_b.append(','.join(map(str, row)))
    return ((header + '\n'.join(rows_a)+'\n').encode('utf-8'),
            (header + '\n'.join(rows_b)+'\n').encode('utf-8'))
