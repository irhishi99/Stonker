"""
Core Performance Attribution & Performance Window Analysis Engine.
Computes risk-adjusted performance metrics, Sharpe, Sortino, Treynor, Jensen's Alpha,
Max Drawdown, Capture Ratios, Tracking Error, Information Ratio, and Multi-Window tables.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Union
from core.ledger import solve_xirr


def calculate_period_performance_metrics(p_returns: pd.Series,
                                         m_returns: pd.Series,
                                         rf_annual: float,
                                         one_year_beta: float,
                                         is_live: bool = False,
                                         start_date_str: str = "",
                                         end_date_str: str = "",
                                         live_nav: float = 0.0,
                                         initial_capital: float = 10000000.0) -> Dict[str, Any]:
    """Calculate comprehensive performance metrics over a given return series window.

    Args:

        p_returns: Portfolio daily returns series.
        m_returns: Benchmark daily returns series.
        rf_annual: Risk-free rate (annual decimal e.g. 0.0448).
        one_year_beta: 1-year daily beta for fallback when n < 20.
        is_live: True if evaluating live ledger portfolio performance.
        start_date_str: Window start date string.
        end_date_str: Window end date string.
        live_nav: Live ending NAV amount in INR.
        initial_capital: Starting capital base in INR.

    Returns:

        Dict of metrics formatted for performance table display.
    """
    merged = pd.concat([p_returns, m_returns], axis=1, keys=["port", "bm"]).dropna()
    n = len(merged)

    if n == 0:
        return {}

    r_p_series = merged["port"]
    r_m_series = merged["bm"]

    # Compounded Period Returns
    if is_live and live_nav > 0:
        r_p_period = (live_nav - initial_capital) / initial_capital
    else:
        r_p_period = float(np.prod(1.0 + r_p_series.values) - 1.0)

    r_m_period = float(np.prod(1.0 + r_m_series.values) - 1.0)
    excess_period = r_p_period - r_m_period

    # Annualization
    ann_factor = 252.0 / max(1, n)
    r_p_ann_comp = ((1.0 + r_p_period) ** ann_factor) - 1.0
    r_p_ann_simple = r_p_period * ann_factor
    compounding_effect = r_p_ann_comp - r_p_ann_simple

    r_m_ann_comp = ((1.0 + r_m_period) ** ann_factor) - 1.0

    # Volatilities
    p_vol_ann = float(r_p_series.std() * np.sqrt(252))
    m_vol_ann = float(r_m_series.std() * np.sqrt(252))

    # Beta decision: if n < 20 sessions, use 1-year beta
    if n < 20:
        beta = one_year_beta
        beta_source = "1-Year Daily Returns (n < 20 sessions)"
    else:
        cov_val = np.cov(r_p_series, r_m_series)[0, 1]
        var_bm = np.var(r_m_series)
        beta = float(cov_val / var_bm) if var_bm > 0 else one_year_beta
        beta_source = "Window Returns (n >= 20 sessions)"

    # Sharpe Ratios
    sharpe_p = (r_p_ann_comp - rf_annual) / p_vol_ann if p_vol_ann > 0 else 0.0
    sharpe_m = (r_m_ann_comp - rf_annual) / m_vol_ann if m_vol_ann > 0 else 0.0

    # Treynor Ratios
    treynor_p = (r_p_ann_comp - rf_annual) / beta if beta != 0 else 0.0
    treynor_m = (r_m_ann_comp - rf_annual) / 1.0  # Benchmark beta = 1.0

    # Jensen's Alpha
    jensen_ann = r_p_ann_comp - (rf_annual + beta * (r_m_ann_comp - rf_annual))
    rf_period = ((1.0 + rf_annual) ** (n / 252.0)) - 1.0
    jensen_period = r_p_period - (rf_period + beta * (r_m_period - rf_period))

    # XIRR
    cfs_p = [(start_date_str, -initial_capital), (end_date_str, initial_capital * (1.0 + r_p_period))]
    cfs_m = [(start_date_str, -initial_capital), (end_date_str, initial_capital * (1.0 + r_m_period))]
    xirr_p = solve_xirr(cfs_p)
    xirr_m = solve_xirr(cfs_m)

    # Sortino Ratios (Downside vol)
    losing_days = r_p_series[r_p_series < 0]
    m_losing_days = r_m_series[r_m_series < 0]

    if len(losing_days) == 0:
        sortino_p_str = "-"
    else:
        downside_vol_p = float(np.sqrt(np.mean(losing_days**2)) * np.sqrt(252))
        sortino_p_val = (r_p_ann_comp - rf_annual) / downside_vol_p if downside_vol_p > 0 else 0.0
        sortino_p_str = f"{sortino_p_val:.2f}"

    if len(m_losing_days) == 0:
        sortino_m_str = "-"
    else:
        downside_vol_m = float(np.sqrt(np.mean(m_losing_days**2)) * np.sqrt(252))
        sortino_m_val = (r_m_ann_comp - rf_annual) / downside_vol_m if downside_vol_m > 0 else 0.0
        sortino_m_str = f"{sortino_m_val:.2f}"

    # Max Drawdowns
    def get_max_drawdown(series: pd.Series) -> float:
        cum = np.cumprod(1.0 + series.values)
        peaks = np.maximum.accumulate(cum)
        dd = (cum - peaks) / peaks
        return float(np.min(dd)) if len(dd) > 0 else 0.0

    mdd_p = get_max_drawdown(r_p_series) * 100.0
    mdd_m = get_max_drawdown(r_m_series) * 100.0

    # Capture Ratios
    up_days = merged[merged["bm"] > 0]
    down_days = merged[merged["bm"] < 0]

    if len(up_days) > 0 and up_days["bm"].mean() != 0:
        up_capture = float((up_days["port"].mean() / up_days["bm"].mean()) * 100.0)
    else:
        up_capture = 100.0

    if len(down_days) > 0 and down_days["bm"].mean() != 0:
        down_capture = float((down_days["port"].mean() / down_days["bm"].mean()) * 100.0)
    else:
        down_capture = 100.0

    # Tracking Error & Information Ratio
    active_diff = r_p_series - r_m_series
    tracking_error = float(active_diff.std() * np.sqrt(252) * 100.0)
    ann_excess = (r_p_ann_comp - r_m_ann_comp) * 100.0
    info_ratio = ann_excess / tracking_error if tracking_error > 0 else 0.0

    return {
        "Start": start_date_str,
        "End": end_date_str,
        "Sessions": n,
        "Portfolio return": f"{r_p_period * 100:.2f}%",
        "Nifty 500 TRI return": f"{r_m_period * 100:.2f}%",
        "Excess return": f"{excess_period * 100:+.2f}%",
        "Portfolio annualised compounded": f"{r_p_ann_comp * 100:.2f}%",
        "Portfolio annualised simple": f"{r_p_ann_simple * 100:.2f}%",
        "Compounding effect": f"{compounding_effect * 100:+.2f}%",
        "Nifty 500 annualised": f"{r_m_ann_comp * 100:.2f}%",
        "Risk-free 1D rate": f"{rf_annual * 100:.2f}%",
        "Portfolio volatility": f"{p_vol_ann * 100:.2f}%",
        "Nifty 500 volatility": f"{m_vol_ann * 100:.2f}%",
        "Beta vs Nifty 500": f"{beta:.3f}",
        "Beta estimated from": beta_source,
        "Sharpe (portfolio, Nifty)": f"{sharpe_p:.2f} / {sharpe_m:.2f}",
        "Treynor (portfolio, Nifty)": f"{treynor_p * 100:.2f}% / {treynor_m * 100:.2f}%",
        "Jensen's alpha annualised": f"{jensen_ann * 100:+.2f}%",
        "Jensen's alpha over the period": f"{jensen_period * 100:+.2f}%",
        "XIRR (portfolio, Nifty)": f"{xirr_p * 100:.2f}% / {xirr_m * 100:.2f}%",
        "Sortino (portfolio, Nifty)": f"{sortino_p_str} / {sortino_m_str}",
        "Max drawdown (portfolio, Nifty)": f"{mdd_p:.2f}% / {mdd_m:.2f}%",
        "Up-capture": f"{up_capture:.1f}%",
        "Down-capture": f"{down_capture:.1f}%",
        "Tracking error": f"{tracking_error:.2f}%",
        "Information ratio": f"{info_ratio:.2f}",
        "raw_p_period": r_p_period,
        "raw_xirr_p": xirr_p
    }


def build_multiwindow_performance_table(equity_df: pd.DataFrame,
                                          indices_df: pd.DataFrame,
                                          macro_df: pd.DataFrame,
                                          ledger_df: pd.DataFrame,
                                          risk_stops_df: pd.DataFrame,
                                          config: Dict[str, Any]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Build standardized 4-window Performance Attribution Table.

    Windows: Live since snapshot, Last quarter (63s), 6-month backtest (126s), 1-year backtest (252s).

    Args:

        equity_df: Equity OHLCV DataFrame.
        indices_df: Indices OHLCV DataFrame.
        macro_df: Macro & Rates DataFrame.
        ledger_df: Trade Ledger DataFrame.
        risk_stops_df: Risk & Stops DataFrame from Step 8.
        config: System configuration dict.

    Returns:

        Tuple of (Performance DataFrame, Raw KPI dict for assertions).
    """
    invested = [t["symbol"] for t in config["universe"]["invested_tickers"]]
    weights = risk_stops_df["Target_Weight"].values if not risk_stops_df.empty else np.full(8, 0.125)

    piv_close = equity_df.pivot(index="Date", columns="Ticker", values="Close")[invested].dropna()
    stk_ret = np.log(piv_close / piv_close.shift(1)).dropna()
    port_ret = (stk_ret * weights).sum(axis=1)

    bm_name = config.get("indices", {}).get("benchmark", "Nifty 500 TRI")
    bm_close = indices_df[indices_df["Index_Name"] == bm_name].set_index("Date")["Close"]
    if bm_close.empty:
        bm_close = indices_df[indices_df["Index_Name"] == "Nifty 50 Spot"].set_index("Date")["Close"]
    bm_ret = np.log(bm_close / bm_close.shift(1)).dropna()

    # 1-year beta
    cov_val = np.cov(port_ret.tail(252), bm_ret.tail(252))[0, 1]
    var_bm = np.var(bm_ret.tail(252))
    one_year_beta = float(cov_val / var_bm) if var_bm > 0 else 1.0

    rf_ann = 0.0448
    snap_date = config["portfolio"]["snapshot_date"]
    latest_date = equity_df["Date"].max()

    # Calculate Live NAV from ledger valuation
    stock_buys = ledger_df[ledger_df["Instrument_Type"] == "EQUITY"]["Total_Cost"].sum()
    opt_buys = ledger_df[ledger_df["Instrument_Type"] == "OPTION"]["Total_Cost"].sum()
    cash_bal = 10000000.0 - stock_buys - opt_buys

    # Live NAV
    snap_eq = equity_df[equity_df["Date"] == latest_date]
    latest_prices = dict(zip(snap_eq["Ticker"], snap_eq["Close"]))
    stock_mtm = sum(row["Shares"] * latest_prices.get(row["Ticker"], 500.0) for _, row in risk_stops_df.iterrows())
    live_nav = stock_mtm + opt_buys + cash_bal

    # Window 1: Live since snapshot
    live_p_ret = port_ret[port_ret.index >= snap_date]
    live_m_ret = bm_ret[bm_ret.index >= snap_date]
    if live_p_ret.empty:
        live_p_ret = port_ret.tail(5)
        live_m_ret = bm_ret.tail(5)

    w1 = calculate_period_performance_metrics(
        live_p_ret, live_m_ret, rf_ann, one_year_beta, is_live=True,
        start_date_str=snap_date, end_date_str=latest_date, live_nav=live_nav
    )

    # Window 2: Last quarter (63 sessions)
    w2 = calculate_period_performance_metrics(
        port_ret.tail(63), bm_ret.tail(63), rf_ann, one_year_beta,
        start_date_str=str(port_ret.tail(63).index[0]), end_date_str=latest_date
    )

    # Window 3: 6-month backtest (126 sessions)
    w3 = calculate_period_performance_metrics(
        port_ret.tail(126), bm_ret.tail(126), rf_ann, one_year_beta,
        start_date_str=str(port_ret.tail(126).index[0]), end_date_str=latest_date
    )

    # Window 4: 1-year backtest (252 sessions)
    w4 = calculate_period_performance_metrics(
        port_ret.tail(252), bm_ret.tail(252), rf_ann, one_year_beta,
        start_date_str=str(port_ret.tail(252).index[0]), end_date_str=latest_date
    )

    metrics_list = [
        "Start", "End", "Sessions", "Portfolio return", "Nifty 500 TRI return", "Excess return",
        "Portfolio annualised compounded", "Portfolio annualised simple", "Compounding effect",
        "Nifty 500 annualised", "Risk-free 1D rate", "Portfolio volatility", "Nifty 500 volatility",
        "Beta vs Nifty 500", "Beta estimated from", "Sharpe (portfolio, Nifty)", "Treynor (portfolio, Nifty)",
        "Jensen's alpha annualised", "Jensen's alpha over the period", "XIRR (portfolio, Nifty)",
        "Sortino (portfolio, Nifty)", "Max drawdown (portfolio, Nifty)", "Up-capture", "Down-capture",
        "Tracking error", "Information ratio"
    ]

    rows = []
    for m in metrics_list:
        rows.append({
            "Performance Metric": m,
            "Live since snapshot": w1.get(m, "-"),
            "Last quarter (63s)": w2.get(m, "-"),
            "6-Month Backtest": w3.get(m, "-"),
            "1-Year Backtest": w4.get(m, "-")
        })

    perf_df = pd.DataFrame(rows)

    raw_kpis = {
        "live_portfolio_return_pct": w1.get("raw_p_period", 0.0) * 100.0,
        "live_xirr_pct": w1.get("raw_xirr_p", 0.0) * 100.0,
        "live_sessions": w1.get("Sessions", 0)
    }

    return perf_df, raw_kpis
