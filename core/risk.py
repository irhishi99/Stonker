"""
Core Risk Analytics and CAPM Engine.
Computes annualised volatility, Beta vs Nifty 500 TRI, risk-free rate,
CAPM expected return, and 3-month quarterly return projection.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple


def calculate_daily_log_returns(series: pd.Series) -> pd.Series:
    """Compute log returns of a price series.

    Args:

        series: Price series.

    Returns:

        Log returns series.
    """
    return np.log(series / series.shift(1)).dropna()


def calculate_annualised_volatility(df: pd.DataFrame) -> float:
    """Calculate 1-year annualised volatility from daily close prices.

    Args:

        df: DataFrame containing Close sorted by Date.

    Returns:

        Annualised volatility as a decimal (e.g. 0.185 for 18.5%).
    """
    if len(df) < 2:
        return 0.0
    log_ret = calculate_daily_log_returns(df["Close"])
    daily_vol = float(log_ret.std())
    ann_vol = daily_vol * np.sqrt(252)
    return round(float(ann_vol), 4)


def calculate_beta(stock_df: pd.DataFrame, benchmark_df: pd.DataFrame) -> float:
    """Calculate Beta relative to benchmark using 1-year daily log returns.

    Args:

        stock_df: Stock DataFrame containing Date and Close.
        benchmark_df: Benchmark DataFrame containing Date and Close.

    Returns:

        Beta float value.
    """
    merged = pd.merge(stock_df[["Date", "Close"]], benchmark_df[["Date", "Close"]], on="Date", suffixes=("_stock", "_bench"))
    merged = merged.sort_values("Date").dropna().reset_index(drop=True)

    if len(merged) < 20:
        return 1.0

    stk_ret = calculate_daily_log_returns(merged["Close_stock"])
    bm_ret = calculate_daily_log_returns(merged["Close_bench"])

    common_idx = stk_ret.index.intersection(bm_ret.index)
    stk_ret = stk_ret.loc[common_idx]
    bm_ret = bm_ret.loc[common_idx]

    cov_matrix = np.cov(stk_ret, bm_ret)
    cov_stk_bm = cov_matrix[0, 1]
    var_bm = cov_matrix[1, 1]

    if var_bm == 0:
        return 1.0

    beta = cov_stk_bm / var_bm
    return round(float(beta), 3)


def calculate_risk_free_rate(macro_df: pd.DataFrame, config: Dict[str, Any]) -> float:
    """Calculate annualised risk-free rate rf from last quarter Nifty 1D Rate / Liquid Fund.

    Args:

        macro_df: Macro DataFrame containing Date, Nifty_1D_Rate_Index or Liquid_Fund_NAV.
        config: System configuration dictionary.

    Returns:

        Annualised risk-free rate decimal (e.g. 0.065 for 6.5%).
    """
    gsec_default = config.get("market_parameters", {}).get("gsec_10y_yield_default", 0.068)

    if macro_df is None or macro_df.empty or len(macro_df) < 63:
        return gsec_default

    df = macro_df.sort_values("Date").reset_index(drop=True)

    if "Nifty_1D_Rate_Index" in df.columns:
        series = df["Nifty_1D_Rate_Index"]
    elif "Liquid_Fund_NAV" in df.columns:
        series = df["Liquid_Fund_NAV"]
    else:
        return gsec_default

    quarter_sub = series.tail(63)
    val_start = quarter_sub.iloc[0]
    val_end = quarter_sub.iloc[-1]

    if val_start <= 0:
        return gsec_default

    quarter_ret = (val_end - val_start) / val_start
    # Annualise 63-session (~1 quarter) return
    ann_rf = ((1.0 + quarter_ret) ** (252.0 / 63.0)) - 1.0
    return round(float(max(0.02, min(0.12, ann_rf))), 4)


def compute_capm_expected_return(beta: float, rf: float, erp: float = 0.0708) -> Tuple[float, float]:
    """Compute CAPM annual expected return and 3-month quarterly expected return.

    Args:

        beta: Stock Beta vs benchmark.
        rf: Risk-free rate (annual decimal).
        erp: Equity Risk Premium (default 7.08% = 0.0708).

    Returns:

        Tuple of (annual_expected_return_pct, quarterly_expected_return_pct).
    """
    ann_er = rf + (beta * erp)
    quarterly_er = ((1.0 + ann_er) ** 0.25) - 1.0

    return round(float(ann_er * 100.0), 2), round(float(quarterly_er * 100.0), 2)
