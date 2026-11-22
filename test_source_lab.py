import io
import pandas as pd
import pytest
from source_lab import inspect_ticker_m1, nominal_expiry

HEAD='Datetime,Contrato,DataReferencia,Open,High,Low,Close,Volume,Open_Adj,High_Adj,Low_Adj,Close_Adj,Ajuste,TickCount\n'

def make_csv(times=None, ticker='WINZ22', adj=1000, sep=','):
    times=times or [f'2022-10-31 09:{i:02d}:00' for i in range(3,15)]
    lines=[HEAD.strip().replace(',',sep)]
    for i,t in enumerate(times):
        close=113000+i*5
        items=[t,ticker,t[:10],str(close),str(close+5),str(close-5),str(close),str(10),
              str(close+adj),str(close+5+adj),str(close-5+adj),str(close+adj),str(adj),'4']
        lines.append(sep.join(items))
    return ('\n'.join(lines)+'\n').encode()

def audit(csv=None):
    return inspect_ticker_m1(csv or make_csv(),'GitHub Gist declarado','Desconhecido')

def test_basic():
    r,d,g,f=audit()
    assert r['minutos_m1']==12 and r['candles_m5_completos']==2
    assert r['minutos_nao_agregados_em_m5']==2
    assert r['tickers_declarados']==['WINZ22']
    assert r['dias_certificados']==0 and not r['backtest_liberado']
    assert f.iloc[0]['datetime']==pd.Timestamp('2022-10-31 09:05')
    assert f.iloc[0]['open']==113010 and f.iloc[0]['open_adj']==114010

def test_tsv():
    r,*_=audit(make_csv(sep='\t'))
    assert r['minutos_m1']==12

def test_gaps():
    dates=[f'2022-10-31 09:{i:02d}:00' for i in (3,4,5,7,8,9,10,11,12,13,14)]
    r,d,g,f=audit(make_csv(dates))
    assert r['saltos_de_tempo']==1 and r['minutos_ausentes_entre_extremos']==1
    assert r['candles_m5_completos']==1

def test_no_ticker():
    with pytest.raises(ValueError, match='ticker'):
        audit(make_csv(ticker='WIN'))

def test_expiration():
    assert nominal_expiry('WINZ22').isoformat()=='2022-12-14'
    assert nominal_expiry('WING22').isoformat()=='2022-02-16'

def test_older_expired_data_warned():
    times=[f'2023-01-02 09:{i:02d}:00' for i in range(5,10)]
    r,*_=audit(make_csv(times))
    assert r['linhas_apos_vencimento_nominal']==5 and not r['backtest_liberado']

def test_duplicate_rejected():
    csv=make_csv()
    with pytest.raises(ValueError,match='repetidos'):
        audit(csv+csv.splitlines()[1]+b'\n')

def test_bad_adjustment_warn_only():
    lines=make_csv().decode().splitlines()
    f=lines[1].split(','); f[12]='1005'; lines[1]=','.join(f)
    csv='\n'.join(lines)+'\n'
    r,*_=audit(csv.encode())
    assert r['registros_com_inconsistencia_entre_ajuste_e_preco']>0

def test_missing_adjusted_rejected():
    lines=make_csv().decode().splitlines()
    csv='\n'.join([','.join(lines[0].split(',')[:11]+lines[0].split(',')[12:])] + [','.join(line.split(',')[:11]+line.split(',')[12:]) for line in lines[1:]])+'\n'
    with pytest.raises(ValueError,match='Série ajustada incompleta'):
        audit(csv.encode())

def test_bad_ohlc():
    lines=make_csv().decode().splitlines()
    fields=lines[1].split(',');fields[4]='100000';lines[1]=','.join(fields)
    with pytest.raises(ValueError,match='OHLC inconsistente'):
        audit(('\n'.join(lines)+'\n').encode())

def test_wrong_tick():
    lines=make_csv().decode().splitlines()
    fields=lines[1].split(',');fields[3]='113001';lines[1]=','.join(fields)
    with pytest.raises(ValueError,match='grade'):
        audit(('\n'.join(lines)+'\n').encode())

def test_wrong_timezone():
    with pytest.raises(ValueError,match='fuso'):
        inspect_ticker_m1(make_csv(),'Origem','UTC falso')

def test_no_source():
    with pytest.raises(ValueError,match='origem'):
        inspect_ticker_m1(make_csv(),'','Desconhecido')

def test_no_silent_sort():
    lines=make_csv().decode().splitlines();lines[1],lines[2]=lines[2],lines[1]
    with pytest.raises(ValueError,match='ordem cronológica'):
        audit(('\n'.join(lines)+'\n').encode())

def test_multiple_tickers_same_day():
    raw=make_csv()
    extra=make_csv(ticker='WINV22').decode().splitlines()[1:]
    a=raw.decode().splitlines()
    allrows=sorted(a[1:]+extra)
    r,d,_,f=audit((a[0]+'\n'+'\n'.join(allrows)+'\n').encode())
    assert len(r['tickers_declarados'])==2
    assert r['candles_m5_completos']==4
