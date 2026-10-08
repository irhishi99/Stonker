"""
Unit Test Suite for Phase 4 Regressions, Factor Models, Risk-Reward, and Hedge Scenarios.
"""

import pytest
import numpy as np
import pandas as pd

from core.regressions import run_ols_regression, compute_autocorrelation_diagnostics
from core.risk_reward import compute_risk_reward_table
from core.hedge_plan import generate_hedge_scenario_analysis, calculate_black_scholes_put_delta


def test_ols_regression_accuracy():
    """Verify OLS regression calculates alpha, beta, and R2 correctly."""
    np.random.seed(42)
    x = pd.Series(np.random.normal(0.001, 0.01, 100))
    # y = 0.0005 + 1.2 * x + noise
    y = 0.0005 + (1.2 * x) + pd.Series(np.random.normal(0, 0.002, 100))

    res = run_ols_regression(y, x)

    assert abs(res["beta"] - 1.2) < 0.15
    assert res["r_squared"] > 0.70
    assert res["n_obs"] == 100


def test_autocorrelation_and_ljung_box():
    """Verify AR(1) and Ljung-Box autocorrelation test."""
    np.random.seed(101)
    # White noise returns
    ret = pd.Series(np.random.normal(0, 0.01, 200))
    res = compute_autocorrelation_diagnostics(ret)

    assert "AR1_phi" in res
    assert "Ljung_Box_Q" in res
    assert "Summary_Sentence" in res


def test_risk_reward_table_exact_match():
    """Verify Risk-Reward calculation and exact aggregate still-at-risk match."""
    risk_stops_df = pd.DataFrame([
        {"Ticker": "STOCK_A", "Price": 100.0, "Shares": 1000, "Stop_Loss": 90.0, "Ann_Vol": 0.20, "Target_Weight": 0.50},
        {"Ticker": "STOCK_B", "Price": 200.0, "Shares": 500, "Stop_Loss": 180.0, "Ann_Vol": 0.25, "Target_Weight": 0.50}
    ])

    dates = pd.date_range("2026-01-01", periods=30)
    equity_df = pd.DataFrame({
        "Date": np.tile(dates, 2),
        "Ticker": ["STOCK_A"]*30 + ["STOCK_B"]*30,
        "Close": [100.0]*30 + [200.0]*30,
        "High": [105.0]*30 + [210.0]*30,
        "Low": [95.0]*30 + [190.0]*30
    })

    rr_df, summary_kpis = compute_risk_reward_table(equity_df, risk_stops_df, total_capital=10000000.0)

    # Risk STOCK_A: 1000 * (100-90) = 10,000
    # Risk STOCK_B: 500 * (200-180) = 10,000
    # Total Still At Risk = 20,000
    assert summary_kpis["Downside_Still_At_Risk_Rs"] == 20000.0

    # Ensure aggregate matches portfolio undiversified row exactly
    undiv_row = rr_df[rr_df["Stock"] == "PORTFOLIO (all stocks at once)"].iloc[0]
    assert undiv_row["Loss_Rs"] == 20000.0


def test_hedge_scenario_downside_capping():
    """Verify option hedge scenario analysis caps portfolio loss on market drops."""
    nifty_spot = 24500.0
    stock_val = 9700000.0
    beta_down = 1.15
    put_strike = 24000.0  # Slightly OTM
    put_premium = 250.0
    lots_held = 8

    scenarios = generate_hedge_scenario_analysis(
        nifty_spot, stock_val, beta_down, put_strike, put_premium, lots_held, 65, 10000000.0
    )

    # On -20% drop, hedged portfolio loss should be significantly smaller than unhedged loss
    drop_20 = scenarios[scenarios["Nifty Move (%)"] == -20.0].iloc[0]
    unhedged_loss = drop_20["Unhedged PnL (% of Capital)"]
    hedged_loss = drop_20["With Puts PnL (% of Capital)"]

    assert hedged_loss > unhedged_loss  # Less negative loss
    assert abs(hedged_loss) < 15.0      # Loss capped around ~8-12% vs -23% unhedged
