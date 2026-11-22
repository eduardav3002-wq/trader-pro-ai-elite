"""Testes de integridade do laboratório v0.8; NÃO validam rentabilidade."""
import pandas as pd
import pytest

from research import robustness_report, summarize_trades
from engine import signal_entry_gate, market_day_gate, demo_data, validate_win_candles


def _trades():
    return pd.DataFrame({
        'entrada_data':['2026-11-16 11:00','2026-11-17 11:00',
                        '2026-11-18 11:00','2026-11-19 11:00'],
        'net_points':[10.,-20.,30.,-5.]})


def test_resumo_correct_metrics():
    result=summarize_trades(_trades())
    assert result['operacoes']==4
    assert result['positivas']==2
    assert result['taxa_acerto']==0.5
    assert result['saldo_pts']==15.
    assert result['drawdown_pts']==-20.
    assert result['profit_factor']==pytest.approx(40/25)


def test_split_does_not_slice_session():
    candles=demo_data(days=4)
    result=robustness_report(_trades(),candles)
    assert result['pregoes']==4
    periods=result['periodos']
    assert list(periods['Operações'])==[2,2]
    assert list(periods['Saldo (pts)'])==[-10,25]
    assert periods['Até'].iloc[0] < periods['De'].iloc[1]


def test_cost_stress_subtracts_extra_once_per_trade():
    result=robustness_report(_trades(),demo_data(days=4),additional_costs=(0,5,10))
    assert result['custos']['Saldo líquido (pts)'].tolist()==[15,-5,-25]
    assert result['custos']['Acerto líquido'].tolist()==[0.5,0.5,0.25]


def test_zero_trades_is_not_100percent():
    empty=_trades().iloc[0:0]
    r=robustness_report(empty,demo_data(days=2))
    assert r['resumo']['taxa_acerto'] is None
    assert r['resumo']['profit_factor'] is None
    assert all(r['custos']['Saldo líquido (pts)'] == 0)


def test_bad_cost_is_rejected():
    with pytest.raises(ValueError,match='não negativos'):
        robustness_report(_trades(),demo_data(days=4),additional_costs=(-1,))


def test_calendar_traps_2026_and_unknown_year():
    assert market_day_gate('2026-11-20 09:00') == 'FERIADO_B3'
    assert market_day_gate('2026-11-21 09:00') == 'FIM_DE_SEMANA'
    assert market_day_gate('2027-01-04 09:00') == 'CALENDARIO_NAO_VALIDADO'
    assert market_day_gate('2026-11-19 09:00') is None


def test_carnival_special_hours():
    assert signal_entry_gate('COMPRA','2026-02-18 12:00','2026-02-18 12:05','WINJ26') == 'FORA_SESSAO'
    assert signal_entry_gate('COMPRA','2026-02-18 13:05','2026-02-18 13:10','WINJ26') == 'ELEGIVEL_HORARIO'


def test_expiry_day_signals_blocked():
    assert signal_entry_gate('COMPRA','2026-06-17 10:00','2026-06-17 10:05','WINM26') == 'DIA_VENCIMENTO'


def test_fake_holiday_candles_refused():
    sample=demo_data(days=1)
    sample['datetime'] += pd.Timestamp('2026-11-20 09:00') - sample['datetime'].iloc[0]
    with pytest.raises(ValueError,match='feriado da B3'):
        validate_win_candles(sample,require_complete_sessions=True,contract='WINZ26')
