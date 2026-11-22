"""Backtest de pesquisa: OHLC 5m validado, 15m apenas fechado, sem overnight."""
from datetime import time
import math

import pandas as pd
import numpy as np

from engine import TICK, validate_win_candles, contract_expiry

ENTRY_CUTOFF = time(17,55)  # margem antes do fechamento do pregão
FLAT_CANDLE = time(18,10)   # saída no fechamento às 18:15, antes do call
COLUMNS = ('sinal_candle','entrada_candle','saida_candle','direcao','entrada','stop','alvo','saida',
           'motivo','gross_points','cost_points','slippage_points','net_points',
           'entrada_data','saida_data','tipo_horario_saida')


def backtest(data, cost_points=2.0, max_hold=12, slippage_ticks=1, max_daily_trades=3,
             max_daily_loss_points=200.0, contract=None):
    """O custo informado equivale a pontos por operação completa, ADICIONAL ao slippage.

    1 tick = 5 pontos. Slippage simétrico adverso em entrada e saída.
    Entradas apenas no candle seguinte, desde que na mesma sessão.
    """
    for key,value in [('custo',cost_points),('limite de perda',max_daily_loss_points)]:
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value < 0:
            raise ValueError(f'Parâmetro inválido: {key}.')
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
    i = 34
    while i < len(df)-1:
        direction = df.at[i,'signal']
        atr = float(df.at[i,'atr'])
        if direction not in ('COMPRA','VENDA') or not np.isfinite(atr) or atr<=0:
            i+=1;continue
        entry_i=i+1
        signal_dt=df.at[i,'datetime']
        entry_dt=df.at[entry_i,'datetime']
        if entry_dt.date()!=signal_dt.date() or entry_dt-signal_dt!=pd.Timedelta(minutes=5):
            i+=1;continue
        if entry_dt.time()>ENTRY_CUTOFF:
            i+=1;continue
        day=entry_dt.date()
        # No vencimento há regras especiais de settlement/horário.
        # Excluímos todo o dia até modelarmos o vencimento explicitamente.
        if expiry and day == expiry:
            i+=1;continue
        d=daily.setdefault(day,{'trades':0,'net':0.0})
        if d['trades']>=max_daily_trades or d['net']<=-max_daily_loss_points:
            i+=1;continue
        side=1 if direction=='COMPRA' else -1
        open_mid=float(df.at[entry_i,'open'])
        entry=open_mid + side*slippage_ticks*TICK
        stop=(math.floor((entry-1.5*atr)/TICK)*TICK if side==1
              else math.ceil((entry+1.5*atr)/TICK)*TICK)
        target=(math.ceil((entry+2.0*atr)/TICK)*TICK if side==1
                else math.floor((entry-2.0*atr)/TICK)*TICK)
        if min(entry,stop,target)<=0 or (side==1 and not stop<entry<target) or (side==-1 and not target<entry<stop):
            i+=1;continue
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
             'entrada_data':str(entry_dt),'saida_data':str(exit_dt),'tipo_horario_saida':time_type}
        records.append(rec)
        d['trades']+=1;d['net']+=net
        i=j+1
    return pd.DataFrame(records,columns=COLUMNS)
