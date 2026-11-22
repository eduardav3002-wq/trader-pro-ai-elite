"""Garantias da triagem descritiva; NUNCA converte histórico em backtest."""
import io
import pandas as pd
import pytest

from historical import audit_exploratory_csv
from quality_lab import quality_triage


def synthetic(days=('2020-02-10','2020-02-12','2020-02-14'), gaps=()):
    rows=[]
    for day in days:
        for ts in pd.date_range(f'{day} 09:00',periods=8,freq='5min'):
            if str(ts) in gaps:
                continue
            rows.append({'datetime':str(ts),'open':100000,'high':100010,
                         'low':99990,'close':100005,'volume':100})
    data=pd.DataFrame(rows).to_csv(index=False).encode('utf-8')
    candles,old,daily,gaplist=audit_exploratory_csv(data,'Arquivo de teste','sintetico.csv')
    return candles,daily,gaplist


def test_expiry_exact_date_and_nearby_label():
    c,d,g=synthetic()
    q,r=quality_triage(c,d,g)
    feb10=q.loc[q.dia=='2020-02-10'].iloc[0]
    feb12=q.loc[q.dia=='2020-02-12'].iloc[0]
    feb14=q.loc[q.dia=='2020-02-14'].iloc[0]
    assert bool(feb10.vencimento_nominal) is False
    assert bool(feb10.proximo_de_vencimento) is True
    assert bool(feb12.vencimento_nominal) is True
    assert bool(feb14.proximo_de_vencimento) is True
    assert r['dias_vencimento_nominal']==1
    assert r['dias_com_discordancia_anterior']==0


def test_detects_alert_text_inconsistency_not_false_expiry():
    c,d,g=synthetic()
    d.loc[d.dia=='2020-02-10','alertas']='DATA_NOMINAL_VENCIMENTO_WIN'
    q,r=quality_triage(c,d,g)
    assert r['dias_com_discordancia_anterior']==1
    assert not bool(q.loc[q.dia=='2020-02-10','vencimento_nominal'].iloc[0])


def test_continuous_segments_and_missing_candle():
    c,d,g=synthetic(days=('2020-07-09',),gaps=('2020-07-09 09:20:00',))
    q,r=quality_triage(c,d,g)
    assert int(q.trechos_continuos_observados.iloc[0])==2
    assert int(q.maior_trecho_continuo_5m.iloc[0])==4
    assert r['dias_com_lacunas']==1
    assert q.classe_principal.iloc[0]=='LACUNAS_INTERNAS'


def test_open_mismatch_but_not_market_certification():
    c,d,g=synthetic(days=('2020-07-09',))
    d.loc[0,'abertura_referencia']='08:55'
    q,r=quality_triage(c,d,g)
    assert q.classe_principal.iloc[0]=='ABERTURA_DIVERGENTE'
    assert not q.apto_para_backtest.any()


def test_no_local_issues_still_uncertified():
    c,d,g=synthetic(days=('2020-07-09',))
    q,r=quality_triage(c,d,g)
    assert q.classe_principal.iloc[0]=='SEM_ALERTAS_LOCAIS'
    assert r['dias_sem_alerta_local']==1
    assert r['pode_gerar_sinais_ou_backtest'] is False
    assert not q.contrato_e_origem_autenticados.any()
    assert not q.limites_sessao_conferidos.any()


def test_bad_daily_count_is_rejected():
    c,d,g=synthetic(days=('2020-07-09',))
    d.loc[0,'candles_5min']=999
    with pytest.raises(ValueError,match='Inconsistência'):
        quality_triage(c,d,g)


def test_duplicate_or_missing_day_rejected():
    c,d,g=synthetic()
    d.loc[1,'dia']=d.loc[0,'dia']
    with pytest.raises(ValueError,match='Dia duplicado'):
        quality_triage(c,d,g)


def test_empty_input_rejected():
    with pytest.raises(ValueError,match='importar dados'):
        quality_triage(pd.DataFrame(),pd.DataFrame(),pd.DataFrame())


def test_actual_uploaded_file_if_present():
    from pathlib import Path
    fn=Path('/mnt/data/WIN_2019_2020_5min_exploratorio.csv')
    if not fn.exists():
        pytest.skip('Arquivo do usuário não está disponível neste ambiente')
    c,report,d,g=audit_exploratory_csv(fn.read_bytes(),'Arquivo público declarado','win.csv')
    q,s=quality_triage(c,d,g)
    assert s['pregoes_observados']==181
    assert s['dias_com_lacunas']==15
    assert s['dias_com_abertura_divergente']==64
    assert s['dias_com_discordancia_anterior']==0
    assert not q.apto_para_backtest.any()
    assert not q.vencimento_nominal[q.dia=='2020-02-10'].any()
    assert q.vencimento_nominal[q.dia=='2020-02-12'].all()
    assert (q.trechos_continuos_observados>=1).all()
