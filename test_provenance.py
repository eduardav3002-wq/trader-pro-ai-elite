"""Testes v1.0 de triagem e regras de expiração B3: dados artificiais."""
import io
import pandas as pd
import pytest

from engine import demo_data, session_bounds, contract_expiry, signal_entry_gate
from provenance import inspect_historical_csv, missing_trading_days
from validation import chronological_validation


AS_OF = '2026-11-22 17:00'


def synthetic_payload(days=4):
    candles = demo_data(days=days).copy()
    candles['symbol'] = 'WINZ26'
    return candles.to_csv(index=False).encode('utf-8'), candles


def inspect(payload, *, as_of=AS_OF, contract='WINZ26'):
    return inspect_historical_csv(payload, 'Exportação de testes fictícios', contract, 'teste.csv', as_of=as_of)


def test_metadados_nunca_autenticam_dados():
    payload, frame = synthetic_payload()
    cleaned, meta = inspect(payload)
    assert len(cleaned) == len(frame)
    assert meta['origem_verificada_independentemente'] is False
    assert meta['classificacao'] == 'CSV_HISTORICO_DECLARADO_NAO_AUTENTICADO'
    assert meta['ticker_presente_no_csv'] is True
    assert meta['pregoes_completos'] == 4
    assert meta['pregoes_inteiros_ausentes'] == 0
    assert len(meta['sha256']) == 64


def test_bloqueia_dia_inteiro_ausente():
    _, frame = synthetic_payload()
    without_middle = frame.loc[frame['datetime'].dt.date != pd.Timestamp('2026-11-17').date()]
    assert missing_trading_days(without_middle) == ['2026-11-17']
    with pytest.raises(ValueError, match='pregões inteiros ausentes'):
        inspect(without_middle.to_csv(index=False).encode('utf-8'))


def test_bloqueia_future_csv():
    payload, frame = synthetic_payload()
    with pytest.raises(ValueError, match='posterior ao instante atual'):
        inspect(payload, as_of='2026-11-17 12:00')


def test_bloqueia_fonte_e_contrato_incorretos():
    payload, frame = synthetic_payload()
    with pytest.raises(ValueError, match='fornecedor'):
        inspect_historical_csv(payload, 'a', 'WINZ26', 'teste.csv', as_of=AS_OF)
    with pytest.raises(ValueError, match='não corresponde'):
        inspect(payload, contract='WINV26')
    with pytest.raises(ValueError, match='contrato real'):
        inspect(payload, contract='WIN')


def test_sem_ticker_ressalva_declaracao():
    payload, frame = synthetic_payload()
    cleaned, meta = inspect(frame.drop(columns='symbol').to_csv(index=False).encode('utf-8'))
    assert not meta['ticker_presente_no_csv']
    assert any('DECLARADO' in w for w in meta['avisos'])


def test_falta_candle_intradiario_rejeita():
    _, frame = synthetic_payload()
    frame = frame.drop(frame.index[2])
    with pytest.raises(ValueError, match='Falha ou salto'):
        inspect(frame.to_csv(index=False).encode('utf-8'))


def test_feriado_rejeita_sem_arrumar_precos():
    _, frame = synthetic_payload(days=1)
    frame['datetime'] = frame.datetime + pd.Timedelta(days=1)
    with pytest.raises(ValueError, match='feriado'):
        inspect(frame.to_csv(index=False).encode('utf-8'))


def test_validacao_expiracao_2026_grade_mercado_oficial():
    assert str(contract_expiry('WINV26')) == '2026-10-14'
    assert str(contract_expiry('WINZ26')) == '2026-12-16'
    assert session_bounds(pd.Timestamp('2026-10-14').date(), 'WINV26')[1].strftime('%H:%M') == '16:55'
    assert session_bounds(pd.Timestamp('2026-12-16').date(), 'WINZ26')[1].strftime('%H:%M') == '17:55'
    assert signal_entry_gate('COMPRA','2026-12-16 10:00','2026-12-16 10:05','WINZ26') == 'DIA_VENCIMENTO'


def test_reserva_fracao_real_em_poucos_dias():
    candles = demo_data(days=4)
    trades = pd.DataFrame({'entrada_data':['2026-11-16 10:00'], 'net_points':[-10.]})
    outcome = chronological_validation(trades, candles, is_demo=True)
    assert outcome['frac_reserva_efetiva'] == 0.5
    assert outcome['pregoes_total'] == 4
    assert any('proporção efetiva 50%' in x for x in outcome['alertas'])
