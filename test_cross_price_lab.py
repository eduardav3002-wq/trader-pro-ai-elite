"""Validação do novo módulo v1.6: sempre somente auditoria matemática."""
import json
import pandas as pd
import pytest
from cross_price_lab import audit_cross_prices, compare_v15_receipt
from source_lab import inspect_ticker_m1

HEADER='Datetime,Contrato,DataReferencia,Open,High,Low,Close,Volume,Open_Adj,High_Adj,Low_Adj,Close_Adj,Ajuste\n'

def fixture_csv(offsets=None, times=None):
    times = times or [f'2022-10-31 09:{i:02d}:00' for i in range(3,15)]
    offsets = offsets if offsets is not None else [63385]*len(times)
    rows=[HEADER.strip()]
    for i,(stamp,delta) in enumerate(zip(times,offsets)):
        opening=113000+5*i
        raw_prices=[opening,opening+10,opening-10,opening+5]
        adj=[x+delta for x in raw_prices]
        row=[stamp,'WINZ22',stamp[:10],*raw_prices,500,*adj,delta]
        rows.append(','.join(map(str,row)))
    return ('\n'.join(rows)+'\n').encode()

def check(data=None):
    return audit_cross_prices(data if data is not None else fixture_csv(),
                              'GitHub (declarado)','Desconhecido')

def test_constant_offset_all_ohlc_and_m5():
    s,d,e,m=check()
    assert s['modelo_matematico_observado']=='ADITIVO_CONSTANTE_NA_AMOSTRA'
    assert s['ajuste_minimo']==s['ajuste_maximo']==63385
    assert s['candles_m1']==12 and s['candles_m5_completos']==2
    assert s['minutos_descartados_m5']==2
    assert s['candles_m5_com_transformacao_nao_uniforme']==0
    assert s['eventos_para_investigar']==0 and e.empty
    assert m['translacao_uniforme_m5'].all()
    assert d.iloc[0]['ajuste_constante_no_dia']
    assert not s['backtest_liberado'] and not s['ordens_liberadas']

def test_intraday_step_change_breaks_transformation_on_a_complete_m5():
    data=fixture_csv(offsets=[63385]*4 + [63390]*8)
    s,d,e,m=check(data)
    assert s['modelo_matematico_observado']=='AJUSTE_VARIAVEL_INTRADIA'
    assert s['mudancas_de_ajuste_entre_minutos_adjacentes']==1
    assert s['minutos_com_retorno_diferente_entre_series']==1
    assert s['dias_com_ajuste_variavel_intradia']==1
    assert s['candles_m5_com_transformacao_nao_uniforme']>=1
    assert 'MUDANCA_AJUSTE_M1' in e['classe'].tolist()
    assert (~m['translacao_uniforme_m5']).sum()>=1

def test_declared_adjustment_inconsistent_logged_without_fabrication():
    rows=fixture_csv().decode().splitlines()
    cells=rows[1].split(','); cells[-1]='63390';rows[1]=','.join(cells)
    s,d,e,m=check(('\n'.join(rows)+'\n').encode())
    assert s['candles_com_ajuste_declarado_divergente']==1
    assert s['modelo_matematico_observado']=='DIVERGENCIAS_NA_TRANSFORMACAO'
    assert 'AJUSTE_DECLARADO_DIVERGENTE' in e.iloc[0]['classe']

def test_nonuniform_ohlc_delta_tracked_if_prices_remain_valid():
    rows=fixture_csv().decode().splitlines()
    cells=rows[1].split(',');cells[9]=str(int(cells[9])+5) # High_Adj
    rows[1]=','.join(cells)
    s,d,e,m=check(('\n'.join(rows)+'\n').encode())
    assert s['candles_com_campos_ohlc_divergentes']==1
    assert s['modelo_matematico_observado']=='DIVERGENCIAS_NA_TRANSFORMACAO'

def test_missing_adjusted_series_is_explicit_not_silent():
    rows=fixture_csv().decode().splitlines()
    trimmed=[','.join(row.split(',')[:8]) for row in rows]
    s,d,e,m=check(('\n'.join(trimmed)+'\n').encode())
    assert not s['serie_ajustada_presente']
    assert s['modelo_matematico_observado']=='SEM_SERIE_AJUSTADA'
    assert s['ajuste_minimo'] is None
    assert len(m)==0
    assert not s['backtest_liberado']

def test_break_in_time_never_bridged_for_m1_returns():
    times=[f'2022-10-31 09:{i:02d}:00' for i in [3,4,5,6,8,9,10,11,12,13,14]]
    offsets=[100]*4+[105]*7
    s,_,ev,_=check(fixture_csv(offsets=offsets,times=times))
    assert s['saltos_de_tempo']==1
    assert s['mudancas_de_ajuste_entre_minutos_adjacentes']==0
    assert s['minutos_com_retorno_diferente_entre_series']==0

def test_no_crossover_from_different_days():
    times=[f'2022-10-31 09:{i:02d}:00' for i in range(5,10)] + [f'2022-11-01 09:{i:02d}:00' for i in range(5,10)]
    s,d,ev,_=check(fixture_csv(offsets=[100]*5+[110]*5,times=times))
    assert s['modelo_matematico_observado']=='ADITIVO_CONSTANTE_POR_CONTRATO_DIA'
    assert s['mudancas_de_ajuste_entre_minutos_adjacentes']==0
    assert len(d)==2
    assert ev.empty

def test_unchanged_receipt_hash_does_not_authenticate():
    raw=fixture_csv();s,*_=check(raw)
    old=json.dumps({'versao':'1.5','sha256':s['sha256']}).encode()
    a=compare_v15_receipt(old,s['sha256'])
    assert a['sha256_igual'] and 'não' in a['aviso']
    assert not compare_v15_receipt(old, '0'*64)['sha256_igual']

def test_invalid_receipts_rejected():
    s,*_=check()
    for raw in [b'{}',b'no-json',b'{"versao":"1.5","sha256":"abc"}',b'[]']:
        with pytest.raises(ValueError): compare_v15_receipt(raw,s['sha256'])

def test_bad_original_csv_never_accepted():
    raw=fixture_csv().decode().splitlines()
    cells=raw[1].split(',');cells[3]='113001';raw[1]=','.join(cells)
    with pytest.raises(ValueError,match='grade'):
        check(('\n'.join(raw)+'\n').encode())
