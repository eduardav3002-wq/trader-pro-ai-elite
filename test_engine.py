"""Testes executáveis com: python test_engine.py"""
import pandas as pd
from engine import analyze, demo_data, validate_win_candles


def raises_with(data,fragment):
    try:
        validate_win_candles(data)
    except ValueError as exc:
        assert fragment in str(exc),str(exc)
    else:
        raise AssertionError('O CSV inválido deveria ter sido rejeitado.')


def test_demo_and_rules():
    source=demo_data()
    valid=validate_win_candles(source)
    assert len(valid)==4*113
    assert all((valid[c] % 5 == 0).all() for c in ['open','high','low','close'])
    assert valid.datetime.iloc[0].strftime('%H:%M')=='09:00'
    assert valid.datetime.iloc[-1].strftime('%H:%M')=='18:20'
    result=analyze(source)
    assert len(result)==len(source)
    assert set(result.signal.unique()).issubset({'COMPRA','VENDA','AGUARDAR'})
    assert set(result.trend15.unique()).issubset({'ALTA','BAIXA','NEUTRA','SEM CONFIRMAÇÃO'})
    assert result.atr.iloc[-1]>0


def test_invalid():
    d=demo_data()
    bad=d.copy();bad.loc[0,'open']=bad.loc[0,'open']+1.25
    raises_with(bad,'tick de 5')
    bad=d.copy();bad.loc[0,'datetime']=bad.loc[0,'datetime'].replace(hour=19)
    raises_with(bad,'Ordene cronologicamente')
    bad=d.copy();bad.loc[1,'datetime']=bad.loc[1,'datetime']+pd.Timedelta(seconds=15)
    raises_with(bad,'Horário inválido')
    bad=d.copy();bad=bad.drop(index=[2]).reset_index(drop=True)
    raises_with(bad,'Falha ou salto')
    bad=d.copy();bad.loc[0,'high']=bad.loc[0,'low']-5
    raises_with(bad,'máxima/mínima inconsistentes')
    bad=d.copy();bad.loc[0,'datetime']=pd.Timestamp('2026-11-20 09:00:00')
    bad=bad.sort_values('datetime').reset_index(drop=True)
    raises_with(bad,'feriado da B3')


def test_no_future_15m():
    src=demo_data()
    first=analyze(src)
    later=src.copy()
    # Alterar apenas candles futuros não pode mudar os sinais 15m passados.
    for i in range(260,len(later)):
        later.loc[i,['open','high','low','close']]=src.loc[i,['open','high','low','close']]+1000
    second=analyze(later)
    assert first.trend15.iloc[:260].equals(second.trend15.iloc[:260])
    assert first.signal.iloc[:260].equals(second.signal.iloc[:260])


if __name__=='__main__':
    test_demo_and_rules();test_invalid();test_no_future_15m()
    print('OK: validação, calendário e prevenção de look-ahead')
