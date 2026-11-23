"""Testes regressivos para métricas descritivas, sem otimização de sinal."""
import pandas as pd
import pytest
from fragility_lab import analyze_fragility
from execution_audit import audit_slippage_scenarios

@pytest.fixture(scope='module')
def output():
    data = pd.read_csv('WINZ26_B3_2026-11-10_a_19_M5.csv')
    trades = audit_slippage_scenarios(data, 'WINZ26')['operacoes_por_cenario']
    return analyze_fragility(trades)


def get(output, limit, slip):
    r=output['resumo']
    return r[(r['Limite (pts)']==limit) & (r['Slippage (ticks por lado)']==slip)].iloc[0]


def test_all_scenarios_and_zero_operations(output):
    assert len(output['resumo'])==12
    for slip in [1,2,3]:
        row=get(output,125,slip)
        assert row['Operações']==0
        assert row['Saldo líquido (pts)']==0
        assert pd.isna(row['Percentual de saídas incertas (%)'])


def test_250_fragility(output):
    a=get(output,250,1)
    assert a['Operações']==4
    assert a['Saldo líquido (pts)']==682
    assert a['Saldo menos melhor operação (pts)']==384
    b=get(output,250,3)
    assert b['Saldo líquido (pts)']==262
    assert b['Saldo menos melhor operação (pts)']==74
    assert b['Saídas intrabar com tempo incerto']==2
    assert b['Dias com operação']==4
    assert not bool(b['Lucro depende da melhor operação'])


def test_500_fragility(output):
    row=get(output,500,3)
    assert row['Operações']==12
    assert row['Saldo líquido (pts)']==486
    assert row['Saldo menos melhor operação (pts)']==-57
    assert bool(row['Lucro depende da melhor operação'])
    assert row['Saídas intrabar com tempo incerto']==9
    assert row['Percentual de saídas incertas (%)']==75


def test_175_apparent_benefit(output):
    row=get(output,175,3)
    assert row['Operações']==1
    assert row['Saldo líquido (pts)']==188
    assert row['Saldo menos melhor operação (pts)']==0
    assert bool(row['Lucro depende da melhor operação'])


def test_dates_and_daily_sums(output):
    daily=output['por_dia']
    grouped=daily.groupby(['Limite (pts)','Slippage (ticks por lado)'])['Saldo líquido (pts)'].sum()
    for row in output['resumo'].itertuples(index=False):
        key=(row[0],row[1]); assert round(grouped.get(key,0),2)==row[5]


def test_reject_duplicate_signals():
    data=pd.DataFrame([{'Limite (pts)':250,'Slippage (ticks por lado)':1,'sinal_candle':1,'entrada_data':'2026-11-11 10:00:00','net_points':23,'tipo_horario_saida':'EXATO_FECHAMENTO_CANDLE'}]*2)
    with pytest.raises(ValueError,match='duplicado'):
        analyze_fragility(data)


def test_reject_foreign_scenario():
    data=pd.DataFrame([{'Limite (pts)':300,'Slippage (ticks por lado)':1,'sinal_candle':1,'entrada_data':'2026-11-11 10:00:00','net_points':23,'tipo_horario_saida':'EXATO_FECHAMENTO_CANDLE'}])
    with pytest.raises(ValueError,match='fora do protocolo'):
        analyze_fragility(data)


def test_validation_missing_column():
    with pytest.raises(ValueError,match='Campos ausentes'):
        analyze_fragility(pd.DataFrame())
