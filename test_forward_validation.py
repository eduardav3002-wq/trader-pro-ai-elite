"""Cenários sintéticos de desenvolvimento, nunca evidência de mercado."""
import hashlib

import pandas as pd
import pytest

from forward_validation import evaluate_forward, _stats, _drawdown, RISK_LIMITS
from engine import validate_win_candles
from risk_comparison import compare_risk_limits


def sample_history():
    return pd.read_csv('WINZ26_B3_2026-11-10_a_19_M5.csv')


def fake_future(history, days=('2026-11-23',)):
    """Duplica artificialmente a geometria do 19/11; PROIBIDO utilizar como preço real."""
    original = history.copy()
    original['datetime'] = pd.to_datetime(original['datetime'])
    last_day = original.loc[original.datetime.dt.date.eq(pd.Timestamp('2026-11-19').date())].copy()
    segments = []
    for day in days:
        section = last_day.copy()
        section['datetime'] = (pd.Timestamp(day) +
                               (section['datetime'] - section['datetime'].dt.normalize()))
        section['contrato'] = 'WINZ26'
        segments.append(section)
    return pd.concat(segments, ignore_index=True)


def payload(frame):
    return frame.to_csv(index=False).encode('utf-8')


def evaluate(frame, history=None, as_of='2026-11-26 20:00'):
    return evaluate_forward(
        sample_history() if history is None else history,
        payload(frame), 'Laboratório sintético, não autenticado', 'WINZ26',
        'arquivo-sintetico.csv', as_of=as_of,
    )


def test_recibo_e_cenarios_congelados_dias_e_operacoes_so_futuros():
    history = sample_history()
    future = fake_future(history)
    result = evaluate(future, history)
    receipt = result['recibo']
    assert receipt['versao'] == '2.2'
    assert receipt['classificacao'] == 'FORWARD_EXPLORATORIO_NAO_AUTENTICADO'
    assert receipt['ordens_liberadas'] is False
    assert receipt['origem_verificada_independentemente'] is False
    assert receipt['pregoes_avaliados'] == 1
    assert receipt['candles_avaliados'] == 113
    assert receipt['sha256_csv_avaliacao'] == hashlib.sha256(payload(future)).hexdigest()
    assert receipt['parametros_congelados']['limites_de_risco_pts'] == list(RISK_LIMITS)
    assert len(result['resumo']) == 4
    assert len(result['estresse']) == 12
    assert len(result['por_dia']) == 4
    assert set(result['por_dia']['Dia']) == {'2026-11-23'}
    assert list(result['resumo']['Limite (pts)']) == list(RISK_LIMITS)
    assert set(result['estresse']['Slippage (ticks por lado)']) == {1, 2, 3}
    if not result['operacoes'].empty:
        assert pd.to_datetime(result['operacoes']['entrada_data']).dt.date.min() >= pd.Timestamp('2026-11-23').date()
    assert (result['resumo']['Operações'].values == result['por_dia']['Operações'].values).all()


def test_simulacao_base_bate_com_o_comparador_anterior_filtrado():
    history = sample_history()
    later = fake_future(history)
    result = evaluate(later, history)['resumo']
    combined = pd.concat([history, later], ignore_index=True)
    expected = compare_risk_limits(combined, 'WINZ26', evaluation_start=pd.Timestamp('2026-11-23'))
    for col in ('Operações', 'Saldo líquido (pts)', 'Rebaixamento máximo (pts)'):
        assert result[col].tolist() == expected[col].tolist()


def test_exige_ticker_no_csv_de_validacao_futura():
    fut = fake_future(sample_history()).drop(columns=['contrato'])
    with pytest.raises(ValueError, match='coluna contrato'):
        evaluate(fut)


def test_bloqueia_pregao_futuro_ainda_nao_encerrado():
    with pytest.raises(ValueError, match='posterior ao instante atual'):
        evaluate(fake_future(sample_history()), as_of='2026-11-23 11:00')


def test_bloqueia_pregao_incompleto_e_sem_lacunas_inventadas():
    fut = fake_future(sample_history()).iloc[:-1]
    with pytest.raises(ValueError, match='Pregão incompleto'):
        evaluate(fut)


def test_bloqueia_pregoes_pulados_antes_do_primeiro_novo():
    fut = fake_future(sample_history(), days=('2026-11-24',))
    with pytest.raises(ValueError, match='pregões faltando'):
        evaluate(fut)


def test_bloqueia_dias_ausentes_entre_pregoes_novos():
    fut = fake_future(sample_history(), days=('2026-11-23', '2026-11-25'))
    with pytest.raises(ValueError, match='pregões inteiros ausentes'):
        evaluate(fut)


def test_bloqueia_feriado_b3_e_ano_invalido():
    with pytest.raises(ValueError, match='feriado'):
        evaluate(fake_future(sample_history(), days=('2026-11-20',)))
    with pytest.raises(ValueError, match='calendário B3 de 2026'):
        evaluate(fake_future(sample_history(), days=('2027-01-04',)))


def test_bloqueia_sobreposicao_da_amostra_inicial():
    with pytest.raises(ValueError, match='apenas pregões posteriores'):
        evaluate(fake_future(sample_history(), days=('2026-11-19',)))


def test_sem_trades_taxa_acerto_e_drawdown_nao_fabricados():
    empty = pd.DataFrame(columns=['net_points', 'entrada_data'])
    stats = _stats(empty, 3)
    assert stats['Taxa de acerto (%)'] is None
    assert stats['Saldo líquido (pts)'] == 0
    assert stats['Rebaixamento máximo (pts)'] == 0
    assert stats['Dias avaliados'] == 3
    assert _drawdown([-20, 50, -40]) == 40.0


def test_bloqueia_ticker_de_outro_contrato_sem_substituir_simbolo():
    fut = fake_future(sample_history())
    fut['contrato'] = 'WINV26'
    with pytest.raises(ValueError, match='não corresponde'):
        evaluate(fut)


def test_validacao_pura_sem_mutar_o_historico():
    history = sample_history()
    before = history.copy(deep=True)
    evaluate(fake_future(history), history)
    pd.testing.assert_frame_equal(before, history)


def test_estresse_da_amostra_nao_e_serie_futura():
    from forward_validation import sample_stress
    report = sample_stress(sample_history(), 'WINZ26')
    assert len(report) == 12
    base = report.loc[report['Slippage (ticks por lado)'].eq(1)]
    standard = compare_risk_limits(sample_history(), 'WINZ26')
    assert base['Operações'].tolist() == standard['Operações'].tolist()
    assert base['Saldo líquido (pts)'].tolist() == standard['Saldo líquido (pts)'].tolist()
    assert report.loc[
        report['Limite (pts)'].eq(250) & report['Slippage (ticks por lado)'].eq(2),
        'Saldo líquido (pts)',
    ].iloc[0] == 292.0
