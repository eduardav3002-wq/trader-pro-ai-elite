"""Validação com calendário e sessões sintéticas: NÃO são dados financeiros."""
import ast
from pathlib import Path
import hashlib

import pandas as pd
import pytest

from forward_lab_v26 import (evaluate_prospective_v26, _baseline,
                             BASELINE_SHA256, _sha_protocol, PROTOCOL_V22, PROTOCOL_V25)
from test_forward_validation import sample_history, fake_future, payload


def check(fut, hist=None, as_of='2026-11-26 20:00'):
    return evaluate_prospective_v26(
        sample_history() if hist is None else hist, payload(fut),
        'TESTE SINTETICO SEM PRECO REAL', 'sintetico.csv', as_of=as_of)


@pytest.fixture(scope='module')
def result():
    return check(fake_future(sample_history()))


def test_base_congelada_tem_sha_fixo_e_oito_sessoes():
    history = sample_history()
    base = _baseline(history)
    assert len(base) == 904
    assert base.datetime.dt.date.nunique() == 8
    assert hashlib.sha256(base.to_csv(index=False).encode('utf-8')).hexdigest() == BASELINE_SHA256


def test_recibos_parametros_e_pre_registro_sem_autenticacao(result):
    receipt = result['recibo']
    assert receipt['qtd_pregoes_novos'] == 1
    assert receipt['datas_novas'] == ['2026-11-23']
    assert receipt['candles_novos'] == 113
    assert receipt['execucao_real'] is False
    assert receipt['fonte_verificada_independentemente'] is False
    assert receipt['recibo_original_v22']['versao'] == '2.2'
    assert receipt['sha256_protocolo_v22'] == _sha_protocol(PROTOCOL_V22)
    assert receipt['sha256_protocolo_v25'] == _sha_protocol(PROTOCOL_V25)
    assert receipt['sha256_base_congelada'] == BASELINE_SHA256
    assert len(result['comparativo']) == 12
    assert len(result['resumo_completo']) == 24
    assert len(result['por_dia']) == 24


def test_todas_as_operacoes_e_pregoes_sao_estritamente_novos(result):
    assert result['por_dia']['Pregão'].eq('2026-11-23').all()
    if len(result['operacoes']):
        assert pd.to_datetime(result['operacoes']['entrada_data']).ge('2026-11-23').all()
    assert '2026-11-20' not in set(result['por_dia']['Pregão'])


def test_resumo_e_registros_diarios_conciliam(result):
    for row in result['resumo_completo'].to_dict('records'):
        day = result['por_dia']
        subset = day.loc[day['Modo'].eq(row['Modo']) &
                         day['Limite (pts)'].eq(row['Limite (pts)']) &
                         day['Slippage (ticks/lado)'].eq(row['Slippage (ticks/lado)'])]
        assert len(subset) == 1
        assert round(float(subset['Resultado realizado (pts)'].sum()),2) == row['Saldo líquido (pts)']
        assert int(subset['Operações'].sum()) == row['Operações']


def test_csv_sem_contrato_recusado():
    no_ticker = fake_future(sample_history()).drop(columns=['contrato'])
    with pytest.raises(ValueError, match='coluna contrato'):
        check(no_ticker)


def test_csv_com_ticker_errado_recusado():
    wrong = fake_future(sample_history())
    wrong.loc[3, 'contrato'] = 'WINV26'
    with pytest.raises(ValueError, match='não corresponde'):
        check(wrong)


def test_pregao_nao_terminado_bloqueado():
    with pytest.raises(ValueError, match='posterior ao instante atual'):
        check(fake_future(sample_history()), as_of='2026-11-23 10:50')


def test_pregao_truncado_bloqueado():
    incomplete = fake_future(sample_history()).iloc[:-1]
    with pytest.raises(ValueError, match='Pregão incompleto'):
        check(incomplete)


def test_primeiro_pregao_pulado_bloqueado():
    with pytest.raises(ValueError, match='pregões faltando'):
        check(fake_future(sample_history(), days=['2026-11-24']))


def test_pregao_interno_faltante_bloqueado():
    with pytest.raises(ValueError, match='pregões inteiros ausentes'):
        check(fake_future(sample_history(), days=['2026-11-23','2026-11-25']))


def test_feriado_nao_tem_operacao():
    with pytest.raises(ValueError, match='feriado'):
        check(fake_future(sample_history(), days=['2026-11-20']))


def test_alteracao_qualquer_preco_ou_candle_da_base_impede_avaliacao():
    history = sample_history().copy()
    history.loc[0,'open'] += 5
    history.loc[0,'high'] += 5
    with pytest.raises(ValueError, match='base congelada'):
        check(fake_future(sample_history()), hist=history)


def test_dados_originais_nao_mutados():
    history = sample_history()
    fut = fake_future(history)
    orig = history.copy(deep=True)
    check(fut, hist=history)
    pd.testing.assert_frame_equal(history, orig)


def test_app_painel_presentes_e_sintaxe_ok():
    code = Path(__file__).with_name('app.py').read_text(encoding='utf-8')
    ast.parse(code)
    assert 'RESEARCH TERMINAL · V3.2' in code
    assert "st.expander('🧭 Validação prospectiva dupla · v2.6'" in code
    assert "st.session_state.get('forward_v26_result')" in code
    assert 'evaluate_prospective_v26(' in code
    assert 'ordem real automatizada' not in code.lower()


def test_painel_sem_csv_nem_resultado_nao_gera_name_error():
    from contextlib import nullcontext
    class EmptyUI:
        def __init__(self):
            self.session_state = {}
            self.messages = []
        def expander(self, *a, **kw): return nullcontext()
        def form(self, *a, **kw): return nullcontext()
        def info(self, text, *a, **kw): self.messages.append(text)
        def caption(self, text, *a, **kw): self.messages.append(text)
        def file_uploader(self, *a, **kw): return None
        def text_input(self, *a, **kw): return 'B3 · Boletim Diário do Mercado'
        def form_submit_button(self, *a, **kw): return False
    code = Path(__file__).with_name('app.py').read_text(encoding='utf-8')
    parsed = ast.parse(code)
    nodes = [n for n in ast.walk(parsed) if isinstance(n, ast.With)
             and len(n.items) == 1
             and isinstance(n.items[0].context_expr, ast.Call)
             and isinstance(n.items[0].context_expr.func, ast.Attribute)
             and n.items[0].context_expr.func.attr == 'expander'
             and n.items[0].context_expr.args
             and isinstance(n.items[0].context_expr.args[0], ast.Constant)
             and 'Validação prospectiva dupla' in n.items[0].context_expr.args[0].value]
    assert len(nodes) == 1
    fake = EmptyUI()
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])),
                 'app.py', 'exec'), {'st': fake})
    assert any('Sem resultado validado' in m for m in fake.messages)
