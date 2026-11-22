"""v1.4: ticker alegado, nunca provado, sem promoção para backtest."""
from __future__ import annotations

import json
import pandas as pd
import pytest

from historical import audit_exploratory_csv
from integrity_lab import assess_integrity
from traceability_lab import nominal_expiry, read_contract_map, traceability_audit, EMPTY_TEMPLATE


def fixtures():
    candles=pd.DataFrame([
      ('2020-02-10 09:00:00',1000,1010,995,1000),
      ('2020-02-10 09:05:00',1000,1005,995,1000),
      ('2020-02-11 09:00:00',1005,1015,1000,1010),
      ('2020-02-11 09:05:00',1010,1020,1005,1015),
      ('2020-02-12 09:00:00',1100,1105,1095,1100),
      ('2020-02-12 09:05:00',1100,1110,1095,1105),
      ('2020-02-13 09:00:00',1110,1115,1105,1110),
      ('2020-02-13 09:05:00',1110,1120,1105,1115)
    ],columns=['datetime','open','high','low','close']).assign(volume=100)
    c,report,d,_=audit_exploratory_csv(candles.to_csv(index=False).encode(), 'GitHub declarado', 'sample.csv')
    days,_,_,_,_=assess_integrity(c,d)
    return d,days,report


def audit(map_bytes=None):
    d,k,origin=fixtures()
    if map_bytes is None:
        return traceability_audit(d,k,origin)
    mapping,digest=read_contract_map(map_bytes)
    return traceability_audit(d,k,origin,mapping,digest)


def test_expiry_nominal_months_and_years():
    assert nominal_expiry('WINZ19').isoformat()=='2019-12-18'
    assert nominal_expiry('WING20').isoformat()=='2020-02-12'
    assert nominal_expiry('winj20').isoformat()=='2020-04-15'
    assert nominal_expiry('WINM20').isoformat()=='2020-06-17'
    assert nominal_expiry('WINQ20').isoformat()=='2020-08-12'


@pytest.mark.parametrize('symbol', ['WIN2020','WINF20','WDOZ20','WINZ2','WINZ2020','WINZ00foo',''])
def test_invalid_contracts_rejected(symbol):
    with pytest.raises(ValueError,match='Contrato inválido'):
        nominal_expiry(symbol)


def test_no_map_blocks_all():
    days,transitions,checklist,dossier=audit()
    assert len(days)==4 and len(transitions)==3
    assert dossier['dias_sem_contrato_alegado']==4
    assert dossier['dias_com_contrato_alegado']==0
    assert dossier['dias_certificados']==0
    assert not days.backtest_liberado.any()
    assert not transitions.troca_efetiva_comprovada.any()
    assert (transitions.situacao=='TICKER_INDETERMINADO').all()
    assert all(x not in ('VALIDADO','CERTIFICADO') for x in checklist.situacao)


def test_declared_mapping_never_verifies_ticker():
    b=('inicio,fim,contrato,documento\n'
       '2020-02-10,2020-02-11,WING20,URL alegada\n'
       '2020-02-12,2020-02-13,WINJ20,\n').encode()
    days,transitions,checklist,dossier=audit(b)
    assert dossier['dias_com_contrato_alegado']==4
    assert dossier['mudancas_de_ticker_declaradas']==1
    assert days.contrato_alegado.tolist()==['WING20','WING20','WINJ20','WINJ20']
    assert transitions.situacao.tolist()==[
        'MESMO_TICKER_ALEGADO_SEM_AUTENTICACAO',
        'MUDANCA_DECLARADA_NAO_COMPROVADA',
        'MESMO_TICKER_ALEGADO_SEM_AUTENTICACAO']
    assert dossier['dias_com_ticker_autenticado']==0
    assert dossier['autoriza_sinais_backtest_ou_ordens'] is False
    assert all(not days[col].any() for col in ['ticker_por_candle_autenticado','origem_primaria_autenticada','backtest_liberado'])


def test_after_expiry_detected_but_no_real_rollover_inferred():
    b='inicio,fim,contrato,documento\n2020-02-12,2020-02-13,WING20,\n'.encode()
    days,_,_,dossier=audit(b)
    assert dossier['dias_declarados_apos_vencimento_nominal']==1
    assert days.loc[days.dia=='2020-02-13','apos_vencimento_nominal_do_contrato_alegado'].iloc[0]
    assert dossier['serie_ajustada_verificada'] is False


def test_overlap_rejected():
    b='inicio,fim,contrato,documento\n2020-02-10,2020-02-12,WING20,\n2020-02-12,2020-02-13,WINJ20,\n'.encode()
    with pytest.raises(ValueError,match='sobrepostos'):
        read_contract_map(b)


def test_reversed_range_rejected():
    b='inicio,fim,contrato,documento\n2020-02-13,2020-02-12,WINJ20,\n'.encode()
    with pytest.raises(ValueError,match='Início após fim'):
        read_contract_map(b)


def test_out_of_period_rejected():
    b='inicio,fim,contrato,documento\n2026-01-01,2026-01-02,WINZ26,\n'.encode()
    with pytest.raises(ValueError,match='2019–2020'):
        read_contract_map(b)


def test_empty_model_rejected_until_filled():
    with pytest.raises(ValueError,match='1 a 500'):
        read_contract_map(EMPTY_TEMPLATE)


def test_ambiguous_daily_rejected():
    d,k,report=fixtures()
    with pytest.raises(ValueError,match='duplicados'):
        traceability_audit(pd.concat([d,d.iloc[[0]]]),k,report)


def test_changed_count_rejected():
    d,k,report=fixtures();k.loc[0,'candles_5min']+=1
    with pytest.raises(ValueError,match='divergem'):
        traceability_audit(d,k,report)


def test_missing_hash_rejected():
    d,k,report=fixtures();report['sha256_recebido']='fake'
    with pytest.raises(ValueError,match='SHA-256'):
        traceability_audit(d,k,report)


def test_serializable_dossier():
    _,_,_,dossier=audit()
    assert json.loads(json.dumps(dossier))['dias_certificados']==0
    assert len(dossier['sha256_historico_recebido'])==64
    assert 'origem' in dossier['aviso'].lower()


def test_hash_changes_with_map_bytes():
    a=b'inicio,fim,contrato,documento\n2020-02-10,2020-02-10,WING20,\n'
    b=b'inicio,fim,contrato,documento\n2020-02-10,2020-02-11,WING20,\n'
    _,sha1=read_contract_map(a);_,sha2=read_contract_map(b)
    assert sha1!=sha2 and len(sha1)==64


def test_csv_spreadsheet_formula_in_reference_rejected():
    payload=b'inicio,fim,contrato,documento\n2020-02-10,2020-02-10,WING20,=HYPERLINK(1)\n'
    with pytest.raises(ValueError,match='fórmula'):
        read_contract_map(payload)


def test_date_requires_padded_iso():
    payload=b'inicio,fim,contrato,documento\n2020-2-10,2020-02-11,WING20,fonte\n'
    with pytest.raises(ValueError,match='Datas'):
        read_contract_map(payload)
