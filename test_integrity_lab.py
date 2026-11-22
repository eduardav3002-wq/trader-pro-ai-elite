"""Testes de integridade: jamais validar ticker, rolagem ou trades pela amostra."""
import pandas as pd
import pytest
from historical import audit_exploratory_csv
from integrity_lab import assess_integrity, compare_daily_export


def fixture_records():
    # Gaps de tempo, variação de preço adjacente e vencimento nominal:
    # a existência desses padrões não autentica nem condena preço algum.
    data=[
        ('2020-02-10 09:00:00',1000,1000,1000,1000),
        ('2020-02-10 09:05:00',1000,1010,1000,1005),
        ('2020-02-10 09:15:00',1105,1115,1105,1110),
        ('2020-02-10 09:20:00',1210,1220,1210,1215),
        ('2020-02-11 09:00:00',1300,1310,1300,1305),
        ('2020-02-11 09:05:00',1305,1310,1300,1310),
        ('2020-02-12 09:00:00',1500,1505,1495,1500),
        ('2020-02-12 09:05:00',1500,1510,1500,1505),
    ]
    return pd.DataFrame(data,columns=['datetime','open','high','low','close']).assign(volume=100)


def audited():
    df=fixture_records()
    return audit_exploratory_csv(df.to_csv(index=False).encode(), 'Fonte declarada sem autenticação','sample.csv')


def test_reports_are_never_certified():
    c,_,d,_=audited()
    days,e,m,v,summary=assess_integrity(c,d)
    assert not days.backtest_liberado.any()
    assert not days.contrato_comprovado.any()
    assert not summary['pode_gerar_sinais_backtest_ou_ordens']
    assert summary['dias_nao_certificados']==len(days)==3


def test_missing_bars_not_interpolated():
    c,_,d,_=audited()
    _,events,_,_,summary=assess_integrity(c,d)
    gap=events[events.tipo=='LACUNA_DE_TEMPO']
    assert len(gap)==1
    assert gap.iloc[0].candles_ausentes==1
    assert summary['candles_ausentes_entre_extremos']==1
    assert summary['saltos_de_tempo']==1


def test_no_gap_crossing_sessions():
    c,_,d,_=audited()
    _,events,_,_,summary=assess_integrity(c,d)
    assert summary['pares_entre_sessoes']==2
    assert not events[(events.tipo=='LACUNA_DE_TEMPO') & (events.dia=='2020-02-11')].shape[0]


def test_adjacent_jump_skips_time_gap():
    c,_,d,_=audited()
    _,events,_,_,summary=assess_integrity(c,d)
    expected=events[events.tipo=='DIFERENCA_PRECO_ADJACENTE']
    assert len(expected)>0
    assert not expected.instante_seguinte.str.contains('09:15:00').any()
    assert summary['comparacoes_intradiarias_contiguas']==4


def test_expiry_nominal_not_identification():
    c,_,d,_=audited()
    days,events,months,expiry,summary=assess_integrity(c,d)
    assert expiry.vencimento_nominal.tolist()==['2020-02-12']
    assert not expiry.troca_de_contrato_comprovada.any()
    assert days.loc[days.dia=='2020-02-10','proximo_vencimento'].iloc[0]
    assert days.loc[days.dia=='2020-02-12','vencimento_nominal'].iloc[0]
    assert summary['datas_vencimento_nominal']==1


def test_summary_by_month():
    c,_,d,_=audited()
    days,_,m,_,summary=assess_integrity(c,d)
    assert m.pregoes.sum()==len(days)==3
    assert m.candles_ausentes_entre_extremos.sum()==1
    assert m.mes.tolist()==['2020-02']


def test_daily_export_matches():
    c,_,d,_=audited()
    s,diff=compare_daily_export(d.copy(),d)
    assert s['comparacao_estrutural_ok'] and diff.empty
    assert not s['autenticidade_verificada']


def test_daily_export_mismatch():
    c,_,d,_=audited()
    bad=d.copy()
    bad.loc[0,'candles_5min']+=1
    s,diff=compare_daily_export(bad,d)
    assert s['datas_divergentes']==1 and not s['comparacao_estrutural_ok']
    assert diff.iloc[0]['dia']=='2020-02-10'


def test_daily_export_missing_day():
    c,_,d,_=audited()
    s,diff=compare_daily_export(d.iloc[1:],d)
    assert s['datas_divergentes']==1


def test_daily_export_duplicate_rejected():
    _,_,d,_=audited()
    with pytest.raises(ValueError,match='duplicado'):
        compare_daily_export(pd.concat([d,d.iloc[[0]]]),d)


def test_bad_report_rejected():
    c,_,d,_=audited()
    bad=d.copy(); bad.loc[0,'barras_ausentes_entre_extremos']=999
    with pytest.raises(ValueError,match='diverge'):
        assess_integrity(c,bad)


def test_repeated_timestamp_rejected():
    c,_,d,_=audited(); c.loc[1,'datetime']=c.loc[0,'datetime']
    with pytest.raises(ValueError,match='duplicados'):
        assess_integrity(c,d)


def test_report_missing_date_rejected():
    c,_,d,_=audited()
    with pytest.raises(ValueError,match='datas'):
        assess_integrity(c,d.iloc[:-1])


def test_missing_field_rejected():
    c,_,d,_=audited()
    with pytest.raises(ValueError,match='Relatório'):
        assess_integrity(c,d.drop(columns=['candles_5min']))


def test_non_finite_price_rejected():
    c,_,d,_=audited(); c.loc[0,'close']=float('nan')
    with pytest.raises(ValueError,match='Preços inválidos'):
        assess_integrity(c,d)
