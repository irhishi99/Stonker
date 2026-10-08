"""
Step 7: Compute Technical Indicators, 63-Day Alpha, Fundamental Screens, and Universe Lock.
Outputs calculations into data/parquet/technical_indicators.parquet.
"""

import os
import pandas as pd
import numpy as np
from typing import Dict, Any

from core.indicators import compute_ticker_indicators
from core.screens import run_fundamental_screens
from core.universe_lock import compute_universe_lock_rankings


def run_step7(config: Dict[str, Any], demo: bool = False) -> Dict[str, Any]:
    """Execute Step 7: Technical indicators, 63d alpha, fundamental screens.

    Args:

        config: System configuration dictionary.
        demo: Flag for synthetic mode.

    Returns:

        Status dictionary with metadata.
    """
    parquet_dir = config.get("paths", {}).get("parquet_dir", "data/parquet")
    output_dir = config.get("paths", {}).get("output_dir", "output")

    equity_df = pd.read_parquet(os.path.join(parquet_dir, "equity_ohlcv.parquet"))
    indices_df = pd.read_parquet(os.path.join(parquet_dir, "indices_ohlcv.parquet"))
    fund_df = pd.read_parquet(os.path.join(parquet_dir, "fundamentals.parquet"))

    bm_name = config.get("indices", {}).get("benchmark", "Nifty 500 TRI")
    bm_df = indices_df[indices_df["Index_Name"] == bm_name].sort_values("Date").reset_index(drop=True)
    if bm_df.empty:
        bm_df = indices_df[indices_df["Index_Name"] == "Nifty 50 Spot"].sort_values("Date").reset_index(drop=True)

    # 1. Fundamental Screens
    eval_df, exc_bullets = run_fundamental_screens(fund_df, equity_df, output_dir=output_dir)

    # 2. Indicators per stock
    all_tickers = equity_df["Ticker"].unique()
    indicator_records = []

    for ticker in all_tickers:
        t_df = equity_df[equity_df["Ticker"] == ticker].sort_values("Date").reset_index(drop=True)
        ind_dict = compute_ticker_indicators(t_df, bm_df, config)
        indicator_records.append(ind_dict)

    ind_df = pd.DataFrame(indicator_records)
    out_parquet = os.path.join(parquet_dir, "technical_indicators.parquet")
    ind_df.to_parquet(out_parquet, engine="pyarrow", index=False)

    # 3. Universe Lock Rankings
    inv, res, rank_df = compute_universe_lock_rankings(equity_df, bm_df, fund_df, config)
    rank_df.to_csv(os.path.join(output_dir, "universe_lock_rankings.csv"), index=False)

    return {
        "status": "OK",
        "tickers_computed": len(ind_df),
        "screen_exceptions": len(exc_bullets),
        "parquet_file": out_parquet,
        "is_demo": demo
    }
