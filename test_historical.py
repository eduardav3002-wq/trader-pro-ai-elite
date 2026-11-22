"""Testes do modo exploratório: sem prova de preço real ou operação executada."""
from datetime import date
import io
from pathlib import Path

import pandas as pd
import pytest

from historical import (historical_day_gate, index_expiry_days, audit_exploratory_csv,
                        read_exploratory_csv, CLOSED_2019, CLOSED_2020)


def sample_5m(day='2020-07-09', n=8):
    index = pd.date_range(f'{day} 09:00',periods=n,freq='5min')
    return pd.DataFrame({'datetime':index.astype(str),
                         'open':[100000]*n,'high':[100010]*n,
                         'low':[99990]*n,'close':[100005]*n,'volume':[100]*n}).to_csv(index=False).encode()


def sample_1m():
    rows=[]
    for j in range(11):
        ts=pd.Timestamp('2020-07-09 09:00') + pd.Timedelta(minutes=j)
        rows.append({'DATE':ts.strftime('%Y.%m.%d'),'TIME':ts.strftime('%H:%M:%S'),
                     'OPEN':100000,'HIGH':100010,'LOW':99990,'CLOSE':100005,
                     'VOL':j+1})
    return pd.DataFrame(rows).to_csv(sep='\t',index=False).encode()


def test_2020_calendar_exceptions():
    assert historical_day_gate('2020-06-11')=='B3_FECHADA'
    assert historical_day_gate('2020-07-09')=='PREGAO_PREVISTO'
    assert historical_day_gate('2020-11-20')=='PREGAO_PREVISTO'
    assert historical_day_gate('2020-02-24')=='B3_FECHADA'
    assert historical_day_gate('2020-02-26')=='ABERTURA_ESPECIAL_13H'


def test_2019_calendar_and_unsupported():
    assert historical_day_gate('2019-12-24')=='B3_FECHADA'
    assert historical_day_gate('2019-12-26')=='PREGAO_PREVISTO'
    assert historical_day_gate('2019-12-25')=='B3_FECHADA'
    assert historical_day_gate('2021-07-09')=='ANO_NAO_SUPORTADO'
    assert historical_day_gate('2020-07-11')=='FIM_DE_SEMANA'


def test_reject_closed_date():
    with pytest.raises(ValueError, match='sem pregão'):
        read_exploratory_csv(sample_5m('2020-06-11'))


def test_reject_non_ticks_and_invalid_ohlc():
    raw=pd.read_csv(io.BytesIO(sample_5m()))
    raw.loc[0,'open']=100003
    with pytest.raises(ValueError,match='múltiplo de 5'):
        read_exploratory_csv(raw.to_csv(index=False).encode())
    raw.loc[0,'open']=100000;raw.loc[0,'high']=99995
    with pytest.raises(ValueError,match='OHLC'):
        read_exploratory_csv(raw.to_csv(index=False).encode())


def test_reject_year_2026():
    with pytest.raises(ValueError,match='2019–2020'):
        read_exploratory_csv(sample_5m('2026-11-19'))


def test_minute_to_5m_drops_partial():
    cleaned, info=read_exploratory_csv(sample_1m())
    assert len(cleaned)==2
    assert info['janelas_parciais_descartadas']==1
    assert info['minutos_em_janelas_descartadas']==1
    assert list(cleaned.volume)==[15,40]


def test_detect_intraday_gap():
    raw=pd.read_csv(io.BytesIO(sample_5m(n=10)))
    raw=raw.drop(index=4).reset_index(drop=True)
    out,report,daily,gaps=audit_exploratory_csv(raw.to_csv(index=False).encode(),'Fonte pública','teste.csv')
    assert len(out)==9
    assert report['saltos_intradiarios_5min']==1
    assert report['candles_5min_ausentes_entre_extremos']==1
    assert report['dias_com_lacunas']==1
    assert report['pode_gerar_sinais_ou_operacoes'] is False


def test_detect_days_missing_between_holidays():
    # Quinta 09/07/2020 é pregão por exceção ao feriado municipal.
    a=pd.read_csv(io.BytesIO(sample_5m('2020-07-08')))
    b=pd.read_csv(io.BytesIO(sample_5m('2020-07-10')))
    report=audit_exploratory_csv(pd.concat([a,b]).to_csv(index=False).encode(),'Projeto público','d.csv')[1]
    assert report['pregoes_esperados_ausentes']==['2020-07-09']


def test_nominal_expiry_dates():
    assert [str(x) for x in index_expiry_days(date(2019,12,1),date(2020,9,1))]==[
        '2019-12-18','2020-02-12','2020-04-15','2020-06-17','2020-08-12']


def test_reject_duplicate_bar():
    raw=pd.read_csv(io.BytesIO(sample_5m()))
    raw.loc[7,'datetime']=raw.loc[6,'datetime']
    with pytest.raises(ValueError,match='repetidos'):
        read_exploratory_csv(raw.to_csv(index=False).encode())


def test_file_size_and_source():
    with pytest.raises(ValueError,match='15 MB'):
        read_exploratory_csv(b'x'*(15_000_001))
    with pytest.raises(ValueError,match='fonte declarada'):
        audit_exploratory_csv(sample_5m(),'','teste.csv')


def test_real_uploaded_file_optional():
    p=Path('/mnt/data/WIN_2019_2020_5min_exploratorio.csv')
    if p.exists():
        _,r,days,gaps=audit_exploratory_csv(p.read_bytes(),'Github público sem autenticação','converted.csv')
        assert r['candles_5min']==19257
        assert r['pregoes_com_dados']==181
        assert r['pregoes_ausentes']==0
        assert r['saltos_intradiarios_5min']==72
        assert r['dias_com_lacunas']==15
        assert r['dias_abertura_divergente']==64


def test_legacy_2026_gate_stays_blocked_on_2020():
    from engine import market_day_gate, validate_win_candles
    assert market_day_gate('2020-07-09 10:00')=='CALENDARIO_NAO_VALIDADO'
    assert market_day_gate('2026-11-20 10:00')=='FERIADO_B3'
    with pytest.raises(ValueError, match='2026'):
        validate_win_candles(pd.read_csv(io.BytesIO(sample_5m('2020-07-09'))),min_rows=5)


def test_special_opening_2020_is_flagged_not_backtested():
    idx=pd.date_range('2020-02-26 13:05',periods=8,freq='5min')
    data=pd.DataFrame({'datetime':idx.astype(str),'open':100000,'high':100010,'low':99990,'close':100005})
    _,r,daily,_=audit_exploratory_csv(data.to_csv(index=False).encode(),'Fonte pública','ash.csv')
    assert 'ABERTURA_ESPECIAL_13H' in daily.alertas.iloc[0]
    assert 'ABERTURA_DIVERGE_DA_REFERENCIA' in daily.alertas.iloc[0]
    assert r['pode_gerar_sinais_ou_operacoes'] is False
