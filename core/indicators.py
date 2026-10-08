"""
Core Technical Indicators Module.
Computes ATR, ADX (+DI/-DI, DI Gap), RSI with Wilder smoothing,
63-session percentage-point alpha vs benchmark, and 20-session swing support/resistance.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average True Range (ATR) using Wilder's smoothing method.

    Args:

        df: DataFrame containing High, Low, Close columns sorted by Date ascending.
        period: Smoothing period (default 14).

    Returns:

        Series containing ATR values aligned with df index.
    """
    if len(df) < period + 1:
        return pd.Series(np.nan, index=df.index)

    high = df["High"].values
    low = df["Low"].values
    close = df["Close"].values

    tr = np.zeros(len(df))
    tr[0] = high[0] - low[0]

    for i in range(1, len(df)):
        tr[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1])
        )

    atr = np.full(len(df), np.nan)
    # Wilder's initial value: simple mean over first period
    atr[period] = np.mean(tr[1:period + 1])

    for i in range(period + 1, len(df)):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period

    return pd.Series(atr, index=df.index)


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index (RSI) using Wilder's smoothing.

    Args:

        df: DataFrame containing Close column sorted by Date ascending.
        period: RSI period (default 14).

    Returns:

        Series containing RSI values (0-100).
    """
    if len(df) < period + 1:
        return pd.Series(np.nan, index=df.index)

    close = df["Close"].values
    diff = np.diff(close)

    gains = np.where(diff > 0, diff, 0.0)
    losses = np.where(diff < 0, -diff, 0.0)

    avg_gain = np.full(len(df), np.nan)
    avg_loss = np.full(len(df), np.nan)
    rsi = np.full(len(df), np.nan)

    # Initial average over first period
    avg_gain[period] = np.mean(gains[:period])
    avg_loss[period] = np.mean(losses[:period])

    if avg_loss[period] == 0:
        rsi[period] = 100.0
    else:
        rs = avg_gain[period] / avg_loss[period]
        rsi[period] = 100.0 - (100.0 / (1.0 + rs))

    for i in range(period + 1, len(df)):
        g = gains[i - 1]
        l = losses[i - 1]
        avg_gain[i] = (avg_gain[i - 1] * (period - 1) + g) / period
        avg_loss[i] = (avg_loss[i - 1] * (period - 1) + l) / period

        if avg_loss[i] == 0:
            rsi[i] = 100.0
        else:
            rs = avg_gain[i] / avg_loss[i]
            rsi[i] = 100.0 - (100.0 / (1.0 + rs))

    return pd.Series(rsi, index=df.index)


def calculate_adx_di(df: pd.DataFrame, period: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """Calculate ADX, +DI, -DI, and DI Gap (+DI - -DI) using Wilder's smoothing.

    Args:

        df: DataFrame containing High, Low, Close sorted by Date.
        period: Period length (default 14).

    Returns:

        Tuple of (ADX, Plus_DI, Minus_DI, DI_Gap) Series.
    """
    n = len(df)
    if n < 2 * period:
        nan_s = pd.Series(np.nan, index=df.index)
        return nan_s, nan_s, nan_s, nan_s

    high = df["High"].values
    low = df["Low"].values
    close = df["Close"].values

    tr = np.zeros(n)
    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)

    for i in range(1, n):
        tr[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1])
        )
        up_move = high[i] - high[i - 1]
        down_move = low[i - 1] - low[i]

        if up_move > down_move and up_move > 0:
            plus_dm[i] = up_move
        if down_move > up_move and down_move > 0:
            minus_dm[i] = down_move

    smoothed_tr = np.full(n, np.nan)
    smoothed_pdm = np.full(n, np.nan)
    smoothed_mdm = np.full(n, np.nan)

    smoothed_tr[period] = np.sum(tr[1:period + 1])
    smoothed_pdm[period] = np.sum(plus_dm[1:period + 1])
    smoothed_mdm[period] = np.sum(minus_dm[1:period + 1])

    for i in range(period + 1, n):
        smoothed_tr[i] = smoothed_tr[i - 1] - (smoothed_tr[i - 1] / period) + tr[i]
        smoothed_pdm[i] = smoothed_pdm[i - 1] - (smoothed_pdm[i - 1] / period) + plus_dm[i]
        smoothed_mdm[i] = smoothed_mdm[i - 1] - (smoothed_mdm[i - 1] / period) + minus_dm[i]

    plus_di = np.full(n, np.nan)
    minus_di = np.full(n, np.nan)
    dx = np.full(n, np.nan)

    for i in range(period, n):
        if smoothed_tr[i] > 0:
            plus_di[i] = 100.0 * (smoothed_pdm[i] / smoothed_tr[i])
            minus_di[i] = 100.0 * (smoothed_mdm[i] / smoothed_tr[i])
            di_sum = plus_di[i] + minus_di[i]
            if di_sum > 0:
                dx[i] = 100.0 * abs(plus_di[i] - minus_di[i]) / di_sum

    adx = np.full(n, np.nan)
    adx_start = 2 * period - 1
    if n > adx_start:
        valid_dx = [x for x in dx[period:adx_start + 1] if not np.isnan(x)]
        if valid_dx:
            adx[adx_start] = np.mean(valid_dx)
            for i in range(adx_start + 1, n):
                if not np.isnan(dx[i]):
                    adx[i] = (adx[i - 1] * (period - 1) + dx[i]) / period

    di_gap = plus_di - minus_di

    return (
        pd.Series(adx, index=df.index),
        pd.Series(plus_di, index=df.index),
        pd.Series(minus_di, index=df.index),
        pd.Series(di_gap, index=df.index)
    )


def calculate_relative_alpha(stock_df: pd.DataFrame, benchmark_df: pd.DataFrame, window: int = 63) -> float:
    """Calculate 63-session cumulative percentage-point alpha vs benchmark.

    Args:

        stock_df: Stock DataFrame containing Date and Close sorted by Date.
        benchmark_df: Benchmark DataFrame containing Date and Close.
        window: Lookback session window (default 63).

    Returns:

        Alpha in percentage points (e.g. +5.20 pp).
    """
    merged = pd.merge(stock_df[["Date", "Close"]], benchmark_df[["Date", "Close"]], on="Date", suffixes=("_stock", "_bench"))
    merged = merged.sort_values("Date").dropna().reset_index(drop=True)

    if len(merged) < window + 1:
        return 0.0

    stk_start = merged["Close_stock"].iloc[-(window + 1)]
    stk_end = merged["Close_stock"].iloc[-1]
    stk_ret = ((stk_end - stk_start) / stk_start) * 100.0

    bm_start = merged["Close_bench"].iloc[-(window + 1)]
    bm_end = merged["Close_bench"].iloc[-1]
    bm_ret = ((bm_end - bm_start) / bm_start) * 100.0

    alpha_pp = stk_ret - bm_ret
    return round(float(alpha_pp), 2)


def calculate_swing_levels(df: pd.DataFrame, window: int = 20) -> Tuple[float, float]:
    """Calculate 20-session swing-low support and swing-high resistance.

    Args:

        df: DataFrame containing High and Low sorted by Date ascending.
        window: Lookback window (default 20).

    Returns:

        Tuple of (swing_low_support, swing_high_resistance).
    """
    if len(df) < window:
        sub = df
    else:
        sub = df.tail(window)

    support = float(sub["Low"].min())
    resistance = float(sub["High"].max())

    return round(support, 2), round(resistance, 2)


def compute_ticker_indicators(ticker_df: pd.DataFrame, benchmark_df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
    """Compute full suite of technical indicators for a single ticker.

    Args:

        ticker_df: DataFrame with OHLCV data for ticker.
        benchmark_df: DataFrame with OHLCV data for benchmark index.
        config: System configuration dictionary.

    Returns:

        Dictionary containing latest indicator values and trend status.
    """
    df = ticker_df.sort_values("Date").reset_index(drop=True)
    bm_df = benchmark_df.sort_values("Date").reset_index(drop=True)

    atr_s = calculate_atr(df, period=config.get("risk_rules", {}).get("atr_period", 14))
    rsi_s = calculate_rsi(df, period=14)
    adx_s, plus_di_s, minus_di_s, di_gap_s = calculate_adx_di(df, period=14)

    latest_idx = df.index[-1]
    latest_close = float(df["Close"].iloc[latest_idx])
    latest_atr = float(atr_s.iloc[latest_idx]) if not np.isnan(atr_s.iloc[latest_idx]) else 0.0
    latest_rsi = float(rsi_s.iloc[latest_idx]) if not np.isnan(rsi_s.iloc[latest_idx]) else 50.0

    latest_adx = float(adx_s.iloc[latest_idx]) if not np.isnan(adx_s.iloc[latest_idx]) else 0.0
    latest_plus_di = float(plus_di_s.iloc[latest_idx]) if not np.isnan(plus_di_s.iloc[latest_idx]) else 0.0
    latest_minus_di = float(minus_di_s.iloc[latest_idx]) if not np.isnan(minus_di_s.iloc[latest_idx]) else 0.0
    latest_di_gap = float(di_gap_s.iloc[latest_idx]) if not np.isnan(di_gap_s.iloc[latest_idx]) else 0.0

    di_gap_min = config.get("risk_rules", {}).get("di_gap_min", 2.0)
    trend = "Bullish" if latest_di_gap >= di_gap_min else "Bearish"

    rs_window = config.get("risk_rules", {}).get("rs_window", 63)
    alpha_pp = calculate_relative_alpha(df, bm_df, window=rs_window)

    support_20d, resistance_20d = calculate_swing_levels(df, window=20)

    return {
        "Ticker": df["Ticker"].iloc[0] if "Ticker" in df.columns else "UNKNOWN",
        "Date": str(df["Date"].iloc[latest_idx]),
        "Close": round(latest_close, 2),
        "ATR_14": round(latest_atr, 2),
        "RSI_14": round(latest_rsi, 2),
        "ADX_14": round(latest_adx, 2),
        "Plus_DI": round(latest_plus_di, 2),
        "Minus_DI": round(latest_minus_di, 2),
        "DI_Gap": round(latest_di_gap, 2),
        "Trend": trend,
        "Alpha_63d_PP": alpha_pp,
        "Support_20D": support_20d,
        "Resistance_20D": resistance_20d
    }
