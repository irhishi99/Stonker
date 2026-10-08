"""
Core Downside Risk Hedging & Option Management Engine.
Calculates down-market portfolio beta, required Nifty put option lots,
enforces the 1-lot minimum trade trigger, and handles the +10% profit-lock roll logic.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple


def calculate_down_market_beta(portfolio_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """Calculate tail hedge ratio: portfolio beta on benchmark down-days (R_bm < 0).

    Args:

        portfolio_returns: Daily portfolio return series.
        benchmark_returns: Daily benchmark return series.

    Returns:

        Down-market Beta float value (defaults to 1.0 if insufficient down days).
    """
    merged = pd.concat([portfolio_returns, benchmark_returns], axis=1, keys=["port", "bm"]).dropna()
    down_days = merged[merged["bm"] < 0]

    if len(down_days) < 5:
        return 1.0

    cov_matrix = np.cov(down_days["port"], down_days["bm"])
    var_bm = cov_matrix[1, 1]

    if var_bm == 0:
        return 1.0

    beta_down = cov_matrix[0, 1] / var_bm
    return round(float(beta_down), 3)


def calculate_required_hedge_lots(stock_value: float,
                                  nifty_spot: float,
                                  beta_down: float,
                                  lot_size: int = 65) -> int:
    """Calculate target number of Nifty put option lots required.

    Args:

        stock_value: Total mark-to-market value of equity sleeve.
        nifty_spot: Current Nifty spot index level.
        beta_down: Tail hedge ratio.
        lot_size: Nifty contract lot size (default 65).

    Returns:

        Integer lot count.
    """
    if nifty_spot <= 0 or lot_size <= 0:
        return 0

    contract_value = nifty_spot * lot_size
    raw_lots = (beta_down * stock_value) / contract_value
    return int(round(raw_lots))


def evaluate_hedge_rebalance(lots_needed: int, lots_held: int) -> Tuple[bool, int, str]:
    """Check if hedge position rebalance is triggered based on 1-lot threshold.

    Args:

        lots_needed: Target option lots required.
        lots_held: Currently held option lots.

    Returns:

        Tuple of (should_trade: bool, lot_difference: int, action_reason: str).
    """
    diff = lots_needed - lots_held

    if abs(diff) >= 1:
        action = "BUY" if diff > 0 else "SELL"
        reason = f"Hedge gap {diff} lot(s) reaches full-lot threshold (Target: {lots_needed}, Held: {lots_held}). Action: {action} {abs(diff)} lot(s)."
        return True, diff, reason
    else:
        reason = f"Hedge gap ({diff} lot(s)) is less than 1 full lot. Maintain {lots_held} lots."
        return False, 0, reason


def evaluate_profit_lock_roll(portfolio_gain_pct: float,
                               nifty_spot: float,
                               current_strike: float,
                               trigger_pct: float = 0.10) -> Tuple[bool, float, str]:
    """Check if +10% profit-lock trigger is reached to roll puts to ~5% OTM strike.

    Args:

        portfolio_gain_pct: Cumulative portfolio gain percentage (e.g. +0.12 for +12%).
        nifty_spot: Current Nifty spot level.
        current_strike: Strike price of currently held puts.
        trigger_pct: Profit-lock trigger threshold (default 0.10 = 10%).

    Returns:

        Tuple of (should_roll: bool, target_new_strike: float, summary_msg: str).
    """
    if portfolio_gain_pct >= trigger_pct:
        # Target strike ~5% below current Nifty spot rounded to nearest 100
        ideal_strike = nifty_spot * 0.95
        new_strike = round(ideal_strike / 100.0) * 100.0

        if new_strike > current_strike:
            msg = f"Profit-lock triggered (+{portfolio_gain_pct * 100:.1f}% >= +{trigger_pct * 100:.1f}%). Roll put strike from {current_strike} to {new_strike} (~5% OTM)."
            return True, new_strike, msg
        else:
            msg = f"Profit-lock trigger active, but current strike {current_strike} already at or above target {new_strike}."
            return False, current_strike, msg
    else:
        msg = f"Portfolio gain (+{portfolio_gain_pct * 100:.1f}%) below profit-lock trigger (+{trigger_pct * 100:.1f}%)."
        return False, current_strike, msg
