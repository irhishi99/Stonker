"""
Core Stop-Loss Management Engine.
Calculates 5x ATR stop-loss, applies 20-session support level adjustments,
enforces upward trailing rules, generates method labels, and computes aggregate portfolio risk.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple


def calculate_stop_loss(price: float,
                        atr: float,
                        support: float,
                        prev_stop: float = 0.0,
                        atr_multiple: float = 5.0,
                        support_buffer_atr: float = 1.0) -> Tuple[float, str, float]:
    """Calculate effective stop-loss, method label, and percentage below price.

    Args:

        price: Current stock price.
        atr: ATR(14) value.
        support: 20-session swing-low support price.
        prev_stop: Previously established stop-loss price (0.0 if new).
        atr_multiple: Multiple of ATR to subtract (default 5.0).
        support_buffer_atr: ATR window buffer below raw stop to check support (default 1.0).

    Returns:

        Tuple of (effective_stop_price, method_label, pct_below_price).
    """
    raw_stop = price - (atr_multiple * atr)
    calc_stop = raw_stop
    is_support_adjusted = False

    # Check if support level lies within 1 ATR below raw stop
    # condition: (raw_stop - support_buffer_atr * atr) <= support <= raw_stop
    if (raw_stop - (support_buffer_atr * atr)) <= support <= raw_stop and support > 0:
        calc_stop = support - 0.01
        is_support_adjusted = True

    # Enforce upward trailing rule
    if prev_stop > 0 and prev_stop > calc_stop:
        effective_stop = prev_stop
        label = "Trailed (prev. stop)"
    elif is_support_adjusted:
        effective_stop = calc_stop
        label = "Support-adjusted"
    else:
        effective_stop = calc_stop
        label = "5 x ATR"

    # Ensure stop does not exceed current price
    effective_stop = min(price - 0.01, effective_stop)
    effective_stop = max(0.01, round(effective_stop, 2))

    pct_below = round(((price - effective_stop) / price) * 100.0, 2)
    return effective_stop, label, pct_below


def calculate_portfolio_still_at_risk(holdings_df: pd.DataFrame) -> float:
    """Calculate aggregate dollar value still at risk if every stop-loss is hit.

    Args:

        holdings_df: DataFrame containing Shares, Price, Stop_Loss columns.

    Returns:

        Total amount in INR still at risk across all holdings.
    """
    if holdings_df is None or holdings_df.empty:
        return 0.0

    risk_per_stock = holdings_df["Shares"] * (holdings_df["Price"] - holdings_df["Stop_Loss"])
    # Ignore negative risk if price < stop
    total_risk = float(np.maximum(0.0, risk_per_stock).sum())
    return round(total_risk, 2)
