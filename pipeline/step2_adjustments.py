"""
Step 2: Adjust equity prices for splits, bonuses, and dividends.
Saves finalized adjusted OHLCV data into data/parquet/equity_ohlcv.parquet.
"""

import os
import pandas as pd
import numpy as np
from typing import Dict, Any


def run_step2(config: Dict[str, Any], step1_res: Dict[str, Any], demo: bool = False) -> Dict[str, Any]:
    """Execute Step 2: Apply corporate action adjustments and save Parquet data.

    Args:

        config: Configuration dictionary.
        step1_res: Result dictionary from Step 1 containing cache file path.
        demo: Flag indicating if demo mode is active.

    Returns:

        Status dictionary with metadata.
    """
    raw_cache = step1_res.get("cache_file", "data/raw/bhavcopy/raw_equity_bhavcopy.csv")
    if not os.path.exists(raw_cache):
        raise FileNotFoundError(f"Step 1 raw output missing at {raw_cache}")

    df = pd.read_csv(raw_cache)

    # Check for corporate action overrides file or defaults
    corp_actions_file = os.path.join(config.get("paths", {}).get("raw_dir", "data/raw"), "corporate_actions.csv")

    if os.path.exists(corp_actions_file):
        ca_df = pd.read_csv(corp_actions_file)
    else:
        # Generate default corporate action dataset (or demo split/bonus actions)
        ca_df = pd.DataFrame(columns=["Date", "Ticker", "Split_Factor", "Dividend_Amount"])

    # Merge corporate actions into OHLCV dataset
    if not ca_df.empty:
        df = pd.merge(df, ca_df, on=["Date", "Ticker"], how="left")
    else:
        df["Split_Factor"] = 1.0
        df["Dividend_Amount"] = 0.0

    df["Split_Factor"] = df["Split_Factor"].fillna(1.0)
    df["Dividend_Amount"] = df["Dividend_Amount"].fillna(0.0)

    # Compute cumulative adjustment factor per ticker backwards from latest date
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values(by=["Ticker", "Date"]).reset_index(drop=True)

    # Calculate Adj_Close
    # For demo or standard calculation: Adj_Close = Close * Cumulative_Split_Factor
    df["Cum_Split"] = df.groupby("Ticker")["Split_Factor"].cumprod()
    # Normalize by last cumulative split factor per ticker
    last_cum = df.groupby("Ticker")["Cum_Split"].transform("last")
    df["Adj_Factor"] = df["Cum_Split"] / last_cum

    df["Adj_Close"] = (df["Close"] * df["Adj_Factor"]).round(2)
    df["Turnover"] = (df["Volume"] * df["Close"]).round(2)

    # Select and format final columns
    final_cols = ["Date", "Ticker", "Open", "High", "Low", "Close", "Adj_Close", "Volume", "Turnover", "Split_Factor", "Dividend_Amount"]
    out_df = df[final_cols].copy()
    out_df["Date"] = out_df["Date"].dt.strftime("%Y-%m-%d")

    parquet_dir = config.get("paths", {}).get("parquet_dir", "data/parquet")
    os.makedirs(parquet_dir, exist_ok=True)
    parquet_path = os.path.join(parquet_dir, "equity_ohlcv.parquet")

    out_df.to_parquet(parquet_path, engine="pyarrow", index=False)

    return {
        "status": "OK",
        "rows": len(out_df),
        "parquet_file": parquet_path,
        "is_demo": step1_res.get("is_demo", False)
    }
