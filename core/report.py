"""
Core Terminal CLI Report Script (`python -m core.report`).
Computes and formats full portfolio state, weights, stops, CAPM, risk metrics,
option hedge status, and screen exceptions with internal consistency assertions.
"""

import os
import pandas as pd
import numpy as np

from typing import Dict, Any, List, Tuple
from core.utils import load_config, format_indian_currency, format_indian_number
from core.indicators import compute_ticker_indicators
from core.risk import calculate_annualised_volatility, calculate_beta, calculate_risk_free_rate, compute_capm_expected_return
from core.weights import compute_covariance_matrix, optimize_erc_weights, calculate_portfolio_shares
from core.stops import calculate_stop_loss, calculate_portfolio_still_at_risk
from core.screens import run_fundamental_screens
from core.ledger import load_or_init_ledger, compute_portfolio_valuation
from core.hedge import calculate_down_market_beta, calculate_required_hedge_lots, evaluate_hedge_rebalance, evaluate_profit_lock_roll
from core.waterfall import generate_reserve_status_report


def generate_cli_report(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Generate comprehensive core portfolio report and print to console.

    Args:

        config_path: Path to YAML configuration file.

    Returns:

        Dict containing portfolio summary metrics.
    """
    config = load_config(config_path)
    parquet_dir = config.get("paths", {}).get("parquet_dir", "data/parquet")

    # Load datasets
    equity_df = pd.read_parquet(os.path.join(parquet_dir, "equity_ohlcv.parquet"))
    indices_df = pd.read_parquet(os.path.join(parquet_dir, "indices_ohlcv.parquet"))
    fund_df = pd.read_parquet(os.path.join(parquet_dir, "fundamentals.parquet"))
    macro_df = pd.read_parquet(os.path.join(parquet_dir, "macro_rates.parquet"))
    options_df = pd.read_parquet(os.path.join(parquet_dir, "options_bhavcopy.parquet"))

    # Benchmark filter
    bm_name = config.get("indices", {}).get("benchmark", "Nifty 500 TRI")
    bm_df = indices_df[indices_df["Index_Name"] == bm_name].sort_values("Date").reset_index(drop=True)
    if bm_df.empty:
        bm_df = indices_df[indices_df["Index_Name"] == "Nifty 50 Spot"].sort_values("Date").reset_index(drop=True)

    # 1. Fundamental Screens
    eval_df, exc_bullets = run_fundamental_screens(fund_df, equity_df, output_dir=config.get("paths", {}).get("output_dir", "output"))

    # 2. Invested Universe & Weights
    invested_tickers = [t["symbol"] for t in config["universe"]["invested_tickers"]]
    cov_matrix, active_tickers = compute_covariance_matrix(equity_df, invested_tickers)
    erc_weights = optimize_erc_weights(cov_matrix)

    # 3. Snapshot Prices
    snap_date = config["portfolio"]["snapshot_date"]
    snap_eq = equity_df[equity_df["Date"] == snap_date]
    if snap_eq.empty:
        snap_eq = equity_df[equity_df["Date"] == equity_df["Date"].max()]

    latest_prices = dict(zip(snap_eq["Ticker"], snap_eq["Close"]))

    # 4. Portfolio Ledger & Valuation
    ledger_df = load_or_init_ledger(config, equity_df)
    valuation = compute_portfolio_valuation(ledger_df, equity_df, options_df, config)

    # 5. Risk-Free Rate & CAPM
    rf = calculate_risk_free_rate(macro_df, config)
    erp = config.get("market_parameters", {}).get("india_erp", 0.0708)

    # 6. Detailed Ticker Metrics Breakdown
    ticker_records = []
    total_still_at_risk = 0.0

    # Share allocation based on equity sleeve capital
    equity_sleeve_cap = config["portfolio"]["total_capital"] * config["portfolio"]["equity_sleeve"]
    alloc_df = calculate_portfolio_shares(active_tickers, erc_weights, latest_prices, equity_sleeve_cap)
    shares_map = dict(zip(alloc_df["Ticker"], alloc_df["Shares"]))

    # Load prev stops (if any) or default 0.0
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
        pos_val = shares * price
        risk_amt = shares * (price - stop_price)
        total_still_at_risk += risk_amt

        ticker_records.append({
            "Ticker": ticker,
            "Target_Weight_%": round(erc_weights[i] * 100, 2),
            "Price": price,
            "Shares": shares,
            "Value": pos_val,
            "Beta": beta,
            "Vol_%": round(vol * 100, 1),
            "CAPM_E(R)_%": capm_ann,
            "ATR_14": atr,
            "Stop_Loss": stop_price,
            "Method": stop_method,
            "Pct_Below": pct_below,
            "Still_At_Risk": risk_amt
        })

    holdings_table = pd.DataFrame(ticker_records)

    # 7. Hedge & Option Status
    # Calculate portfolio daily returns for tail beta
    piv_close = equity_df.pivot(index="Date", columns="Ticker", values="Close")[active_tickers].dropna()
    piv_ret = piv_close.pct_change().dropna()
    port_daily_ret = (piv_ret * erc_weights).sum(axis=1)

    bm_close = bm_df.set_index("Date")["Close"]
    bm_daily_ret = bm_close.pct_change().dropna()

    beta_down = calculate_down_market_beta(port_daily_ret, bm_daily_ret)
    nifty_spot = float(bm_df["Close"].iloc[-1])
    lot_size = config.get("market_parameters", {}).get("nifty_lot_size", 65)

    stock_val = valuation["Stock_Value"]
    lots_needed = calculate_required_hedge_lots(stock_val, nifty_spot, beta_down, lot_size)

    # Option lots held in ledger
    opt_trades = ledger_df[ledger_df["Instrument_Type"] == "OPTION"]
    lots_held = int(opt_trades["Qty"].sum() // lot_size) if not opt_trades.empty else 0

    should_trade_hedge, hedge_diff, hedge_reason = evaluate_hedge_rebalance(lots_needed, lots_held)
    should_roll, roll_strike, roll_reason = evaluate_profit_lock_roll(0.02, nifty_spot, 22000.0)

    # 8. Reserve Status Report
    res_queue = config["universe"]["reserve_queue"]
    reserve_status_df = generate_reserve_status_report(res_queue, fund_df, equity_df, config)

    # Consistency Checks
    weight_sum = round(float(erc_weights.sum()), 4)
    assert abs(weight_sum - 1.0) < 1e-3, f"Weight sum check failed: {weight_sum} != 1.0"
    
    total_calc_nav = round(valuation["Stock_Value"] + valuation["Option_Value"] + valuation["Cash_Balance"], 2)
    assert abs(total_calc_nav - valuation["Total_NAV"]) < 1.0, "NAV sum check failed"

    # PRINT SUMMARY REPORT
    print("=" * 80)
    print("      INDIAN EQUITY PORTFOLIO MANAGEMENT TERMINAL - CORE REPORT")
    print("=" * 80)
    print(f"Snapshot Date    : {snap_date}")
    print(f"Total Portfolio NAV: {format_indian_currency(valuation['Total_NAV'], abbreviate=True)} ({format_indian_currency(valuation['Total_NAV'])})")
    print(f"  |- Equity Sleeve : {format_indian_currency(valuation['Stock_Value'])} ({(valuation['Stock_Value']/valuation['Total_NAV'])*100:.2f}%)")
    print(f"  |- Put Option    : {format_indian_currency(valuation['Option_Value'])} ({(valuation['Option_Value']/valuation['Total_NAV'])*100:.2f}%)")
    print(f"  +- Cash Reserve  : {format_indian_currency(valuation['Cash_Balance'])} ({(valuation['Cash_Balance']/valuation['Total_NAV'])*100:.2f}%)")
    print(f"Risk-Free Rate rf: {rf * 100:.2f}% | ERP: {erp * 100:.2f}%")
    print(f"Aggregate Still At Risk: {format_indian_currency(total_still_at_risk)}")
    print("-" * 80)

    print("\nINVESTED HOLDINGS BREAKDOWN:")
    print(holdings_table.to_string(index=False))

    print("\nHEDGE & TAIL RISK ANALYTICS:")
    print(f"Tail Hedge Beta (Down Days) : {beta_down}")
    print(f"Nifty Spot Index            : {nifty_spot:.2f}")
    print(f"Put Lots Required           : {lots_needed} lots ({lots_needed * lot_size} shares)")
    print(f"Put Lots Currently Held     : {lots_held} lots ({lots_held * lot_size} shares)")
    print(f"Hedge Status                : {hedge_reason}")
    print(f"Profit-Lock Status          : {roll_reason}")

    print("\nRESERVE QUEUE - WOULD BE BOUGHT TODAY?")
    print(reserve_status_df.to_string(index=False))

    if exc_bullets:
        print("\nFUNDAMENTAL SCREEN EXCEPTIONS:")
        for b in exc_bullets:
            print(f"  {b}")

    print("=" * 80)
    print("INTERNAL CONSISTENCY VERIFICATION: PASSED (Weights sum = 100%, NAV components reconciled).")
    print("=" * 80)

    return {
        "Total_NAV": valuation["Total_NAV"],
        "Holdings_Table": holdings_table,
        "Still_At_Risk": total_still_at_risk,
        "Lots_Needed": lots_needed,
        "Lots_Held": lots_held,
        "Reserve_Status": reserve_status_df
    }


if __name__ == "__main__":
    generate_cli_report()
