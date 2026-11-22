"""Segurança e diagnósticos v1.8 - cenários inteiramente sintéticos."""
import pandas as pd
import pytest

from discrepancy_lab import controlled_demo_pair, diagnose_m1_differences


def run(a=None,b=None,**kwargs):
    orig_a, orig_b = controlled_demo_pair()
    return diagnose_m1_differences(
        orig_a if a is None else a, orig_b if b is None else b,
        kwargs.pop('sa', 'DEMONSTRAÇÃO SINTÉTICA A'), kwargs.pop('sb','DEMONSTRAÇÃO SINTÉTICA B'),
        kwargs.pop('tza','Desconhecido'), kwargs.pop('tzb','Desconhecido'), **kwargs)


def test_demo_known_differences_and_safety():
    r,fields,ranges,events = run()
    assert r['minutos_em_comum']==19
    assert r['minutos_com_divergencia_ohlc']==2
    assert r['minutos_somente_a']==1
    assert r['minutos_somente_b']==1
    assert r['minutos_com_diferenca_volume']==1
    assert r['eventos_total']==5  # 2 OHLC, 1 volume, 2 exclusividades
    assert r['eventos_exibidos']==5
    assert not r['mesmo_arquivo']
    assert r['dias_certificados']==0
    assert r['backtest_liberado'] is False
    assert r['ordens_liberadas'] is False
    assert len(ranges)==2
    assert set(ranges['ausente_em'])=={'A','B'}
    assert set(events['tipo'])=={'AUSENTE_A','AUSENTE_B','OHLC_DIVERGENTE','VOLUME_DIVERGENTE'}


def test_field_max_and_counts():
    r,fields,*_=run()
    stats=fields.set_index('campo')
    assert stats.loc['HIGH','minutos_com_diferenca']==2
    assert stats.loc['OPEN','minutos_com_diferenca']==1
    assert stats.loc['LOW','minutos_com_diferenca']==1
    assert stats.loc['CLOSE','minutos_com_diferenca']==1
    assert stats.loc['HIGH','maior_diferenca_absoluta_pts']==10
    assert stats.loc['OPEN','maior_diferenca_absoluta_pts']==5
    assert r['deslocamento_uniforme_pts_na_sobreposicao'] is None


def test_same_bytes_are_not_independent():
    a,_=controlled_demo_pair()
    r,fields,ranges,events=run(a,a)
    assert r['mesmo_arquivo']
    assert r['minutos_em_comum']==20
    assert r['minutos_com_divergencia_ohlc']==0
    assert r['minutos_somente_a']==r['minutos_somente_b']==0
    assert events.empty and ranges.empty
    assert r['eventos_total']==0
    assert fields['minutos_com_diferenca'].sum()==0


def test_constant_shift_descriptive_not_tradeable():
    a,_ = controlled_demo_pair()
    b=pd.read_csv(__import__('io').BytesIO(a))
    for field in ['Open','High','Low','Close']:
        b[field] += 10
    converted=b.to_csv(index=False).encode()
    r,fields,ranges,events=run(a,converted)
    assert r['deslocamento_uniforme_pts_na_sobreposicao']==10
    assert not r['deslocamento_uniforme_comprovado_como_rolagem']
    assert r['minutos_com_divergencia_ohlc']==20
    assert r['backtest_liberado'] is False


def test_only_volume_change_is_not_ohlc_difference():
    a,_=controlled_demo_pair()
    b=pd.read_csv(__import__('io').BytesIO(a))
    b.loc[3,'Volume'] += 45
    r,fields,ranges,events=run(a,b.to_csv(index=False).encode())
    assert r['minutos_com_divergencia_ohlc']==0
    assert r['minutos_com_diferenca_volume']==1
    assert r['eventos_total']==1
    assert events.iloc[0]['tipo']=='VOLUME_DIVERGENTE'


def test_missing_volume_kept_separate():
    a,_=controlled_demo_pair()
    b=pd.read_csv(__import__('io').BytesIO(a)).drop(columns=['Volume'])
    r,_,_,events=run(a,b.to_csv(index=False).encode())
    assert r['minutos_com_diferenca_volume'] is None
    assert r['minutos_com_divergencia_ohlc']==0 and events.empty


def test_different_tickers_not_matched():
    a,_=controlled_demo_pair()
    b=a.replace(b'WINZ22',b'WINM23')
    r,fields,ranges,events=run(a,b)
    assert r['minutos_em_comum']==0
    assert r['minutos_somente_a']==20
    assert r['minutos_somente_b']==20
    assert r['deslocamento_uniforme_pts_na_sobreposicao'] is None
    assert fields['maior_diferenca_absoluta_pts'].isna().all()


def test_missing_runs_group_without_crossing_date():
    a,_=controlled_demo_pair()
    b=pd.read_csv(__import__('io').BytesIO(a))
    b=b.loc[~b['Datetime'].str.contains('09:05:00|09:06:00|09:14:00')].reset_index(drop=True)
    r,_,ranges,_=run(a,b.to_csv(index=False).encode())
    assert r['minutos_somente_a']==3
    assert len(ranges)==2
    assert sorted(ranges['minutos_exclusivos'].tolist())==[1,2]
    assert set(ranges['ausente_em'])=={'B'}


def test_fusos_differ_without_conversion():
    a,_=controlled_demo_pair()
    r,*_=run(a,a,tzb='America/Sao_Paulo (declarado)')
    assert r['fusos_declarados_iguais'] is False
    assert r['minutos_em_comum']==20 # coincidentes em texto, não instantes comprovados
    assert r['dias_certificados']==0


def test_bad_data_rejected_by_existing_validator():
    a,_=controlled_demo_pair()
    b=a.decode().splitlines()
    fields=b[1].split(',')
    fields[2]='110002' # fora da grade WIN
    b[1]=','.join(fields)
    with pytest.raises(ValueError,match='grade'):
        run(a,('\n'.join(b)+'\n').encode())


def test_event_cap_counts_all():
    import io
    a,_=controlled_demo_pair()
    # Gera 700 minutos cronológicos em dias distintos para manter hora/minuto válidos.
    rows=[]
    for day in range(1,6):
        for minute in range(140):
            hour=9 + minute//60
            minute_of_hour=minute%60
            price=110000 + day*10 + minute*5
            rows.append([f'2022-11-{day:02d} {hour:02d}:{minute_of_hour:02d}:00','WINZ22',price,price+10,price-5,price+5,1])
    df=pd.DataFrame(rows,columns=['Datetime','Contrato','Open','High','Low','Close','Volume'])
    x=df.to_csv(index=False).encode()
    for fld in ['Open','High','Low','Close']:
        df[fld] += 5
    y=df.to_csv(index=False).encode()
    r,_,_,events=run(x,y)
    assert r['minutos_com_divergencia_ohlc']==700
    assert r['eventos_total']==700
    assert r['eventos_exibidos']==500 and r['eventos_truncados']
    assert len(events)==500


def test_reject_empty_source():
    with pytest.raises(ValueError,match='origem'):
        run(sa='')
