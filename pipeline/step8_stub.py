"""
Step 8: Risk Analytics, CAPM Expected Returns, ERC Weights, Stop-Loss Levels, and Options Hedge State.
Outputs calculations into data/parquet/portfolio_risk_stops.parquet.
"""

import os
import pandas as pd
import numpy as np
from typing import Dict, Any

from core.risk import calculate_annualised_volatility, calculate_beta, calculate_risk_free_rate, compute_capm_expected_return
from core.weights import compute_covariance_matrix, optimize_erc_weights, calculate_portfolio_shares
from core.stops import calculate_stop_loss, calculate_portfolio_still_at_risk
from core.hedge import calculate_down_market_beta, calculate_required_hedge_lots, evaluate_hedge_rebalance, evaluate_profit_lock_roll
from core.indicators import compute_ticker_indicators


def run_step8(config: Dict[str, Any], demo: bool = False) -> Dict[str, Any]:
    """Execute Step 8: Risk metrics, ERC weights, stop-losses, and options hedging.

    Args:

        config: System configuration dict.
        demo: Flag for synthetic mode.

    Returns:

        Status dictionary.
    """
    parquet_dir = config.get("paths", {}).get("parquet_dir", "data/parquet")

    equity_df = pd.read_parquet(os.path.join(parquet_dir, "equity_ohlcv.parquet"))
    indices_df = pd.read_parquet(os.path.join(parquet_dir, "indices_ohlcv.parquet"))
    macro_df = pd.read_parquet(os.path.join(parquet_dir, "macro_rates.parquet"))

    bm_name = config.get("indices", {}).get("benchmark", "Nifty 500 TRI")
    bm_df = indices_df[indices_df["Index_Name"] == bm_name].sort_values("Date").reset_index(drop=True)
    if bm_df.empty:
        bm_df = indices_df[indices_df["Index_Name"] == "Nifty 50 Spot"].sort_values("Date").reset_index(drop=True)

    invested_tickers = [t["symbol"] for t in config["universe"]["invested_tickers"]]
    cov_matrix, active_tickers = compute_covariance_matrix(equity_df, invested_tickers)
    erc_weights = optimize_erc_weights(cov_matrix)

    snap_date = config["portfolio"]["snapshot_date"]
    snap_eq = equity_df[equity_df["Date"] == snap_date]
    if snap_eq.empty:
        snap_eq = equity_df[equity_df["Date"] == equity_df["Date"].max()]

    latest_prices = dict(zip(snap_eq["Ticker"], snap_eq["Close"]))

    rf = calculate_risk_free_rate(macro_df, config)
    erp = config.get("market_parameters", {}).get("india_erp", 0.0708)

    equity_sleeve_cap = config["portfolio"]["total_capital"] * config["portfolio"]["equity_sleeve"]
    alloc_df = calculate_portfolio_shares(active_tickers, erc_weights, latest_prices, equity_sleeve_cap)
    shares_map = dict(zip(alloc_df["Ticker"], alloc_df["Shares"]))

    records = []
    total_still_at_risk = 0.0

    for i, ticker in enumerate(active_tickers):
        t_df = equity_df[equity_df["Ticker"] == ticker].sort_values("Date").reset_index(drop=True)
        ind = compute_ticker_indicators(t_df, bm_df, config)

        beta = calculate_beta(t_df, bm_df)
        vol = calculate_annualised_volatility(t_df)
        capm_ann, capm_q = compute_capm_expected_return(beta, rf, erp)

        price = latest_prices.get(ticker, 500.0)
        atr = ind["ATR_14"]
        support = ind["Support_20D"]

        stop_price, stop_method, pct_below = calculate_stop_loss(price, atr, support)
        shares = shares_map.get(ticker, 0)
        risk_amt = shares * (price - stop_price)
        total_still_at_risk += risk_amt

        records.append({
            "Ticker": ticker,
            "Target_Weight": round(erc_weights[i], 4),
            "Price": price,
            "Shares": shares,
            "Allocated_Value": round(shares * price, 2),
            "Beta": beta,
            "Ann_Vol": vol,
            "CAPM_Expected_Return_Ann_%": capm_ann,
            "CAPM_Expected_Return_3M_%": capm_q,
            "ATR_14": atr,
            "Support_20D": support,
            "Stop_Loss": stop_price,
            "Stop_Method": stop_method,
            "Pct_Below": pct_below,
            "Still_At_Risk": round(risk_amt, 2)
        })

    risk_df = pd.DataFrame(records)
    out_parquet = os.path.join(parquet_dir, "portfolio_risk_stops.parquet")
    risk_df.to_parquet(out_parquet, engine="pyarrow", index=False)

    return {
        "status": "OK",
        "invested_count": len(risk_df),
        "total_still_at_risk": round(total_still_at_risk, 2),
        "parquet_file": out_parquet,
        "is_demo": demo
    }
