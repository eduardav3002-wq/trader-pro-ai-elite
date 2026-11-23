"""Backtest de pesquisa: OHLC 5m validado, 15m apenas fechado, sem overnight."""
from datetime import time
import math

import pandas as pd
import numpy as np

from engine import TICK, validate_win_candles, contract_expiry, signal_entry_gate, ENTRY_CUTOFF

FLAT_CANDLE = time(18,10)   # saída no fechamento às 18:15, antes do call
COLUMNS = ('sinal_candle','entrada_candle','saida_candle','direcao','entrada','stop','alvo','saida',
           'motivo','gross_points','cost_points','slippage_points','net_points',
           'entrada_data','saida_data','tipo_horario_saida','risco_stop_estimado_pts','rr_teorico')


def backtest(data, cost_points=2.0, max_hold=12, slippage_ticks=1, max_daily_trades=3,
             max_daily_loss_points=200.0, contract=None,
             max_trade_risk_points=None, max_consecutive_losses=None,
             min_reward_risk=0.0, return_audit=False):
    """O custo informado equivale a pontos por operação completa, ADICIONAL ao slippage.

    1 tick = 5 pontos. Slippage simétrico adverso em entrada e saída.
    Entradas apenas no candle seguinte, desde que na mesma sessão.
    """
    for key,value in [('custo',cost_points),('limite de perda',max_daily_loss_points),
                      ('RR mínimo', min_reward_risk)]:
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value < 0:
            raise ValueError(f'Parâmetro inválido: {key}.')
    if max_trade_risk_points is not None and (isinstance(max_trade_risk_points, bool)
            or not isinstance(max_trade_risk_points,(int,float))
            or not math.isfinite(max_trade_risk_points) or max_trade_risk_points<=0):
        raise ValueError('Limite de risco por operação deve ser positivo.')
    if max_consecutive_losses is not None and (not isinstance(max_consecutive_losses,int)
            or isinstance(max_consecutive_losses,bool) or max_consecutive_losses < 1):
        raise ValueError('Limite de perdas consecutivas deve ser inteiro positivo.')
    if not isinstance(return_audit, bool):
        raise ValueError('return_audit inválido.')
    if not (isinstance(slippage_ticks,int) and not isinstance(slippage_ticks,bool) and slippage_ticks >= 0):
        raise ValueError('Slippage em ticks deve ser um inteiro não negativo.')
    if not (isinstance(max_hold,int) and not isinstance(max_hold,bool) and max_hold >= 1
            and isinstance(max_daily_trades,int) and not isinstance(max_daily_trades,bool) and max_daily_trades >= 1):
        raise ValueError('Duração e limite diário devem ser inteiros positivos.')
    required = {'datetime','open','high','low','close','signal','atr'}
    if not required.issubset(data.columns):
        raise ValueError('Execute analyze() sobre os candles antes do backtest.')
    # Exige todos os candles do início ao fim de cada sessão apresentada.
    # Evita contar liquidação fictícia em um CSV cortado antes do fechamento.
    df = validate_win_candles(
        data, require_complete_sessions=True, contract=contract).reset_index(drop=True)
    expiry = contract_expiry(contract) if contract else None
    records=[]
    daily = {}
    decisions = {}
    risk_checks = {}
    i = 34
    while i < len(df):
        direction = df.at[i,'signal']
        atr = float(df.at[i,'atr'])
        if direction not in ('COMPRA','VENDA'):
            i+=1;continue
        if not np.isfinite(atr) or atr<=0:
            decisions[i]='ATR_INVALIDO'; i+=1;continue
        entry_i=i+1
        signal_dt=df.at[i,'datetime']
        next_dt=df.at[entry_i,'datetime'] if entry_i < len(df) else None
        gate=signal_entry_gate(direction,signal_dt,next_dt,contract)
        if gate != 'ELEGIVEL_HORARIO':
            decisions[i]=gate; i+=1;continue
        entry_dt=next_dt
        day=entry_dt.date()
        d=daily.setdefault(day,{'trades':0,'net':0.0,'loss_streak':0})
        if d['trades']>=max_daily_trades:
            decisions[i]='MAX_OPERACOES_DIA'; i+=1;continue
        if d['net']<=-max_daily_loss_points:
            decisions[i]='LIMITE_PERDA_REALIZADA_DIA'; i+=1;continue
        if max_consecutive_losses is not None and d['loss_streak']>=max_consecutive_losses:
            decisions[i]='PAUSA_PERDAS_CONSECUTIVAS'; i+=1;continue
        side=1 if direction=='COMPRA' else -1
        open_mid=float(df.at[entry_i,'open'])
        entry=open_mid + side*slippage_ticks*TICK
        stop=(math.floor((entry-1.5*atr)/TICK)*TICK if side==1
              else math.ceil((entry+1.5*atr)/TICK)*TICK)
        target=(math.ceil((entry+2.0*atr)/TICK)*TICK if side==1
                else math.floor((entry-2.0*atr)/TICK)*TICK)
        if min(entry,stop,target)<=0 or (side==1 and not stop<entry<target) or (side==-1 and not target<entry<stop):
            decisions[i]='STOP_ALVO_INVALIDOS'; i+=1;continue
        # Stop teórico inclui slippage adverso adicional na saída e taxas;
        # gaps e liquidez ruim podem produzir perdas MAIORES que esta projeção.
        risk_points=round(side*(entry-stop)+slippage_ticks*TICK+cost_points,2)
        potential_gain=round(side*(target-entry)-slippage_ticks*TICK-cost_points,2)
        rr=(potential_gain/risk_points) if risk_points>0 else 0.0
        risk_checks[i] = (risk_points, round(rr, 3))
        if max_trade_risk_points is not None and risk_points>max_trade_risk_points:
            decisions[i]='RISCO_OPERACAO_EXCEDIDO'; i+=1;continue
        if rr<min_reward_risk:
            decisions[i]='RR_INSUFICIENTE'; i+=1;continue
        # A entrada só existe no próximo candle; nunca atravessa outro pregão.
        end_i=entry_i
        while end_i+1 < len(df) and end_i-entry_i+1 < max_hold:
            following=df.at[end_i+1,'datetime']
            if following.date()!=day or following.time()>FLAT_CANDLE:
                break
            end_i+=1
        exit_mid=None
        reason='TEMPO'
        for j in range(entry_i,end_i+1):
            opening=float(df.at[j,'open']); hi=float(df.at[j,'high']); lo=float(df.at[j,'low'])
            if side==1:
                if opening<=stop: exit_mid=opening;reason='GAP_STOP'
                elif opening>=target: exit_mid=target;reason='ALVO'
                elif lo<=stop: exit_mid=stop;reason='STOP'
                elif hi>=target: exit_mid=target;reason='ALVO'
            else:
                if opening>=stop: exit_mid=opening;reason='GAP_STOP'
                elif opening<=target: exit_mid=target;reason='ALVO'
                elif hi>=stop: exit_mid=stop;reason='STOP'
                elif lo<=target: exit_mid=target;reason='ALVO'
            if exit_mid is not None:break
        if exit_mid is None:
            j=end_i
            exit_mid=float(df.at[j,'close'])
            if df.at[j,'datetime'].time()==FLAT_CANDLE or (j+1<len(df) and df.at[j+1,'datetime'].date()!=day):
                reason='FIM_SESSAO'
            elif j==len(df)-1:
                reason='FIM_DADOS'
        exit_fill=exit_mid-side*slippage_ticks*TICK
        gross=round(side*(exit_mid-open_mid),2)
        slip=2*slippage_ticks*TICK
        net=round(gross-slip-cost_points,2)
        exited_at_close = reason in ('TEMPO','FIM_SESSAO','FIM_DADOS')
        exit_dt = df.at[j,'datetime'] + pd.Timedelta(minutes=5) if exited_at_close else df.at[j,'datetime']
        time_type = 'EXATO_FECHAMENTO_CANDLE' if exited_at_close else 'INICIO_CANDLE_SAIDA_INTRA_5M_TEMPO_INCERTO'
        rec={'sinal_candle':i,'entrada_candle':entry_i,'saida_candle':j,
             'direcao':direction,'entrada':entry,'stop':stop,'alvo':target,'saida':exit_fill,
             'motivo':reason,'gross_points':gross,'cost_points':cost_points,
             'slippage_points':slip,'net_points':net,
             'entrada_data':str(entry_dt),'saida_data':str(exit_dt),'tipo_horario_saida':time_type,
             'risco_stop_estimado_pts':risk_points,'rr_teorico':round(rr,3)}
        records.append(rec)
        d['trades']+=1;d['net']+=net
        d['loss_streak']=(d['loss_streak']+1) if net<0 else 0
        decisions[i]='EXECUTADA'
        # Sinais surgidos enquanto há posição são documentados, não executados.
        for held in range(i+1,j+1):
            if df.at[held,'signal'] in ('COMPRA','VENDA'):
                decisions[held]='POSICAO_ABERTA'
        i=j+1
    trades=pd.DataFrame(records,columns=COLUMNS)
    if not return_audit:
        return trades
    audit_rows=[]
    for idx in df.index[df.signal.isin(('COMPRA','VENDA'))]:
        risk_points, reward_risk = risk_checks.get(idx, (None, None))
        audit_rows.append({'sinal_candle':int(idx),
                           'sinal_data':str(df.at[idx,'datetime']),
                           'direcao':str(df.at[idx,'signal']),
                           'decisao':decisions.get(int(idx),'SEM_CANDLE_SEGUINTE'),
                           'risco_stop_estimado_pts':risk_points,
                           'limite_risco_pts':max_trade_risk_points,
                           'rr_teorico':reward_risk,
                           'janela_entrada':df.at[idx,'entry_gate_code'] if 'entry_gate_code' in df else signal_entry_gate(df.at[idx,'signal'],df.at[idx,'datetime'],df.at[idx+1,'datetime'] if idx+1<len(df) else None,contract)})
    return trades,pd.DataFrame(audit_rows,columns=('sinal_candle','sinal_data','direcao','decisao','janela_entrada','risco_stop_estimado_pts','limite_risco_pts','rr_teorico'))
