"""
Trader Pro AI Elite - Motor de Sinais v0.1
Motor educativo de análise. Não envia ordens e não fornece garantia de lucro.
"""

from __future__ import annotations
import pandas as pd
import numpy as np


REQUIRED_COLUMNS = ["datetime", "open", "high", "low", "close", "volume"]


def normalize_candles(df: pd.DataFrame) -> pd.DataFrame:
    """Valida e normaliza um DataFrame OHLCV."""
    data = df.copy()
    data.columns = [str(c).strip().lower() for c in data.columns]

    # Aceita alguns nomes comuns em português.
    aliases = {
        "data": "datetime", "date": "datetime", "time": "datetime",
        "abertura": "open", "máxima": "high", "maxima": "high",
        "mínima": "low", "minima": "low", "fechamento": "close",
        "volume": "volume", "vol": "volume"
    }
    data = data.rename(columns=aliases)

    missing = [c for c in REQUIRED_COLUMNS if c not in data.columns]
    if missing:
        raise ValueError(
            "Colunas ausentes: " + ", ".join(missing) +
            ". Esperado: datetime, open, high, low, close, volume."
        )

    data = data[REQUIRED_COLUMNS].copy()
    data["datetime"] = pd.to_datetime(data["datetime"], errors="coerce")
    for col in ["open", "high", "low", "close", "volume"]:
        data[col] = pd.to_numeric(data[col], errors="coerce")

    data = data.dropna().sort_values("datetime").drop_duplicates("datetime")
    if len(data) < 60:
        raise ValueError("Precisamos de pelo menos 60 candles de 5 minutos para esta versão.")
    if (data[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError("Os preços precisam ser maiores que zero.")
    if (data["high"] < data["low"]).any():
        raise ValueError("Há candles com máxima menor que a mínima.")
    return data.reset_index(drop=True)


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula EMA 9/21, RSI 14, ATR 14 e média de volume."""
    d = df.copy()
    d["ema9"] = d["close"].ewm(span=9, adjust=False).mean()
    d["ema21"] = d["close"].ewm(span=21, adjust=False).mean()

    delta = d["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    d["rsi"] = 100 - (100 / (1 + rs))
    d.loc[(avg_loss == 0) & (avg_gain > 0), "rsi"] = 100
    d.loc[(avg_gain == 0) & (avg_loss > 0), "rsi"] = 0

    previous_close = d["close"].shift(1)
    tr = pd.concat([
        d["high"] - d["low"],
        (d["high"] - previous_close).abs(),
        (d["low"] - previous_close).abs()
    ], axis=1).max(axis=1)
    d["atr"] = tr.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    d["volume_avg20"] = d["volume"].rolling(20).mean()

    # Confirmação de rompimento: máxima/mínima dos 10 candles ANTERIORES.
    d["previous_high10"] = d["high"].shift(1).rolling(10).max()
    d["previous_low10"] = d["low"].shift(1).rolling(10).min()
    return d


def add_15m_trend(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula a tendência de 15 min e associa a última barra de 15 min já encerrada."""
    d = df.copy().set_index("datetime")
    bars = d[["open", "high", "low", "close", "volume"]].resample(
        "15min", label="right", closed="right"
    ).agg({
        "open": "first", "high": "max", "low": "min",
        "close": "last", "volume": "sum"
    }).dropna()

    bars["ema9_15"] = bars["close"].ewm(span=9, adjust=False).mean()
    bars["ema21_15"] = bars["close"].ewm(span=21, adjust=False).mean()
    bars["trend15"] = np.where(
        bars["ema9_15"] > bars["ema21_15"], "ALTA",
        np.where(bars["ema9_15"] < bars["ema21_15"], "BAIXA", "NEUTRA")
    )
    # merge_asof usa somente a barra de 15m cujo horário de fechamento já ocorreu.
    left = d.reset_index().sort_values("datetime")
    right = bars[["ema9_15", "ema21_15", "trend15"]].reset_index()
    merged = pd.merge_asof(
        left, right, on="datetime", direction="backward", allow_exact_matches=True
    )
    return merged


def analyze_market(raw_df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Retorna candles com indicadores e a decisão referente ao último candle."""
    data = normalize_candles(raw_df)
    data = add_indicators(data)
    data = add_15m_trend(data)

    last = data.iloc[-1]
    checks = {
        "tendencia_15m": last.get("trend15") in ("ALTA", "BAIXA"),
        "medias_5m": pd.notna(last["ema9"]) and pd.notna(last["ema21"]),
        "rsi": pd.notna(last["rsi"]),
        "atr": pd.notna(last["atr"]) and last["atr"] > 0,
        "volume": pd.notna(last["volume_avg20"]),
        "rompimento": pd.notna(last["previous_high10"]) and pd.notna(last["previous_low10"]),
    }

    decision = "AGUARDAR"
    reasons = []
    side = None

    if not all(checks.values()):
        reasons.append("Histórico insuficiente para calcular todos os filtros.")
    else:
        # Evita mercado sem separação mínima entre as médias.
        ema_gap = abs(last["ema9"] - last["ema21"])
        trend_strength_ok = ema_gap >= 0.10 * last["atr"]
        volume_ok = last["volume"] >= last["volume_avg20"]
        bullish = (
            last["trend15"] == "ALTA"
            and last["ema9"] > last["ema21"]
            and 50 <= last["rsi"] < 70
            and last["close"] > last["previous_high10"]
            and trend_strength_ok
            and volume_ok
        )
        bearish = (
            last["trend15"] == "BAIXA"
            and last["ema9"] < last["ema21"]
            and 30 < last["rsi"] <= 50
            and last["close"] < last["previous_low10"]
            and trend_strength_ok
            and volume_ok
        )

        if bullish:
            decision, side = "COMPRA", "long"
            reasons.append("Tendência de 15 min e médias de 5 min alinhadas para alta.")
            reasons.append("RSI, volume e rompimento confirmaram os filtros compradores.")
        elif bearish:
            decision, side = "VENDA", "short"
            reasons.append("Tendência de 15 min e médias de 5 min alinhadas para baixa.")
            reasons.append("RSI, volume e rompimento confirmaram os filtros vendedores.")
        else:
            reasons.append("As condições completas de entrada não foram satisfeitas.")
            if last["rsi"] >= 70:
                reasons.append("RSI elevado: evitar perseguir movimento possivelmente esticado.")
            elif last["rsi"] <= 30:
                reasons.append("RSI muito baixo: evitar perseguir movimento possivelmente esticado.")
            if not volume_ok:
                reasons.append("Volume abaixo da média de 20 candles.")
            if not trend_strength_ok:
                reasons.append("Médias próximas: tendência pode estar fraca ou lateral.")
            if last["trend15"] == "NEUTRA":
                reasons.append("Tendência de 15 minutos sem direção definida.")

    entry = float(last["close"])
    atr = float(last["atr"]) if pd.notna(last["atr"]) else None
    stop = target = risk_points = None
    if side and atr:
        # Parâmetros experimentais v0.1: stop 1 ATR e alvo 1,5R.
        stop_distance = max(atr, 5.0)
        stop_distance = round(stop_distance / 5) * 5  # WIN: grade de 5 pontos
        risk_points = stop_distance
        if side == "long":
            stop = entry - stop_distance
            target = entry + 1.5 * stop_distance
        else:
            stop = entry + stop_distance
            target = entry - 1.5 * stop_distance

    result = {
        "signal": decision,
        "datetime": last["datetime"],
        "close": entry,
        "trend15": last.get("trend15", "INDEFINIDA"),
        "ema9": float(last["ema9"]) if pd.notna(last["ema9"]) else None,
        "ema21": float(last["ema21"]) if pd.notna(last["ema21"]) else None,
        "rsi": float(last["rsi"]) if pd.notna(last["rsi"]) else None,
        "atr": atr,
        "volume": float(last["volume"]),
        "volume_avg20": float(last["volume_avg20"]) if pd.notna(last["volume_avg20"]) else None,
        "entry": entry if side else None,
        "stop": stop,
        "target": target,
        "risk_points": risk_points,
        "reasons": reasons,
        "checks": checks,
    }
    return data, result
