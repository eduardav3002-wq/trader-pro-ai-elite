"""Auditoria do backtest antigo: não altera dados e não recalcula lucros."""
from datetime import time
import math
import pandas as pd

from engine import TICK, HOLIDAYS_2026, SPECIAL_OPEN_2026


def audit_trades(trades):
    needed = {'direcao','entrada','stop','alvo','saida','entrada_data','saida_data'}
    if not needed.issubset(trades.columns):
        raise ValueError('Envie CSV de OPERAÇÕES com colunas: ' + ', '.join(sorted(needed)))
    out=trades.copy()
    status=[]; issues=[]
    for _,row in out.iterrows():
        errors=[]
        for c in ('entrada','stop','alvo','saida'):
            try:
                price=float(row[c])
                if not math.isfinite(price) or price<=0 or abs(price/TICK-round(price/TICK))>1e-7:
                    errors.append(f'{c}: preço fora da grade WIN (5 pts)')
            except (TypeError,ValueError):
                errors.append(f'{c}: preço ausente/inválido')
        try:
            entered=pd.Timestamp(row['entrada_data'])
            exited=pd.Timestamp(row['saida_data'])
            if entered.tzinfo is not None: entered=entered.tz_convert('America/Sao_Paulo').tz_localize(None)
            if exited.tzinfo is not None: exited=exited.tz_convert('America/Sao_Paulo').tz_localize(None)
            if entered.weekday()>=5 or not (time(9,0)<=entered.time()<=time(18,20)):
                errors.append('entrada fora do pregão regular')
            if exited.weekday()>=5 or not (time(9,0)<=exited.time()<=time(18,25)):
                errors.append('saída fora do pregão regular')
            if entered.date() in HOLIDAYS_2026 or exited.date() in HOLIDAYS_2026:
                errors.append('feriado B3: sem negociação WIN')
            if entered.date() in SPECIAL_OPEN_2026 and entered.time()<SPECIAL_OPEN_2026[entered.date()]:
                errors.append('entrada anterior à abertura especial B3')
            if entered.date()!=exited.date(): errors.append('operação atravessa pregão')
            if exited < entered: errors.append('saída anterior à entrada')
        except (TypeError,ValueError,OverflowError):
            errors.append('data de entrada/saída inválida')
        if row['direcao'] not in ('COMPRA','VENDA'):
            errors.append('direção não reconhecida')
        status.append('REJEITADA' if errors else 'PASSOU VALIDACAO BASICA')
        issues.append(' | '.join(errors) if errors else 'Sem inconsistências básicas detectadas; origem NÃO certificada')
    out['status_auditoria']=status
    out['problemas']=issues
    return out
