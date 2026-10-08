"""
Schema validation unit tests for all generated Parquet datasets.
"""

import os
import pandas as pd
import pytest


def test_equity_ohlcv_schema():
    """Validate schema of equity_ohlcv.parquet."""
    path = "data/parquet/equity_ohlcv.parquet"
    assert os.path.exists(path), f"Parquet file missing at {path}"

    df = pd.read_parquet(path)
    expected_cols = ["Date", "Ticker", "Open", "High", "Low", "Close", "Adj_Close", "Volume", "Turnover", "Split_Factor", "Dividend_Amount"]

    for col in expected_cols:
        assert col in df.columns, f"Missing column {col} in equity_ohlcv.parquet"

    assert len(df) > 0, "equity_ohlcv.parquet is empty"


def test_indices_ohlcv_schema():
    """Validate schema of indices_ohlcv.parquet."""
    path = "data/parquet/indices_ohlcv.parquet"
    assert os.path.exists(path), f"Parquet file missing at {path}"

    df = pd.read_parquet(path)
    expected_cols = ["Date", "Index_Name", "Open", "High", "Low", "Close", "Daily_Return"]

    for col in expected_cols:
        assert col in df.columns, f"Missing column {col} in indices_ohlcv.parquet"

    assert len(df) > 0, "indices_ohlcv.parquet is empty"


def test_fundamentals_schema():
    """Validate schema of fundamentals.parquet."""
    path = "data/parquet/fundamentals.parquet"
    assert os.path.exists(path), f"Parquet file missing at {path}"

    df = pd.read_parquet(path)
    expected_cols = [
        "Ticker", "Sector", "Market_Cap_Cr", "ROCE_Pct", "OPM_Pct",
        "Debt_To_Equity", "Interest_Coverage", "OCF_Cr", "YoY_Profit_Growth_Pct",
        "Pledged_Pct", "Fetch_Date", "Data_Source"
    ]

    for col in expected_cols:
        assert col in df.columns, f"Missing column {col} in fundamentals.parquet"

    assert len(df) == 15, f"Expected 15 fundamental records, got {len(df)}"


def test_macro_rates_schema():
    """Validate schema of macro_rates.parquet."""
    path = "data/parquet/macro_rates.parquet"
    assert os.path.exists(path), f"Parquet file missing at {path}"

    df = pd.read_parquet(path)
    expected_cols = ["Date", "Liquid_Fund_NAV", "Nifty_1D_Rate_Index", "GSec_10Y_Yield_Pct", "Brent_Crude_USD"]

    for col in expected_cols:
        assert col in df.columns, f"Missing column {col} in macro_rates.parquet"

    assert len(df) > 0, "macro_rates.parquet is empty"


def test_options_bhavcopy_schema():
    """Validate schema of options_bhavcopy.parquet."""
    path = "data/parquet/options_bhavcopy.parquet"
    assert os.path.exists(path), f"Parquet file missing at {path}"

    df = pd.read_parquet(path)
    expected_cols = [
        "Date", "Symbol", "Expiry", "Strike", "Option_Type", "Open", "High", "Low",
        "Close", "Volume", "Open_Interest", "Implied_Volatility", "Underlying_Spot", "Lot_Size"
    ]

    for col in expected_cols:
        assert col in df.columns, f"Missing column {col} in options_bhavcopy.parquet"

    assert len(df) > 0, "options_bhavcopy.parquet is empty"
