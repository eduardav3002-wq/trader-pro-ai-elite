"""Backtest retrospectivo, sem execução de ordens ou dados futuros na geração dos sinais."""
import math
import pandas as pd


def backtest(data, cost_points=2.0, max_hold=12):
    if cost_points < 0 or not math.isfinite(cost_points) or max_hold < 1:
        raise ValueError('Parâmetros inválidos.')
    required = {'open','high','low','close','signal','atr'}
    if not required.issubset(data.columns):
        raise ValueError('Execute analyze() antes do backtest.')
    df = data.reset_index(drop=True)
    records=[]
    i=34
    # Sinal no fechamento de i; entrada no candle i+1. Uma operação por vez.
    while i < len(df)-1:
        direction = df.at[i,'signal']
        atr = df.at[i,'atr']
        if direction not in ('COMPRA','VENDA') or pd.isna(atr) or atr <= 0:
            i += 1
            continue
        entry_i=i+1
        entry=float(df.at[entry_i,'open'])
        if not math.isfinite(entry):
            i += 1; continue
        side=1 if direction=='COMPRA' else -1
        stop=entry-side*1.5*float(atr)
        target=entry+side*2.0*float(atr)
        last_i=min(entry_i+max_hold-1,len(df)-1)
        exit_price=None; reason='TEMPO'
        for j in range(entry_i,last_i+1):
            hi=float(df.at[j,'high']); lo=float(df.at[j,'low']); op=float(df.at[j,'open'])
            # Gap: se abriu além do stop/alvo, executar na abertura (conservador).
            if side==1:
                if op<=stop: exit_price=op; reason='GAP_STOP'
                elif op>=target: exit_price=target; reason='ALVO'
                elif lo<=stop: exit_price=stop; reason='STOP'
                elif hi>=target: exit_price=target; reason='ALVO'
            else:
                if op>=stop: exit_price=op; reason='GAP_STOP'
                elif op<=target: exit_price=target; reason='ALVO'
                elif hi>=stop: exit_price=stop; reason='STOP'
                elif lo<=target: exit_price=target; reason='ALVO'
            # Se stop e alvo ocorrerem no mesmo candle, stop tem prioridade.
            if exit_price is not None: break
        if exit_price is None:
            j=last_i;exit_price=float(df.at[j,'close'])
            reason='FIM_DADOS' if j==len(df)-1 else 'TEMPO'
        gross=side*(exit_price-entry)
        rec={'sinal_candle':i,'entrada_candle':entry_i,'saida_candle':j,
             'direcao':direction,'entrada':round(entry,2),'stop':round(stop,2),
             'alvo':round(target,2),'saida':round(exit_price,2),'motivo':reason,
             'gross_points':round(gross,2),'cost_points':float(cost_points),
             'net_points':round(gross-cost_points,2)}
        if 'datetime' in df:
            rec['entrada_data']=str(df.at[entry_i,'datetime'])
            rec['saida_data']=str(df.at[j,'datetime'])
        records.append(rec)
        i=j+1  # Não reutiliza o candle de saída para um sinal.
    return pd.DataFrame(records)
