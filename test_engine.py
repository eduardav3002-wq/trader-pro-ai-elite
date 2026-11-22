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


def test_contract_and_full_sessions():
    from engine import contract_expiry
    assert str(contract_expiry('WINZ26')) == '2026-12-16'
    assert str(contract_expiry('WINV26')) == '2026-10-14'
    d = demo_data()
    assert len(validate_win_candles(d, require_complete_sessions=True, contract='WINZ26')) == 452
    try:
        validate_win_candles(d, contract='WINV26')
    except ValueError as exc:
        assert 'posteriores ao vencimento' in str(exc)
    else:
        raise AssertionError('Datas posteriores ao vencimento devem ser rejeitadas.')
    try:
        validate_win_candles(d.iloc[1:].reset_index(drop=True),
                             require_complete_sessions=True, contract='WINZ26')
    except ValueError as exc:
        assert 'Pregão incompleto' in str(exc)
    else:
        raise AssertionError('Sessão sem primeiro candle deve ser rejeitada.')
    try:
        contract_expiry('WIN_CONTINUO')
    except ValueError:
        pass
    else:
        raise AssertionError('Símbolo contínuo não deve passar como vencimento.')


def test_symbol_declared_in_csv():
    d = demo_data()
    d['ticker'] = 'WINZ26'
    validate_win_candles(d, contract='WINZ26')
    d.loc[1, 'ticker'] = 'WINV26'
    try:
        validate_win_candles(d, contract='WINZ26')
    except ValueError as exc:
        assert 'não corresponde' in str(exc)
    else:
        raise AssertionError('Contratos misturados devem ser rejeitados.')
