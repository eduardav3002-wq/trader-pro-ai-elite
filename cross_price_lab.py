"""Trader Pro AI Elite v1.6 — auditoria matemática ORIGINAIS × AJUSTADOS.

Só descreve transformações dos dados apresentados. Não autentica mercado,
fonte, contrato, licença, pregão, rolagem ou rentabilidade.
"""
from __future__ import annotations

import hashlib
from datetime import timedelta

import numpy as np
import pandas as pd

from source_lab import (_read_content, _numeric, PRICE_COLS, ADJ_COLS,
                        inspect_ticker_m1)

EPS = 1e-6


def audit_cross_prices(raw: bytes, source: str, timezone_declared: str,
                       filename: str = 'arquivo.csv'):
    """Retorna (resumo JSON, resumo por contrato/dia, eventos CSV, M5 comparado CSV).

    Valida usando source_lab v1.5 antes de auditar o deslocamento. Apenas aritmética
    no arquivo recebido; nunca determina causa nem transforma candles em trades.
    """
    prior, _, _, m5 = inspect_ticker_m1(raw, source, timezone_declared, filename)
    df = _read_content(raw)
    df['datetime'] = pd.to_datetime(df['datetime'], errors='raise')
    df['contrato'] = df['contrato'].astype(str).str.strip().str.upper()
    df['dia'] = df['datetime'].dt.strftime('%Y-%m-%d')
    df['janela_m5'] = df['datetime'].dt.floor('5min')

    numeric = [c for c in PRICE_COLS + ADJ_COLS + ('ajuste',) if c in df.columns]
    _numeric(df, tuple(numeric))
    events = []
    daily_rows = []
    m5_rows = []

    adjusted = all(col in df.columns for col in ADJ_COLS)
    if adjusted:
        diffs = pd.DataFrame({col: df[adj].to_numpy(dtype='float64') -
                                      df[col].to_numpy(dtype='float64')
                              for col, adj in zip(PRICE_COLS, ADJ_COLS)}, index=df.index)
        df['offset'] = diffs['open']
        spread = diffs.max(axis=1)-diffs.min(axis=1)
        unequal_fields = spread > EPS
        if 'ajuste' in df.columns:
            unequal_declared = (df['offset']-df['ajuste']).abs()>EPS
        else:
            unequal_declared = pd.Series(False, index=df.index)
        for i in df.index[unequal_fields | unequal_declared]:
            flags=[]
            if bool(unequal_fields.loc[i]): flags.append('DIFERENCA_OHLC_NAO_UNIFORME')
            if bool(unequal_declared.loc[i]): flags.append('AJUSTE_DECLARADO_DIVERGENTE')
            events.append({'dia':df.at[i,'dia'],'datetime':str(df.at[i,'datetime']),
                           'contrato_declarado':df.at[i,'contrato'],
                           'classe':' + '.join(flags),
                           'diferenca_pontos':float(df.at[i,'offset']),
                           'detalhe':'A relação dos preços no mesmo candle não é a translação declarada'})
    else:
        df['offset'] = np.nan
        unequal_fields = pd.Series(False, index=df.index)
        unequal_declared = pd.Series(False, index=df.index)

    transitions = 0
    changed_returns = 0
    intraday_var_days = 0
    for (ticker,day), grp in df.groupby(['contrato','dia'], sort=True):
        g = grp.sort_values('datetime')
        offset = g['offset']
        changes = 0
        incompatible_returns = 0
        if adjusted:
            # Não cruza sessões, não compara tickers distintos e não salta lacunas.
            adjacent = (g['datetime'].diff() == pd.Timedelta(minutes=1))
            offset_movement = offset.diff().abs()
            mismatch = adjacent & (offset_movement > EPS)
            # Em modelo aditivo uniforme, diferenças de close são idênticas.
            different_returns = adjacent & ((g['close_adj'].diff()-g['close'].diff()).abs()>EPS)
            changes = int(mismatch.sum())
            incompatible_returns = int(different_returns.sum())
            transitions += changes
            changed_returns += incompatible_returns
            intraday_var_days += int(offset.max()-offset.min()>EPS)
            for i in g.index[mismatch]:
                events.append({'dia':day,'datetime':str(df.at[i,'datetime']),
                               'contrato_declarado':ticker,'classe':'MUDANCA_AJUSTE_M1',
                               'diferenca_pontos':float(df.at[i,'offset']),
                               'detalhe':'Deslocamento mudou entre minutos adjacentes; não é rolagem comprovada'})
        daily_rows.append({'dia':day,'contrato_declarado':ticker,'candles_m1':len(g),
            'offset_minimo':float(offset.min()) if adjusted else None,
            'offset_maximo':float(offset.max()) if adjusted else None,
            'ajuste_constante_no_dia':bool(offset.max()-offset.min() <= EPS) if adjusted else None,
            'mudancas_ajuste_m1':changes,'diferencas_retorno_m1':incompatible_returns,
            'inconsistencias_campos':int(unequal_fields.loc[g.index].sum()),
            'inconsistencias_ajuste_declarado':int(unequal_declared.loc[g.index].sum()),
            'status':'EXPLORATORIO_NAO_CERTIFICADO'})

    m5_incompatible = 0
    if adjusted:
        for _, r in m5.iterrows():
            deltas = {c:float(r[adj]-r[c]) for c,adj in zip(PRICE_COLS,ADJ_COLS)}
            m5_bad = max(deltas.values())-min(deltas.values())>EPS
            m5_incompatible += int(m5_bad)
            m5_rows.append({'datetime':str(r['datetime']),
                'contrato_declarado':r['contrato_declarado'],
                'offset_open':deltas['open'],'offset_high':deltas['high'],
                'offset_low':deltas['low'],'offset_close':deltas['close'],
                'translacao_uniforme_m5':not m5_bad,
                'status':'EXPLORATORIO_NAO_CERTIFICADO'})
            if m5_bad:
                events.append({'dia':str(r['datetime'])[:10], 'datetime':str(r['datetime']),
                    'contrato_declarado':r['contrato_declarado'],
                    'classe':'TRANSFORMACAO_M5_NAO_UNIFORME',
                    'diferenca_pontos':deltas['open'],
                    'detalhe':'OHLC M5 agregados não diferem por um deslocamento único'})

    if not adjusted:
        model='SEM_SERIE_AJUSTADA'
        min_offset=max_offset=None
    else:
        min_offset, max_offset = float(df['offset'].min()), float(df['offset'].max())
        if int(unequal_fields.sum()) or int(unequal_declared.sum()):
            model='DIVERGENCIAS_NA_TRANSFORMACAO'
        elif abs(max_offset-min_offset)<=EPS:
            model='ADITIVO_CONSTANTE_NA_AMOSTRA'
        elif intraday_var_days==0:
            model='ADITIVO_CONSTANTE_POR_CONTRATO_DIA'
        else:
            model='AJUSTE_VARIAVEL_INTRADIA'

    summary = {
        'versao':'1.6', 'arquivo':filename, 'sha256':hashlib.sha256(raw).hexdigest(),
        'fonte_declarada':source, 'fuso_declarado':timezone_declared,
        'contratos_declarados':prior['tickers_declarados'],
        'candles_m1':prior['minutos_m1'],'candles_m5_completos':prior['candles_m5_completos'],
        'minutos_descartados_m5':prior['minutos_nao_agregados_em_m5'],
        'saltos_de_tempo':prior['saltos_de_tempo'],
        'serie_ajustada_presente':adjusted,'modelo_matematico_observado':model,
        'ajuste_minimo':min_offset,'ajuste_maximo':max_offset,
        'candles_com_campos_ohlc_divergentes':int(unequal_fields.sum()),
        'candles_com_ajuste_declarado_divergente':int(unequal_declared.sum()),
        'mudancas_de_ajuste_entre_minutos_adjacentes':transitions,
        'minutos_com_retorno_diferente_entre_series':changed_returns,
        'dias_com_ajuste_variavel_intradia':intraday_var_days,
        'candles_m5_com_transformacao_nao_uniforme':m5_incompatible,
        'eventos_para_investigar':len(events),
        'dados_originais_autenticados':False,'contratos_confirmados':0,
        'dias_certificados':0,'backtest_liberado':False,'ordens_liberadas':False,
        'limitacoes':[
          'Transformações calculadas a partir do mesmo arquivo NÃO são validação cruzada por uma segunda fonte independente.',
          'Ajuste aditivo constante é propriedade matemática da amostra, NÃO prova método de ajuste, ticker, fuso nem rolagem.',
          'Mudanças intradiárias de offset exigem investigação; não são preços negociáveis nem sinais.',
          'Sem timestamps e sessões autenticados, a ausência de lacunas internas não certifica o pregão.',
          'A série ajustada pode ter níveis não executáveis; não a usar para backtest ou ordens.',
          'Sem qualquer operação ou backtest neste laboratório.'
        ]
    }
    return (summary,
            pd.DataFrame(daily_rows),
            pd.DataFrame(events, columns=['dia','datetime','contrato_declarado','classe','diferenca_pontos','detalhe']),
            pd.DataFrame(m5_rows, columns=['datetime','contrato_declarado','offset_open','offset_high','offset_low','offset_close',
                                            'translacao_uniforme_m5','status']))


def compare_v15_receipt(raw_json: bytes, new_sha256: str) -> dict:
    """Compara identidade do arquivo; nunca comprova fonte, autenticidade ou preços."""
    import json
    import re
    if not raw_json or len(raw_json) > 100_000:
        raise ValueError('Laudo anterior deve ser JSON com até 100 KB.')
    try:
        receipt = json.loads(raw_json.decode('utf-8-sig'))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError('Não foi possível interpretar o laudo JSON da v1.5.') from exc
    if not isinstance(receipt, dict) or str(receipt.get('versao')) != '1.5':
        raise ValueError('Envie um laudo de fonte v1.5 gerado pelo aplicativo.')
    old_sha = receipt.get('sha256')
    if not isinstance(old_sha, str) or not re.fullmatch(r'[0-9a-fA-F]{64}', old_sha):
        raise ValueError('Laudo da v1.5 está sem SHA-256 completo válido.')
    if not isinstance(new_sha256, str) or not re.fullmatch(r'[0-9a-fA-F]{64}', new_sha256):
        raise ValueError('SHA-256 atual é inválido.')
    return {'versao_origem':'1.5', 'sha256_igual':old_sha.lower() == new_sha256.lower(),
            'aviso':'Mesmo SHA-256 confirma apenas bytes iguais, não fonte nem autenticidade.'}
