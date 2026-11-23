"""Regressão da auditoria pareada: histórico público exploratório, sem backtest externo."""
import pandas as pd
import pytest

from execution_audit import audit_slippage_scenarios


@pytest.fixture(scope='module')
def audit():
    src = pd.read_csv('WINZ26_B3_2026-11-10_a_19_M5.csv')
    return audit_slippage_scenarios(src, 'WINZ26')


def pair(audit, limit, slip):
    p = audit['comparacoes']
    return p.loc[p['Limite (pts)'].eq(limit) &
                 p['Slippage comparado (ticks/lado)'].eq(slip)].iloc[0]


def trades(audit, limit, slip):
    t = audit['operacoes_pareadas']
    return t.loc[t['Limite (pts)'].eq(limit) &
                 t['Slippage comparado (ticks/lado)'].eq(slip)]


def test_estrutura_e_exportacoes(audit):
    assert len(audit['comparacoes']) == 8
    assert not audit['operacoes_pareadas'].empty
    assert len(audit['operacoes_por_cenario']) == (2+2+1+4*3+12*3)
    assert set(audit) == {'comparacoes','operacoes_pareadas','operacoes_por_cenario'}


def test_250_risco_pnl_decomposto_1_para_2(audit):
    row = pair(audit,250,2)
    assert row['Operações em comum'] == 4
    assert row['Saldo base (pts)'] == 682
    assert row['Saldo comparado (pts)'] == 292
    assert row['Variação do resultado bruto (pts)'] == -350
    assert row['Variação dos custos (pts)'] == -40
    assert row['Variação líquida (pts)'] == -390


def test_250_risco_pnl_decomposto_1_para_3(audit):
    row = pair(audit,250,3)
    assert row['Operações em comum'] == 4
    assert row['Variação do resultado bruto (pts)'] == -340
    assert row['Variação dos custos (pts)'] == -80
    assert row['Variação líquida (pts)'] == -420
    assert row['Rebaixamento comparado (pts)'] == 192


def test_175_falsa_melhora_foi_operacao_bloqueada(audit):
    row = pair(audit,175,3)
    assert row['Só na base'] == 1
    assert row['Operações comparadas'] == 1
    sample = trades(audit,175,3)
    missing = sample.loc[sample['Correspondência'].eq('SO_BASE')].iloc[0]
    assert missing['Candle sinal'] == 444
    assert missing['Motivo sem operação'] == 'RISCO_OPERACAO_EXCEDIDO'
    assert missing['Saldo base (pts)'] == -167
    assert missing['Saldo comparado (pts)'] == 0


def test_saidas_de_trades_250_mudaram(audit):
    sample=trades(audit,250,2).set_index('Candle sinal')
    assert sample.at[314,'Saída base'] == 'ALVO'
    assert sample.at[314,'Saída comparada'] == 'TEMPO'
    assert sample.at[441,'Saída base'] == 'FIM_SESSAO'
    assert sample.at[441,'Saída comparada'] == 'STOP'
    assert sample.at[314,'Variação líquida (pts)'] == -195
    assert sample.at[441,'Variação líquida (pts)'] == -180


def test_custos_e_resultado_somam_para_todos_os_cenarios(audit):
    p=audit['comparacoes']
    assert (p['Variação líquida (pts)'].round(2) ==
            (p['Variação do resultado bruto (pts)']+p['Variação dos custos (pts)']).round(2)).all()


def test_500_drawdown_maior_que_200_por_operacao_e_acumulado(audit):
    row=pair(audit,500,3)
    assert row['Rebaixamento comparado (pts)'] == 1062
    assert row['Operações em comum'] == 12


def test_sem_pregoes_falsos_ou_incompletos():
    src=pd.read_csv('WINZ26_B3_2026-11-10_a_19_M5.csv')
    with pytest.raises(ValueError):
        audit_slippage_scenarios(src.head(22),'WINZ26')


def test_nao_selecionar_automaticamente_melhor_limite(audit):
    assert 'melhor_limite' not in audit
    assert 'ordens_liberadas' not in audit
