"""
Unit Test Suite for Phase 5 Performance Attribution & Efficient Frontier Engines.
"""

import pytest
import numpy as np
import pandas as pd

from core.performance import calculate_period_performance_metrics
from core.frontier import (
    optimize_gmvp_long_only, optimize_gmvp_bounded, optimize_tangency_portfolio,
    calculate_effective_number_of_stocks, compute_efficient_frontier_curve
)


def test_performance_ratios_math():
    """Verify Sharpe, Treynor, Jensen, and Sortino calculations."""
    dates = pd.date_range("2026-01-01", periods=100)
    np.random.seed(42)

    p_ret = pd.Series(np.random.normal(0.001, 0.01, 100), index=dates)
    m_ret = pd.Series(np.random.normal(0.0008, 0.012, 100), index=dates)

    res = calculate_period_performance_metrics(
        p_ret, m_ret, rf_annual=0.0448, one_year_beta=1.1,
        is_live=False, start_date_str="2026-01-01", end_date_str="2026-04-10"
    )

    assert "Sharpe (portfolio, Nifty)" in res
    assert "Treynor (portfolio, Nifty)" in res
    assert "Jensen's alpha annualised" in res
    assert "Sortino (portfolio, Nifty)" in res
    assert res["Sessions"] == 100


def test_sortino_dash_when_no_losing_days():
    """Verify Sortino ratio displays '-' when there are zero losing days."""
    dates = pd.date_range("2026-01-01", periods=30)
    # Strictly positive daily returns -> no losing days
    p_ret = pd.Series(np.full(30, 0.005), index=dates)
    m_ret = pd.Series(np.full(30, 0.003), index=dates)

    res = calculate_period_performance_metrics(
        p_ret, m_ret, rf_annual=0.0448, one_year_beta=1.0,
        start_date_str="2026-01-01", end_date_str="2026-01-30"
    )

    assert res["Sortino (portfolio, Nifty)"].startswith("- /") or "-" in res["Sortino (portfolio, Nifty)"]


def test_gmvp_bounds_and_sum():
    """Verify GMVP long-only and bounded weights sum to 1.0 and respect bounds."""
    np.random.seed(42)
    cov = np.cov(np.random.normal(0, 0.02, (250, 8)), rowvar=False) * 252.0

    w_lo = optimize_gmvp_long_only(cov)
    assert abs(np.sum(w_lo) - 1.0) < 1e-4
    assert (w_lo >= -1e-6).all()

    w_bd = optimize_gmvp_bounded(cov, 0.05, 0.15)
    assert abs(np.sum(w_bd) - 1.0) < 1e-4
    for w in w_bd:
        assert 0.049 <= w <= 0.151


def test_tangency_max_sharpe():
    """Verify Tangency portfolio achieves higher Sharpe ratio than equal weights."""
    np.random.seed(42)
    mu = np.array([0.15, 0.18, 0.12, 0.22, 0.10, 0.14, 0.20, 0.16])
    cov = np.cov(np.random.normal(0, 0.02, (250, 8)), rowvar=False) * 252.0
    rf = 0.0448

    w_tangency = optimize_tangency_portfolio(mu, cov, rf)
    w_equal = np.full(8, 0.125)

    s_tangency = (w_tangency @ mu - rf) / np.sqrt(w_tangency.T @ cov @ w_tangency)
    s_equal = (w_equal @ mu - rf) / np.sqrt(w_equal.T @ cov @ w_equal)

    assert s_tangency >= s_equal - 1e-4


def test_effective_number_of_stocks():
    """Verify N_eff calculation."""
    # Equal 8 stocks -> N_eff should be 8.0
    w_eq = np.full(8, 0.125)
    assert calculate_effective_number_of_stocks(w_eq) == 8.0

    # 1 concentrated stock -> N_eff should be 1.0
    w_conc = np.array([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    assert calculate_effective_number_of_stocks(w_conc) == 1.0
