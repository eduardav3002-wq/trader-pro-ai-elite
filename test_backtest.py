"""Testes executáveis com: python test_backtest.py"""
from pathlib import Path
import pandas as pd
from engine import analyze, demo_data
from backtest import backtest, ENTRY_CUTOFF
from audit import audit_trades


def test_backtest():
    out=analyze(demo_data())
    trades=backtest(out)
    assert len(trades)>0, 'Teste precisa de pelo menos uma operação sintética.'
    assert (trades.entrada_candle > trades.sinal_candle).all()
    assert (trades.saida_candle >= trades.entrada_candle).all()
    assert (trades.entrada % 5==0).all()
    assert (trades.stop % 5==0).all()
    assert (trades.alvo % 5==0).all()
    assert (trades.saida % 5==0).all()
    assert (trades.slippage_points==10).all()
    assert ((trades.gross_points - trades.cost_points - trades.slippage_points - trades.net_points).abs()<1e-6).all()
    dates=pd.to_datetime(trades.entrada_data)
    end=pd.to_datetime(trades.saida_data)
    assert (dates.dt.date == end.dt.date).all()
    assert dates.dt.time.le(ENTRY_CUTOFF).all()
    assert (trades.groupby(dates.dt.date).size()<=3).all()
    # Drawdown precisa começar com patrimônio zero.
    e=pd.concat([pd.Series([0.]),trades.net_points.cumsum().reset_index(drop=True)],ignore_index=True)
    assert float((e-e.cummax()).min())<=0



def test_audit_old():
    root=Path(__file__).resolve().parent
    old=root/'_backtest_v03_amostra.csv'
    if old.exists():
        audited=audit_trades(pd.read_csv(old))
        assert len(audited)==15
        assert (audited.status_auditoria=='REJEITADA').all()
        assert audited.problemas.str.contains('grade WIN').all()
        assert audited.problemas.str.contains('feriado B3').all()


if __name__=='__main__':
    test_backtest()
    test_audit_old()
    count = len(backtest(analyze(demo_data())))
    print(f'OK: backtest, risco, slippage, sessão e auditoria ({count} trades fictícios)')


def test_reject_partial_sessions():
    from engine import analyze
    # A análise do candle pode funcionar; o backtest precisa de pregões fechados.
    partial = analyze(demo_data().iloc[1:].reset_index(drop=True),contract='WINZ26')
    try:
        backtest(partial, contract='WINZ26')
    except ValueError as exc:
        assert 'Pregão incompleto' in str(exc)
    else:
        raise AssertionError('Backtest de pregão incompleto deve ser bloqueado.')


def test_v06_risk_controls_and_audit():
    source=analyze(demo_data(), profile='seletivo')
    trades, audit=backtest(source, max_trade_risk_points=125.0,
                            max_consecutive_losses=2,min_reward_risk=1.0,
                            return_audit=True)
    assert not audit.empty
    assert len(audit)==int(source.signal.isin(['COMPRA','VENDA']).sum())
    assert (audit.decisao=='EXECUTADA').sum()==len(trades)
    assert trades.risco_stop_estimado_pts.le(125.0).all()
    assert trades.rr_teorico.ge(1.0).all()
    # Regra de pausa verifica sequência de perdas realizadas (por dia).
    for _, day in trades.groupby(pd.to_datetime(trades.entrada_data).dt.date):
        streak=0
        for x in day.net_points:
            assert streak < 2
            streak=streak+1 if x<0 else 0
    blocked, blocked_audit=backtest(source,max_trade_risk_points=5.0,
                                    return_audit=True)
    assert blocked.empty
    assert (blocked_audit.decisao=='RISCO_OPERACAO_EXCEDIDO').any()
    for params in ({'max_trade_risk_points':-1},
                   {'max_consecutive_losses':0},
                   {'min_reward_risk':float('nan')}):
        try:
            backtest(source,**params)
        except ValueError:
            pass
        else:
            raise AssertionError('Parâmetro de risco inválido passou.')
