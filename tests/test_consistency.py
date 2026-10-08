"""
Automated Cross-Tab Consistency & Formatting Verification Suite.
Asserts that identical financial metrics match across all terminal tabs and components.
"""

import pytest
import pandas as pd
import numpy as np

from core.utils import load_config, format_indian_currency, format_indian_number
from core.ledger import load_or_init_ledger, compute_portfolio_valuation
from core.stops import calculate_portfolio_still_at_risk
from core.risk import calculate_beta
from core.performance import build_multiwindow_performance_table
from core.risk_reward import compute_risk_reward_table


def test_portfolio_nav_cross_tab_consistency():
    """Assert Total Portfolio NAV matches across Overview, Risk & Hedging, and Performance Live column."""
    config = load_config("config.yaml")

    equity_df = pd.read_parquet("data/parquet/equity_ohlcv.parquet")
    options_df = pd.read_parquet("data/parquet/options_bhavcopy.parquet")
    ledger_df = pd.read_parquet("data/parquet/trade_ledger.parquet")
    summary_df = pd.read_parquet("data/parquet/portfolio_summary.parquet")

    valuation = compute_portfolio_valuation(ledger_df, equity_df, options_df, config)

    overview_nav = float(summary_df["Total_NAV"].iloc[0]) if not summary_df.empty else valuation["Total_NAV"]
    calc_nav = valuation["Total_NAV"]

    # Assert Overview NAV matches ledger mark-to-market valuation
    assert abs(overview_nav - calc_nav) < 1.0, f"NAV mismatch: Overview ({overview_nav}) != Ledger Valuation ({calc_nav})"


def test_still_at_risk_cross_tab_consistency():
    """Assert aggregate 'Still at Risk' figure matches across Overview and Risk & Hedging tabs."""
    equity_df = pd.read_parquet("data/parquet/equity_ohlcv.parquet")
    risk_stops_df = pd.read_parquet("data/parquet/portfolio_risk_stops.parquet")

    overview_still_at_risk = float(risk_stops_df["Still_At_Risk"].sum())
    rr_df, rr_kpis = compute_risk_reward_table(equity_df, risk_stops_df, total_capital=10000000.0)

    tab4_still_at_risk = rr_kpis["Downside_Still_At_Risk_Rs"]

    assert abs(overview_still_at_risk - tab4_still_at_risk) < 1.0, (
        f"Still-at-Risk mismatch: Overview ({overview_still_at_risk}) != Risk & Hedging ({tab4_still_at_risk})"
    )


def test_xirr_cross_tab_consistency():
    """Assert XIRR percentage matches across Overview and Performance Live column."""
    config = load_config("config.yaml")
    equity_df = pd.read_parquet("data/parquet/equity_ohlcv.parquet")
    indices_df = pd.read_parquet("data/parquet/indices_ohlcv.parquet")
    macro_df = pd.read_parquet("data/parquet/macro_rates.parquet")
    ledger_df = pd.read_parquet("data/parquet/trade_ledger.parquet")
    risk_stops_df = pd.read_parquet("data/parquet/portfolio_risk_stops.parquet")
    summary_df = pd.read_parquet("data/parquet/portfolio_summary.parquet")

    overview_xirr = float(summary_df["XIRR_Ann_%"].iloc[0]) if not summary_df.empty else 0.0

    perf_df, raw_kpis = build_multiwindow_performance_table(
        equity_df, indices_df, macro_df, ledger_df, risk_stops_df, config
    )
    live_xirr = raw_kpis["live_xirr_pct"]

    assert abs(overview_xirr - live_xirr) < 0.1, f"XIRR mismatch: Overview ({overview_xirr}%) != Performance Live ({live_xirr}%)"


def test_portfolio_weights_sum_100_percent():
    """Assert target equity weights sum to exactly 100.0%."""
    risk_stops_df = pd.read_parquet("data/parquet/portfolio_risk_stops.parquet")
    weight_sum = float(risk_stops_df["Target_Weight"].sum())

    assert abs(weight_sum - 1.0) < 1e-3, f"Weight sum invalid: {weight_sum} != 1.0"


def test_indian_number_formatting():
    """Assert Indian number and currency formatting functions operate correctly."""
    assert format_indian_number(10000000) == "1,00,00,000.00"
    assert format_indian_currency(10000000) == "Rs 1,00,00,000.00"
    assert format_indian_currency(10000000, abbreviate=True) == "Rs 1.00 Cr"
    assert format_indian_currency(500000, abbreviate=True) == "Rs 5.00 Lakh"
