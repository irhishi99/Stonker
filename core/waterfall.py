"""
Core Reserve Replacement Waterfall Engine.
Executes replacement logic on stop-loss breaches and evaluates reserve queue eligibility.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple
from core.screens import evaluate_stock_screens


def evaluate_reserve_candidate(ticker: str,
                                sector: str,
                                fund_df: pd.DataFrame,
                                equity_df: pd.DataFrame,
                                config: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    """Evaluate whether a reserve queue candidate qualifies for portfolio entry today.

    Args:

        ticker: Reserve candidate ticker.
        sector: Sector classification.
        fund_df: Fundamentals DataFrame.
        equity_df: Daily equity OHLCV DataFrame.
        config: System configuration dict.

    Returns:

        Tuple of (is_eligible: bool, plain_english_reason: str, metrics_dict).
    """
    # Filter ticker price history
    t_df = equity_df[equity_df["Ticker"] == ticker].sort_values("Date").reset_index(drop=True)

    # Criterion 3: 1 year of prices (>= 200 trading sessions)
    if len(t_df) < 200:
        reason = f"FAIL: Insufficient price history ({len(t_df)} sessions < 200 required)."
        return False, reason, {"history_sessions": len(t_df)}

    # Filter fundamentals
    f_sub = fund_df[fund_df["Ticker"] == ticker]
    if f_sub.empty:
        reason = "FAIL: Missing fundamental data."
        return False, reason, {}

    f_row = f_sub.iloc[0]

    # Calculate 63-session median turnover
    turnover_cr = (t_df.tail(63)["Turnover"].median() / 1e7) if len(t_df) >= 10 else 0.0
    f_row_copy = f_row.copy()
    f_row_copy["Median_Turnover_Cr"] = turnover_cr

    # Criterion 1: Hard fundamentals screen
    screen_res = evaluate_stock_screens(f_row_copy, sector)
    if not screen_res["Hard_Pass"]:
        failures = "; ".join(screen_res["Hard_Failures"])
        reason = f"FAIL: Hard fundamental screen failed ({failures})."
        return False, reason, screen_res

    # Criterion 4: Median turnover >= 5 Cr/day
    if turnover_cr < 5.0:
        reason = f"FAIL: Median turnover Rs {turnover_cr:.2f} Cr/day < Rs 5.0 Cr threshold."
        return False, reason, screen_res

    # Criterion 5: Latest quarter profit up YoY (> 0%)
    yoy_p = float(f_row.get("YoY_Profit_Growth_Pct", 0.0))
    if yoy_p <= 0.0:
        reason = f"FAIL: YoY profit growth {yoy_p:.1f}% <= 0.0%."
        return False, reason, screen_res

    # Criterion 2: DI gap >= 2
    from core.indicators import calculate_adx_di
    _, _, _, di_gap_s = calculate_adx_di(t_df, period=14)
    latest_di_gap = float(di_gap_s.iloc[-1]) if not np.isnan(di_gap_s.iloc[-1]) else 0.0

    if latest_di_gap < 2.0:
        reason = f"FAIL: DI gap {latest_di_gap:.2f} < +2.0 (Bearish / Weak trend)."
        return False, reason, {"DI_Gap": latest_di_gap}

    reason = f"PASS: Eligible for immediate purchase (DI gap: +{latest_di_gap:.2f}, Turnover: Rs {turnover_cr:.2f} Cr, YoY Profit: +{yoy_p:.1f}%)."
    return True, reason, {"DI_Gap": latest_di_gap, "Turnover_Cr": turnover_cr, "YoY_Profit": yoy_p}


def execute_reserve_waterfall(stopped_ticker: str,
                              sold_tickers_history: List[str],
                              reserve_queue: List[Dict[str, str]],
                              current_invested: List[Dict[str, Any]],
                              fund_df: pd.DataFrame,
                              equity_df: pd.DataFrame,
                              config: Dict[str, Any]) -> Dict[str, Any]:
    """Execute reserve replacement waterfall logic when a stock hits stop-loss.

    Args:

        stopped_ticker: Ticker symbol of stopped out stock.
        sold_tickers_history: List of previously sold tickers (never return).
        reserve_queue: List of reserve ticker metadata dicts.
        current_invested: List of current invested ticker metadata dicts.
        fund_df: Fundamentals DataFrame.
        equity_df: Daily equity OHLCV DataFrame.
        config: System configuration dict.

    Returns:

        Dict with outcome ("RESERVE_BUY", "HOLDING_TOPUP", "LIQUID_CASH"), selected_ticker, reason.
    """
    all_sold = set(sold_tickers_history + [stopped_ticker])

    # Step 1: Check reserve queue in order
    for res_meta in reserve_queue:
        r_ticker = res_meta["symbol"]
        r_sector = res_meta.get("sector", "Capital Goods & EPC")

        if r_ticker in all_sold:
            continue

        is_qual, reason_msg, _ = evaluate_reserve_candidate(r_ticker, r_sector, fund_df, equity_df, config)
        if is_qual:
            return {
                "Outcome": "RESERVE_BUY",
                "Selected_Ticker": r_ticker,
                "Reason": f"Replaced {stopped_ticker} with reserve {r_ticker}. {reason_msg}"
            }

    # Step 2: Fallback 1 - Top up existing invested holdings in uptrend under 15% cap
    from core.indicators import calculate_adx_di
    uptrend_candidates = []

    for inv in current_invested:
        sym = inv["symbol"]
        if sym in all_sold:
            continue
        cur_w = float(inv.get("weight", 0.10))
        if cur_w >= 0.15:
            continue

        t_df = equity_df[equity_df["Ticker"] == sym].sort_values("Date").reset_index(drop=True)
        if not t_df.empty:
            _, _, _, di_gap_s = calculate_adx_di(t_df, period=14)
            latest_gap = float(di_gap_s.iloc[-1]) if not np.isnan(di_gap_s.iloc[-1]) else 0.0
            if latest_gap >= 2.0:
                uptrend_candidates.append((sym, cur_w, latest_gap))

    if uptrend_candidates:
        # Pick candidate with lowest current weight
        uptrend_candidates.sort(key=lambda x: x[1])
        topup_sym = uptrend_candidates[0][0]
        return {
            "Outcome": "HOLDING_TOPUP",
            "Selected_Ticker": topup_sym,
            "Reason": f"No qualified reserve available. Top up existing holding {topup_sym} (in uptrend DI gap >= 2) under 15% cap."
        }

    # Step 3: Fallback 2 - Liquid ETF / Cash
    return {
        "Outcome": "LIQUID_CASH",
        "Selected_Ticker": "NIPPON_LIQUID_BEES",
        "Reason": f"No reserve or existing holding qualified for top-up. Proceeds held in Liquid Fund / Cash."
    }


def generate_reserve_status_report(reserve_queue: List[Dict[str, str]],
                                   fund_df: pd.DataFrame,
                                   equity_df: pd.DataFrame,
                                   config: Dict[str, Any]) -> pd.DataFrame:
    """Generate 'Would be bought today?' status report for all reserve candidates.

    Args:

        reserve_queue: List of reserve queue ticker dicts.
        fund_df: Fundamentals DataFrame.
        equity_df: Equity OHLCV DataFrame.
        config: System configuration dict.

    Returns:

        DataFrame with Ticker, Sector, Would_Be_Bought_Today, Reason.
    """
    records = []
    for res_meta in reserve_queue:
        sym = res_meta["symbol"]
        sec = res_meta.get("sector", "Capital Goods & EPC")
        is_qual, reason, _ = evaluate_reserve_candidate(sym, sec, fund_df, equity_df, config)

        records.append({
            "Ticker": sym,
            "Sector": sec,
            "Would_Be_Bought_Today": "YES" if is_qual else "NO",
            "Reason": reason
        })

    return pd.DataFrame(records)
