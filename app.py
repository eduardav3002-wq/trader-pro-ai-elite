"""Trader Pro AI Elite v1.2 — pesquisa mobile-first, sem corretora nem ordens."""
import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from audit import audit_trades
from backtest import backtest
from research import robustness_report
from validation import chronological_validation
from provenance import inspect_historical_csv
from historical import audit_exploratory_csv, historical_day_gate, CLOSED_2019, CLOSED_2020, CALENDAR_SOURCES
from quality_lab import quality_triage
from engine import analyze, demo_data, HOLIDAYS_2026, market_day_gate, signal_entry_gate, ENTRY_GATE_LABELS

st.set_page_config(page_title='Trader Pro AI Elite · v1.2',page_icon='📈',layout='wide',initial_sidebar_state='collapsed')
st.markdown("""<style>
:root {color-scheme:dark}
.stApp{background:radial-gradient(ellipse at 100% 0%,#1f173f 0%,#0c1020 35%,#080c16 72%);color:#edf1ff}
/* Reduz controles flutuantes nativos quando embutidos no navegador móvel. */
.block-container{max-width:1160px;padding:5.0rem 1rem 3.4rem}
html{scroll-padding-top:5rem}
[data-testid="stHeader"]{background:#0b0d19dd!important}
[data-testid="stToolbar"], [data-testid="stDecoration"]{display:none!important}
[data-testid="stAppViewContainer"]{overflow-x:hidden}
header[data-testid="stHeader"]{background:transparent}
#MainMenu,footer{visibility:hidden}
h1,h2,h3{letter-spacing:-.025em;color:#f2f1ff}
[data-testid="stMetric"]{background:linear-gradient(150deg,#202540,#131b30);border:1px solid #343958;padding:15px;border-radius:17px}
[data-testid="stMetricLabel"]{color:#adbbd7}
[data-testid="stMetricValue"]{font-size:clamp(1.12rem,3.9vw,1.9rem)}
[data-testid="stFileUploader"]{background:#131a2c;border-radius:15px}
[data-testid="stAlert"]{border-radius:13px}
section[data-testid="stSidebar"]{background:#11162a}
.stButton button[kind="primary"]{background:linear-gradient(105deg,#6b59eb,#8e62d8);color:white;border:0;border-radius:12px;font-weight:700}
.stButton button,.stDownloadButton button{min-height:42px;border-radius:12px}
[data-baseweb="tab-list"]{overflow-x:auto;gap:6px;scrollbar-width:thin}
[data-baseweb="tab"]{white-space:nowrap;flex-shrink:0}
.hero{padding:25px 23px;border-radius:21px;background:linear-gradient(118deg,#272455 0%,#181e3d 54%,#102537 100%);border:1px solid #49457c;margin:0 0 16px;box-shadow:0 18px 42px #05051245}
.eyebrow{color:#b6a4ff;font-size:.72rem;font-weight:800;letter-spacing:.17em}
.hero-title{font-size:clamp(1.65rem,5.8vw,2.75rem);font-weight:850;line-height:1.15;letter-spacing:-.055em;margin:9px 0 12px;color:#f7f7ff}
.hero-sub{color:#bfcbe4;font-size:.89rem;line-height:1.55}
.pill{display:inline-block;border-radius:99px;padding:8px 11px;background:#34305e;color:#e6dcff;font-weight:700;font-size:.73rem;margin-top:15px;border:1px solid #5e528c}
.signal{border-radius:17px;padding:18px 20px;border:1px solid #41466e;background:linear-gradient(125deg,#18243b,#181c35);margin:14px 0}
.signal strong{font-size:1.55rem}.muted{color:#b2bed5;font-size:.88rem}
.micro-note{color:#c2c3db;font-size:.8rem}
@media(max-width:640px){
 .block-container{padding:6.8rem .65rem 2.4rem}
 .hero{padding:19px 15px;border-radius:17px}
 .hero-title{font-size:1.7rem}
 .hero-sub{font-size:.8rem}
 .signal{padding:15px}
 [data-testid="stMetric"]{padding:11px;border-radius:12px}
 [data-testid="stMetricValue"]{font-size:1.2rem}
 [data-baseweb="tab"]{padding:12px 10px}
 .stButton button,.stDownloadButton button{white-space:normal;line-height:1.2;min-height:50px}
 [data-testid="stMetricLabel"]{font-size:.8rem}
 [data-testid="stDataFrame"]{max-width:100%}
 h2{font-size:1.35rem!important}
}
</style>""",unsafe_allow_html=True)

st.markdown('''<div class="hero"><div class="eyebrow">RESEARCH TERMINAL · V1.2</div>
<div class="hero-title">◈ TRADER PRO AI ELITE</div>
<div class="hero-sub">WIN · Intraday · Filtros EMA 9/21, RSI 14, ATR 14 e tendência 15m</div>
<span class="pill">● PESQUISA SEGURA · ORDENS DESATIVADAS</span></div>''',unsafe_allow_html=True)
st.caption('v1.2 mobile-first · motor experimental auditável · sem IA treinada, cotações ao vivo ou ordens reais. Acurácia futura desconhecida.')
st.markdown('### 📁 Escolha como analisar')
source = st.radio('Fonte dos candles', ['Demonstração fictícia', 'CSV histórico 2026 · origem declarada', '🔬 Explorar 2019–2020 · SEM backtest'], index=0, horizontal=False, label_visibility='collapsed')
st.caption('Demonstração = dados fictícios. Histórico 2026 = validação estrita por contrato. Explorar 2019–2020 = auditoria sem sinais/backtest.')
with st.sidebar:
    st.header('⚙️ Central de controle')
    chart_bars=st.slider('Candles no gráfico',30,180,75,15)
    show_ema=st.toggle('Exibir médias móveis',True)
    profile_ui=st.radio('Perfil de pesquisa',
                        ['Seletivo v1.1 (mesma regra, pesquisa)','Base v0.5 (comparação)'],index=0)
    profile='seletivo' if profile_ui.startswith('Seletivo') else 'base'
    st.caption('Seletivo aplica filtros de volatilidade/candles. Valores escolhidos para demonstrar regras, NÃO ajustados ao WIN real.')
    st.divider()
    st.caption('CALENDÁRIO B3: feriados e fins de semana bloqueados. Esta versão valida apenas o calendário de 2026 e rejeita anos não certificados.')
    st.caption('Modo rigoroso: contrato WIN específico e dias completos de 2026. Modo exploratório 2019–2020: apenas qualidade de dados, sem gerar operações.')

out=None
provenance=None
contract=None
historical_report=None
historical_daily=None
historical_gaps=None
historical_candles=None
if source.startswith('CSV histórico'):
    st.subheader('📁 Importação histórica — dados fornecidos pelo usuário')
    st.info('Obtenha o CSV de uma plataforma/fornecedor que tenha direito de fornecer WIN intraday. O app não busca dados da B3 automaticamente e não pode verificar a origem externa.')
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
            contract=contract_input.strip().upper()
            checked, provenance=inspect_historical_csv(payload,provider,contract,uploaded.name)
            out=analyze(checked,contract=contract,profile=profile)
            st.warning('Estrutura e continuidade aprovadas. COTAÇÕES NÃO AUTENTICADAS: o aplicativo não consegue atestar que preços existiram na B3.')
            st.caption(f"Contrato: {contract} · {provenance['pregoes_completos']} pregões inteiros · SHA-256: {provenance['sha256'][:16]}…")
            st.download_button('⬇️ Baixar comprovante de triagem JSON', json.dumps(provenance,ensure_ascii=False,indent=2).encode('utf-8'), 'triagem_win_v12.json', 'application/json', use_container_width=True)
        except (ValueError,TypeError,pd.errors.ParserError,UnicodeError) as exc:
            st.error(f'CSV rejeitado: {exc}')
            st.caption('Confira: contrato específico, horário de abertura em Brasília, todos os candles de cada sessão e pregões consecutivos.')
elif source.startswith('🔬 Explorar'):
    st.subheader('🔬 Histórico 2019–2020: auditoria de qualidade')
    st.warning('MODO EXPLORATÓRIO — nenhuma operação, sinal, lucro ou backtest é gerado. Ticker, rolagem, fusos e origem primária permanecem não verificados.')
    st.caption('Aceita o data.csv ORIGINAL (TSV de 1 minuto) ou WIN_2019_2020_5min_exploratorio.csv. Se receber 1 minuto, converte apenas blocos de 5 minutos completos; não preenche lacunas.')
    historic_upload=st.file_uploader('Envie o CSV/TSV histórico gratuito',type=['csv','tsv','txt'],key='historic_2019_2020')
    historic_source=st.text_input('Fonte declarada do arquivo',value='GitHub — FGV_Trabalho_WIN (origem primária não verificada)',key='historic_source')
    if historic_upload is None:
        st.info('Toque em Upload e escolha o arquivo que já baixamos. A análise fica na aba 🔬 Histórico.')
    else:
        try:
            historical_candles,historical_report,historical_daily,historical_gaps=audit_exploratory_csv(
                historic_upload.getvalue(),historic_source,historic_upload.name)
            st.success(f"Arquivo lido para auditoria: {historical_report['candles_5min']:,} candles em {historical_report['pregoes_com_dados']} dias (não autenticados).".replace(',','.'))
            if historical_report['dias_com_lacunas'] or historical_report['dias_abertura_divergente']:
                st.warning('Há lacunas ou aberturas divergentes; os dias NÃO foram certificados como pregões completos.')
            st.caption('SHA-256 recebido: ' + historical_report['sha256_recebido'][:24] + '…')
        except (ValueError,TypeError,pd.errors.ParserError,UnicodeError) as exc:
            st.error(f'Arquivo exploratório rejeitado: {exc}')
else:
    try:
        out=analyze(demo_data(),profile=profile)
        provenance={'classificacao':'DEMONSTRACAO_FICTICIA','origem_verificada_independentemente':False,
                    'fonte_declarada':'Gerador sintético local','contrato_declarado':'NENHUM',
                    'sha256':None,'candles':len(out)}
    except (ValueError,TypeError) as exc:
        st.error(f'Erro na demonstração: {exc}')
    st.warning('DEMONSTRAÇÃO 100% FICTÍCIA: candles e operações são INVENTADOS. Não avaliam eficácia no mercado.')

tab_historic,tab_terminal,tab_decision,tab_bt,tab_robust,tab_audit,tab_data=st.tabs(['🔬 Histórico','📈 Sinais','🛑 Não operar','🧪 Backtest','🧬 Robustez','🛡️ Auditoria','🔐 Dados'])

with tab_historic:
    st.subheader('🔬 Auditoria histórica 2019–2020')
    st.caption('Este laboratório só descreve o arquivo recebido; não usa os preços para emitir COMPRA/VENDA nem calcula resultados de investimento.')
    if historical_report is None:
        st.info('Selecione “🔬 Explorar 2019–2020” e carregue o CSV original ou o convertido para gerar a auditoria.')
    else:
        r=historical_report
        c1,c2=st.columns(2)
        c1.metric('Candles íntegros 5m',f"{r['candles_5min']:,}".replace(',','.'))
        c2.metric('Pregões observados',r['pregoes_com_dados'])
        c1.metric('Dias com lacunas',r['dias_com_lacunas'])
        c2.metric('Dias com abertura divergente',r['dias_abertura_divergente'])
        c1.metric('Saltos internos 5m',r['saltos_intradiarios_5min'])
        c2.metric('Pregões inteiros ausentes',r['pregoes_ausentes'])
        st.warning('🛑 CONTRATO NÃO IDENTIFICADO · ORIGEM NÃO AUTENTICADA · BACKTEST BLOQUEADO. Mesmo dias sem saltos podem estar incompletos nas extremidades.')
        st.markdown('**Datas de vencimento nominal na amostra**')
        st.write(', '.join(r['vencimentos_nominais_na_amostra']) or 'Nenhuma')
        st.caption('São datas de atenção à rolagem, NÃO evidência de que o CSV trocou de contrato ou corrigiu preços.')
        if r['conversao']['tipo_entrada']=='TSV_1MIN':
            st.info(f"Conversão interna 1m → 5m: {r['conversao']['janelas_parciais_descartadas']} janelas incompletas descartadas; nenhum valor criado ou interpolado.")
        if r['pregoes_ausentes']:
            st.error('Datas esperadas sem registros: '+ ', '.join(r['pregoes_esperados_ausentes'][:12]))
        st.subheader('🧬 Laboratório de Qualidade v1.2')
        st.caption('Triagem descritiva — separa lacunas, aberturas e datas de rolagem. Nenhum dia é certificado, mesmo quando não aparece um alerta local.')
        triage,quality_summary=quality_triage(historical_candles,historical_daily,historical_gaps)
        q1,q2=st.columns(2)
        q1.metric('Dias com abertura divergente',quality_summary['dias_com_abertura_divergente'])
        q2.metric('Dias com lacunas',quality_summary['dias_com_lacunas'])
        q1.metric('Dias sem alerta local',quality_summary['dias_sem_alerta_local'])
        q2.metric('Divergências nos alertas',quality_summary['dias_com_discordancia_anterior'])
        st.warning('🛑 TODOS os dias: contrato, origem das cotações e encerramento NÃO CERTIFICADOS. “Sem alertas locais” NÃO equivale a apto para operar.')
        st.info('🔎 Conferência de vencimento: **10/02/2020 = próximo ao vencimento**; **12/02/2020 = vencimento nominal**. Os rótulos são recalculados pelas datas, independentemente do texto do relatório antigo.')
        if quality_summary['dias_com_discordancia_anterior']:
            st.error('Encontramos divergências entre datas nominais e rótulos anteriores; confira o CSV de triagem antes de qualquer análise adicional.')
        chosen=st.selectbox('Filtrar pregões por problema',[
            'Dias com alerta','Todos os pregões','Lacunas internas','Abertura divergente',
            'Vencimento nominal','Proximidade de vencimento','Sem alertas locais'
        ],key='quality_filter_v12')
        if chosen=='Lacunas internas':
            selection=triage[triage.lacunas_internas>0]
        elif chosen=='Abertura divergente':
            selection=triage[triage.primeiro_candle!=triage.abertura_referencia]
        elif chosen=='Vencimento nominal':
            selection=triage[triage.vencimento_nominal]
        elif chosen=='Proximidade de vencimento':
            selection=triage[triage.proximo_de_vencimento]
        elif chosen=='Sem alertas locais':
            selection=triage[triage.classe_principal=='SEM_ALERTAS_LOCAIS']
        elif chosen=='Todos os pregões':
            selection=triage
        else:
            selection=triage[triage.classe_principal!='SEM_ALERTAS_LOCAIS']
        st.caption(f'{len(selection)} dias na seleção. Mostrando até 12 cartões no celular; CSV completo disponível abaixo.')
        for rec in selection.head(12).to_dict('records'):
            with st.container(border=True):
                st.markdown('**'+rec['dia']+'**')
                st.write(f"{rec['candles_5min']} candles · {rec['primeiro_candle']}–{rec['ultimo_candle']} · {rec['trechos_continuos_observados']} trechos internos")
                st.caption(rec['motivos'])
                st.caption('Não certificado · Backtest bloqueado')
        if len(selection)>12:
            st.caption('Exibindo 12 cartões; veja todas as datas pelo CSV.')
        with st.expander('🔍 Ver todas as datas, lacunas e trechos em tabela'):
            st.dataframe(triage,use_container_width=True,hide_index=True)
            st.dataframe(historical_daily,use_container_width=True,hide_index=True)
            if not historical_gaps.empty:
                st.dataframe(historical_gaps,use_container_width=True,hide_index=True)
        st.download_button('⬇️ Baixar triagem de qualidade v1.2 (CSV)',
            triage.to_csv(index=False).encode('utf-8-sig'),
            'triagem_qualidade_win_v12.csv','text/csv',use_container_width=True)
        st.download_button('⬇️ Baixar resumo do laboratório v1.2 (JSON)',
            json.dumps(quality_summary,ensure_ascii=False,indent=2).encode('utf-8'),
            'resumo_qualidade_win_v12.json','application/json',use_container_width=True)
        st.download_button('⬇️ Baixar relatório exploratório (JSON)',
            json.dumps(r,ensure_ascii=False,indent=2).encode('utf-8'),
            'auditoria_exploratoria_win_v12.json','application/json',use_container_width=True)
        st.download_button('⬇️ Baixar qualidade por dia (CSV)',
            historical_daily.to_csv(index=False).encode('utf-8-sig'),
            'qualidade_por_dia_win_v12.csv','text/csv',use_container_width=True)
        st.download_button('⬇️ Baixar lacunas internas (CSV)',
            historical_gaps.to_csv(index=False).encode('utf-8-sig'),
            'lacunas_win_v12.csv','text/csv',use_container_width=True)
        st.caption('Dados do usuário, horários de Brasília DECLARADOS (não comprovados). Não confundir ausência de pregões inteiros com ausência de lacunas intradiárias.')
    st.markdown('**Calendário histórico: fontes**')
    st.markdown('\n'.join([f"- [B3: calendário de 2019]({CALENDAR_SOURCES['2019']})",
                            f"- [B3: calendário de 2020]({CALENDAR_SOURCES['2020']})",
                            f"- [B3: exceções de 2020]({CALENDAR_SOURCES['2020_excecoes']})"]))
    st.caption('Exceções 2020: 11/06 fechado; 09/07 e 20/11 abertos; 26/02 início às 13h. Não equiparar um calendário previsto à presença comprovada de negócios a cada minuto.')

with tab_terminal:
    if out is None:
        st.warning('Sinais bloqueados para histórico 2019–2020 não autenticado.' if source.startswith('🔬 Explorar') else 'Aguardando um CSV de candles válido para exibir sinais.')
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
        st.caption('Sinal retrospectivo. Não é cotação ao vivo nem recomendação para operar. NOVAS ordens seguem desligadas. A classificação de evidência fica na aba Robustez.')
        left,right=st.columns(2)
        left.metric('Fechamento (pontos)',f'{last["close"]:,.0f}'.replace(',','.'))
        right.metric('RSI 14',f'{last["rsi"]:.1f}'.replace('.',','))
        left.metric('Tendência 5m',str(last['trend']))
        right.metric('Confirmação 15m',str(last['trend15']))
        st.metric('ATR 14',f'{last["atr"]:.1f}'.replace('.',','))
        st.caption(f"Amostra: {len(out)} candles em {out.datetime.dt.date.nunique()} pregões · Sinais elegíveis historicamente: {out.entry_gate_code.eq('ELEGIVEL_HORARIO').sum()} · Nunca indica operação ao vivo.")
        st.subheader('Candles históricos · 5 minutos')
        chart=out.tail(chart_bars)
        fig=go.Figure()
        fig.add_trace(go.Candlestick(x=chart.datetime,open=chart.open,high=chart.high,low=chart.low,close=chart.close,
                                    name='Candles',increasing_line_color='#40d4a1',decreasing_line_color='#ff6b82'))
        if show_ema:
            fig.add_trace(go.Scatter(x=chart.datetime,y=chart.ema9,name='EMA 9',line=dict(color='#71baff',width=1.6)))
            fig.add_trace(go.Scatter(x=chart.datetime,y=chart.ema21,name='EMA 21',line=dict(color='#f4c36e',width=1.6)))
        fig.update_layout(template='plotly_dark',height=345,xaxis_rangeslider_visible=False,paper_bgcolor='#080e1a',
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
                           'decisoes_trader_pro_ai_elite_v11.csv','text/csv',
                           use_container_width=True)

with tab_bt:
    st.write('🧪 Pesquisa retrospectiva. Não confunda resultados com acertos futuros.')
    st.caption('Na aba 🧬 Robustez, veja metades temporais, reserva cronológica e sensibilidade a custos adicionais.')
    st.caption('Abertura seguinte, stop prioritário no candle com toque simultâneo, nenhuma ordem enviada. Dias completos obrigatórios.')
    if out is None:
        st.warning('Backtest indisponível para a série 2019–2020 sem identificação de contrato e sessões completas.' if source.startswith('🔬 Explorar') else 'Aguardando dados validados para liberar o backtest.')
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
        enable_risk=st.checkbox('Ativar travas extras v1.1 (experimentais)',value=profile=='seletivo')
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
        run=st.button('Executar backtest v1.1',type='primary',use_container_width=True)
        compare=st.button('Comparar base v0.5 × seletivo v1.1 (mesmos parâmetros)',use_container_width=True)
        if compare:
            try:
                raw_data=demo_data() if source=='Demonstração fictícia' else checked
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
                    hard_blocks=attempts[~attempts.decisao.eq('EXECUTADA')]
                    st.caption(f'{len(hard_blocks)} sinais candidatos sem execução no simulador. Alguns bloqueios são por limite de risco/posição aberta; não são prova de previsibilidade.')
                    for item in decision_counts.to_dict('records'):
                        st.write(f"• **{item['Decisão']}**: {item['Quantidade']} sinal(is)")
                    with st.expander('Detalhar cada tentativa'):
                        st.dataframe(attempts,hide_index=True,use_container_width=True)
                exported=trades.copy()
                exported['tipo_dado']=provenance['classificacao']
                exported['contrato_declarado']=provenance.get('contrato_declarado','NENHUM')
                exported['sha256_csv_origem']=provenance.get('sha256')
                st.download_button('Baixar operações v1.1 (CSV)',exported.to_csv(index=False).encode('utf-8-sig'),
                                   'backtest_trader_pro_ai_elite_v11.csv','text/csv',use_container_width=True)
                st.download_button('Baixar auditoria de entradas (CSV)',attempts.to_csv(index=False).encode('utf-8-sig'),
                                   'auditoria_entradas_v11.csv','text/csv',use_container_width=True)
                config={'perfil':profile,'custo_pontos':float(cost),
                        'slippage_ticks_por_lado':int(slip),'max_operacoes_dia':int(daily_limit),
                        'max_hold_candles':int(max_hold),'limite_perda_diaria_pontos':float(daily_loss),
                        'risco_max_stop_pontos':float(max_risk) if max_risk is not None else None,
                        'max_perdas_seguidas':int(loss_streak) if loss_streak is not None else None,
                        'min_rr_teorico':float(min_rr)}
                st.download_button('Baixar relatório de origem e parâmetros (JSON)',
                    json.dumps({'versao':'1.0','dados':provenance,'parametros':config,
                                'total_operacoes':len(trades),'saldo_pontos':net,
                                'calendario':{'mercado':'B3 WIN','ano':2026,'feriados_bloqueados':len(HOLIDAYS_2026),
                                              'anos_sem_calendario':'BLOQUEADOS'}},
                               ensure_ascii=False,indent=2).encode('utf-8'),
                    'relatorio_origem_v11.json','application/json',use_container_width=True)
                st.caption('Saldo em pontos, não reais. Custos, liquidez e preço de execução são aproximações. Não operar dinheiro real.')
            except (ValueError,TypeError) as exc:
                st.error(f'Não foi possível executar: {exc}')


with tab_robust:
    st.subheader('🧬 Laboratório de robustez v1.1')
    st.caption('Esta aba mostra fragilidade da amostra e custo adicional no mesmo backtest. NÃO treina IA, não otimiza parâmetros, não mede probabilidade de acerto futuro e não usa cotações ao vivo.')
    if out is None:
        st.warning('A robustez de uma estratégia NÃO pode ser medida neste arquivo exploratório sem contrato verificado.' if source.startswith('🔬 Explorar') else 'Aguardando dados de candles válidos para avaliar a robustez.')
    else:
        st.info('A comparação divide os pregões cronologicamente, sem cortar um pregão ao meio. É uma análise DENTRO da mesma amostra, não um verdadeiro teste fora da amostra.')
        if st.button('🔬 Calcular diagnóstico de robustez',type='primary',key='v11_robust',use_container_width=True):
            try:
                diagnostic_trades=backtest(out,cost_points=float(cost),max_hold=int(max_hold),
                    slippage_ticks=int(slip),max_daily_trades=int(daily_limit),
                    max_daily_loss_points=float(daily_loss),contract=contract,
                    max_trade_risk_points=float(max_risk) if max_risk is not None else None,
                    max_consecutive_losses=int(loss_streak) if loss_streak is not None else None,
                    min_reward_risk=float(min_rr))
                report=robustness_report(diagnostic_trades,out,additional_costs=(0,5,10,20))
                st.caption('Dados: ' + ('FICTÍCIOS (DEMONSTRAÇÃO)' if source=='Demonstração fictícia' else 'CSV HISTÓRICO DECLARADO, NÃO AUTENTICADO'))
                summary=report['resumo']
                k1,k2=st.columns(2)
                k1.metric('Operações simuladas',summary['operacoes'])
                k2.metric('Saldo líquido (pts)',f"{summary['saldo_pts']:+.1f}")
                k1.metric('Taxa histórica líquida',f"{summary['taxa_acerto']:.1%}" if summary['taxa_acerto'] is not None else 'N/D')
                k2.metric('Drawdown (pts)',f"{summary['drawdown_pts']:.1f}")
                if diagnostic_trades.empty:
                    st.warning('Sem operações simuladas: não é possível inferir consistência ou desempenho.')
                st.markdown('**Comparação entre períodos inteiros**')
                if report['periodos'].empty:
                    st.warning('É necessário pelo menos dois pregões completos para dividir a amostra.')
                else:
                    periods=report['periodos'].copy()
                    periods['Acerto líquido']=periods['Acerto líquido'].map(lambda x: 'N/D' if pd.isna(x) else f'{x:.1%}')
                    st.dataframe(periods,use_container_width=True,hide_index=True)
                    st.download_button('Baixar comparação temporal (CSV)',periods.to_csv(index=False).encode('utf-8-sig'),
                                       'robustez_periodos_v11.csv','text/csv',use_container_width=True)
                st.markdown('**Teste de custos extras por operação**')
                st.caption('Os extras de 0, 5, 10 e 20 pontos são SUBTRAÍDOS do resultado líquido já calculado. Não são os custos totais; não há reexecução da estratégia.')
                stressed=report['custos'].copy()
                stressed['Acerto líquido']=stressed['Acerto líquido'].map(lambda x: 'N/D' if pd.isna(x) else f'{x:.1%}')
                st.dataframe(stressed,use_container_width=True,hide_index=True)
                st.download_button('Baixar cenários de custo (CSV)',stressed.to_csv(index=False).encode('utf-8-sig'),
                                   'robustez_custos_v11.csv','text/csv',use_container_width=True)
                # Leitura vertical para celular: tabelas detalhadas continuam disponíveis
                # acima, mas os resultados-chave não exigem arrastar horizontalmente.
                st.subheader('📱 Resumo por período')
                if not report['periodos'].empty:
                    for item in report['periodos'].to_dict('records'):
                        with st.container(border=True):
                            st.markdown(f"**{item['Período']}** · {item['De']} a {item['Até']}")
                            st.write(f"{item['Pregões']} pregões · {item['Operações']} operações · Saldo {item['Saldo (pts)']:+.1f} pts")
                st.subheader('📅 Avaliação cronológica v1.1')
                st.caption('Os últimos ~30% dos pregões INTEIROS são reservados; o arredondamento pode alterar muito a proporção em amostras pequenas. Sem otimização neste painel.')
                validation = chronological_validation(
                    diagnostic_trades, out,
                    is_demo=(source == 'Demonstração fictícia'),
                    reserve_fraction=0.30, extra_cost_points=10.0)
                st.warning('🛑 ' + validation['classificacao'])
                st.caption(f"Divisão efetiva: {validation['pregoes_estudo']} pregões de estudo / {validation['pregoes_reserva']} de reserva ({validation['frac_reserva_efetiva']:.0%} da amostra); objetivo: 30%.")
                for item in validation['segmentos'].to_dict('records'):
                    with st.container(border=True):
                        st.markdown('**' + item['Segmento'] + '**')
                        st.caption(f"{item['De']} a {item['Até']} · {item['Pregões']} pregões")
                        st.write(f"Operações: **{item['Operações']}** · Resultado: **{item['Saldo (pts)']:+.1f} pts**")
                        win_text = 'N/D' if item['Acerto líquido'] is None else f"{item['Acerto líquido']:.1%}"
                        st.caption(f"Acerto líquido da amostra: {win_text} · Drawdown: {item['Drawdown (pts)']:.1f} pts")
                reserve=validation['reserva']
                reserve_stress=validation['reserva_com_custo_extra']
                st.metric('Reserva com +10 pts de custos/oper.',f"{reserve_stress['saldo_pts']:+.1f} pts")
                st.caption('Custo extra subtraído dos resultados já simulados. Não reexecuta a estratégia nem modela liquidez.')
                with st.expander('⚠️ Critérios e limitações da validação',expanded=True):
                    for message in validation['alertas']:
                        st.write('• ' + message)
                st.download_button('Baixar resultados por pregão (CSV)',
                    validation['por_dia'].to_csv(index=False).encode('utf-8-sig'),
                    'validacao_por_pregao_v11.csv','text/csv',use_container_width=True)
                st.download_button('Baixar separação temporal (CSV)',
                    validation['segmentos'].to_csv(index=False).encode('utf-8-sig'),
                    'validacao_segmentos_v11.csv','text/csv',use_container_width=True)
                for warning in report['alertas']:
                    st.warning(warning)
                st.caption('Não há IA treinada, probabilidades preditivas ou autorização para ordens. Proibir uso real com base somente nesses relatórios.')
            except (ValueError,TypeError,KeyError) as exc:
                st.error(f'Não foi possível avaliar robustez: {exc}')

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
    st.markdown('''**Para estudar dados históricos:** exporte OHLC de 5 minutos de um único vencimento WIN em 2026, com início de candle no fuso de Brasília, todas as sessões completas e dias consecutivos de negociação. Inclua `symbol` se seu fornecedor oferecer. Declare a origem e o ticker (ex.: WINZ26). Uma planilha de operações não substitui candles.''')
    st.download_button('⬇️ Baixar modelo CSV vazio', b'datetime,open,high,low,close,volume,symbol\n', 'modelo_candles_win.csv', 'text/csv', use_container_width=True)
    st.caption('O modelo é só um CABEÇALHO. Não contém preços inventados e não valida sozinho o contrato.')
    st.markdown('**Como obter os dados:** verifique se sua plataforma ou fornecedor tem exportação histórica de candles WIN 5m para CSV. Pode haver custos/licenciamento; o serviço de cotações históricas diárias de ações da B3 não equivale a WIN intradiário.')
    st.subheader('📆 Bloqueio obrigatório de feriados da B3')
    st.caption('Tabela oficial de 2026: candles e entradas de WIN em datas sem pregão são bloqueados. Datas especiais são validadas separadamente; anos além de 2026 não são autorizados até atualização do calendário.')
    holidays=pd.DataFrame({'Feriados B3 2026': [x.strftime('%d/%m/%Y') for x in sorted(HOLIDAYS_2026)]})
    st.dataframe(holidays,hide_index=True,use_container_width=True)
    st.caption('Fonte oficial: https://www.b3.com.br/pt_br/noticias/calendario-de-negociacao-da-b3-confira-o-funcionamento-da-bolsa-em-2026.htm')
    st.markdown('---')
    st.subheader('🧪 Autoteste de calendário — sem dados de mercado')
    st.caption('O teste gera candles ARTIFICIAIS apenas na memória e confere regras de bloqueio: validação do CSV, bloqueio do dia e elegibilidade de entrada. Não declara origem histórica nem mede resultados de trading.')
    if st.button('🛡️ Executar autoteste de feriados', key='calendar_selftest_10', use_container_width=True):
        from engine import validate_win_candles
        scenarios = [
            ('19/11/2026 · dia útil', '2026-11-19', None, 'ELEGIVEL_HORARIO', None),
            ('20/11/2026 · feriado B3', '2026-11-20', 'FERIADO_B3', 'FERIADO_B3', 'feriado da B3'),
            ('21/11/2026 · sábado', '2026-11-21', 'FIM_DE_SEMANA', 'FIM_DE_SEMANA', 'sábado/domingo'),
            ('02/01/2027 · ano não validado', '2027-01-02', 'CALENDARIO_NAO_VALIDADO', 'CALENDARIO_NAO_VALIDADO', 'calendário B3 de 2026'),
        ]
        example = demo_data(days=1)
        report = []
        for label, day, expected_day_block, expected_gate, expected_error in scenarios:
            candidate = example.copy()
            shift = pd.Timestamp(day + ' 09:00') - candidate.datetime.iloc[0]
            candidate['datetime'] = candidate.datetime + shift
            clock = pd.Timestamp(day + ' 10:00')
            actual_day_block = market_day_gate(clock)
            actual_gate = signal_entry_gate('COMPRA', clock, clock + pd.Timedelta(minutes=5), contract='WINZ26')
            got_rejected = False
            error_message = ''
            try:
                validate_win_candles(candidate, require_complete_sessions=True, contract='WINZ26')
            except ValueError as exc:
                got_rejected = True
                error_message = str(exc)
            expected_rejection = expected_error is not None
            passed = (actual_day_block == expected_day_block and actual_gate == expected_gate
                      and got_rejected == expected_rejection
                      and (not expected_error or expected_error in error_message))
            report.append({'Data': label,
                           'Candles': 'BLOQUEADOS' if got_rejected else 'ACEITOS',
                           'Sinal': actual_gate,
                           'Teste': 'PASSOU' if passed else 'FALHOU'})
        # Casos adicionais que não dependem de dados de negociação autenticados.
        extra_checks = [
            ('18/02/2026 antes das 13h',
             signal_entry_gate('COMPRA',pd.Timestamp('2026-02-18 12:00'),pd.Timestamp('2026-02-18 12:05'),contract='WINJ26') == 'FORA_SESSAO', 'FORA_SESSAO'),
            ('18/02/2026 após 13h',
             signal_entry_gate('COMPRA',pd.Timestamp('2026-02-18 13:05'),pd.Timestamp('2026-02-18 13:10'),contract='WINJ26') == 'ELEGIVEL_HORARIO', 'ELEGIVEL_HORARIO'),
            ('17/06/2026 vencimento WINM26',
             signal_entry_gate('COMPRA',pd.Timestamp('2026-06-17 10:00'),pd.Timestamp('2026-06-17 10:05'),contract='WINM26') == 'DIA_VENCIMENTO', 'DIA_VENCIMENTO'),
            ('24/12/2026 feriado B3',
             market_day_gate(pd.Timestamp('2026-12-24 10:00')) == 'FERIADO_B3', 'FERIADO_B3'),
            ('09/07/2026 pregão normal',
             signal_entry_gate('COMPRA', pd.Timestamp('2026-07-09 09:05'),
                               pd.Timestamp('2026-07-09 09:10'),contract='WINQ26') == 'ELEGIVEL_HORARIO',
             'ELEGIVEL_HORARIO'),
            ('31/12/2026 sem pregão',
             market_day_gate(pd.Timestamp('2026-12-31 10:00')) == 'FERIADO_B3', 'FERIADO_B3'),
        ]
        report.extend({'Data':label,'Candles':'NÃO APLICÁVEL','Sinal':gate,
                       'Teste':'PASSOU' if passed else 'FALHOU'} for label,passed,gate in extra_checks)
        count = sum(item['Teste'] == 'PASSOU' for item in report)
        if count == len(report):
            st.success(f'✅ {count}/{len(report)} verificações aprovadas: o calendário e os horários especiais respeitam as travas previstas.')
        else:
            st.error(f'⚠️ {count}/{len(report)} verificações aprovadas. Confira as regras antes de confiar no bloqueio.')
        st.dataframe(pd.DataFrame(report), use_container_width=True, hide_index=True)
        st.caption('Importante: este autoteste verifica regras previstas no código. Não autentica calendário para outros anos, feriados extraordinários ou negociações reais.')
    st.caption('A v1.1 não baixa dados de terceiros, não verifica licenças, não acessa cotações ao vivo e não envia ordens. Resultado retrospectivo não prevê acertos futuros.')

st.divider()
st.caption('Trader Pro AI Elite · v1.2 · Simulador de pesquisa. Horários de referência B3 para 2026; verifique o calendário oficial e possíveis mudanças. Não utilizar para decisões financeiras reais.')
