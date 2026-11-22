import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from engine import analyze, demo_data

st.set_page_config(page_title='Trader Pro AI Elite',page_icon='📈',layout='wide',initial_sidebar_state='collapsed')
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

st.markdown('''<div class="hero"><div class="eyebrow">ANALYTICS TERMINAL · V0.2</div>
<div class="hero-title">◈ TRADER PRO AI ELITE</div>
<div class="hero-sub">WIN · Intraday · Motor experimental de sinais · Confirmação manual</div>
<span class="pill">● MODO DE PESQUISA — sem ordens reais</span></div>''',unsafe_allow_html=True)

with st.sidebar:
    st.header('⚙️ Central de controle')
    source=st.radio('Fonte dos dados',['Demonstração fictícia','CSV histórico'],index=0)
    chart_bars=st.slider('Candles no gráfico',30,180,75,15)
    show_ema=st.toggle('Exibir médias móveis',True)
    st.divider()
    st.caption('Sem conexão com corretora ou cotações em tempo real. Sinais experimentais não são recomendações.')

if source=='CSV histórico':
    uploaded=st.file_uploader('Envie candles de 5 minutos em CSV',type=['csv'],help='Colunas: datetime, open, high, low, close')
    if uploaded is None:
        st.info('Envie um arquivo CSV para iniciar a análise histórica.');st.stop()
    try:
        df=pd.read_csv(uploaded)
        if 'datetime' in df.columns:
            df['datetime']=pd.to_datetime(df['datetime'],errors='coerce')
            if df.datetime.isna().any(): raise ValueError('Datas inválidas na coluna datetime.')
            if not df.datetime.is_monotonic_increasing: raise ValueError('Ordene os candles do mais antigo para o mais recente.')
    except Exception as exc:
        st.error(f'Não foi possível ler o arquivo: {exc}');st.stop()
    st.info('Fonte: CSV enviado pelo usuário. A autenticidade e a periodicidade dos dados não foram verificadas.')
else:
    df=demo_data()
    st.warning('DEMONSTRAÇÃO — preços, candles e sinais fictícios. Não são dados da B3.')

try:
    out=analyze(df)
except (ValueError,TypeError) as exc:
    st.error(f'Não foi possível analisar os dados: {exc}');st.stop()
last=out.iloc[-1]
signal=str(last['signal'])
color={'COMPRA':'#4bd4a3','VENDA':'#ff7f91','AGUARDAR':'#f1c56e'}[signal]
reason=[]
if last['condition']=='POSSÍVEL LATERALIZAÇÃO': reason.append('As médias estão próximas em relação à volatilidade (ATR).')
if signal=='AGUARDAR':
    if last['rsi']<33: reason.append('RSI abaixo de 33: evitar perseguir um movimento possivelmente esticado.')
    elif last['rsi']>67: reason.append('RSI acima de 67: evitar entrada após possível esticamento.')
    else: reason.append('Não houve alinhamento completo entre tendência, RSI e filtro de lateralização.')
else: reason.append('Tendência, RSI e filtro de lateralização estão alinhados pelas regras experimentais.')

st.markdown(f'''<div class="signal" style="border-left:5px solid {color}"><div class="muted">DECISÃO DO MOTOR · ÚLTIMO CANDLE</div>
<strong style="color:{color}">{signal}</strong><div class="muted">{reason[0]}</div></div>''',unsafe_allow_html=True)

c1,c2=st.columns(2)
with c1:
    st.metric('Fechamento (dados carregados)',f'{last["close"]:,.0f}'.replace(',','.'))
    st.metric('RSI 14',f'{last["rsi"]:.1f}'.replace('.',','))
with c2:
    st.metric('Tendência (EMA 9/21)',str(last['trend']))
    st.metric('ATR 14',f'{last["atr"]:.1f}'.replace('.',','))

st.subheader('📊 Candles · 5 minutos (esperado)')
chart=out.tail(chart_bars).copy()
x=chart['datetime'] if 'datetime' in chart.columns else chart.index
fig=go.Figure()
fig.add_trace(go.Candlestick(x=x,open=chart['open'],high=chart['high'],low=chart['low'],close=chart['close'],name='Candles',increasing_line_color='#40d4a1',decreasing_line_color='#ff6b82'))
if show_ema:
    fig.add_trace(go.Scatter(x=x,y=chart['ema9'],name='EMA 9',line=dict(color='#71baff',width=1.6)))
    fig.add_trace(go.Scatter(x=x,y=chart['ema21'],name='EMA 21',line=dict(color='#f4c36e',width=1.6)))
fig.update_layout(template='plotly_dark',height=390,xaxis_rangeslider_visible=False,paper_bgcolor='#080e1a',plot_bgcolor='#0e1929',font=dict(color='#b9c9dc'),margin=dict(l=5,r=5,t=25,b=10),legend=dict(orientation='h',y=1.12,x=0),xaxis=dict(showgrid=False),yaxis=dict(gridcolor='#23334a',side='right'))
st.plotly_chart(fig,use_container_width=True,config={'displaylogo':False,'scrollZoom':False})

with st.expander('🔎 Por que o motor tomou essa decisão?',expanded=True):
    for item in reason: st.write('• '+item)
    st.write('• Tendência EMA 9/21: **'+str(last['trend'])+'**')
    st.write('• Condição: **'+str(last['condition'])+'**')
    st.caption('Estas são regras fixas experimentais; não representam inteligência artificial treinada nem probabilidade de acerto.')

with st.expander('🎯 Plano técnico ilustrativo'):
    if signal=='AGUARDAR':
        st.info('Nenhuma entrada sugerida: os filtros não foram satisfeitos.')
    else:
        a,b,c=st.columns(3)
        a.metric('Entrada ref.',f'{last["close"]:,.0f}')
        b.metric('Stop estimado',f'{last["stop"]:,.0f}')
        c.metric('Alvo estimado',f'{last["target"]:,.0f}')
        st.caption('Níveis calculados por ATR, sem considerar custos, slippage ou execução real.')

with st.expander('🗂️ Histórico dos últimos candles'):
    cols=[c for c in ['datetime','close','ema9','ema21','rsi','atr','trend','condition','signal'] if c in out.columns]
    st.dataframe(out[cols].tail(20),use_container_width=True,hide_index=True)

st.divider()
st.caption('Trader Pro AI Elite · v0.2 · Protótipo de pesquisa. Não calcula taxa de acerto nem executa operações. Não utilizar para decisões financeiras reais.')
