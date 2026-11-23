"""Cenarios artificiais para Smart Alerts. Nao sao cotacoes nem sinais reais."""
import ast
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from smart_alerts_v27 import (
    BRT, DEMO_SCENARIOS, SmartAlert, default_alert, demo_alert,
    effective_alert, eligible_live_candidate, should_notify,
)

T = datetime(2026, 11, 23, 10, 50, tzinfo=ZoneInfo('America/Sao_Paulo'))


def test_inicial_e_nao_operar_sem_feed():
    a = default_alert(T)
    assert a.status == 'NAO_OPERAR'
    assert a.event_id == 'sem_feed'
    assert not should_notify(None, a)


@pytest.mark.parametrize('scenario', list(DEMO_SCENARIOS))
def test_demo_somente_simulacao_60_segundos(scenario):
    a = demo_alert(scenario, T)
    assert a.mode == 'DEMONSTRACAO'
    assert a.expires_at == T + timedelta(seconds=60)
    assert 'demo:' in a.event_id
    assert should_notify(None, a)
    assert not should_notify(a.event_id, a)


def test_demo_dados_expirados_bloqueia_e_silencia():
    a = demo_alert('COMPRA', T)
    assert effective_alert(a, T + timedelta(seconds=59)).status == 'COMPRA'
    old = effective_alert(a, T + timedelta(seconds=60))
    assert old.status == 'NAO_OPERAR'
    assert old.event_id == 'demo_expirou'


def test_cenarios_desconhecidos_recusados():
    with pytest.raises(ValueError):
        demo_alert('COMPRA_CERTA', T)
    with pytest.raises(ValueError):
        demo_alert('VENDA', T, ttl_seconds=1000)


@pytest.mark.parametrize('key,changed', [
    ('feed_authorized',False),('quote_verified',False),
    ('candle_completed',False),('calendar_open',False),
    ('session_open',False),('risk_permitted',False),
])
def test_live_candidate_fail_closed_se_requisito_falhar(key, changed):
    values=dict(proposed='COMPRA', feed_authorized=True, quote_verified=True,
                quote_at=T-timedelta(seconds=4), now=T, candle_completed=True,
                calendar_open=True, session_open=True, risk_permitted=True)
    values[key]=changed
    status, _ = eligible_live_candidate(**values)
    assert status == 'NAO_OPERAR'


@pytest.mark.parametrize('when', [None,T-timedelta(seconds=45),T+timedelta(seconds=4)])
def test_live_candidate_sem_relogio_confiavel(when):
    status, _ = eligible_live_candidate(proposed='VENDA',feed_authorized=True,
        quote_verified=True, quote_at=when, now=T, candle_completed=True,
        calendar_open=True,session_open=True,risk_permitted=True)
    assert status == 'NAO_OPERAR'


def test_live_candidate_integro_so_informativo():
    status, reason = eligible_live_candidate(proposed='COMPRA',feed_authorized=True,
        quote_verified=True, quote_at=T-timedelta(seconds=4), now=T,
        candle_completed=True,calendar_open=True,session_open=True,risk_permitted=True)
    assert status == 'COMPRA'
    assert 'confirmacao manual' in reason


def test_nao_aceita_horarios_naive():
    with pytest.raises(ValueError,match='fuso'):
        SmartAlert('COMPRA','Teste','1',T.replace(tzinfo=None),T+timedelta(seconds=60))


def test_ui_usa_status_controlados_e_nao_conecta_corretora():
    app=Path(__file__).with_name('app.py').read_text(encoding='utf-8')
    ast.parse(app)
    assert 'RESEARCH TERMINAL · V3.2' in app
    assert 'Smart Alerts · v3.2' in app
    assert "@st.fragment(run_every='5s')" in app
    assert 'eligible_live_candidate(' not in app
    assert 'smart27_current' in app
    assert 'ordens reais' in app
