import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from engine import analyze_market

st.set_page_config(
    page_title="Trader Pro AI Elite",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
.stApp {background: #0b0e12; color: #f2f4f7;}
[data-testid="stMetric"] {background:#151b22; padding:14px; border:1px solid #26313d; border-radius:12px;}
div[data-testid="stAlert"] {border-radius:12px;}
h1, h2, h3 {color:#f4f5f7;}
.small-muted {color:#9ba7b4; font-size:0.88rem;}
</style>
""", unsafe_allow_html=True)


def demo_data(n=240, seed=17):
    """Gera candles fictícios apenas para demonstrar a interface."""
    rng = np.random.default_rng(seed)
    times = pd.date_range("2026-11-20 09:00", periods=n, freq="5min")
    drift = np.r_[np.full(80, 0.9), np.full(80, -0.35), np.full(80, 0.65)]
    noise = rng.normal(0, 18, n)
    close = 130000 + np.cumsum(drift + noise)
    open_ = np.r_[close[0] - rng.normal(0, 8), close[:-1]]
    spread = rng.uniform(8, 35, n)
    high = np.maximum(open_, close) + spread
    low = np.minimum(open_, close) - spread
    volume = rng.integers(500, 1800, n)
    return pd.DataFrame({
        "datetime": times, "open": open_, "high": high,
        "low": low, "close": close, "volume": volume
    })


def br_number(value, decimals=1):
    if value is None or pd.isna(value):
        return "—"
    return f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


st.title("📈 TRADER PRO AI ELITE")
st.caption("MOTOR DE SINAIS · WIN · INTRADAY · VERSÃO 0.1")
st.warning(
    "MODO DE DESENVOLVIMENTO — esta versão não está conectada à B3 ou a uma corretora. "
    "O modo de demonstração usa dados fictícios. Nenhuma ordem é enviada."
)

with st.sidebar:
    st.subheader("Configurações")
    st.write("Mercado: **WIN — Mini-índice**")
    st.write("Gráfico de análise: **5 minutos**")
    st.write("Filtro de tendência: **15 minutos**")
    st.write("Execução: **Manual (desativada nesta versão)**")
    st.caption("Parâmetros experimentais; ainda não validados.")

st.subheader("Dados de mercado")
uploaded = st.file_uploader(
    "Envie um CSV com candles de 5 minutos",
    type=["csv"],
    help="Colunas necessárias: datetime, open, high, low, close, volume."
)

if uploaded is not None:
    try:
        source_df = pd.read_csv(uploaded)
        data_source = "Arquivo CSV enviado"
    except Exception as exc:
        st.error(f"Não foi possível ler o CSV: {exc}")
        st.stop()
else:
    source_df = demo_data()
    data_source = "DEMONSTRAÇÃO — dados fictícios"
    st.info("Nenhum CSV enviado. Exibindo dados fictícios para demonstrar o funcionamento.")

st.caption(f"Fonte: {data_source}")

try:
    candles, result = analyze_market(source_df)
except Exception as exc:
    st.error(f"Erro ao analisar os dados: {exc}")
    st.stop()

signal = result["signal"]
if signal == "COMPRA":
    st.success("SINAL: COMPRA — apenas análise; nenhuma ordem será enviada.")
elif signal == "VENDA":
    st.error("SINAL: VENDA — apenas análise; nenhuma ordem será enviada.")
else:
    st.info("SINAL: AGUARDAR — os filtros de entrada não foram todos confirmados.")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Último fechamento", br_number(result["close"], 0))
m2.metric("Tendência 15 min", result["trend15"])
m3.metric("RSI 14", br_number(result["rsi"], 1))
m4.metric("ATR 14", br_number(result["atr"], 1))

if signal in ("COMPRA", "VENDA"):
    st.subheader("Plano técnico ilustrativo")
    c1, c2, c3 = st.columns(3)
    c1.metric("Entrada de referência", br_number(result["entry"], 0))
    c2.metric("Stop estimado", br_number(result["stop"], 0))
    c3.metric("Alvo estimado", br_number(result["target"], 0))
    st.caption("Stop e alvo usam parâmetros experimentais (1 ATR de risco e alvo de 1,5R). Não são ordens.")

st.subheader("Por que o motor decidiu assim?")
for reason in result["reasons"]:
    st.write("• " + reason)

with st.expander("Ver indicadores e filtros"):
    st.write({
        "EMA 9": br_number(result["ema9"], 2),
        "EMA 21": br_number(result["ema21"], 2),
        "Volume atual": br_number(result["volume"], 0),
        "Média de volume (20)": br_number(result["volume_avg20"], 0),
        "Filtros calculáveis": result["checks"],
    })

st.subheader("Gráfico de candles — 5 minutos")
plot_df = candles.tail(100)
fig = go.Figure(data=[go.Candlestick(
    x=plot_df["datetime"],
    open=plot_df["open"], high=plot_df["high"],
    low=plot_df["low"], close=plot_df["close"],
    name="WIN (dados enviados/demonstração)"
)])
fig.add_trace(go.Scatter(
    x=plot_df["datetime"], y=plot_df["ema9"],
    mode="lines", name="EMA 9", line=dict(width=1.5)
))
fig.add_trace(go.Scatter(
    x=plot_df["datetime"], y=plot_df["ema21"],
    mode="lines", name="EMA 21", line=dict(width=1.5)
))
fig.update_layout(
    template="plotly_dark", height=430,
    margin=dict(l=10, r=10, t=20, b=10),
    xaxis_rangeslider_visible=False,
    paper_bgcolor="#0b0e12", plot_bgcolor="#0b0e12",
    legend=dict(orientation="h", y=1.02, x=0)
)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Últimos candles e indicadores")
view = candles.tail(12)[[
    "datetime", "open", "high", "low", "close", "ema9", "ema21", "rsi", "atr"
]].copy()
view["datetime"] = view["datetime"].dt.strftime("%d/%m %H:%M")
st.dataframe(view, use_container_width=True, hide_index=True)

st.divider()
st.subheader("Integridade e segurança")
st.write(
    "Esta versão não calcula taxa de acerto, não promete rentabilidade, "
    "não faz backtest validado e não executa operações. A próxima etapa será "
    "adicionar testes históricos reproduzíveis, custos, slippage e validação fora da amostra."
)
st.caption("Trader Pro AI Elite · Protótipo de pesquisa · v0.1")
