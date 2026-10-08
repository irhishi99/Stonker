"""
Core Regressions, Factor Models, and Time-Series Autocorrelation Module.
Computes single-index models, benchmark comparison regressions, 4-factor capex model,
macro multi-factor model (Brent & G-Sec), and AR(1) / Ljung-Box autocorrelation diagnostics.
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import chi2
from typing import Dict, Any, List, Tuple


def run_ols_regression(y: pd.Series, x: pd.Series) -> Dict[str, Any]:
    """Run simple OLS regression y = alpha + beta * x.

    Args:

        y: Dependent variable series (returns).
        x: Independent variable series (benchmark returns).

    Returns:

        Dict with alpha_ann_pct, alpha_t, beta, beta_se, r_squared, n_obs, residual_std.
    """
    df = pd.concat([y, x], axis=1).dropna()
    if len(df) < 20:
        return {
            "alpha_ann_pct": 0.0, "alpha_t": 0.0, "beta": 1.0, "beta_se": 0.0,
            "r_squared": 0.0, "n_obs": len(df), "residual_std": 0.0
        }

    y_vals = df.iloc[:, 0].values
    x_vals = df.iloc[:, 1].values

    x_const = sm.add_constant(x_vals)
    model = sm.OLS(y_vals, x_const).fit()

    alpha_daily = model.params[0]
    beta = model.params[1]

    alpha_t = model.tvalues[0]
    beta_se = model.bse[1]
    r_squared = model.rsquared

    alpha_ann_pct = alpha_daily * 252.0 * 100.0
    res_std = float(np.std(model.resid))

    return {
        "alpha_ann_pct": round(float(alpha_ann_pct), 2),
        "alpha_t": round(float(alpha_t), 2),
        "beta": round(float(beta), 3),
        "beta_se": round(float(beta_se), 3),
        "r_squared": round(float(r_squared), 4),
        "n_obs": int(len(df)),
        "residual_std": res_std
    }


def compute_single_index_decomposition(equity_df: pd.DataFrame,
                                        benchmark_df: pd.DataFrame,
                                        invested_tickers: List[str],
                                        weights: np.ndarray) -> pd.DataFrame:
    """Compute single-index model risk decomposition for individual stocks and PORTFOLIO.

    Args:

        equity_df: Equity OHLCV DataFrame.
        benchmark_df: Benchmark OHLCV DataFrame.
        invested_tickers: List of invested stock symbols.
        weights: Array of portfolio weights.

    Returns:

        DataFrame with columns: Stock, Days, Alpha (ann. %), Alpha t, Beta, Beta s.e.,
        R-squared, Total vol, Systematic vol, Stock-specific vol.
    """
    piv = equity_df.pivot(index="Date", columns="Ticker", values="Close")[invested_tickers].dropna()
    stk_returns = np.log(piv / piv.shift(1)).dropna()

    bm_close = benchmark_df.set_index("Date")["Close"]
    bm_returns = np.log(bm_close / bm_close.shift(1)).dropna()

    bm_vol = float(bm_returns.std() * np.sqrt(252))

    records = []

    for ticker in invested_tickers:
        r_stock = stk_returns[ticker]
        res = run_ols_regression(r_stock, bm_returns)

        total_vol = float(r_stock.std() * np.sqrt(252) * 100.0)
        sys_vol = abs(res["beta"]) * bm_vol * 100.0
        idiosyncratic_vol = np.sqrt(max(0.0, total_vol**2 - sys_vol**2))

        records.append({
            "Stock": ticker,
            "Days": res["n_obs"],
            "Alpha (ann. %)": res["alpha_ann_pct"],
            "Alpha t": res["alpha_t"],
            "Beta": res["beta"],
            "Beta s.e.": res["beta_se"],
            "R-squared": res["r_squared"],
            "Total vol (%)": round(total_vol, 2),
            "Systematic vol (%)": round(sys_vol, 2),
            "Stock-specific vol (%)": round(idiosyncratic_vol, 2)
        })

    # Portfolio row
    port_returns = (stk_returns * weights).sum(axis=1)
    port_res = run_ols_regression(port_returns, bm_returns)
    port_total_vol = float(port_returns.std() * np.sqrt(252) * 100.0)
    port_sys_vol = abs(port_res["beta"]) * bm_vol * 100.0
    port_idio_vol = np.sqrt(max(0.0, port_total_vol**2 - port_sys_vol**2))

    records.append({
        "Stock": "PORTFOLIO",
        "Days": port_res["n_obs"],
        "Alpha (ann. %)": port_res["alpha_ann_pct"],
        "Alpha t": port_res["alpha_t"],
        "Beta": port_res["beta"],
        "Beta s.e.": port_res["beta_se"],
        "R-squared": port_res["r_squared"],
        "Total vol (%)": round(port_total_vol, 2),
        "Systematic vol (%)": round(port_sys_vol, 2),
        "Stock-specific vol (%)": round(port_idio_vol, 2)
    })

    return pd.DataFrame(records)


def compute_benchmark_comparison_regressions(portfolio_returns: pd.Series,
                                               indices_df: pd.DataFrame,
                                               equity_df: pd.DataFrame) -> pd.DataFrame:
    """Regress portfolio returns on 10 index histories + Nifty 500 + Equal-weight Capex Universe.

    Args:

        portfolio_returns: Daily portfolio return series.
        indices_df: Indices OHLCV DataFrame.
        equity_df: Equity OHLCV DataFrame.

    Returns:

        DataFrame with Benchmark, Days, Beta, R-squared.
    """
    records = []

    # 1. Index histories
    piv_idx = indices_df.pivot(index="Date", columns="Index_Name", values="Close")
    idx_returns = np.log(piv_idx / piv_idx.shift(1)).dropna()

    for col in idx_returns.columns:
        res = run_ols_regression(portfolio_returns, idx_returns[col])
        records.append({
            "Benchmark": col,
            "Days": res["n_obs"],
            "Beta": res["beta"],
            "R-squared": res["r_squared"]
        })

    # 2. Equal-weight Capex Universe (all stocks in dataset)
    piv_all = equity_df.pivot(index="Date", columns="Ticker", values="Close")
    all_ret = np.log(piv_all / piv_all.shift(1)).dropna()
    eq_capex_ret = all_ret.mean(axis=1)

    res_capex = run_ols_regression(portfolio_returns, eq_capex_ret)
    records.append({
        "Benchmark": "Equal-Weight Capex Universe (15 Stocks)",
        "Days": res_capex["n_obs"],
        "Beta": res_capex["beta"],
        "R-squared": res_capex["r_squared"]
    })

    return pd.DataFrame(records)


def compute_4factor_capex_model(portfolio_returns: pd.Series,
                                indices_df: pd.DataFrame,
                                equity_df: pd.DataFrame) -> Tuple[pd.DataFrame, str, pd.DataFrame]:
    """Fit 4-Factor Capex Cycle Model: Market + Size + Momentum + Capex Factor.

    Args:

        portfolio_returns: Portfolio daily returns.
        indices_df: Indices OHLCV DataFrame.
        equity_df: Equity OHLCV DataFrame.

    Returns:

        Tuple of (Factor Loadings DataFrame, Warning Message, Factor Correlation Matrix DataFrame).
    """
    piv_idx = indices_df.pivot(index="Date", columns="Index_Name", values="Close")
    idx_ret = np.log(piv_idx / piv_idx.shift(1)).dropna()

    nifty500 = idx_ret.get("Nifty 500 TRI", idx_ret.get("Nifty 50 Spot"))
    smallcap = idx_ret.get("Nifty Smallcap 500", nifty500)
    momentum = idx_ret.get("Nifty500 Momentum 50", nifty500)

    piv_all = equity_df.pivot(index="Date", columns="Ticker", values="Close")
    capex_universe = np.log(piv_all / piv_all.shift(1)).dropna().mean(axis=1)

    # Construct Factor Returns
    f_market = nifty500
    f_size = smallcap - nifty500
    f_momentum = momentum - nifty500
    f_capex = capex_universe - nifty500

    factors_df = pd.concat([f_market, f_size, f_momentum, f_capex], axis=1, keys=["Market", "Size", "Momentum", "Capex"]).dropna()
    merged = pd.concat([portfolio_returns, factors_df], axis=1).dropna()

    y = merged.iloc[:, 0].values
    X = merged.iloc[:, 1:].values
    X_const = sm.add_constant(X)

    model = sm.OLS(y, X_const).fit()

    loadings = []
    factor_names = ["Intercept", "Market (Nifty 500)", "Size (Smallcap - N500)", "Momentum (Mom50 - N500)", "Capex (Universe - N500)"]
    for name, b, t in zip(factor_names, model.params, model.tvalues):
        loadings.append({
            "Factor": name,
            "Loading (Beta)": round(float(b), 4),
            "t-Statistic": round(float(t), 2),
            "Significant (|t| > 2)": "YES" if abs(t) > 2.0 else "NO"
        })

    loadings_df = pd.DataFrame(loadings)

    # Correlation Matrix Check
    corr_df = factors_df.corr().round(3)
    high_corrs = []
    for i in range(len(corr_df.columns)):
        for j in range(i + 1, len(corr_df.columns)):
            val = corr_df.iloc[i, j]
            if abs(val) > 0.7:
                high_corrs.append(f"{corr_df.columns[i]} vs {corr_df.columns[j]} (|r| = {abs(val):.2f} > 0.7)")

    if high_corrs:
        warning_msg = f"⚠️ WARNING: High factor multicollinearity detected! {'; '.join(high_corrs)}. Factor t-stats may be inflated."
    else:
        warning_msg = "✅ Factor correlation check passed (All pair-wise |r| <= 0.70)."

    return loadings_df, warning_msg, corr_df


def compute_macro_multifactor_model(portfolio_returns: pd.Series,
                                     indices_df: pd.DataFrame,
                                     macro_df: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
    """Fit Macro Multi-Factor Model: Market + Brent Crude Daily Change + 10Y G-Sec Price Return.

    Args:

        portfolio_returns: Portfolio daily returns.
        indices_df: Indices OHLCV DataFrame.
        macro_df: Macro & Rates DataFrame.

    Returns:

        Tuple of (Regression Summary DataFrame, One-Line Verdict String).
    """
    bm_close = indices_df[indices_df["Index_Name"] == "Nifty 500 TRI"].set_index("Date")["Close"]
    if bm_close.empty:
        bm_close = indices_df[indices_df["Index_Name"] == "Nifty 50 Spot"].set_index("Date")["Close"]
    bm_ret = np.log(bm_close / bm_close.shift(1)).dropna()

    m_df = macro_df.set_index("Date")
    brent_ret = m_df["Brent_Crude_USD"].pct_change().dropna()

    # 10Y G-Sec yield change -> price return approx = -7.0 * dy
    gsec_dy = m_df["GSec_10Y_Yield_Pct"].diff().dropna() / 100.0
    gsec_price_ret = -7.0 * gsec_dy

    factors = pd.concat([bm_ret, brent_ret, gsec_price_ret], axis=1, keys=["Market", "Crude", "GSec"]).dropna()
    merged = pd.concat([portfolio_returns, factors], axis=1).dropna()

    y = merged.iloc[:, 0].values
    X_single = sm.add_constant(merged["Market"].values)
    m_single = sm.OLS(y, X_single).fit()

    X_multi = sm.add_constant(merged[["Market", "Crude", "GSec"]].values)
    m_multi = sm.OLS(y, X_multi).fit()

    table_data = [{
        "Days": int(len(merged)),
        "Beta Market (t)": f"{m_multi.params[1]:.3f} (t={m_multi.tvalues[1]:.2f})",
        "Beta Crude (t)": f"{m_multi.params[2]:.4f} (t={m_multi.tvalues[2]:.2f})",
        "Beta G-Sec (t)": f"{m_multi.params[3]:.4f} (t={m_multi.tvalues[3]:.2f})",
        "R-squared Single": round(float(m_single.rsquared), 4),
        "R-squared Multi": round(float(m_multi.rsquared), 4),
        "Adjusted R-squared": round(float(m_multi.rsquared_adj), 4)
    }]

    t_crude = abs(m_multi.tvalues[2])
    t_gsec = abs(m_multi.tvalues[3])

    if t_crude > 2.0 and t_gsec > 2.0:
        verdict = "VERDICT: Both Brent Crude and 10Y G-Sec yields statistically significantly impact portfolio returns (|t| > 2.0)."
    elif t_crude > 2.0:
        verdict = "VERDICT: Brent Crude oil price changes significantly impact returns (|t| > 2.0), while 10Y G-Sec yields do not."
    elif t_gsec > 2.0:
        verdict = "VERDICT: 10Y G-Sec yield changes significantly impact returns (|t| > 2.0), while Brent Crude does not."
    else:
        verdict = "VERDICT: Neither Brent Crude nor 10Y G-Sec yields exert statistically significant incremental impact over the market (|t| <= 2.0)."

    return pd.DataFrame(table_data), verdict


def compute_autocorrelation_diagnostics(portfolio_returns: pd.Series) -> Dict[str, Any]:
    """Compute AR(1), Lags 1-5 autocorrelations, Ljung-Box test, and weekly lag-1 autocorrelation.

    Args:

        portfolio_returns: Daily portfolio return series.

    Returns:

        Dict with AR1_phi, AR1_t, autocorrelations list, significant_lags, ljung_box_q, ljung_box_p, weekly_autocorr, summary_sentence.
    """
    ret = portfolio_returns.dropna().values
    n = len(ret)

    if n < 30:
        return {"summary_sentence": "Insufficient data for autocorrelation analysis."}

    # AR(1) OLS
    y_ar = ret[1:]
    x_ar = sm.add_constant(ret[:-1])
    m_ar = sm.OLS(y_ar, x_ar).fit()

    phi = float(m_ar.params[1])
    phi_t = float(m_ar.tvalues[1])

    # Lags 1-5 Autocorrelation
    bounds = 1.96 / np.sqrt(n)
    autocorrs = []
    sig_lags = []

    for lag in range(1, 6):
        corr = float(pd.Series(ret).autocorr(lag=lag))
        autocorrs.append({"Lag": lag, "Autocorr": round(corr, 4), "Bound": round(bounds, 4)})
        if abs(corr) > bounds:
            sig_lags.append(lag)

    # Ljung-Box Test
    lb_res = sm.stats.acorr_ljungbox(ret, lags=[5], return_df=True)
    q_stat = float(lb_res["lb_stat"].iloc[0])
    p_val = float(lb_res["lb_pvalue"].iloc[0])

    # Weekly non-overlapping 5-day return autocorrelation
    weekly_rets = pd.Series(ret).groupby(np.arange(n) // 5).sum()
    weekly_ac = float(weekly_rets.autocorr(lag=1))

    if q_stat > 11.07:  # 5% chi-squared critical value for df=5
        summary = f"Reject Random Walk hypothesis at 5% level (Q={q_stat:.2f} > 11.07, p={p_val:.4f}). Significant serial dependency detected."
    else:
        summary = f"Accept Random Walk / Market Efficiency hypothesis at 5% level (Q={q_stat:.2f} <= 11.07, p={p_val:.4f}). Daily returns exhibit no significant serial correlation."

    return {
        "AR1_phi": round(phi, 4),
        "AR1_t": round(phi_t, 2),
        "Autocorrelations": pd.DataFrame(autocorrs),
        "Significant_Lags": sig_lags if sig_lags else "None",
        "Ljung_Box_Q": round(q_stat, 2),
        "Ljung_Box_P": round(p_val, 4),
        "Weekly_Lag1_Autocorr": round(weekly_ac, 4),
        "Summary_Sentence": summary
    }
