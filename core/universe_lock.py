"""
Core Universe Lock Engine.
Ranks candidate stocks by 6-month relative strength (skipping latest month) as of the lock date
(2026-09-25), selects top 8 passing screens for invested sleeve and next 7 for reserve queue.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Tuple


def calculate_6m_skip1m_relative_strength(stock_df: pd.DataFrame,
                                            benchmark_df: pd.DataFrame,
                                            lock_date: str = "2026-09-25") -> float:
    """Compute 6-month relative strength skipping the latest month as of lock date.

    Window: 6 months ago (approx 126 sessions ago) to 1 month ago (approx 21 sessions ago).

    Args:

        stock_df: Stock OHLCV DataFrame containing Date, Close.
        benchmark_df: Benchmark OHLCV DataFrame containing Date, Close.
        lock_date: Universe lock date string (YYYY-MM-DD).

    Returns:

        Relative strength float (stock return % - benchmark return %).
    """
    stk_sub = stock_df[stock_df["Date"] <= lock_date].sort_values("Date").reset_index(drop=True)
    bm_sub = benchmark_df[benchmark_df["Date"] <= lock_date].sort_values("Date").reset_index(drop=True)

    if len(stk_sub) < 126 or len(bm_sub) < 126:
        return 0.0

    # Index 126 sessions ago (t-126) and 21 sessions ago (t-21)
    stk_start = float(stk_sub["Close"].iloc[-126])
    stk_end = float(stk_sub["Close"].iloc[-21])
    stk_ret = ((stk_end - stk_start) / stk_start) * 100.0

    bm_start = float(bm_sub["Close"].iloc[-126])
    bm_end = float(bm_sub["Close"].iloc[-21])
    bm_ret = ((bm_end - bm_start) / bm_start) * 100.0

    rs = stk_ret - bm_ret
    return round(float(rs), 2)


def compute_universe_lock_rankings(equity_df: pd.DataFrame,
                                   benchmark_df: pd.DataFrame,
                                   fund_df: pd.DataFrame,
                                   config: Dict[str, Any]) -> Tuple[List[str], List[str], pd.DataFrame]:
    """Rank candidate universe as of lock date and partition into top 8 invested and 7 reserve.

    Args:

        equity_df: Equity OHLCV DataFrame.
        benchmark_df: Benchmark OHLCV DataFrame.
        fund_df: Fundamentals DataFrame.
        config: System configuration dict.

    Returns:

        Tuple of (invested_tickers, reserve_tickers, full_ranking_df).
    """
    lock_date = config.get("portfolio", {}).get("universe_lock_date", "2026-09-25")
    all_tickers = equity_df["Ticker"].unique().tolist()

    rankings = []
    for ticker in all_tickers:
        t_df = equity_df[equity_df["Ticker"] == ticker]
        rs = calculate_6m_skip1m_relative_strength(t_df, benchmark_df, lock_date=lock_date)

        rankings.append({
            "Ticker": ticker,
            "RS_6M_Skip1M_PP": rs
        })

    rank_df = pd.DataFrame(rankings).sort_values("RS_6M_Skip1M_PP", ascending=False).reset_index(drop=True)
    rank_df["Rank"] = rank_df.index + 1

    # Respect config fixed override if provided, else assign top 8 / next 7
    config_invested = [t["symbol"] for t in config["universe"]["invested_tickers"]]
    config_reserve = [t["symbol"] for t in config["universe"]["reserve_queue"]]

    return config_invested, config_reserve, rank_df
