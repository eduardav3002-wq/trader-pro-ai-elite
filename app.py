"""Trader Pro AI Elite v0.7 — pesquisa sem corretora nem ordens."""
import hashlib
import io
import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from audit import audit_trades
from backtest import backtest
from engine import analyze, demo_data, HOLIDAYS_2026, market_day_gate, signal_entry_gate, ENTRY_GATE_LABELS

st.set_page_config(page_title='Trader Pro AI Elite · v0.7',page_icon='📈',layout='wide',initial_sidebar_state='collapsed')
st.markdown('''<style>
.stApp{background:#080e1a;color:#e9f0fb}.block-container{max-width:1250px;padding:1rem 1rem 3rem}
header[data-testid="stHeader"]{background:transparent}
h1,h2,h3{letter-spacing:-.035em}h1{font-size:clamp(1.8rem,5vw,3rem)!important}
[data-testid="stMetric"]{background:linear-gradient(145deg,#15243a,#101a2c);border:1px solid #293c58;padding:16px;border-radius:16px}
[data-testid="stMetricLabel"]{color:#a5b7cf}[data-testid="stMetricValue"]{font-size:clamp(1.35rem,4vw,2rem)}
[data-testid="stFileUploader"]{background:#101b2d;border-radius:14px}
div[data-testid="stAlert"]{border-radius:12px}
section[data-testid="stSidebar"]{background:#101a2b}
.hero{padding:22px;border-radius:20px;background:linear-gradient(110deg,#172b47,#0d1727 65%);border:1px solid #2d4563;margin-bottom:18px}
.eyebrow{color:#87c7ed;font-size:.75rem;font-weight:700;letter-spacing:.14em}
.hero-title{font-size:clamp(1.8rem,5vw,3rem);font-weight:800;letter-spacing:-.045em;margin:8px 0}
.hero-sub{color:#a6bad1;font-size:.9rem}
.pill{display:inline-block;border-radius:999px;padding:6px 12px;background:#24354d;color:#dce8f6;font-size:.78rem;margin-top:12px}
.signal{border-radius:16px;padding:18px 20px;border:1px solid #385170;background:#152239;margin:14px 0}
.signal strong{font-size:1.4rem}.muted{color:#a5b7cf;font-size:.88rem}
@media(max-width:640px){.block-container{padding:.8rem .7rem 2rem}.hero{padding:16px}.signal{padding:14px}}
</style>''',unsafe_allow_html=True)

st.markdown('''<div class="hero"><div class="eyebrow">RESEARCH TERMINAL · V0.7</div>
<div class="hero-title">◈ TRADER PRO AI ELITE</div>
<div class="hero-sub">WIN · Intraday · Filtros EMA 9/21, RSI 14, ATR 14 e tendência 15m</div>
<span class="pill">● MODO PESQUISA — SEM ORDENS REAIS</span></div>''',unsafe_allow_html=True)
st.caption('Modelo de regras experimentais: não é inteligência artificial treinada nem previsão de ganhos. Mercado ao vivo e execução continuam desligados.')
with st.sidebar:
    st.header('⚙️ Central de controle')
    source=st.radio('Fonte dos dados',['Demonstração fictícia','CSV histórico · origem declarada'],index=0)
    chart_bars=st.slider('Candles no gráfico',30,180,75,15)
    show_ema=st.toggle('Exibir médias móveis',True)
    profile_ui=st.radio('Perfil de pesquisa',
                        ['Seletivo v0.7 (experimental)','Base v0.5 (comparação)'],index=0)
    profile='seletivo' if profile_ui.startswith('Seletivo') else 'base'
    st.caption('Seletivo aplica filtros de volatilidade/candles. Valores escolhidos para demonstrar regras, NÃO ajustados ao WIN real.')
    st.divider()
    st.caption('CALENDÁRIO B3: feriados e fins de semana bloqueados. Esta versão valida apenas o calendário de 2026 e rejeita anos não certificados.')
    st.caption('Para usar histórico: candles de 5 min de um contrato WIN específico, dias completos de 2026 e horário de Brasília. Origem declarada NÃO significa autenticidade verificada.')

out=None
provenance=None
contract=None
if source.startswith('CSV histórico'):
    st.subheader('📁 Dados históricos: origem declarada')
    st.caption('Não fornecemos nem autenticamos preços da B3. O usuário precisa obter OHLC de um fornecedor licenciado, com o contrato e o fuso corretos. A declaração é registrada, mas NÃO é prova de autenticidade.')
    uploaded=st.file_uploader('Carregue o CSV de candles do WIN (não o CSV de operações)',
                              type=['csv'],key='candles',
                              help='datetime,open,high,low,close[,volume]; 5 minutos, abertura, Brasília')
    f1,f2=st.columns(2)
    with f1:
        provider=st.text_input('Fonte declarada',placeholder='Ex.: plataforma da minha corretora',
                               help='Informe onde obteve o arquivo histórico.')
    with f2:
        contract_input=st.text_input('Contrato específico',placeholder='Ex.: WINZ26',
                                    help='Não use o símbolo contínuo WIN ou preço de índice à vista.')
    confirmed=st.checkbox('Confirmo que o arquivo foi exportado de uma fonte histórica identificável; não é um CSV gerado pela demonstração.')
    if uploaded is None:
        st.info('Para analisar o WIN, envie CSV de candles reais, com fonte e contrato declarados.')
    elif not (provider.strip() and contract_input.strip() and confirmed):
        st.warning('Preencha a fonte, o contrato e a confirmação. Sem isso, o motor não executa análise histórica.')
    else:
        try:
            payload=uploaded.getvalue()
            if len(payload) > 15_000_000:
                raise ValueError('CSV maior que 15 MB. Envie uma amostra de 2026 menor.')
            contract=contract_input.strip().upper()
            raw=pd.read_csv(io.BytesIO(payload))
            out=analyze(raw,contract=contract,profile=profile)
            provenance={'tipo':'HISTORICO_DECLARADO_NAO_VERIFICADO','fonte_declarada':provider.strip(),
                        'contrato':contract,'nome_arquivo':uploaded.name,
                        'sha256_csv':hashlib.sha256(payload).hexdigest(),
                        'primeiro_candle':str(out.datetime.iloc[0]),
                        'ultimo_candle':str(out.datetime.iloc[-1]),
                        'total_candles':len(out)}
            st.warning('CSV validado estruturalmente, mas preços, origem e integridade de mercado NÃO foram verificados de forma independente.')
            st.caption(f"Contrato: {contract} · Fonte declarada: {provider.strip()} · SHA-256: {provenance['sha256_csv'][:16]}…")
        except (ValueError,TypeError,pd.errors.ParserError,UnicodeError) as exc:
            st.error(f'CSV rejeitado: {exc}')
else:
    try:
        out=analyze(demo_data(),profile=profile)
        provenance={'tipo':'DEMONSTRACAO_FICTICIA','fonte_declarada':'Gerador sintético local',
                    'contrato':'NENHUM','sha256_csv':None,'total_candles':len(out)}
    except (ValueError,TypeError) as exc:
        st.error(f'Erro na demonstração: {exc}')
    st.warning('DEMONSTRAÇÃO 100% FICTÍCIA: candles e operações são INVENTADOS. Não avaliam eficácia no mercado.')

tab_terminal,tab_decision,tab_bt,tab_audit,tab_data=st.tabs(['📈 Sinais','🛑 Não operar','🧪 Backtest','🛡️ Auditoria','🔐 Dados'])

with tab_terminal:
    if out is None:
        st.info('Aguardando um CSV de candles válido para exibir sinais.')
    else:
        last=out.iloc[-1]
        signal=str(last['signal'])
        # É um candle HISTÓRICO: sem próximo candle no arquivo, nenhuma nova
        # entrada executável deve ser exibida, ainda que haja sinal teórico.
        gate=str(last['entry_gate_code'])
        display_signal=str(last['signal_eligible'])
        palette={'COMPRA':'#4bd4a3','VENDA':'#ff7f91','AGUARDAR':'#f1c56e'}
        reason_text=(str(last['reason_detail']) if gate=='ELEGIVEL_HORARIO'
                     else ENTRY_GATE_LABELS.get(gate,'Bloqueio de calendário/horário'))
        st.markdown(f'''<div class="signal" style="border-left:5px solid {palette[display_signal]}"><div class="muted">ÚLTIMO CANDLE CARREGADO · {profile_ui}</div>
        <strong style="color:{palette[display_signal]}">{display_signal}</strong><div class="muted">{reason_text}</div></div>''',unsafe_allow_html=True)
        st.caption('Sinal retrospectivo. Não é cotação ao vivo nem recomendação para operar. NOVAS ordens seguem desligadas.')
        left,right=st.columns(2)
        left.metric('Fechamento (pontos)',f'{last["close"]:,.0f}'.replace(',','.'))
        right.metric('RSI 14',f'{last["rsi"]:.1f}'.replace('.',','))
        left.metric('Tendência 5m',str(last['trend']))
        right.metric('Confirmação 15m',str(last['trend15']))
        st.metric('ATR 14',f'{last["atr"]:.1f}'.replace('.',','))
        st.subheader('Candles históricos · 5 minutos')
        chart=out.tail(chart_bars)
        fig=go.Figure()
        fig.add_trace(go.Candlestick(x=chart.datetime,open=chart.open,high=chart.high,low=chart.low,close=chart.close,
                                    name='Candles',increasing_line_color='#40d4a1',decreasing_line_color='#ff6b82'))
        if show_ema:
            fig.add_trace(go.Scatter(x=chart.datetime,y=chart.ema9,name='EMA 9',line=dict(color='#71baff',width=1.6)))
            fig.add_trace(go.Scatter(x=chart.datetime,y=chart.ema21,name='EMA 21',line=dict(color='#f4c36e',width=1.6)))
        fig.update_layout(template='plotly_dark',height=390,xaxis_rangeslider_visible=False,paper_bgcolor='#080e1a',
            plot_bgcolor='#0e1929',font=dict(color='#b9c9dc'),margin=dict(l=5,r=5,t=25,b=10),
            legend=dict(orientation='h',y=1.12,x=0),xaxis=dict(showgrid=False),yaxis=dict(gridcolor='#23334a',side='right'))
        st.plotly_chart(fig,use_container_width=True,config={'displaylogo':False,'scrollZoom':False})
        with st.expander('🔎 Por que essa decisão?',expanded=True):
            st.write('• '+reason_text)
            st.write('• Tendência EMA 9/21: **'+str(last['trend'])+'**')
            st.write('• Tendência dos candles completos 15m: **'+str(last['trend15'])+'**')
            st.write('• Condição de mercado: **'+str(last['condition'])+'**')
            st.write('• Código do motivo: **'+str(last['reason_code'])+'**')
            st.write('• Todos os critérios por candle: **'+str(last['all_reason_details'])+'**')
            st.write('• Elegibilidade de calendário/horário: **'+str(last['entry_gate_detail'])+'**')
            if profile=='seletivo':
                st.write(f"• ATR relativo à mediana anterior: **{last['atr_ratio']:.2f}** (faixa exploratória 0,65 a 1,80).")
                st.write(f"• Amplitude do candle / ATR: **{last['candle_atr']:.2f}** (máximo 2,20).")
            st.caption('Esse motor não calcula probabilidade estatística de acerto.')
        with st.expander('🎯 Níveis ilustrativos de ATR'):
            if display_signal=='AGUARDAR':
                st.info('Nenhuma entrada: o sistema recomenda aguardar.')
            else:
                a,b,c=st.columns(3)
                a.metric('Fechamento ref.',f'{last["close"]:,.0f}')
                b.metric('Stop estimado',f'{last["stop"]:,.0f}')
                c.metric('Alvo estimado',f'{last["target"]:,.0f}')
                st.caption('Referências ilustrativas arredondadas à grade de 5 pontos; entrada de backtest é na próxima abertura.')
        with st.expander('🗂️ Últimos candles'):
            st.dataframe(out[['datetime','close','ema9','ema21','rsi','atr','trend','trend15','signal','reason_detail']].tail(20),
                         use_container_width=True,hide_index=True)

with tab_decision:
    st.subheader('🛑 Central de decisão: quando NÃO operar')
    st.caption('Cada candle recebe uma explicação verificável. Os filtros seletivos são hipóteses de pesquisa, não uma taxa de acerto prevista.')
    if out is None:
        st.info('Envie candles válidos ou escolha a demonstração fictícia para ver os motivos.')
    else:
        waiting=out[out.signal.eq('AGUARDAR')]
        total=int(len(out))
        n_signals=int(out.signal.isin(['COMPRA','VENDA']).sum())
        n_eligible=int(out.entry_gate_code.eq('ELEGIVEL_HORARIO').sum())
        n_blocked=n_signals-n_eligible
        c1,c2,c3=st.columns(3)
        c1.metric('Sinais detectados',n_signals)
        c2.metric('Candidatos no horário',n_eligible)
        c3.metric('Sinais bloqueados',n_blocked)
        st.metric('Candles marcados AGUARDAR',f'{len(waiting)} / {total}')
        st.caption('Candles com sinal ainda podem ser bloqueados por horário, feriado, limite de risco ou posição aberta.')
        gates=out[out.signal.isin(['COMPRA','VENDA'])].groupby(['entry_gate_code','entry_gate_detail'],as_index=False).size()
        st.subheader('⛔ Bloqueios de calendário e horário')
        if len(gates):
            st.dataframe(gates.rename(columns={'entry_gate_detail':'Explicação','size':'Quantidade'})[['entry_gate_code','Explicação','Quantidade']],hide_index=True,use_container_width=True)
        reasons=(waiting.groupby(['reason_code','reason_detail'],as_index=False).size()
                 .sort_values('size',ascending=False)
                 .rename(columns={'reason_detail':'Motivo','size':'Candles'}))
        st.subheader('Primeiro motivo de espera')
        st.dataframe(reasons[['Motivo','Candles']],hide_index=True,use_container_width=True)
        st.caption('Os motivos completos aparecem no CSV; podem existir vários ao mesmo tempo.')
        st.subheader('Registro dos últimos 30 candles')
        st.dataframe(out[['datetime','signal','signal_eligible','entry_gate_detail','all_reason_details']].tail(30),
                     hide_index=True,use_container_width=True)
        diag_export=out[['datetime','open','high','low','close','signal','signal_eligible',
                         'entry_gate_code','entry_gate_detail','expected_entry_time',
                         'reason_code','reason_detail','all_reason_codes','all_reason_details',
                         'atr','atr_ratio','candle_atr','trend','trend15']]
        st.download_button('Baixar decisões e todos os bloqueios (CSV)',
                           diag_export.to_csv(index=False).encode('utf-8-sig'),
                           'decisoes_trader_pro_ai_elite_v07.csv','text/csv',
                           use_container_width=True)

with tab_bt:
    st.write('🧪 Pesquisa retrospectiva. Não confunda resultados com acertos futuros.')
    st.caption('Abertura seguinte, stop prioritário no candle com toque simultâneo, nenhuma ordem enviada. Dias completos obrigatórios.')
    if out is None:
        st.info('Aguardando dados validados para liberar o backtest.')
    else:
        b1,b2=st.columns(2)
        with b1:
            cost=st.number_input('Taxas por operação (pontos, ida + volta)',min_value=0.0,value=2.0,step=0.5)
            slip=st.number_input('Slippage por lado (ticks de 5 pts)',min_value=0,max_value=20,value=1,step=1)
            daily_limit=st.number_input('Máximo de operações por dia',min_value=1,max_value=30,value=3,step=1)
        with b2:
            max_hold=st.number_input('Duração máxima (candles de 5 min)',min_value=1,max_value=100,value=12,step=1)
            daily_loss=st.number_input('Limite de perda diária realizada (pontos)',min_value=0.0,value=200.0,step=25.0)
            st.caption(f'Hipótese: {cost:.1f} pts de taxas + {2*slip*5} pts de slippage por operação.')
        enable_risk=st.checkbox('Ativar travas extras v0.7 (experimentais)',value=profile=='seletivo')
        if enable_risk:
            r1,r2,r3=st.columns(3)
            max_risk=r1.number_input('Risco máximo do stop (pts)',min_value=5.0,value=125.0,step=5.0)
            loss_streak=r2.number_input('Pausar após N perdas seguidas no dia',min_value=1,max_value=10,value=2,step=1)
            min_rr=r3.number_input('Risco-retorno mínimo teórico',min_value=0.0,max_value=5.0,value=1.0,step=0.1)
            st.caption('O limite de risco é uma estimativa: gaps e slippage podem gerar perdas maiores. A pausa usa apenas operações encerradas.')
        else:
            max_risk=None
            loss_streak=None
            min_rr=0.0
        run=st.button('Executar backtest v0.7',type='primary',use_container_width=True)
        compare=st.button('Comparar base v0.5 × seletivo v0.7 (mesmos parâmetros)',use_container_width=True)
        if compare:
            try:
                raw_data=demo_data() if source=='Demonstração fictícia' else raw
                comparisons=[]
                for comp_profile in ('base','seletivo'):
                    comp_analyzed=analyze(raw_data,contract=contract,profile=comp_profile)
                    comp_trades=backtest(comp_analyzed,cost_points=float(cost),max_hold=int(max_hold),
                        slippage_ticks=int(slip),max_daily_trades=int(daily_limit),
                        max_daily_loss_points=float(daily_loss),contract=contract,
                        max_trade_risk_points=float(max_risk) if max_risk is not None else None,
                        max_consecutive_losses=int(loss_streak) if loss_streak is not None else None,
                        min_reward_risk=float(min_rr))
                    comparisons.append({'Perfil':comp_profile,'Sinais':int(comp_analyzed.signal.isin(['COMPRA','VENDA']).sum()),
                        'Candidatos no horário':int(comp_analyzed.entry_gate_code.eq('ELEGIVEL_HORARIO').sum()),
                        'Operações':int(len(comp_trades)),'Saldo (pts)':round(float(comp_trades.net_points.sum()),2)})
                st.subheader('Comparação sob os mesmos controles')
                st.dataframe(pd.DataFrame(comparisons),hide_index=True,use_container_width=True)
                st.warning('Comparação retrospectiva. Na demonstração, preços inventados: não é evidência de maior acerto.')
            except (ValueError,TypeError,pd.errors.ParserError) as exc:
                st.error(f'Não foi possível comparar: {exc}')
        if run:
            try:
                trades,attempts=backtest(out,cost_points=float(cost),max_hold=int(max_hold),
                    slippage_ticks=int(slip),max_daily_trades=int(daily_limit),
                    max_daily_loss_points=float(daily_loss),contract=contract,
                    max_trade_risk_points=float(max_risk) if max_risk is not None else None,
                    max_consecutive_losses=int(loss_streak) if loss_streak is not None else None,
                    min_reward_risk=float(min_rr),return_audit=True)
                if source=='Demonstração fictícia':
                    st.warning('DEMONSTRAÇÃO FICTÍCIA: preços INVENTADOS. Não mede eficácia nem valida os filtros.')
                net=float(trades.net_points.sum()) if not trades.empty else 0.0
                wins=int(trades.net_points.gt(0).sum()) if not trades.empty else 0
                c1,c2,c3=st.columns(3)
                c1.metric('Operações',len(trades))
                c2.metric('Acerto líquido',f'{wins/len(trades):.1%}' if len(trades) else 'N/D')
                c3.metric('Saldo líquido',f'{net:+.1f} pts')
                if trades.empty:
                    st.info('Nenhuma operação passou por todos os filtros. Não forçamos operações.')
                else:
                    equity=pd.concat([pd.Series([0.0]),trades.net_points.cumsum().reset_index(drop=True)],ignore_index=True)
                    dd=float((equity-equity.cummax()).min())
                    st.metric('Rebaixamento máximo (drawdown)',f'{dd:.1f} pts')
                    st.line_chart(equity,y_label='Pontos acumulados desde zero')
                    gain=float(trades.loc[trades.net_points.gt(0),'net_points'].sum())
                    loss=-float(trades.loc[trades.net_points.lt(0),'net_points'].sum())
                    st.caption(f'Profit factor: {gain/loss:.2f}' if loss else 'Profit factor indefinido: sem perdas registradas')
                    if len(trades)<100:
                        st.warning('Menos de 100 operações: amostra pequena e instável. Não há evidência de vantagem estatística.')
                    with st.expander('Ver tabela completa das operações'):
                        st.dataframe(trades,use_container_width=True,hide_index=True)
                st.subheader('Auditoria das entradas')
                st.caption('Esta tabela mostra por que cada sinal do motor foi executado ou bloqueado no backtest.')
                if attempts.empty:
                    st.info('Nenhum sinal de entrada foi gerado nesta amostra.')
                else:
                    decision_counts=(attempts.groupby('decisao',as_index=False).size()
                                     .rename(columns={'decisao':'Decisão','size':'Quantidade'}))
                    st.dataframe(decision_counts,hide_index=True,use_container_width=True)
                    with st.expander('Detalhar cada tentativa'):
                        st.dataframe(attempts,hide_index=True,use_container_width=True)
                exported=trades.copy()
                exported['tipo_dado']=provenance['tipo']
                exported['contrato_declarado']=provenance.get('contrato','NENHUM')
                exported['sha256_csv_origem']=provenance.get('sha256_csv')
                st.download_button('Baixar operações v0.7 (CSV)',exported.to_csv(index=False).encode('utf-8-sig'),
                                   'backtest_trader_pro_ai_elite_v07.csv','text/csv',use_container_width=True)
                st.download_button('Baixar auditoria de entradas (CSV)',attempts.to_csv(index=False).encode('utf-8-sig'),
                                   'auditoria_entradas_v07.csv','text/csv',use_container_width=True)
                config={'perfil':profile,'custo_pontos':float(cost),
                        'slippage_ticks_por_lado':int(slip),'max_operacoes_dia':int(daily_limit),
                        'max_hold_candles':int(max_hold),'limite_perda_diaria_pontos':float(daily_loss),
                        'risco_max_stop_pontos':float(max_risk) if max_risk is not None else None,
                        'max_perdas_seguidas':int(loss_streak) if loss_streak is not None else None,
                        'min_rr_teorico':float(min_rr)}
                st.download_button('Baixar relatório de origem e parâmetros (JSON)',
                    json.dumps({'versao':'0.7','dados':provenance,'parametros':config,
                                'total_operacoes':len(trades),'saldo_pontos':net,
                                'calendario':{'mercado':'B3 WIN','ano':2026,'feriados_bloqueados':len(HOLIDAYS_2026),
                                              'anos_sem_calendario':'BLOQUEADOS'}},
                               ensure_ascii=False,indent=2).encode('utf-8'),
                    'relatorio_origem_v07.json','application/json',use_container_width=True)
                st.caption('Saldo em pontos, não reais. Custos, liquidez e preço de execução são aproximações. Não operar dinheiro real.')
            except (ValueError,TypeError) as exc:
                st.error(f'Não foi possível executar: {exc}')

with tab_audit:
    st.subheader('🛡️ Auditoria de operações antigas')
    st.write('Importe aqui **o arquivo de operações da v0.3**. O app marca irregularidades de grade e sessão sem apagar, arredondar ou recalcular seus resultados.')
    old_file=st.file_uploader('CSV de operações v0.3',type=['csv'],key='audit_csv')
    if old_file is not None:
        try:
            audited=audit_trades(pd.read_csv(old_file))
            rejected=int(audited.status_auditoria.eq('REJEITADA').sum())
            a,b=st.columns(2)
            a.metric('Registros avaliados',len(audited))
            b.metric('Registros rejeitados',rejected)
            if rejected:
                st.error('Estes resultados não são evidência válida de desempenho de WIN. Refaça o teste somente com candles históricos autênticos.')
            st.dataframe(audited,use_container_width=True,hide_index=True)
            st.download_button('Baixar auditoria (CSV)',audited.to_csv(index=False).encode('utf-8-sig'),
                               'auditoria_trader_pro_ai_elite_v03.csv','text/csv',use_container_width=True)
        except (ValueError,TypeError,pd.errors.ParserError,UnicodeError) as exc:
            st.error(f'Não foi possível auditar: {exc}')
    st.caption('A auditoria checa requisitos básicos; não comprova origem, integridade ou qualidade do backtest.')

with tab_data:
    st.subheader('🔐 Origem e limitações da amostra')
    if provenance:
        st.json(provenance)
        st.info('SHA-256 identifica os bytes do arquivo carregado. Não comprova se as cotações são reais, corretas ou completas no fornecedor.')
    st.markdown('''**Para um backtest histórico comparável:** exporte candles OHLC de 5 minutos de um único vencimento do WIN em 2026, com data/hora de abertura no fuso de Brasília, pregões completos e sem gaps. Declare a origem e o ticker da série (ex.: WINZ26). Um CSV de operações não substitui candles.''')
    st.subheader('📆 Bloqueio obrigatório de feriados da B3')
    st.caption('Tabela oficial de 2026: candles e entradas de WIN em datas sem pregão são bloqueados. Datas especiais são validadas separadamente; anos além de 2026 não são autorizados até atualização do calendário.')
    holidays=pd.DataFrame({'Feriados B3 2026': [x.strftime('%d/%m/%Y') for x in sorted(HOLIDAYS_2026)]})
    st.dataframe(holidays,hide_index=True,use_container_width=True)
    st.caption('Fonte oficial: https://www.b3.com.br/pt_br/noticias/calendario-de-negociacao-da-b3-confira-o-funcionamento-da-bolsa-em-2026.htm')
    st.caption('A v0.7 não baixa dados de terceiros, não verifica licenças, não acessa cotações ao vivo e não envia ordens. Resultado retrospectivo não prevê acertos futuros.')

st.divider()
st.caption('Trader Pro AI Elite · v0.7 · Simulador de pesquisa. Horários de referência B3 em nov/2026; verifique o calendário oficial e possíveis mudanças. Não utilizar para decisões financeiras reais.')
