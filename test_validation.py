"""Testes de segmentação v0.9; não testam rentabilidade futura."""
import pandas as pd
import pytest

from engine import demo_data, market_day_gate, signal_entry_gate
from validation import chronological_validation


def trades_fixture():
    return pd.DataFrame({
        'entrada_data': [
            '2026-11-16 10:00', '2026-11-17 10:00',
            '2026-11-18 10:00', '2026-11-19 10:00'],
        'net_points': [20., -5., -10., 40.],
    })


def test_reserva_respeita_dias_e_usa_30_porcento():
    r = chronological_validation(trades_fixture(), demo_data(days=4), is_demo=True)
    assert r['pregoes_estudo'] == 2
    assert r['pregoes_reserva'] == 2
    assert r['estudo']['saldo_pts'] == 15
    assert r['reserva']['saldo_pts'] == 30
    assert r['segmentos'].iloc[0]['Até'] < r['segmentos'].iloc[1]['De']
    assert r['classificacao'] == 'SIMULAÇÃO — SEM EVIDÊNCIA DE MERCADO'


def test_custo_extra_na_reserva_sem_duplicar():
    r = chronological_validation(trades_fixture(), demo_data(days=4),
                                 is_demo=False, extra_cost_points=10)
    assert r['reserva']['saldo_pts'] == 30
    assert r['reserva_com_custo_extra']['saldo_pts'] == 10
    assert 'INSUFICIENTE' in r['classificacao']


def test_custo_extra_nao_inventa_operacoes_vencedoras():
    sample = trades_fixture().iloc[0:0]
    r = chronological_validation(sample, demo_data(days=4), is_demo=False)
    assert r['reserva']['operacoes'] == 0
    assert r['reserva']['taxa_acerto'] is None
    assert r['reserva_com_custo_extra']['saldo_pts'] == 0
    assert any('Não há operações' in x for x in r['alertas'])


def test_entrada_fora_amostra_rejeitada():
    t=trades_fixture()
    t.loc[0, 'entrada_data']='2026-11-13 10:00'
    with pytest.raises(ValueError,match='fora dos pregões'):
        chronological_validation(t, demo_data(days=4),is_demo=True)


def test_pregoes_insuficientes_bloqueados():
    with pytest.raises(ValueError,match='pelo menos dois'):
        chronological_validation(trades_fixture().iloc[0:0],demo_data(days=1),is_demo=True)


def test_argumentos_invalidos_bloqueados():
    with pytest.raises(ValueError,match='10% e 50%'):
        chronological_validation(trades_fixture(),demo_data(days=4),is_demo=False,reserve_fraction=0.8)
    with pytest.raises(ValueError,match='não negativo'):
        chronological_validation(trades_fixture(),demo_data(days=4),is_demo=False,extra_cost_points=-1)
    with pytest.raises(ValueError,match='booleano'):
        chronological_validation(trades_fixture(),demo_data(days=4),is_demo='não')


def test_julho_nove_aberto_conforme_b3():
    assert market_day_gate('2026-07-09 09:00') is None
    assert signal_entry_gate('COMPRA','2026-07-09 09:05', '2026-07-09 09:10', 'WINQ26') == 'ELEGIVEL_HORARIO'


def test_dezembro_trinta_um_fechado():
    assert market_day_gate('2026-12-31 10:00') == 'FERIADO_B3'
