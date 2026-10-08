"""
Core Equal Risk Contribution (ERC) Weighting Module.
Optimizes equity weights to equalize risk contributions using scipy SLSQP
subject to 5%-15% weight bounds and sums to 100% of equity sleeve.
Calculates whole share allocations based on snapshot prices.
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from typing import Dict, Any, List, Tuple


def compute_covariance_matrix(equity_df: pd.DataFrame, tickers: List[str]) -> Tuple[np.ndarray, List[str]]:
    """Compute 1-year daily log-return covariance matrix for tickers.

    Args:

        equity_df: Equity OHLCV DataFrame containing Date, Ticker, Close.
        tickers: List of ticker symbols.

    Returns:

        Tuple of (N x N covariance matrix, active ticker list).
    """
    piv = equity_df.pivot(index="Date", columns="Ticker", values="Close")
    active_tickers = [t for t in tickers if t in piv.columns]
    piv = piv[active_tickers].dropna()

    log_returns = np.log(piv / piv.shift(1)).dropna()
    cov_matrix = log_returns.cov().values * 252.0  # Annualised covariance

    return cov_matrix, active_tickers


def erc_objective(weights: np.ndarray, cov: np.ndarray) -> float:
    """ERC objective function: sum of squared differences between relative risk contributions and 1/N.

    Args:

        weights: Portfolio weights vector (1D array).
        cov: Covariance matrix (2D array).

    Returns:

        Objective scalar value.
    """
    w = np.array(weights)
    port_var = float(w.T @ cov @ w)
    if port_var <= 0:
        return 1e6

    # Relative Risk Contribution: rRC_i = w_i * (cov @ w)_i / port_var
    marginal_contrib = cov @ w
    risk_contrib = w * marginal_contrib / port_var

    target_rc = 1.0 / len(w)
    return float(np.sum((risk_contrib - target_rc) ** 2))


def optimize_erc_weights(cov_matrix: np.ndarray,
                         weight_min: float = 0.05,
                         weight_max: float = 0.15) -> np.ndarray:
    """Solve for ERC portfolio weights via SLSQP under min/max weight bounds.

    Args:

        cov_matrix: N x N covariance matrix.
        weight_min: Minimum weight bound (default 0.05).
        weight_max: Maximum weight bound (default 0.15).

    Returns:

        Optimized weight vector summing to 1.0.
    """
    n = cov_matrix.shape[0]
    initial_w = np.full(n, 1.0 / n)

    bounds = [(weight_min, weight_max) for _ in range(n)]
    constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}]

    res = minimize(
        erc_objective,
        initial_w,
        args=(cov_matrix,),
        method='SLSQP',
        bounds=bounds,
        constraints=constraints,
        options={'ftol': 1e-9, 'maxiter': 500}
    )

    if not res.success:
        # Fallback to equal weights clipped within bounds if SLSQP fails
        w_raw = np.clip(initial_w, weight_min, weight_max)
        return w_raw / np.sum(w_raw)

    weights = res.x / np.sum(res.x)
    return weights


def calculate_portfolio_shares(tickers: List[str],
                               weights: np.ndarray,
                               latest_prices: Dict[str, float],
                               equity_capital: float) -> pd.DataFrame:
    """Calculate whole share allocations and actual invested values.

    Args:

        tickers: List of ticker symbols.
        weights: Array of target weights (summing to 1.0).
        latest_prices: Dict mapping ticker to snapshot close price.
        equity_capital: Total equity sleeve capital (e.g. Rs 97,00,000).

    Returns:

        DataFrame containing Ticker, Target_Weight, Price, Shares, Allocated_Value, Actual_Weight.
    """
    records = []
    total_allocated = 0.0

    for ticker, target_w in zip(tickers, weights):
        price = latest_prices.get(ticker, 1.0)
        target_val = equity_capital * target_w
        shares = int(target_val // price)
        alloc_val = round(shares * price, 2)
        total_allocated += alloc_val

        records.append({
            "Ticker": ticker,
            "Target_Weight": round(float(target_w), 4),
            "Price": round(float(price), 2),
            "Shares": shares,
            "Allocated_Value": alloc_val
        })

    df = pd.DataFrame(records)
    df["Actual_Weight"] = (df["Allocated_Value"] / equity_capital).round(4)
    return df
