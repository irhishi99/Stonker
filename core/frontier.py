"""
Core Modern Portfolio Theory (MPT) Efficient Frontier & Portfolio Optimization Engine.
Computes Long-Only Efficient Frontier, GMVP (long-only & 5-15% limits), Tangency Portfolio,
CML & CAL lines, and Effective Number of Stocks N_eff = 1/sum(w^2).
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from typing import Dict, Any, List, Tuple


def compute_portfolio_mean_and_cov(equity_df: pd.DataFrame,
                                    invested_tickers: List[str]) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """Compute 1-year annualised mean returns and covariance matrix for invested tickers.

    Args:

        equity_df: Equity OHLCV DataFrame.
        invested_tickers: List of 8 invested stock symbols.

    Returns:

        Tuple of (mean returns array mu, covariance matrix cov, active tickers list).
    """
    piv = equity_df.pivot(index="Date", columns="Ticker", values="Close")[invested_tickers].dropna()
    log_ret = np.log(piv / piv.shift(1)).dropna()

    mu = log_ret.mean().values * 252.0  # Annualised mean returns
    cov = log_ret.cov().values * 252.0   # Annualised covariance matrix

    return mu, cov, list(piv.columns)


def optimize_gmvp_long_only(cov: np.ndarray) -> np.ndarray:
    """Solve for Global Minimum Variance Portfolio (Long-Only: w_i >= 0, sum w_i = 1).

    Args:

        cov: Covariance matrix.

    Returns:

        Weight vector summing to 1.0.
    """
    n = cov.shape[0]
    initial_w = np.full(n, 1.0 / n)
    bounds = [(0.0, 1.0) for _ in range(n)]
    constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}]

    res = minimize(lambda w: w.T @ cov @ w, initial_w, method='SLSQP', bounds=bounds, constraints=constraints)
    w = res.x if res.success else initial_w
    return w / np.sum(w)


def optimize_gmvp_bounded(cov: np.ndarray, min_w: float = 0.05, max_w: float = 0.15) -> np.ndarray:
    """Solve for GMVP under 5-15% weight limits.

    Args:

        cov: Covariance matrix.
        min_w: Min weight bound (0.05).
        max_w: Max weight bound (0.15).

    Returns:

        Weight vector summing to 1.0.
    """
    n = cov.shape[0]
    initial_w = np.full(n, 1.0 / n)
    bounds = [(min_w, max_w) for _ in range(n)]
    constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}]

    res = minimize(lambda w: w.T @ cov @ w, initial_w, method='SLSQP', bounds=bounds, constraints=constraints)
    w = res.x if res.success else initial_w
    return w / np.sum(w)


def optimize_tangency_portfolio(mu: np.ndarray, cov: np.ndarray, rf: float = 0.0448) -> np.ndarray:
    """Solve for Maximum Sharpe Ratio Tangency Portfolio (Long-Only).

    Args:

        mu: Annualised mean returns vector.
        cov: Covariance matrix.
        rf: Risk-free rate.

    Returns:

        Weight vector summing to 1.0.
    """
    n = len(mu)
    initial_w = np.full(n, 1.0 / n)
    bounds = [(0.0, 1.0) for _ in range(n)]
    constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}]

    def neg_sharpe(w):
        port_ret = w @ mu
        port_vol = np.sqrt(w.T @ cov @ w)
        if port_vol <= 0:
            return 1e6
        return -(port_ret - rf) / port_vol

    res = minimize(neg_sharpe, initial_w, method='SLSQP', bounds=bounds, constraints=constraints)
    w = res.x if res.success else initial_w
    return w / np.sum(w)


def compute_efficient_frontier_curve(mu: np.ndarray, cov: np.ndarray, num_points: int = 50) -> Tuple[np.ndarray, np.ndarray]:
    """Compute Long-Only Efficient Frontier points (Volatility, Return).

    Args:

        mu: Mean returns vector.
        cov: Covariance matrix.
        num_points: Number of frontier points (default 50).

    Returns:

        Tuple of (vols_array, rets_array).
    """
    n = len(mu)
    gmvp_w = optimize_gmvp_long_only(cov)
    min_ret = float(gmvp_w @ mu)
    max_ret = float(np.max(mu))

    target_rets = np.linspace(min_ret, max_ret, num_points)
    frontier_vols = []
    frontier_rets = []

    for r_target in target_rets:
        bounds = [(0.0, 1.0) for _ in range(n)]
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0},
            {'type': 'eq', 'fun': lambda w, r=r_target: (w @ mu) - r}
        ]
        res = minimize(lambda w: w.T @ cov @ w, gmvp_w, method='SLSQP', bounds=bounds, constraints=constraints)
        if res.success:
            vol = np.sqrt(res.x.T @ cov @ res.x)
            frontier_vols.append(vol)
            frontier_rets.append(r_target)

    return np.array(frontier_vols), np.array(frontier_rets)


def calculate_effective_number_of_stocks(weights: np.ndarray) -> float:
    """Calculate Effective Number of Stocks N_eff = 1 / sum(w^2).

    Args:

        weights: Weight vector.

    Returns:

        N_eff float value.
    """
    sum_sq = np.sum(weights ** 2)
    return round(float(1.0 / sum_sq), 2) if sum_sq > 0 else 1.0


def compute_frontier_summary_table(equity_df: pd.DataFrame,
                                     risk_stops_df: pd.DataFrame,
                                     rf: float = 0.0448) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """Compute GMVP vs Our Weights Summary Table and Weights Comparison Matrix.

    Args:

        equity_df: Equity OHLCV DataFrame.
        risk_stops_df: Risk & Stops DataFrame from Step 8.
        rf: Risk-free rate.

    Returns:

        Tuple of (Summary Table DataFrame, Weights Comparison DataFrame, Plotly Data Dict).
    """
    invested = [t["symbol"] for t in config["universe"]["invested_tickers"]] if "config" in globals() else list(risk_stops_df["Ticker"].unique())
    mu, cov, active_tickers = compute_portfolio_mean_and_cov(equity_df, invested)

    # Weights
    w_our = risk_stops_df["Target_Weight"].values if not risk_stops_df.empty else np.full(len(active_tickers), 1.0/len(active_tickers))
    w_our = w_our / np.sum(w_our)

    w_gmvp_lo = optimize_gmvp_long_only(cov)
    w_gmvp_bd = optimize_gmvp_bounded(cov, 0.05, 0.15)
    w_tangency = optimize_tangency_portfolio(mu, cov, rf)

    def eval_p(w, name):
        r = float(w @ mu)
        v = float(np.sqrt(w.T @ cov @ w))
        s = (r - rf) / v if v > 0 else 0.0
        neff = calculate_effective_number_of_stocks(w)
        return {
            "Portfolio": name,
            "Volatility (%)": round(v * 100.0, 2),
            "Past-Year Mean Return (%)": round(r * 100.0, 2),
            "Sharpe Ratio": round(s, 2),
            "Effective No. of Stocks": neff
        }

    summary_records = [
        eval_p(w_our, "Our ERC Portfolio (5-15%)"),
        eval_p(w_gmvp_lo, "GMVP Long-Only"),
        eval_p(w_gmvp_bd, "GMVP Bounded (5-15%)"),
        eval_p(w_tangency, "Tangency Portfolio (Max Sharpe)")
    ]

    summary_df = pd.DataFrame(summary_records)

    # Weights comparison table
    w_comp_df = pd.DataFrame({
        "Stock": active_tickers,
        "Our ERC Weight (%)": (w_our * 100).round(2),
        "GMVP Long-Only (%)": (w_gmvp_lo * 100).round(2),
        "GMVP Bounded 5-15% (%)": (w_gmvp_bd * 100).round(2),
        "Tangency (Max Sharpe) (%)": (w_tangency * 100).round(2)
    })

    # Efficient Frontier Curve
    f_vols, f_rets = compute_efficient_frontier_curve(mu, cov)

    plot_data = {
        "mu": mu, "cov": cov, "active_tickers": active_tickers,
        "w_our": w_our, "w_gmvp_lo": w_gmvp_lo, "w_gmvp_bd": w_gmvp_bd, "w_tangency": w_tangency,
        "f_vols": f_vols, "f_rets": f_rets, "rf": rf
    }

    return summary_df, w_comp_df, plot_data
