"""Regressão da proteção pré-entrada, independentemente do desempenho da amostra."""
import ast
from pathlib import Path

import pandas as pd
import pytest

import backtest as bt
from backtest import backtest
from daily_budget_v25 import compare_daily_budget, compare_guarded_future
from engine import analyze
from forward_validation import evaluate_forward, RISK_LIMITS, SLIPPAGE_SCENARIOS
from test_forward_validation import fake_future, sample_history, payload


@pytest.fixture(scope='module')
def report():
    return compare_daily_budget(sample_history(), 'WINZ26')


def row(report, limit, slip, mode):
    df = report['resumo']
    return df.loc[df['Limite (pts)'].eq(limit) &
                  df['Slippage (ticks/lado)'].eq(slip) & df['Modo'].eq(mode)].iloc[0]


def test_cenarios_pares_e_resultados_legados_preservados(report):
    assert len(report['resumo']) == 2 * len(RISK_LIMITS) * len(SLIPPAGE_SCENARIOS)
    legacy_expect = {
        1: {125: (0, 0), 175: (2, 31), 250: (4, 682), 500: (12, 636)},
        2: {125: (0, 0), 175: (2, 21), 250: (4, 292), 500: (12, 561)},
        3: {125: (0, 0), 175: (1, 188), 250: (4, 262), 500: (12, 486)},
    }
    for slip, limits in legacy_expect.items():
        for limit, expected in limits.items():
            rec = row(report, limit, slip, 'LEGADO_V22')
            assert (rec['Operações'], rec['Saldo líquido (pts)']) == expected
            assert rec['Sinais bloqueados pelo orçamento'] == 0


def test_nova_trava_reproduz_bloqueios_e_resultados_da_amostra(report):
    a = row(report, 250, 3, 'PROTEGIDO_V25')
    b = row(report, 500, 3, 'PROTEGIDO_V25')
    assert (a['Operações'], a['Saldo líquido (pts)'], a['Sinais bloqueados pelo orçamento']) == (2, -4, 2)
    assert (b['Operações'], b['Saldo líquido (pts)'], b['Sinais bloqueados pelo orçamento']) == (2, -4, 17)
    assert (report['bloqueios']['risco_stop_estimado_pts'] >
            report['bloqueios']['orcamento_restante_antes_entrada_pts']).all()
    assert not report['bloqueios']['sinal_candle'].isna().any()


def test_pregoes_reconciliam_e_datas_nao_sao_inventadas(report):
    days = report['por_dia']
    assert len(days) == 24 * 8
    assert '2026-11-20' not in set(days['Pregão'])
    for r in report['resumo'].to_dict('records'):
        selected = days.loc[days['Limite (pts)'].eq(r['Limite (pts)']) &
                            days['Slippage (ticks/lado)'].eq(r['Slippage (ticks/lado)']) &
                            days['Modo'].eq(r['Modo'])]
        assert round(selected['Resultado realizado (pts)'].sum(), 2) == r['Saldo líquido (pts)']
        assert selected['Operações'].sum() == r['Operações']


def test_o_motor_padrao_e_o_mesmo_e_flag_invalida_falha():
    history = analyze(sample_history(), contract='WINZ26', profile='seletivo')
    parms = dict(contract='WINZ26', max_trade_risk_points=500,
                 max_consecutive_losses=2, min_reward_risk=1)
    original = backtest(history, **parms)
    flag_false = backtest(history, enforce_pretrade_daily_budget=False, **parms)
    pd.testing.assert_frame_equal(original, flag_false)
    for bad in ('true', 1, None):
        with pytest.raises(ValueError, match='booleano'):
            backtest(history, enforce_pretrade_daily_budget=bad, **parms)


def synthetic(monkeypatch, *, gap=False):
    times = pd.date_range('2026-11-10 09:00', periods=55, freq='5min')
    df = pd.DataFrame({'datetime': times, 'open': 130000., 'high': 130010.,
                       'low': 129910., 'close': 130000.,
                       'signal': ['AGUARDAR']*len(times), 'atr':60.})
    df.loc[[34, 36, 38] if not gap else [34, 37], 'signal'] = 'COMPRA'
    if gap:
        df.loc[35, 'low'] = 129990.
        df.loc[36, ['open','high','low','close']] = [129700., 129710., 129690., 129705.]
    monkeypatch.setattr(bt, 'validate_win_candles', lambda data, **kw: data.copy())
    monkeypatch.setattr(bt, 'signal_entry_gate', lambda *a: 'ELEGIVEL_HORARIO')
    return df


def test_orcamento_reduz_apos_perdas_realizadas(monkeypatch):
    df = synthetic(monkeypatch)
    base = backtest(df, max_daily_loss_points=200)
    guarded, audit = backtest(df, max_daily_loss_points=200,
                              enforce_pretrade_daily_budget=True, return_audit=True)
    assert len(base) == 3
    assert len(guarded) == 2
    assert (guarded['net_points'] == -97).all()
    blocked = audit.loc[audit['decisao'].eq('ORCAMENTO_DIARIO_INSUFICIENTE')].iloc[0]
    assert blocked['sinal_candle'] == 38
    assert blocked['orcamento_restante_antes_entrada_pts'] == 6.0
    assert blocked['risco_stop_estimado_pts'] == 97.0


def test_stop_nao_garante_limite_diario_quando_ha_gap(monkeypatch):
    df = synthetic(monkeypatch, gap=True)
    trades, audit = backtest(df, max_daily_loss_points=200,
                             enforce_pretrade_daily_budget=True, return_audit=True)
    assert len(trades) == 1
    assert trades.iloc[0]['motivo'] == 'GAP_STOP'
    assert trades.iloc[0]['net_points'] < -200
    assert audit.loc[audit['sinal_candle'].eq(37), 'decisao'].iloc[0] == 'LIMITE_PERDA_REALIZADA_DIA'


def test_protege_mesmo_com_zero_saldo_e_sem_ganhos_expandirem_orcamento(monkeypatch):
    df = synthetic(monkeypatch)
    trades, audit = backtest(df, max_daily_loss_points=0,
                             enforce_pretrade_daily_budget=True, return_audit=True)
    assert trades.empty
    assert (audit.loc[audit['decisao'].eq('ORCAMENTO_DIARIO_INSUFICIENTE'),
                      'orcamento_restante_antes_entrada_pts'] == 0).all()


def test_futura_sintetica_exclui_aquecimento_e_nao_muda_recibo_legado():
    history = sample_history()
    future = fake_future(history)
    kwargs = dict(as_of='2026-11-26 20:00')
    before = evaluate_forward(history, payload(future), 'LAB SINTETICO', 'WINZ26', 'synthetic.csv', **kwargs)
    added = compare_guarded_future(history, payload(future), 'LAB SINTETICO', 'WINZ26', 'synthetic.csv', **kwargs)
    assert before['recibo']['versao'] == '2.2'
    assert added['protocolo']['protocolo_v22_alterado'] is False
    assert added['protocolo']['recibo_validacao_v22']['sha256_csv_avaliacao'] == before['recibo']['sha256_csv_avaliacao']
    assert set(added['por_dia']['Pregão']) == {'2026-11-23'}
    assert (pd.to_datetime(added['operacoes']['entrada_data']) >= pd.Timestamp('2026-11-23')).all()
    assert not added['por_dia']['Pregão'].eq('2026-11-19').any()


def test_futura_rejeita_arquivo_com_dia_ausente_ou_ticker_incorreto():
    fut = fake_future(sample_history(), days=('2026-11-24',))
    with pytest.raises(ValueError, match='pregões faltando'):
        compare_guarded_future(sample_history(), payload(fut), 'LAB', 'WINZ26', 'fake.csv', as_of='2026-11-26 20:00')
    fut = fake_future(sample_history())
    fut['contrato'] = 'WINV26'
    with pytest.raises(ValueError, match='não corresponde'):
        compare_guarded_future(sample_history(), payload(fut), 'LAB', 'WINZ26', 'fake.csv', as_of='2026-11-26 20:00')


def test_app_v25_sem_acessar_variavel_nao_definida():
    app_text=Path(__file__).with_name('app.py').read_text(encoding='utf-8')
    ast.parse(app_text)
    assert 'RESEARCH TERMINAL · V3.2' in app_text
    assert '🛡️ Orçamento de risco antes da entrada · v2.5' in app_text
    assert "if 'sample_v25_budget' not in st.session_state:" in app_text
    assert "if 'later_v25_guard' in st.session_state:" in app_text
    assert 'import broker' not in app_text


def test_painel_v25_aberto_antes_do_calculo_nao_trava():
    from test_app_fragility_guard import FakeStreamlit

    class UIFake(FakeStreamlit):
        def button(self, *args, **kwargs):
            return False

    code = Path(__file__).with_name('app.py').read_text(encoding='utf-8')
    nodes = [node for node in ast.walk(ast.parse(code))
             if isinstance(node, ast.With) and len(node.items) == 1
             and isinstance(node.items[0].context_expr, ast.Call)
             and isinstance(node.items[0].context_expr.func, ast.Attribute)
             and node.items[0].context_expr.func.attr == 'expander'
             and node.items[0].context_expr.args
             and isinstance(node.items[0].context_expr.args[0], ast.Constant)
             and 'Orçamento de risco antes da entrada' in node.items[0].context_expr.args[0].value]
    assert len(nodes) == 1
    compiled = compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), code, 'exec')
    st = UIFake()
    exec(compiled, {'st': st})
    assert len(st.info_messages) == 1
    assert 'Toque no botão acima' in st.info_messages[0]
    assert not st.downloads


def test_painel_v25_resultado_carregado_nao_refaz_auditoria():
    from test_app_fragility_guard import FakeStreamlit

    class UIFake(FakeStreamlit):
        def button(self, *args, **kwargs):
            return False

    code = Path(__file__).with_name('app.py').read_text(encoding='utf-8')
    nodes = [node for node in ast.walk(ast.parse(code))
             if isinstance(node, ast.With) and len(node.items) == 1
             and isinstance(node.items[0].context_expr, ast.Call)
             and isinstance(node.items[0].context_expr.func, ast.Attribute)
             and node.items[0].context_expr.func.attr == 'expander'
             and node.items[0].context_expr.args
             and isinstance(node.items[0].context_expr.args[0], ast.Constant)
             and 'Orçamento de risco antes da entrada' in node.items[0].context_expr.args[0].value]
    report = {
        'resumo': pd.DataFrame([{'Limite (pts)': 250, 'Operações': 1}]),
        'bloqueios': pd.DataFrame(),
        'por_dia': pd.DataFrame([{'Pregão': '2026-11-10'}]),
        'operacoes': pd.DataFrame(),
        'protocolo': {'versao': '2.5'},
    }
    st = UIFake({'sample_v25_budget': report})
    compiled = compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), code, 'exec')
    exec(compiled, {'st': st, 'json': __import__('json')})
    assert len(st.downloads) == 5
