"""Auditoria EXPLORATÓRIA de WIN 2019–2020 (nunca motor de ordens/backtest).

As datas de feriados seguem ofícios públicos da B3, inclusive exceções 2020.
Não autentica fornecedor, fusos, série contínua, horários de ENCERRAMENTO,
interrupções operacionais, vencimentos específicos nem ajustes de rolagem.
"""
from __future__ import annotations

from datetime import date, time, timedelta
import hashlib
import io
import math

import numpy as np
import pandas as pd

MAX_BYTES = 15_000_000
TICK = 5
CALENDAR_SOURCES = {
    '2019': 'https://www.b3.com.br/data/files/F8/B3/88/A0/33E97610F157B776AC094EA8/CL%20049-2018_EN_VOP%20Feriados%202019_v7%20R_2.pdf',
    '2020': 'https://www.b3.com.br/data/files/97/C7/BB/E1/F50BF6109A4874F6AC094EA8/OC%20003-2020-VOP%20Feriados%202020.pdf',
    '2020_excecoes': 'https://www.b3.com.br/pt_br/noticias/funcionamento-da-b3-8AE490C97215B74E0172959F18F11323.htm',
}
CLOSED_2019 = frozenset(date.fromisoformat(x) for x in (
    '2019-01-01','2019-01-25','2019-03-04','2019-03-05',
    '2019-04-19','2019-05-01','2019-06-20','2019-07-09',
    '2019-11-15','2019-11-20','2019-12-24','2019-12-25','2019-12-31'))
CLOSED_2020 = frozenset(date.fromisoformat(x) for x in (
    '2020-01-01','2020-02-24','2020-02-25','2020-04-10',
    '2020-04-21','2020-05-01','2020-06-11','2020-09-07',
    '2020-10-12','2020-11-02','2020-12-24','2020-12-25','2020-12-31'))
CLOSED = CLOSED_2019 | CLOSED_2020
SPECIAL_START = {date(2019,3,6): time(13,0), date(2020,2,26): time(13,0)}


def historical_day_gate(day):
    """Somente identifica pregões previstos pelos calendários consultados.

    Não comprova negociação contínua em cada minuto nem valida horários finais.
    """
    day = pd.Timestamp(day).date()
    if day.year not in (2019, 2020):
        return 'ANO_NAO_SUPORTADO'
    if day.weekday() >= 5:
        return 'FIM_DE_SEMANA'
    if day in CLOSED:
        return 'B3_FECHADA'
    if day in SPECIAL_START:
        return 'ABERTURA_ESPECIAL_13H'
    return 'PREGAO_PREVISTO'


def index_expiry_days(start, end):
    """Quartas-feiras mais próximas do dia 15 nos meses pares (datas nominais).

    As datas devem ser verificadas frente a eventuais exceções do contrato.
    """
    out = []
    for year in range(start.year, end.year+1):
        for month in (2,4,6,8,10,12):
            dates = [date(year,month,d) for d in range(12,19) if date(year,month,d).weekday()==2]
            if dates and start <= dates[0] <= end:
                out.append(dates[0])
    return out


def _check_ohlc(frame, *, freq):
    if len(frame) < 1:
        raise ValueError('Arquivo contém poucos candles para inspeção.')
    if frame.datetime.isna().any() or frame.datetime.duplicated().any():
        raise ValueError('Há horários inválidos ou repetidos; nenhuma interpolação é permitida.')
    if not frame.datetime.is_monotonic_increasing:
        raise ValueError('Os candles devem estar ordenados do mais antigo para o mais recente.')
    for col in ('open','high','low','close'):
        frame[col] = pd.to_numeric(frame[col], errors='coerce')
        values = frame[col].to_numpy(dtype=float)
        if not np.isfinite(values).all() or (values <= 0).any():
            raise ValueError(f'Valores inválidos de {col}.')
        if (np.abs(values/TICK - np.round(values/TICK)) > 1e-7).any():
            raise ValueError(f'Preço não é múltiplo de 5 pontos em {col}.')
    if (frame.high < frame[['open','close','low']].max(axis=1)).any() or (frame.low > frame[['open','close']].min(axis=1)).any():
        raise ValueError('OHLC inconsistente com máxima/mínima.')
    if frame.datetime.dt.second.ne(0).any() or frame.datetime.dt.microsecond.ne(0).any():
        raise ValueError('Os timestamps devem representar início de minuto exato.')
    if freq == 5 and (frame.datetime.dt.minute % 5).ne(0).any():
        raise ValueError('O CSV 5min deve ter horários de abertura múltiplos de 5.')
    if not bool(frame.datetime.dt.year.isin([2019, 2020]).all()):
        raise ValueError('Modo exploratório restrito a 2019–2020. Para 2026, use o modo histórico rigoroso.')
    bad_days = sorted({x for x in frame.datetime.dt.date if historical_day_gate(x) in ('B3_FECHADA','FIM_DE_SEMANA','ANO_NAO_SUPORTADO')})
    if bad_days:
        raise ValueError('Datas sem pregão previsto no calendário 2019/2020: ' + ', '.join(map(str,bad_days[:5])))
    if 'volume' in frame:
        frame['volume'] = pd.to_numeric(frame.volume,errors='coerce')
        if frame.volume.isna().any() or (~np.isfinite(frame.volume.to_numpy(dtype=float))).any() or (frame.volume < 0).any():
            raise ValueError('Volume inválido no CSV.')
    else:
        frame['volume'] = 0
    return frame


def read_exploratory_csv(payload: bytes):
    """Recebe CSV 5min padronizado ou TSV 1min (DATE/TIME/OPEN/.../VOL).

    Converte 1m apenas com 5 barras contínuas; retorna descartes contados.
    Arquivo nunca recebe etiqueta de origem comprovada.
    """
    if not isinstance(payload,bytes) or not payload or len(payload) > MAX_BYTES:
        raise ValueError('Envie um arquivo de até 15 MB, não vazio.')
    try:
        raw = pd.read_csv(io.BytesIO(payload), sep=None, engine='python', encoding='utf-8-sig', on_bad_lines='error')
    except (ValueError, UnicodeError, pd.errors.ParserError) as exc:
        raise ValueError('CSV/TSV ilegível; use o arquivo original ou o convertido de 5 minutos.') from exc
    raw.columns = [str(c).strip().lower() for c in raw.columns]
    if {'date','time','open','high','low','close'}.issubset(raw.columns):
        # O cabeçalho DATE+TIME indica o formato MINUTO do arquivo de pesquisa.
        times = pd.to_datetime(raw['date'].astype(str).str.strip() + ' ' + raw['time'].astype(str).str.strip(),
                               format='%Y.%m.%d %H:%M:%S',errors='coerce')
        if times.isna().any():
            raise ValueError('Data/hora no formato original inválida.')
        df = raw[['open','high','low','close']].copy()
        df.insert(0,'datetime',times)
        if 'vol' in raw:
            df['volume']=raw['vol']
        df=_check_ohlc(df,freq=1)
        slot=df.datetime.dt.floor('5min')
        agg = df.groupby(slot,sort=True).agg(open=('open','first'),high=('high','max'),
                                             low=('low','min'),close=('close','last'),
                                             volume=('volume','sum'),count=('close','size'),
                                             first=('datetime','min'),last=('datetime','max'))
        complete = (agg['count'].eq(5) & agg['first'].eq(agg.index)
                    & agg['last'].eq(agg.index+pd.Timedelta(minutes=4)))
        rejected = int((~complete).sum())
        filtered=agg.loc[complete,['open','high','low','close','volume']].copy().reset_index().rename(columns={'datetime':'datetime'})
        if 'datetime' not in filtered:
            filtered=filtered.rename(columns={filtered.columns[0]:'datetime'})
        return _check_ohlc(filtered,freq=5), {'tipo_entrada':'TSV_1MIN','minutos_recebidos':int(len(df)),
                    'janelas_parciais_descartadas':rejected,'minutos_em_janelas_descartadas':int(agg.loc[~complete,'count'].sum())}
    if {'datetime','open','high','low','close'}.issubset(raw.columns):
        df=raw[['datetime','open','high','low','close'] + (['volume'] if 'volume' in raw else [])].copy()
        df['datetime']=pd.to_datetime(df.datetime,errors='coerce')
        if getattr(df.datetime.dt,'tz',None) is not None:
            raise ValueError('CSV 5min com fuso: exporte timestamps locais de abertura sem offset, Brasília declarada.')
        return _check_ohlc(df,freq=5), {'tipo_entrada':'CSV_5MIN','minutos_recebidos':None,
                                  'janelas_parciais_descartadas':None,'minutos_em_janelas_descartadas':None}
    raise ValueError('Colunas não reconhecidas: use datetime,open,high,low,close[,volume] ou DATE/TIME/OPEN/HIGH/LOW/CLOSE/VOL.')


def audit_exploratory_csv(payload:bytes, source_name:str, filename:str):
    """Produz relatório descritivo: nenhum sinal, backtest ou ordem é gerado."""
    if not isinstance(source_name,str) or len(source_name.strip()) < 3 or len(source_name.strip())>200:
        raise ValueError('Identifique a fonte declarada (mínimo 3 caracteres).')
    df, conversion=read_exploratory_csv(payload)
    days = sorted(set(df.datetime.dt.date))
    all_days=pd.bdate_range(min(days), max(days)).date
    missing = [d.isoformat() for d in all_days if d not in CLOSED and d not in days]
    expiry=index_expiry_days(days[0],days[-1])
    expiry_set=set(expiry)
    daily=[]; gap_records=[]
    for day, frame in df.groupby(df.datetime.dt.date,sort=True):
        stamps=frame.datetime.reset_index(drop=True)
        delta=stamps.diff()
        gaps=delta.gt(pd.Timedelta(minutes=5))
        for idx in list(gaps[gaps].index):
            gap_records.append({'dia':day.isoformat(), 'anterior':str(stamps.iloc[idx-1]),
                'seguinte':str(stamps.iloc[idx]),
                'candles_5min_ausentes':int(delta.iloc[idx]/pd.Timedelta(minutes=5)-1)})
        start=stamps.iloc[0].time()
        expected=SPECIAL_START.get(day,time(9,0))
        flags=[]
        if start!=expected:
            flags.append('ABERTURA_DIVERGE_DA_REFERENCIA')
        if gaps.any():
            flags.append('LACUNA_INTRADIARIA')
        if day in expiry_set:
            flags.append('DATA_NOMINAL_VENCIMENTO_WIN')
        if any(abs((day-e).days)<=2 for e in expiry_set):
            flags.append('PROXIMO_DE_VENCIMENTO_ROLAGEM_NAO_VERIFICADA')
        if historical_day_gate(day)=='ABERTURA_ESPECIAL_13H':
            flags.append('ABERTURA_ESPECIAL_13H')
        daily.append({'dia':day.isoformat(),'candles_5min':len(frame), 'primeiro_candle':start.strftime('%H:%M'),
                      'ultimo_candle':stamps.iloc[-1].strftime('%H:%M'),
                      'lacunas_internas':int(gaps.sum()),'barras_ausentes_entre_extremos':int(sum(
                          k['candles_5min_ausentes'] for k in gap_records if k['dia']==day.isoformat())),
                      'abertura_referencia':expected.strftime('%H:%M'),
                      'status_calendario':historical_day_gate(day),
                      'alertas':'; '.join(flags) if flags else 'LIMITES_DO_PREGAO_NAO_AFERIDOS'})
    report = {
        'versao':'1.1','classificacao':'EXPLORATORIO_NAO_VALIDADO_SEM_BACKTEST',
        'fonte_declarada':source_name.strip(),'arquivo':str(filename)[:160],
        'sha256_recebido':hashlib.sha256(payload).hexdigest(),
        'autenticidade_cotacoes_confirmada':False,
        'contrato_individual_identificado':False,
        'fuso_horario_comprovado':False,
        'pode_gerar_sinais_ou_operacoes':False,
        'candles_5min':int(len(df)), 'pregoes_com_dados':len(days),
        'primeiro_candle':str(df.datetime.min()),'ultimo_candle':str(df.datetime.max()),
        'pregoes_esperados_ausentes':missing,
        'pregoes_ausentes':len(missing),
        'saltos_intradiarios_5min':len(gap_records),
        'candles_5min_ausentes_entre_extremos':sum(x['candles_5min_ausentes'] for x in gap_records),
        'dias_com_lacunas':sum(d['lacunas_internas']>0 for d in daily),
        'dias_abertura_divergente':sum(d['primeiro_candle']!=d['abertura_referencia'] for d in daily),
        'vencimentos_nominais_na_amostra':[d.isoformat() for d in expiry],
        'conversao':conversion,'fontes_calendario':CALENDAR_SOURCES,
        'ressalvas':[
            'Calendário 2019–2020 cotejado com comunicados da B3; horários efetivos de encerramento não foram certificados.',
            'Feriados e horários podem ter exceções ou mudanças; qualidade e completude dos candles não estão garantidas.',
            'Candles sem ticker, contrato/vencimento e procedência primária; rolagem e ajuste de preços não verificados.',
            'Datas de vencimento são nominais. Não são prova de troca de contrato ou do preço ajustado.',
            'Lacunas podem decorrer de suspensão, ausência de transações ou falhas de coleta: causa não apurada.',
            'Não existe autorização de negociação, recomendação ou teste de rentabilidade nesse modo.',
        ],
    }
    return df,report,pd.DataFrame(daily),pd.DataFrame(gap_records,columns=['dia','anterior','seguinte','candles_5min_ausentes'])
