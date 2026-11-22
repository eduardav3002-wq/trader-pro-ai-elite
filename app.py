"""Trader Pro AI Elite v0.4 — Streamlit, pesquisa sem corretora nem ordens."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from audit import audit_trades
from backtest import backtest
from engine import analyze, demo_data

st.set_page_config(page_title='Trader Pro AI Elite · v0.4',page_icon='📈',layout='wide',initial_sidebar_state='collapsed')
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

st.markdown('''<div class="hero"><div class="eyebrow">RESEARCH TERMINAL · V0.4</div>
<div class="hero-title">◈ TRADER PRO AI ELITE</div>
<div class="hero-sub">WIN · Intraday · Filtros EMA 9/21, RSI 14, ATR 14 e tendência 15m</div>
<span class="pill">● MODO PESQUISA — SEM ORDENS REAIS</span></div>''',unsafe_allow_html=True)
st.caption('Modelo de regras experimentais: não é inteligência artificial treinada nem previsão de ganhos. Mercado ao vivo e execução continuam desligados.')
with st.sidebar:
    st.header('⚙️ Central de controle')
    source=st.radio('Fonte dos dados',['Demonstração fictícia','CSV histórico'],index=0)
    chart_bars=st.slider('Candles no gráfico',30,180,75,15)
    show_ema=st.toggle('Exibir médias móveis',True)
    st.divider()
    st.caption('CSV histórico precisa de OHLC de 5 minutos do WIN. Datas sem fuso são interpretadas em Brasília. O programa NÃO autentica os dados.')

out=None
if source=='CSV histórico':
    uploaded=st.file_uploader('Carregue candles do WIN (não o CSV de operações)',type=['csv'],key='candles',help='datetime,open,high,low,close[,volume] · horários de abertura em Brasília')
    if uploaded is None:
        st.info('Para analisar o WIN, envie um CSV histórico com candles OHLC reais de 5 minutos. O CSV de operações v0.3 pode ser enviado na aba Auditoria.')
    else:
        try:
            raw=pd.read_csv(uploaded)
            out=analyze(raw)
            st.info('Arquivo submetido à validação técnica. Fonte e autenticidade dos preços NÃO verificadas; sessões especiais e feriados exigem confirmação externa.')
        except (ValueError,TypeError,pd.errors.ParserError,UnicodeError) as exc:
            st.error(f'CSV rejeitado: {exc}')
else:
    try:
        out=analyze(demo_data())
    except (ValueError,TypeError) as exc:
        st.error(f'Erro na demonstração: {exc}')
    st.warning('DEMONSTRAÇÃO 100% FICTÍCIA: nem candles nem resultados representam o mercado real da B3.')

tab_terminal,tab_bt,tab_audit=st.tabs(['📈 Terminal de sinais','🧪 Backtesting','🛡️ Auditoria v0.3'])

with tab_terminal:
    if out is None:
        st.info('Aguardando um CSV de candles válido para exibir sinais.')
    else:
        last=out.iloc[-1]
        signal=str(last['signal'])
        palette={'COMPRA':'#4bd4a3','VENDA':'#ff7f91','AGUARDAR':'#f1c56e'}
        reason=[]
        if last['trend15']=='SEM CONFIRMAÇÃO':
            reason.append('Ainda não existem candles completos suficientes para confirmar a tendência de 15 minutos.')
        elif last['condition']=='POSSÍVEL LATERALIZAÇÃO':
            reason.append('As médias móveis estão próximas: possível lateralização.')
        elif signal=='AGUARDAR':
            reason.append('Os filtros de tendência 5m/15m, RSI e rompimento não estão alinhados. NÃO OPERAR.')
        else:
            reason.append('Tendência 5m/15m, RSI e rompimento de três candles estão alinhados no modelo experimental.')
        st.markdown(f'''<div class="signal" style="border-left:5px solid {palette[signal]}"><div class="muted">STATUS DO ÚLTIMO CANDLE · HISTÓRICO</div>
        <strong style="color:{palette[signal]}">{signal}</strong><div class="muted">{reason[0]}</div></div>''',unsafe_allow_html=True)
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
            for item in reason: st.write('• '+item)
            st.write('• Tendência EMA 9/21: **'+str(last['trend'])+'**')
            st.write('• Tendência dos candles completos 15m: **'+str(last['trend15'])+'**')
            st.write('• Condição de mercado: **'+str(last['condition'])+'**')
            st.caption('Esse motor não calcula probabilidade estatística de acerto.')
        with st.expander('🎯 Níveis ilustrativos de ATR'):
            if signal=='AGUARDAR':
                st.info('Nenhuma entrada: o sistema recomenda aguardar.')
            else:
                a,b,c=st.columns(3)
                a.metric('Fechamento ref.',f'{last["close"]:,.0f}')
                b.metric('Stop estimado',f'{last["stop"]:,.0f}')
                c.metric('Alvo estimado',f'{last["target"]:,.0f}')
                st.caption('Referências ilustrativas arredondadas à grade de 5 pontos; entrada de backtest é na próxima abertura.')
        with st.expander('🗂️ Últimos candles'):
            st.dataframe(out[['datetime','close','ema9','ema21','rsi','atr','trend','trend15','condition','signal']].tail(20),
                         use_container_width=True,hide_index=True)

with tab_bt:
    st.write('Backtest histórico com validação rigorosa. **Nunca confunda resultado retrospectivo com probabilidade futura.**')
    st.caption('Entrada na abertura do candle seguinte, até 17:55; stop tem prioridade, limite 3 operações/dia por padrão, zeragem até 18:15. 1 contrato por operação para interpretação de pontos.')
    if out is None:
        st.info('Envie candles válidos ou escolha demonstração fictícia para liberar o backtest.')
    else:
        b1,b2=st.columns(2)
        with b1:
            cost=st.number_input('Taxas estimadas por operação (pontos, ida + volta)',min_value=0.0,value=2.0,step=0.5)
            slip=st.number_input('Slippage por lado (ticks de 5 pontos)',min_value=0,max_value=20,value=1,step=1)
            daily_limit=st.number_input('Máximo de operações por dia',min_value=1,max_value=30,value=3,step=1)
        with b2:
            max_hold=st.number_input('Duração máxima (candles de 5 min)',min_value=1,max_value=100,value=12,step=1)
            daily_loss=st.number_input('Limite de perda líquida diária (pontos)',min_value=0.0,value=200.0,step=25.0)
        st.caption(f'Exemplo de fricção: {cost:.1f} pts de taxas + {2*slip*5} pts de slippage por operação; isto é uma hipótese, não preço de corretora.')
        run=st.button('Executar backtest v0.4',type='primary',use_container_width=True)
        if run:
            try:
                trades=backtest(out,cost_points=cost,max_hold=int(max_hold),slippage_ticks=int(slip),
                                max_daily_trades=int(daily_limit),max_daily_loss_points=daily_loss)
                if source=='Demonstração fictícia':
                    st.warning('Resultado abaixo é exclusivamente de preços INVENTADOS. Não mede eficácia no mercado WIN.')
                if trades.empty:
                    st.info('Nenhuma operação aprovada pelos filtros nesta amostra. Isso é um resultado possível e não deve ser forçado.')
                else:
                    net=float(trades.net_points.sum())
                    wins=int(trades.net_points.gt(0).sum())
                    equity=pd.concat([pd.Series([0.0]),trades.net_points.cumsum().reset_index(drop=True)],ignore_index=True)
                    dd=float((equity-equity.cummax()).min())
                    c1,c2,c3,c4=st.columns(4)
                    c1.metric('Operações',int(len(trades)))
                    c2.metric('Acerto líquido',f'{wins/len(trades):.1%}')
                    c3.metric('Saldo líquido',f'{net:+.1f} pts')
                    c4.metric('Drawdown (do zero)',f'{dd:.1f} pts')
                    st.line_chart(equity,y_label='Pontos acumulados · inicia em zero')
                    st.dataframe(trades,use_container_width=True,hide_index=True)
                    st.download_button('Baixar operações v0.4 (CSV)',trades.to_csv(index=False).encode('utf-8-sig'),
                                       'backtest_trader_pro_ai_elite_v04.csv','text/csv',use_container_width=True)
                    st.caption('Pontos, não reais. Valor teórico de cada ponto WIN: R$0,20 por contrato; tributação, corretora e liquidez reais não foram verificadas.')
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

st.divider()
st.caption('Trader Pro AI Elite · v0.4 · Simulador de pesquisa. Horários de referência B3 em nov/2026; verifique o calendário oficial e possíveis mudanças. Não utilizar para decisões financeiras reais.')
