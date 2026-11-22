"""v1.5: auditoria descritiva de CSV intradiário M1 com ticker explícito.

Não autentica preços/ticker, não transforma dados em sinal e não certifica backtests.
Nunca mistura preços originais e ajustados nem preenche minutos ausentes.
"""
from __future__ import annotations

import hashlib
import io
import re
from datetime import date, timedelta

import pandas as pd

TICK = 5
MAX_BYTES = 15_000_000
M1_COLS = ('datetime', 'contrato', 'open', 'high', 'low', 'close')
PRICE_COLS = ('open', 'high', 'low', 'close')
ADJ_COLS = ('open_adj', 'high_adj', 'low_adj', 'close_adj')
MONTH_CODES = {'G': 2, 'J': 4, 'M': 6, 'Q': 8, 'V': 10, 'Z': 12}
CODE_RE = re.compile(r'^WIN([GJMQVZ])(\d{2})$')


def nominal_expiry(ticker: str) -> date:
    """Convenção mensal nominal; não substitui calendários históricos oficiais."""
    match = CODE_RE.fullmatch(ticker)
    if not match:
        raise ValueError(f'Contrato não reconhecido: {ticker!r}. Esperado como WINZ22.')
    month, year = MONTH_CODES[match.group(1)], 2000 + int(match.group(2))
    base = date(year, month, 15)
    before = base - timedelta(days=(base.weekday() - 2) % 7)
    after = before + timedelta(days=7)
    return before if (base - before).days <= (after - base).days else after


def _read_content(raw: bytes) -> pd.DataFrame:
    if not raw or len(raw) > MAX_BYTES:
        raise ValueError('O CSV precisa ter conteúdo e tamanho até 15 MB para esta inspeção móvel.')
    try:
        decoded = raw.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise ValueError('Use um CSV UTF-8 (com ou sem BOM).') from exc
    # A fonte possui CSV com vírgulas. Também aceitamos separador ; e TSV.
    head = next((line for line in decoded.splitlines() if line.strip()), '')
    sep = '\t' if head.count('\t') > max(head.count(','), head.count(';')) else (';' if head.count(';') > head.count(',') else ',')
    try:
        data = pd.read_csv(io.StringIO(decoded), sep=sep, dtype={'Contrato': 'string', 'contrato': 'string'}, low_memory=False)
    except (pd.errors.ParserError, ValueError) as exc:
        raise ValueError('Arquivo CSV/TSV não pôde ser lido sem perdas.') from exc
    data.columns = [str(col).strip().lower() for col in data.columns]
    if data.columns.duplicated().any():
        raise ValueError('Colunas repetidas após normalização.')
    if not set(M1_COLS).issubset(data.columns):
        raise ValueError('Colunas obrigatórias: Datetime, Contrato, Open, High, Low, Close.')
    if len(data) == 0 or len(data) > 250_000:
        raise ValueError('Forneça entre 1 e 250.000 linhas para a inspeção.')
    return data


def _numeric(data: pd.DataFrame, cols: tuple[str, ...]) -> None:
    for col in cols:
        if col not in data.columns:
            continue
        try:
            data[col] = pd.to_numeric(data[col], errors='raise')
        except (ValueError, TypeError) as exc:
            raise ValueError(f'Coluna {col} possui valor não numérico.') from exc
        if data[col].isna().any() or not data[col].map(lambda v: -1e15 < float(v) < 1e15).all():
            raise ValueError(f'Coluna {col} contém dados vazios ou inválidos.')


def _validate_ohlc(data: pd.DataFrame, cols: tuple[str, ...], name: str):
    op, hi, lo, cl = cols
    invalid = (data[hi] < data[[op, cl, lo]].max(axis=1)) | (data[lo] > data[[op, cl, hi]].min(axis=1))
    if invalid.any():
        raise ValueError(f'OHLC inconsistente na série {name}: {int(invalid.sum())} linha(s).')
    if any((((data[col] / TICK) - (data[col] / TICK).round()).abs() > 1e-7).any() for col in cols):
        raise ValueError(f'Preço fora da grade de {TICK} pontos na série {name}.')


def inspect_ticker_m1(raw: bytes, source: str, timezone_declared: str,
                      filename: str = 'arquivo.csv'):
    """Retorna (resumo, por_dia, lacunas, candles_5min) — somente pesquisa."""
    if not source.strip():
        raise ValueError('Informe a origem declarada do arquivo.')
    if timezone_declared not in ('America/Sao_Paulo (declarado)', 'Desconhecido'):
        raise ValueError('Escolha um fuso entre as opções oferecidas.')
    data = _read_content(raw)
    data['datetime'] = pd.to_datetime(data['datetime'], errors='coerce')
    if data['datetime'].isna().any():
        raise ValueError('Há timestamps inválidos ou sem data/hora.')
    if getattr(data['datetime'].dt, 'tz', None) is not None:
        raise ValueError('Use CSV sem fuso e declare a convenção original; datas com offset devem ser convertidas separadamente.')
    if (data['datetime'].dt.second != 0).any() or (data['datetime'].dt.microsecond != 0).any():
        raise ValueError('A inspeção aceita candles M1 iniciados em minuto exato.')
    data['contrato'] = data['contrato'].astype(str).str.strip().str.upper()
    tickers = data['contrato'].unique().tolist()
    if not tickers or any(CODE_RE.fullmatch(t) is None for t in tickers):
        raise ValueError('Todos os candles precisam de ticker WIN individual válido (ex.: WINZ22).')
    if data.duplicated(['datetime','contrato']).any():
        raise ValueError('Há registros repetidos no mesmo minuto para um contrato.')
    if not data.sort_values(['datetime','contrato']).index.equals(data.index):
        raise ValueError('Arquivo fora de ordem cronológica; não reordenamos silenciosamente.')
    cols = list(PRICE_COLS) + [c for c in ADJ_COLS if c in data.columns]
    if 'ajuste' in data.columns:
        cols.append('ajuste')
    if 'volume' in data.columns:
        cols.append('volume')
    _numeric(data, tuple(cols))
    _validate_ohlc(data, PRICE_COLS, 'original')
    adjusted = all(c in data.columns for c in ADJ_COLS)
    if any(c in data.columns for c in ADJ_COLS) and not adjusted:
        raise ValueError('Série ajustada incompleta: envie as quatro colunas *_Adj ou nenhuma.')
    if adjusted:
        _validate_ohlc(data, ADJ_COLS, 'ajustada')
    if 'volume' in data.columns and (data['volume'] < 0).any():
        raise ValueError('Volume negativo não é aceito.')
    if 'datareferencia' in data.columns:
        dates_ref = pd.to_datetime(data['datareferencia'], errors='coerce')
        if dates_ref.isna().any() or not dates_ref.dt.date.eq(data['datetime'].dt.date).all():
            raise ValueError('DataReferencia difere da data do candle.')
    delta_series = None
    inconsistency_count = 0
    if adjusted:
        differences = pd.concat([data[adj].sub(data[rawcol]).rename(rawcol)
                                 for adj,rawcol in zip(ADJ_COLS,PRICE_COLS)],axis=1)
        inconsistency_count = int((differences.sub(differences['open'], axis=0).abs() > 1e-6).any(axis=1).sum())
        if 'ajuste' in data.columns:
            inconsistency_count += int((differences['open']-data['ajuste']).abs().gt(1e-6).sum())
        delta_series = differences['open']
    data['dia'] = data['datetime'].dt.date
    data['janela'] = data['datetime'].dt.floor('5min')
    gap_rows=[]
    day_rows=[]
    complete=[]
    expired_rows=0
    for (ticker, day), group in data.groupby(['contrato','dia'], sort=True):
        group = group.sort_values('datetime')
        expiration = nominal_expiry(ticker)
        if day > expiration:
            expired_rows += len(group)
        times = group['datetime'].tolist()
        gaps=0
        missing=0
        for left,right in zip(times,times[1:]):
            minutes=int((right-left).total_seconds()/60)
            if minutes > 1:
                gaps += 1
                missing += minutes-1
                gap_rows.append({'dia':str(day),'contrato_declarado':ticker,
                    'de':str(left),'ate':str(right),'minutos_ausentes':minutes-1})
        day_rows.append({'dia':str(day),'contrato_declarado':ticker,
            'primeiro_minuto':str(times[0]),'ultimo_minuto':str(times[-1]),
            'candles_m1':len(group),'saltos_de_tempo':gaps,'minutos_ausentes_entre_extremos':missing,
            'vencimento_nominal':expiration.isoformat(),
            'apos_vencimento_nominal':bool(day>expiration),
            'status':'NAO_AUTENTICADO_NAO_CERTIFICADO'})
        for win,chunk in group.groupby('janela',sort=True):
            minutes = sorted((item-minute).total_seconds() for item,minute in [(v,win) for v in chunk['datetime']])
            if len(chunk)==5 and minutes==[0.0,60.0,120.0,180.0,240.0]:
                row={'datetime':win,'contrato_declarado':ticker,
                    'open':float(chunk.iloc[0]['open']), 'high':float(chunk['high'].max()),
                    'low':float(chunk['low'].min()),'close':float(chunk.iloc[-1]['close']),
                    'minutos_confirmados':5,'origem_autenticada':False}
                if 'volume' in chunk.columns:
                    row['volume']=float(chunk['volume'].sum())
                if adjusted:
                    row.update({'open_adj':float(chunk.iloc[0]['open_adj']),
                                'high_adj':float(chunk['high_adj'].max()),
                                'low_adj':float(chunk['low_adj'].min()),
                                'close_adj':float(chunk.iloc[-1]['close_adj'])})
                complete.append(row)
    five=pd.DataFrame(complete,columns=(['datetime','contrato_declarado','open','high','low','close','minutos_confirmados','origem_autenticada']+
                       (['volume'] if 'volume' in data.columns else [])+
                       (list(ADJ_COLS) if adjusted else [])))
    daily=pd.DataFrame(day_rows)
    missing=pd.DataFrame(gap_rows,columns=['dia','contrato_declarado','de','ate','minutos_ausentes'])
    # Quantidade de grupos M1 não utilizados é explícita; nenhum preço é inventado.
    unused_m1=int(len(data)-5*len(five))
    summary={'versao':'1.5','arquivo':filename,'sha256':hashlib.sha256(raw).hexdigest(),
       'fonte_declarada':source.strip(),'fuso_declarado':timezone_declared,
       'minutos_m1':int(len(data)),'dias_com_registros':int(data['dia'].nunique()),
       'tickers_declarados':tickers,'tickers_confirmados_independentemente':0,
       'linhas_apos_vencimento_nominal':int(expired_rows),
       'candles_m5_completos':int(len(five)), 'minutos_nao_agregados_em_m5':unused_m1,
       'saltos_de_tempo':int(len(missing)),
       'minutos_ausentes_entre_extremos':int(missing['minutos_ausentes'].sum()) if len(missing) else 0,
       'precos_ajustados_presentes':bool(adjusted),
       'registros_com_inconsistencia_entre_ajuste_e_preco':int(inconsistency_count),
       'ajuste_minimo_observado':float(delta_series.min()) if adjusted else None,
       'ajuste_maximo_observado':float(delta_series.max()) if adjusted else None,
       'dias_certificados':0,'backtest_liberado':False,'ordens_liberadas':False,
       'observacoes':[
          'Contrato declarado no CSV NÃO é contrato autenticado.',
          'Timestamp e fuso são declarados, não conferidos contra uma fonte oficial.',
          'Um dia sem lacunas internas pode estar incompleto no início ou fim.',
          'OHLC originais e ajustados permanecem separados, sem execução de estratégias.',
          'Vencimentos são nominais; horários especiais e rolagens exigem documentos externos.',
          'Amostra pública de um único dia não sustenta avaliação de desempenho.'
       ]}
    return summary, daily, missing, five
