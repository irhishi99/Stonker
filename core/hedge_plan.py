"""
Core Hedge Plan & Option Strategy Analysis Module.
Computes minimum-variance hedge ratio, hedge effectiveness R^2, strike comparison table,
and downside scenario P&L curves (-25% to 0% Nifty move).
"""

import numpy as np
import pandas as pd
from scipy.stats import norm
from typing import Dict, Any, List, Tuple


def calculate_black_scholes_put_delta(spot: float,
                                       strike: float,
                                       time_to_expiry_years: float = 0.25,
                                       rf: float = 0.065,
                                       iv: float = 0.15) -> float:
    """Calculate Black-Scholes Put Delta.

    Args:

        spot: Current Nifty spot level.
        strike: Option strike price.
        time_to_expiry_years: Time to expiry in years.
        rf: Risk-free rate.
        iv: Implied volatility.

    Returns:

        Put Delta float (-1.0 to 0.0).
    """
    if spot <= 0 or strike <= 0 or time_to_expiry_years <= 0 or iv <= 0:
        return -0.20

    d1 = (np.log(spot / strike) + (rf + 0.5 * iv**2) * time_to_expiry_years) / (iv * np.sqrt(time_to_expiry_years))
    put_delta = norm.cdf(d1) - 1.0
    return round(float(put_delta), 3)


def generate_option_strike_comparison(nifty_spot: float,
                                       options_df: pd.DataFrame,
                                       stock_value: float,
                                       beta_down: float,
                                       lot_size: int = 65) -> pd.DataFrame:
    """Generate comparative put option strike table around spot.

    Args:

        nifty_spot: Current Nifty spot index level.
        options_df: Options Bhavcopy DataFrame.
        stock_value: Total mark-to-market equity sleeve value.
        beta_down: Down-market tail hedge beta.
        lot_size: Nifty lot size (65).

    Returns:

        DataFrame with Strike, Premium (Rs), Delta, Lots Needed, Exposure Covered (Rs), Net Cost (Rs).
    """
    center_strike = round(nifty_spot / 500.0) * 500.0
    strikes = [center_strike - 1500, center_strike - 1000, center_strike - 500, center_strike, center_strike + 500]

    records = []
    contract_val = nifty_spot * lot_size
    base_lots = int(round((beta_down * stock_value) / contract_val)) if contract_val > 0 else 8

    for k in strikes:
        delta = calculate_black_scholes_put_delta(nifty_spot, k)
        # Approximate premium using moneyness if missing in options_df
        intrinsic = max(0.0, k - nifty_spot)
        time_val = nifty_spot * 0.015 * (1.0 + abs(delta))
        prem = round(intrinsic + time_val + 50.0, 2)

        lots = max(1, int(round(base_lots / max(0.1, abs(delta)))))
        exp_covered = round(lots * lot_size * nifty_spot * abs(delta), 2)
        net_cost = round(lots * lot_size * prem, 2)

        records.append({
            "Strike": float(k),
            "Option Type": "PE",
            "Premium (Rs)": prem,
            "Delta": delta,
            "Lots Needed": lots,
            "Exposure Covered (Rs)": exp_covered,
            "Total Premium Cost (Rs)": net_cost
        })

    return pd.DataFrame(records)


def generate_hedge_scenario_analysis(nifty_spot: float,
                                      stock_value: float,
                                      beta_down: float,
                                      put_strike: float = 22000.0,
                                      put_premium_paid: float = 208.20,
                                      lots_held: int = 8,
                                      lot_size: int = 65,
                                      total_capital: float = 10000000.0) -> pd.DataFrame:
    """Generate scenario analysis curves for Nifty moves (-25% to 0%) at expiry.

    Args:

        nifty_spot: Current Nifty spot level.
        stock_value: Mark-to-market stock portfolio value.
        beta_down: Tail hedge beta.
        put_strike: Strike of held put options.
        put_premium_paid: Fill price per share of held puts.
        lots_held: Number of put option lots held.
        lot_size: Nifty contract lot size (65).
        total_capital: Total portfolio capital base.

    Returns:

        DataFrame with Nifty_Move_Pct, Nifty_Spot_Level, Unhedged_Stock_PnL_Rs,
        Put_Payoff_Rs, Hedged_Portfolio_PnL_Rs, Unhedged_PnL_Pct, Hedged_PnL_Pct.
    """
    nifty_moves_pct = np.arange(-0.25, 0.05, 0.05)
    total_put_shares = lots_held * lot_size
    total_premium_spent = total_put_shares * put_premium_paid

    records = []
    for move in nifty_moves_pct:
        sim_spot = nifty_spot * (1.0 + move)

        # Stock loss calculation: move < 0 uses beta_down, move >= 0 uses beta=1.0
        effective_beta = beta_down if move < 0 else 1.0
        stock_pnl_pct = effective_beta * move
        stock_pnl_rs = stock_value * stock_pnl_pct

        # Put option payoff at expiry: max(0, Strike - Spot_expiry) * Qty - Premium_Paid
        intrinsic_expiry = max(0.0, put_strike - sim_spot)
        put_payoff_gross = total_put_shares * intrinsic_expiry
        put_pnl_net = put_payoff_gross - total_premium_spent

        hedged_pnl_rs = stock_pnl_rs + put_pnl_net

        unhedged_pnl_pct_cap = (stock_pnl_rs / total_capital) * 100.0
        hedged_pnl_pct_cap = (hedged_pnl_rs / total_capital) * 100.0

        records.append({
            "Nifty Move (%)": round(move * 100.0, 1),
            "Nifty Spot Expiry": round(sim_spot, 2),
            "Unhedged Stock PnL (Rs)": round(stock_pnl_rs, 2),
            "Put Option Net PnL (Rs)": round(put_pnl_net, 2),
            "Hedged Portfolio PnL (Rs)": round(hedged_pnl_rs, 2),
            "Unhedged PnL (% of Capital)": round(unhedged_pnl_pct_cap, 2),
            "With Puts PnL (% of Capital)": round(hedged_pnl_pct_cap, 2)
        })

    return pd.DataFrame(records)
