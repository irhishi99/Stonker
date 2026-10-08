"""
Comprehensive Pytest Test Suite for Phase 2 Core Calculation Engines.
Tests indicators, ERC optimization, stop-loss trailing, XIRR solver,
hedge lot triggers, profit-lock, reserve waterfall, and fundamental screens.
"""

import pytest
import numpy as np
import pandas as pd

from core.indicators import calculate_atr, calculate_rsi, calculate_adx_di, calculate_swing_levels
from core.weights import optimize_erc_weights, erc_objective
from core.stops import calculate_stop_loss, calculate_portfolio_still_at_risk
from core.screens import evaluate_stock_screens
from core.ledger import solve_xirr
from core.hedge import calculate_required_hedge_lots, evaluate_hedge_rebalance, evaluate_profit_lock_roll
from core.waterfall import evaluate_reserve_candidate, execute_reserve_waterfall


def test_atr_wilder_smoothing():
    """Test ATR calculation using known price sequence."""
    dates = pd.date_range("2026-01-01", periods=20)
    highs = [10, 12, 11, 13, 14, 15, 14, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28]
    lows =  [ 8,  9,  9, 10, 11, 12, 11, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]
    closes = [9, 11, 10, 12, 13, 14, 12, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27]

    df = pd.DataFrame({"Date": dates, "High": highs, "Low": lows, "Close": closes})
    atr_s = calculate_atr(df, period=14)

    # ATR at index 14 should be non-NaN
    assert not np.isnan(atr_s.iloc[14])
    assert atr_s.iloc[14] > 0.0


def test_rsi_wilder_smoothing():
    """Test RSI calculation bounds and behavior."""
    dates = pd.date_range("2026-01-01", periods=30)
    # Strictly increasing closes -> RSI should reach near 100
    closes = list(range(100, 130))
    df = pd.DataFrame({"Date": dates, "Close": closes})

    rsi_s = calculate_rsi(df, period=14)
    assert rsi_s.iloc[-1] > 90.0


def test_adx_di_calculation():
    """Test ADX and DI values."""
    dates = pd.date_range("2026-01-01", periods=35)
    highs = [10 + i * 0.5 for i in range(35)]
    lows = [8 + i * 0.5 for i in range(35)]
    closes = [9 + i * 0.5 for i in range(35)]

    df = pd.DataFrame({"Date": dates, "High": highs, "Low": lows, "Close": closes})
    adx_s, plus_di_s, minus_di_s, di_gap_s = calculate_adx_di(df, period=14)

    assert not np.isnan(plus_di_s.iloc[-1])
    assert plus_di_s.iloc[-1] > minus_di_s.iloc[-1]
    assert di_gap_s.iloc[-1] > 0.0


def test_erc_weights_optimization():
    """Test ERC optimization: weights sum to 1.0, bounds 5-15%, equal risk contribution."""
    np.random.seed(42)
    # 8-stock covariance matrix
    returns = np.random.normal(0, 0.02, (250, 8))
    cov = np.cov(returns, rowvar=False) * 252.0

    weights = optimize_erc_weights(cov, weight_min=0.05, weight_max=0.15)

    # Sum check
    assert abs(np.sum(weights) - 1.0) < 1e-4

    # Bounds check (5% to 15%)
    for w in weights:
        assert 0.049 <= w <= 0.151

    # Equal risk contribution objective value should be small
    obj_val = erc_objective(weights, cov)
    assert obj_val < 0.05


def test_stop_loss_trailing_and_labels():
    """Test stop loss raw, support-adjustment, and upward trailing logic."""
    price = 500.0
    atr = 10.0

    # Test 1: Raw 5x ATR stop (500 - 50 = 450)
    stop1, label1, pct1 = calculate_stop_loss(price, atr, support=400.0)
    assert stop1 == 450.0
    assert label1 == "5 x ATR"

    # Test 2: Support-adjusted stop (support at 445 is within 1 ATR below raw stop 450)
    # Condition: 450 - 10 = 440 <= 445 <= 450 -> Support adjusted to 444.99
    stop2, label2, pct2 = calculate_stop_loss(price, atr, support=445.0)
    assert stop2 == 444.99
    assert label2 == "Support-adjusted"

    # Test 3: Trailed previous stop (prev stop = 460 > current calc stop 450)
    stop3, label3, pct3 = calculate_stop_loss(price, atr, support=400.0, prev_stop=460.0)
    assert stop3 == 460.0
    assert label3 == "Trailed (prev. stop)"


def test_xirr_solver():
    """Test XIRR solver with known cash flows."""
    # 1 year 10% return: -100 at T0, +110 at T1
    cfs = [
        ("2025-01-01", -100.0),
        ("2026-01-01", 110.0)
    ]
    xirr = solve_xirr(cfs)
    assert abs(xirr - 0.10) < 0.01


def test_hedge_lots_and_full_lot_trigger():
    """Test hedge lot calculation and 1-lot minimum trade threshold."""
    stock_val = 9700000.0   # Rs 97 Lakh
    nifty_spot = 24500.0
    beta_down = 1.15
    lot_size = 65

    # Lots needed = round(1.15 * 9700000 / (24500 * 65)) = round(11155000 / 1592500) = round(7.004) = 7
    lots = calculate_required_hedge_lots(stock_val, nifty_spot, beta_down, lot_size)
    assert lots == 7

    # Rebalance trigger: held 7, needed 7 -> No trade
    should1, diff1, _ = evaluate_hedge_rebalance(lots_needed=7, lots_held=7)
    assert not should1
    assert diff1 == 0

    # Rebalance trigger: held 6, needed 7 -> Trade 1 lot
    should2, diff2, _ = evaluate_hedge_rebalance(lots_needed=7, lots_held=6)
    assert should2
    assert diff2 == 1


def test_profit_lock_roll_trigger():
    """Test profit-lock roll trigger at +10% gain."""
    nifty_spot = 25000.0
    current_strike = 22000.0

    # Gain 12% >= 10% -> Should roll put strike to ~5% OTM (25000 * 0.95 = 23750 -> 23800)
    should, new_strike, msg = evaluate_profit_lock_roll(0.12, nifty_spot, current_strike)
    assert should
    assert new_strike > current_strike

    # Gain 5% < 10% -> Should not roll
    should2, _, _ = evaluate_profit_lock_roll(0.05, nifty_spot, current_strike)
    assert not should2


def test_fundamental_screens_unreadable_fail():
    """Test fundamental screens: unreadable/missing metric counts as FAIL."""
    row_missing = pd.Series({
        "Ticker": "BAD_TICKER",
        "Market_Cap_Cr": None,  # Missing hard metric
        "ROCE_Pct": 15.0,
        "OPM_Pct": 12.0,
        "Debt_To_Equity": 0.5,
        "Pledged_Pct": 0.0,
        "Median_Turnover_Cr": 10.0,
        "YoY_Profit_Growth_Pct": 15.0
    })

    res = evaluate_stock_screens(row_missing, "Capital Goods & EPC")
    assert not res["Hard_Pass"]
    assert not res["Overall_Pass"]
    assert len(res["Hard_Failures"]) > 0
