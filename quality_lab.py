"""Camada de TRIAGEM DESCRITIVA v1.2: nenhum sinal, ordem ou backtest.

Toda linha permanece NÃO CERTIFICADA: um dia sem lacunas detectadas não prova
origem das cotações, ticker, horário efetivo de fechamento ou ajuste de rolagem.
"""
from __future__ import annotations

from datetime import date
import pandas as pd

from historical import index_expiry_days

CLASSES = {
    'LACUNAS_INTERNAS': 'Lacunas internas',
    'ABERTURA_DIVERGENTE': 'Abertura divergente',
    'VENCIMENTO_NOMINAL': 'Vencimento nominal',
    'ROLAGEM_PROXIMA': 'Proximidade de vencimento',
    'SEM_ALERTAS_LOCAIS': 'Sem alertas locais',
}


def quality_triage(candles: pd.DataFrame, daily: pd.DataFrame, gaps: pd.DataFrame):
    """Reconstrói alertas pela DATA (sem confiar no texto do relatório anterior).

    Não conclui que nenhuma barra faltou quando a sessão não está completa.
    As janelas contínuas são APENAS entre os dois extremos observados.
    Retorna (tabela por dia, resumo), ambos exclusivamente descritivos.
    """
    if candles is None or daily is None or len(candles) == 0 or len(daily) == 0:
        raise ValueError('É necessário importar dados históricos para calcular a qualidade.')
    needed={'datetime'}
    if not needed.issubset(candles.columns):
        raise ValueError('Falta a coluna datetime nos candles.')
    needed_daily={'dia','candles_5min','primeiro_candle','ultimo_candle','abertura_referencia','lacunas_internas','alertas'}
    if not needed_daily.issubset(daily.columns):
        raise ValueError('Relatório diário incompleto.')
    frame=candles.copy()
    frame['datetime']=pd.to_datetime(frame['datetime'],errors='raise')
    if frame['datetime'].isna().any() or frame['datetime'].duplicated().any():
        raise ValueError('Candles inválidos ou repetidos.')
    frame=frame.sort_values('datetime')
    first=frame.datetime.min().date()
    last=frame.datetime.max().date()
    expiries=index_expiry_days(first,last)
    expiry_set=set(expiries)
    counts=frame.groupby(frame.datetime.dt.date)
    if len(counts)!=len(daily):
        raise ValueError('A tabela diária não coincide com as datas dos candles.')
    dates_seen=set()
    result=[]
    for raw in daily.to_dict('records'):
        day=date.fromisoformat(str(raw['dia']))
        if day in dates_seen or day not in counts.groups:
            raise ValueError('Dia duplicado ou ausente na auditoria.')
        dates_seen.add(day)
        group=counts.get_group(day)
        times=group.datetime.reset_index(drop=True)
        deltas=times.diff()
        broken=deltas.gt(pd.Timedelta(minutes=5))
        jump_count=int(broken.sum())
        if len(group)!=int(raw['candles_5min']) or jump_count!=int(raw['lacunas_internas']):
            raise ValueError(f'Inconsistência de quantidade de candles/lacunas em {day}.')
        sizes=broken.cumsum().value_counts()
        longest=int(sizes.max())
        num_segments=int(len(sizes))
        open_mismatch=str(raw['primeiro_candle']) != str(raw['abertura_referencia'])
        is_expiry=day in expiry_set
        near_expiry=any(abs((day-e).days)<=2 for e in expiry_set)
        categories=[]
        if jump_count:
            categories.append('LACUNAS_INTERNAS')
        if open_mismatch:
            categories.append('ABERTURA_DIVERGENTE')
        if is_expiry:
            categories.append('VENCIMENTO_NOMINAL')
        elif near_expiry:
            categories.append('ROLAGEM_PROXIMA')
        if not categories:
            categories=['SEM_ALERTAS_LOCAIS']
        prior=str(raw['alertas']).split('; ')
        nominal_old='DATA_NOMINAL_VENCIMENTO_WIN' in prior
        # Detecta divergência na UI/dados antigos, sem assumir que o antigo era certo.
        inconsistent=bool(nominal_old != is_expiry)
        result.append({
            'dia':day.isoformat(),
            'classe_principal': next((x for x in ('LACUNAS_INTERNAS','ABERTURA_DIVERGENTE','VENCIMENTO_NOMINAL','ROLAGEM_PROXIMA') if x in categories),'SEM_ALERTAS_LOCAIS'),
            'motivos':'; '.join(CLASSES[x] for x in categories),
            'lacunas_internas':jump_count,
            'candles_5min':len(group),
            'trechos_continuos_observados':num_segments,
            'maior_trecho_continuo_5m':longest,
            'primeiro_candle':str(raw['primeiro_candle']),
            'abertura_referencia':str(raw['abertura_referencia']),
            'ultimo_candle':str(raw['ultimo_candle']),
            'vencimento_nominal':is_expiry,
            'proximo_de_vencimento':near_expiry and not is_expiry,
            'discordancia_marcacao_anterior':inconsistent,
            'limites_sessao_conferidos':False,
            'contrato_e_origem_autenticados':False,
            'apto_para_backtest':False,
        })
    out=pd.DataFrame(result).sort_values('dia').reset_index(drop=True)
    summary={
        'versao':'1.2','classificacao':'AUDITORIA_EXPLORATORIA_SEM_BACKTEST',
        'pregoes_observados':int(len(out)),
        'dias_com_lacunas':int(out.lacunas_internas.gt(0).sum()),
        'dias_com_abertura_divergente':int((out.primeiro_candle!=out.abertura_referencia).sum()),
        'dias_vencimento_nominal':int(out.vencimento_nominal.sum()),
        'dias_proximos_vencimento':int(out.proximo_de_vencimento.sum()),
        'dias_sem_alerta_local':int(out.classe_principal.eq('SEM_ALERTAS_LOCAIS').sum()),
        'dias_com_discordancia_anterior':int(out.discordancia_marcacao_anterior.sum()),
        'maior_trecho_continuo_5m_observado':int(out.maior_trecho_continuo_5m.max()),
        'limites_sessao_conferidos':False,'contrato_e_origem_autenticados':False,
        'pode_gerar_sinais_ou_backtest':False,
        'expiries_nominais':[x.isoformat() for x in expiries],
        'observacao':'Ausência de alertas locais NÃO certifica a sessão nem os preços; horário efetivo de encerramento não confirmado.'
    }
    return out, summary
