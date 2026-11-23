"""Smoke tests for the frozen DEMO-only publisher and the v3.2 diagnostics."""
from datetime import datetime, timezone
from pathlib import Path
import ast
import pytest
from bridge_v31 import make_event, BridgeConfig, publish_demo, project_url

class FakeResponse:
    status = 201
    def __enter__(self): return self
    def __exit__(self, typ, val, tb): pass

def test_demo_payload_and_private_header_never_in_event():
    requests=[]
    def fake_request(req, timeout):
        requests.append(req)
        return FakeResponse()
    config = BridgeConfig('https://abcdefgh.supabase.co', 'sb_secret_'+ 'a'*25)
    e=publish_demo(config,'NAO_OPERAR',opener=fake_request,
                   now=datetime(2026,11,23,tzinfo=timezone.utc))
    assert e['mode']=='DEMONSTRACAO' and e['contract']=='WINZ26'
    assert e['status']=='NAO_OPERAR' and len(e['event_id'])>=30
    assert 'secret' not in str(e).lower()
    assert requests[0].headers['Apikey'].startswith('sb_secret_')

def test_invalid_url_and_status_fail_closed():
    with pytest.raises(ValueError): project_url('https://example.com')
    with pytest.raises(ValueError): make_event('LIVE_COMPRA')

def test_app_audit_ui_and_version_are_present():
    app=Path(__file__).with_name('app.py').read_text(encoding='utf-8')
    ast.parse(app)
    assert 'RESEARCH TERMINAL · V3.2' in app
    assert 'bridge32_publish_log' in app
    assert 'NÃO CONFIRMADO' in app
    assert 'ponte_publicacoes_demo_v32.csv' in app
    assert 'record_bridge32_publish(event' in app
