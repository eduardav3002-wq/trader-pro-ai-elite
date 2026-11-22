"""Laboratório EXPLORATÓRIO de integridade v1.3 — WIN 2019/2020.

Compara preços entre candles observados, sem pressupor transações durante
intervalos ausentes. Marca datas nominais de vencimento, nunca infere o ticker,
a rolagem efetiva, continuidade contratual ou a autenticidade dos preços.
NUNCA chama motor de sinais, backtest, nem libera dados para negociação.
"""
from __future__ import annotations

from datetime import date
import math
import numpy as np
import pandas as pd

from historical import index_expiry_days

CANDLES_FIELDS = {'datetime','open','high','low','close'}
DAILY_FIELDS = {'dia','candles_5min','primeiro_candle','ultimo_candle',
                'lacunas_internas','barras_ausentes_entre_extremos','abertura_referencia'}


def _validated_inputs(candles: pd.DataFrame, daily: pd.DataFrame):
    if not isinstance(candles,pd.DataFrame) or candles.empty or not CANDLES_FIELDS.issubset(candles.columns):
        raise ValueError('Candles ausentes ou sem preços OHLC/datetime.')
    if not isinstance(daily,pd.DataFrame) or daily.empty or not DAILY_FIELDS.issubset(daily.columns):
        raise ValueError('Relatório por dia incompleto para conferir a continuidade.')
    frame=candles.copy()
    frame['datetime']=pd.to_datetime(frame.datetime, errors='raise')
    if (frame.datetime.isna().any() or frame.datetime.duplicated().any()
        or not frame.datetime.is_monotonic_increasing):
        raise ValueError('Timestamps inválidos, duplicados ou fora de ordem.')
    if not frame.datetime.dt.minute.mod(5).eq(0).all():
        raise ValueError('Somente candles de abertura alinhados em 5 minutos.')
    for col in ('open','high','low','close'):
        frame[col]=pd.to_numeric(frame[col],errors='coerce')
        if not np.isfinite(frame[col].to_numpy(dtype=float)).all() or frame[col].le(0).any():
            raise ValueError('Preços inválidos ou ausentes.')
    d=daily.copy()
    d['dia']=pd.to_datetime(d.dia,errors='raise').dt.strftime('%Y-%m-%d')
    if d.dia.isna().any() or d.dia.duplicated().any():
        raise ValueError('Datas inválidas ou duplicadas no relatório diário.')
    df_days=frame.datetime.dt.strftime('%Y-%m-%d')
    groups=frame.groupby(df_days,sort=True)
    if set(groups.groups)!=set(d.dia):
        raise ValueError('Relatório diário não corresponde às datas dos candles.')
    d_index=d.set_index('dia')
    for day, g in groups:
        ref=d_index.loc[day]
        steps=g.datetime.diff()
        missing=int(((steps / pd.Timedelta(minutes=5))-1).where(steps>pd.Timedelta(minutes=5),0).sum())
        if (len(g)!=int(ref['candles_5min'])
            or g.datetime.iloc[0].strftime('%H:%M')!=str(ref['primeiro_candle'])
            or g.datetime.iloc[-1].strftime('%H:%M')!=str(ref['ultimo_candle'])
            or int(steps.gt(pd.Timedelta(minutes=5)).sum())!=int(ref['lacunas_internas'])
            or missing!=int(ref['barras_ausentes_entre_extremos'])):
            raise ValueError('Relatório diário diverge dos candles em '+day+'.')
    return frame,d


def assess_integrity(candles:pd.DataFrame, daily:pd.DataFrame):
    """Retorna (dias, eventos, meses, vencimentos, resumo).

    Percentis calculados na amostra inteira são APENAS descritivos e sujeitos a
    seleção/look-ahead; não podem calibrar sinais ou garantir qualidade.
    """
    f,d=_validated_inputs(candles,daily)
    date_s=f.datetime.dt.strftime('%Y-%m-%d')
    prev_time=f.datetime.shift(1)
    prev_date=date_s.shift(1)
    same_day=date_s.eq(prev_date)
    difftime=f.datetime-prev_time
    adjacent=same_day & difftime.eq(pd.Timedelta(minutes=5))
    missing=same_day & difftime.gt(pd.Timedelta(minutes=5))
    overnight=~same_day & prev_time.notna()
    # Não interpretamos variações após lacuna como negociações contínuas.
    jumps=(f.open-f.close.shift(1)).abs()
    adjacent_gaps=jumps[adjacent]
    percentile=float(adjacent_gaps.quantile(.999)) if not adjacent_gaps.empty else 0.0
    # Limiar exploratório é derivado da amostra; nunca é critério validado de erro.
    intraday_threshold=int(max(20,math.ceil(percentile/5)*5))
    intraday_flags=adjacent & jumps.ge(intraday_threshold)
    overnight_gaps=jumps[overnight]
    boundary_threshold=float(overnight_gaps.quantile(.95)) if not overnight_gaps.empty else float('inf')
    boundary_flags=overnight & jumps.ge(boundary_threshold) & jumps.gt(0)

    first_day=pd.Timestamp(f.datetime.iloc[0]).date()
    last_day=pd.Timestamp(f.datetime.iloc[-1]).date()
    expiries=index_expiry_days(first_day,last_day)
    expiry_set=set(expiries)
    day_numbers={str(x):int(i) for i,x in enumerate(d.dia)}
    records=[]
    for idx in np.flatnonzero(missing.to_numpy()):
        records.append({'dia':date_s.iloc[idx],'instante_anterior':str(prev_time.iloc[idx]),
                        'instante_seguinte':str(f.datetime.iloc[idx]),
                        'tipo':'LACUNA_DE_TEMPO',
                        'candles_ausentes':int(difftime.iloc[idx]/pd.Timedelta(minutes=5)-1),
                        'variacao_abertura_vs_fechamento_anterior_pts':float(f.open.iloc[idx]-f.close.iloc[idx-1]),
                        'interpretacao':'Intervalo sem candles; movimento intermediário desconhecido',
                        'contrato_identificado':False})
    for idx in np.flatnonzero(intraday_flags.to_numpy()):
        records.append({'dia':date_s.iloc[idx],'instante_anterior':str(prev_time.iloc[idx]),
                        'instante_seguinte':str(f.datetime.iloc[idx]),
                        'tipo':'DIFERENCA_PRECO_ADJACENTE',
                        'candles_ausentes':0,
                        'variacao_abertura_vs_fechamento_anterior_pts':float(f.open.iloc[idx]-f.close.iloc[idx-1]),
                        'interpretacao':'Variação rara nesta amostra; não implica erro ou rolagem',
                        'contrato_identificado':False})
    for idx in np.flatnonzero(boundary_flags.to_numpy()):
        records.append({'dia':date_s.iloc[idx],'instante_anterior':str(prev_time.iloc[idx]),
                        'instante_seguinte':str(f.datetime.iloc[idx]),
                        'tipo':'DIFERENCA_ENTRE_SESSOES_P95',
                        'candles_ausentes':None,
                        'variacao_abertura_vs_fechamento_anterior_pts':float(f.open.iloc[idx]-f.close.iloc[idx-1]),
                        'interpretacao':'Entre sessões; não há continuidade ou mesma série contratual comprovada',
                        'contrato_identificado':False})
    cols=['dia','instante_anterior','instante_seguinte','tipo','candles_ausentes',
          'variacao_abertura_vs_fechamento_anterior_pts','interpretacao','contrato_identificado']
    events=pd.DataFrame(records,columns=cols).sort_values(['dia','instante_seguinte','tipo']).reset_index(drop=True)

    # Primeiro candle de cada pregão frente ao ÚLTIMO registrado do pregão anterior:
    # NÃO é a mesma coisa que gap em 5 minutos e NÃO identifica rolagem.
    session_gaps={date_s.iloc[idx]:float(f.open.iloc[idx]-f.close.iloc[idx-1])
                  for idx in np.flatnonzero(overnight.to_numpy())}
    intraday_counts=events.loc[events.tipo.eq('DIFERENCA_PRECO_ADJACENTE'),'dia'].value_counts().to_dict()
    near_dates={day: min((abs((date.fromisoformat(day)-ex).days) for ex in expiries),default=10_000)
                for day in d.dia}
    day_records=[]
    for raw in d.to_dict('records'):
        day=raw['dia']
        close_gap=session_gaps.get(day)
        close_gap_large=close_gap is not None and abs(close_gap)>=boundary_threshold and abs(close_gap)>0
        warnings=[]
        if int(raw['lacunas_internas'])>0: warnings.append('LACUNAS_INTERNAS')
        if str(raw['primeiro_candle'])!=str(raw['abertura_referencia']): warnings.append('ABERTURA_DIVERGENTE')
        if near_dates[day]==0: warnings.append('VENCIMENTO_NOMINAL')
        elif near_dates[day]<=2: warnings.append('PROXIMO_VENCIMENTO')
        if close_gap_large: warnings.append('MOVIMENTO_ENTRE_SESSOES_P95')
        if intraday_counts.get(day,0): warnings.append('DIFERENCA_PRECO_ADJACENTE_RARA')
        day_records.append({
            'dia':day,'candles_5min':int(raw['candles_5min']),
            'lacunas_internas':int(raw['lacunas_internas']),
            'candles_ausentes_entre_extremos':int(raw['barras_ausentes_entre_extremos']),
            'abertura_divergente':str(raw['primeiro_candle'])!=str(raw['abertura_referencia']),
            'primeiro_candle':str(raw['primeiro_candle']),'ultimo_candle':str(raw['ultimo_candle']),
            'diferenca_entre_sessoes_pts':close_gap,
            'entre_sessoes_top5pct_amostra':bool(close_gap_large),
            'descontinuidades_preco_adjacent_limite':int(intraday_counts.get(day,0)),
            'vencimento_nominal':near_dates[day]==0,
            'proximo_vencimento':0<near_dates[day]<=2,
            'avisos_investigacao':'; '.join(warnings) if warnings else 'SEM_ALERTA_LOCAL',
            'status':'NAO_CERTIFICADO','contrato_comprovado':False,
            'origem_primaria_comprovada':False,'backtest_liberado':False,
        })
    days=pd.DataFrame(day_records)
    days['mes']=days.dia.str[:7]
    monthly=(days.groupby('mes',sort=True)
             .agg(pregoes=('dia','size'),candles_5min=('candles_5min','sum'),
                  dias_com_lacunas=('lacunas_internas',lambda x:int((x>0).sum())),
                  candles_ausentes_entre_extremos=('candles_ausentes_entre_extremos','sum'),
                  dias_abertura_divergente=('abertura_divergente','sum'),
                  dias_diferenca_preco_adj=('descontinuidades_preco_adjacent_limite',lambda x:int((x>0).sum())),
                  dias_inter_sessoes_top5=('entre_sessoes_top5pct_amostra','sum'),
                  vencimentos_nominais=('vencimento_nominal','sum'))
             .reset_index())
    for col in monthly.columns[1:]:monthly[col]=monthly[col].astype(int)
    expiry_records=[]
    for e in expiries:
        exp=e.isoformat()
        window=days[days.dia.map(lambda x:abs((date.fromisoformat(x)-e).days)<=2)]
        expiry_records.append({'vencimento_nominal':exp,
              'dias_observados_na_janela':int(len(window)),
              'dias_abertura_divergente':int(window.abertura_divergente.sum()),
              'dias_com_lacunas':int(window.lacunas_internas.gt(0).sum()),
              'maior_diferenca_entre_sessoes_pts':float(window.diferenca_entre_sessoes_pts.abs().max()) if window.diferenca_entre_sessoes_pts.notna().any() else None,
              'troca_de_contrato_comprovada':False,
              'observacao':'Vencimento nominal: não prova contrato, dia de rolagem ou ajuste.'})
    exp_table=pd.DataFrame(expiry_records,columns=['vencimento_nominal','dias_observados_na_janela',
       'dias_abertura_divergente','dias_com_lacunas','maior_diferenca_entre_sessoes_pts',
       'troca_de_contrato_comprovada','observacao'])
    summary={'versao':'1.3','tipo':'INTEGRIDADE_EXPLORATORIA_SEM_BACKTEST',
             'pregoes_observados':int(len(days)),'candles_observados':int(len(f)),
             'meses_observados':int(len(monthly)),'datas_vencimento_nominal':int(len(expiries)),
             'dias_lacunas':int(days.lacunas_internas.gt(0).sum()),
             'saltos_de_tempo':int(missing.sum()),
             'candles_ausentes_entre_extremos':int(days.candles_ausentes_entre_extremos.sum()),
             'dias_abertura_divergente':int(days.abertura_divergente.sum()),
             'comparacoes_intradiarias_contiguas':int(adjacent.sum()),
             'limiar_descritivo_diferenca_intradiaria_pts':intraday_threshold,
             'diferencas_preco_adjacente_acima_limiar':int(intraday_flags.sum()),
             'pares_entre_sessoes':int(overnight.sum()),
             'limiar_descritivo_top5pct_entre_sessoes_pts':round(boundary_threshold,3) if math.isfinite(boundary_threshold) else None,
             'diferencas_entre_sessoes_top5pct':int(boundary_flags.sum()),
             'dias_sem_alerta_local_v13':int(days.avisos_investigacao.eq('SEM_ALERTA_LOCAL').sum()),
             'dias_nao_certificados':int(len(days)),
             'contrato_identificado':False,'origem_primaria_autenticada':False,
             'serie_continua_ajustada_comprovada':False,'encerramentos_certificados':False,
             'pode_gerar_sinais_backtest_ou_ordens':False,
             'metodologia':'Diferenças de abertura vs. fechamento anterior apenas entre candles de 5m adjacentes; nunca atravessa lacuna ou sessão. Limiar intradiário exploratório: máximo de 20 pts e percentil 99,9 da amostra (arredondado para tick). Entre sessões: percentil 95 do valor absoluto. Valores relativos à própria amostra, não calibrados fora dela.',
             'ressalvas':['Variações de preço NÃO demonstram troca de contrato ou falha de negociação.',
                          'Diferenças entre sessões podem refletir mercado, feriados, horários parciais, ou troca de contrato desconhecida.',
                          'Padrões e limiares usam a própria amostra e não são sinal preditivo.',
                          'Uma lacuna temporal NÃO prova que não houve negociação.',
                          'Não há autenticação do ticker, origem primária, fuso, rolagem, horário final ou continuidade real.',
                          'NÃO há dados liberados para backtest, ordens ou decisões financeiras reais.']}
    return days,events,monthly,exp_table,summary


def compare_daily_export(reference:pd.DataFrame, original:pd.DataFrame):
    """Conferência opcional do CSV de auditoria v1.2 contra o recalculado.

    Não autentica fonte de preços. Falha de comparação informa divergências;
    não modifica nenhum registro de mercado.
    """
    if not isinstance(reference,pd.DataFrame) or not isinstance(original,pd.DataFrame):
        raise ValueError('Relatórios diários precisam ser tabelas.')
    columns=['dia','candles_5min','primeiro_candle','ultimo_candle',
             'lacunas_internas','barras_ausentes_entre_extremos','abertura_referencia']
    if not set(columns).issubset(reference.columns) or not set(columns).issubset(original.columns):
        raise ValueError('Arquivo de qualidade por dia sem colunas esperadas da v1.2.')
    a=reference[columns].copy();b=original[columns].copy()
    for x in (a,b):
        x['dia']=pd.to_datetime(x.dia,errors='raise').dt.strftime('%Y-%m-%d')
        if x.dia.duplicated().any() or x.dia.isna().any():
            raise ValueError('Dia duplicado ou inválido no CSV de qualidade.')
        for col in ['candles_5min','lacunas_internas','barras_ausentes_entre_extremos']:
            x[col]=pd.to_numeric(x[col],errors='raise').astype(int)
    joined=a.merge(b,on='dia',how='outer',suffixes=('_csv','_atual'),indicator=True)
    missing=joined._merge.ne('both')
    comparisons=[joined[col+'_csv'].ne(joined[col+'_atual']) for col in columns if col!='dia']
    mismatch=missing.copy()
    for p in comparisons: mismatch = mismatch | p
    diff=joined.loc[mismatch,['dia','_merge']].copy()
    for col in columns[1:]:
        diff[col+'_csv']=joined.loc[mismatch,col+'_csv']
        diff[col+'_atual']=joined.loc[mismatch,col+'_atual']
    diff=diff.sort_values('dia').reset_index(drop=True)
    return {'linhas_csv':int(len(a)),'linhas_recalculadas':int(len(b)),
            'datas_divergentes':int(len(diff)),
            'comparacao_estrutural_ok':bool(diff.empty),
            'autenticidade_verificada':False}, diff
