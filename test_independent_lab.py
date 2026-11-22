"""Cenários de segurança e comparação v1.7 — sem correção de dados."""
import io
import pandas as pd
import pytest

from independent_lab import compare_independent_m1

H='Datetime,Contrato,Open,High,Low,Close,Volume,Open_Adj,High_Adj,Low_Adj,Close_Adj,Ajuste\n'

def data(times=None,ticker='WINZ22',shift=0,adjust=63385,vol=100):
    times=times or [f'2022-10-31 09:{minute:02d}:00' for minute in range(3,13)]
    rows=[H.strip()]
    for j,t in enumerate(times):
        px=113000+j*5+shift
        rows.append(','.join(map(str,[t,ticker,px,px+10,px-5,px+5,vol,
                    px+adjust,px+10+adjust,px-5+adjust,px+5+adjust,adjust])))
    return ('\n'.join(rows)+'\n').encode()

def cmp(a=None,b=None,**kw):
    return compare_independent_m1(data() if a is None else a,data() if b is None else b,
        kw.pop('sa','Laboratório A'),kw.pop('sb','Laboratório B'),
        kw.pop('tza','Desconhecido'),kw.pop('tzb','Desconhecido'),**kw)

def test_same_file_no_independence():
    r,d,e=cmp()
    assert r['classificacao']=='MESMO_ARQUIVO_NAO_INDEPENDENTE'
    assert r['candles_com_mesmo_ticker_e_minuto']==10
    assert r['candles_ohlc_identicos']==10
    assert r['pregoes_certificados']==0 and not r['backtest_liberado'] and not r['ordens_liberadas']
    assert len(d)==1 and e.empty

def test_different_adjustment_same_original():
    r,*_=cmp(data(adjust=63385),data(adjust=50))
    assert r['candles_ohlc_identicos']==10
    assert r['classificacao']=='PRECOS_COINCIDENTES_ORIGEM_NAO_COMPROVADA'

def test_price_difference_detected():
    r,d,e=cmp(data(),data(shift=5))
    assert r['candles_ohlc_divergentes']==10
    assert r['diferenca_absoluta_maxima_pontos']==5
    assert len(e)==10
    assert set(e['motivo'])=={'OHLC_DIVERGENTE'}
    assert int(d.iloc[0]['divergencias_ohlc'])==10

def test_partial_overlap_no_interpolation():
    t0=[f'2022-10-31 09:{i:02d}:00' for i in range(3,8)]
    t1=[f'2022-10-31 09:{i:02d}:00' for i in range(6,11)]
    r,d,e=cmp(data(times=t0),data(times=t1))
    assert r['candles_com_mesmo_ticker_e_minuto']==2
    assert r['candles_apenas_a']==3 and r['candles_apenas_b']==3
    assert r['candles_ohlc_divergentes']==2  # different start-price in this test
    assert set(e['motivo'])=={'AUSENTE_A','AUSENTE_B','OHLC_DIVERGENTE'}

def test_no_overlap_different_ticker():
    r,_,e=cmp(data(),data(ticker='WINZ24'))
    assert r['classificacao']=='SEM_SOBREPOSICAO_EXATA'
    assert r['candles_com_mesmo_ticker_e_minuto']==0 and len(e)==20

def test_duplicate_minute_rejected():
    raw=data().decode().splitlines()
    altered=('\n'.join(raw+[raw[-1]])+'\n').encode()
    with pytest.raises(ValueError,match='repetidos'):
        cmp(data(),altered)

def test_wrong_ticker_rejected():
    with pytest.raises(ValueError,match='ticker'):
        cmp(data(),data(ticker='WIN'))

def test_bad_ohlc_rejected():
    raw=data().decode().replace('113010,112995,113005','113000,112995,113005')
    # modify real high in first row
    lines=data().decode().splitlines()
    row=lines[1].split(','); row[3]='112990'; lines[1]=','.join(row)
    with pytest.raises(ValueError,match='OHLC'):
        cmp(data(),('\n'.join(lines)+'\n').encode())

def test_timezone_ambiguity_and_mismatch():
    r,*_=cmp(data(),data(adjust=100),tza='Desconhecido',tzb='America/Sao_Paulo (declarado)')
    assert r['fusos_compativeis_declarados'] is False
    assert r['classificacao']=='FUSOS_DECLARADOS_INCOMPATIVEIS'
    assert any('NÃO foram convertidos' in msg for msg in r['avisos'])
    assert r['pregoes_certificados']==0

def test_same_reference_warns():
    r,*_=cmp(data(),data(adjust=100),ref_a='https://example.org/raw',ref_b='https://example.org/raw')
    assert r['mesma_referencia_declarada']

def test_same_labels_warns():
    r,*_=cmp(data(),data(adjust=100),sa='Site X',sb='site x')
    assert r['mesmo_rotulo_fonte']

def test_original_price_only_ignores_adjusted():
    r,*_=cmp(data(adjust=100),data(adjust=10000))
    assert r['candles_ohlc_identicos']==10 and r['candles_ohlc_divergentes']==0

def test_invalid_empty_source():
    with pytest.raises(ValueError,match='fonte'):
        cmp(data(),data(),sa=' ')

def test_empty_no_file():
    with pytest.raises(ValueError):
        cmp(data(),b'')

def test_renamed_ticker_key_blocks_pairing():
    r,*_=cmp(data(),data(ticker='WINM23'))
    assert r['candles_ohlc_identicos']==0

def test_short_reference_warns_not_certified():
    r,*_=cmp(data(),data(adjust=40),ref_a='fonte 1',ref_b='fonte 2')
    assert not r['origem_confirmada_independentemente']
    assert r['pregoes_certificados']==0

def test_unmatched_total_and_export():
    t1=['2022-10-31 09:03:00','2022-10-31 09:04:00']
    t2=['2022-10-31 10:03:00','2022-10-31 10:04:00']
    r,d,e=cmp(data(times=t1),data(times=t2))
    assert r['candles_apenas_a']==2 and r['candles_apenas_b']==2
    assert r['linhas_evento_total']==4
    assert 'motivo' in e.to_csv(index=False)


def test_volume_difference_separate_from_prices():
    r,*_=cmp(data(vol=10),data(vol=200))
    assert r['candles_ohlc_identicos']==10
    assert r['volumes_comparaveis_numericamente']
    assert r['candles_com_volume_diferente']==10
    assert not r['origem_confirmada_independentemente']

def test_same_content_different_bytes_warns():
    a=data()
    b=a.decode().replace(',', ';').encode()
    r,*_=cmp(a,b)
    assert not r['mesmos_bytes']
    assert r['mesmo_conteudo_ohlc_e_minutos']
    assert any('reexportação' in w for w in r['avisos'])
