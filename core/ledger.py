"""
Core Trade Ledger & Portfolio Valuation Engine.
Manages trade execution history in Parquet, initial seeds day-0 snapshot,
computes mark-to-market portfolio NAV, and solves for dated XIRR.
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime
from scipy.optimize import newton, brentq
from typing import Dict, Any, List, Tuple


def solve_xirr(cash_flows: List[Tuple[str, float]]) -> float:
    """Solve for XIRR on dated cash flows.

    Args:

        cash_flows: List of (date_str 'YYYY-MM-DD', amount) tuples.
                    Negative amounts are outflows (investments), positive are inflows/ending NAV.

    Returns:

        Annualized internal rate of return as a decimal (e.g. 0.145 for 14.5%).
    """
    if not cash_flows or len(cash_flows) < 2:
        return 0.0

    # Sort by date
    parsed = [(datetime.strptime(dt, "%Y-%m-%d"), amt) for dt, amt in cash_flows]
    parsed.sort(key=lambda x: x[0])

    t0 = parsed[0][0]
    times = np.array([(d - t0).days / 365.0 for d, _ in parsed])
    amounts = np.array([amt for _, amt in parsed])

    # Ensure there is at least one negative and one positive cash flow
    if not (np.any(amounts < 0) and np.any(amounts > 0)):
        return 0.0

    def npv(r: float) -> float:
        if r <= -0.99:
            return 1e9
        return float(np.sum(amounts / ((1.0 + r) ** times)))

    def npv_prime(r: float) -> float:
        if r <= -0.99:
            return 1e9
        return float(np.sum(-times * amounts / ((1.0 + r) ** (times + 1.0))))

    try:
        r_sol = newton(npv, fprime=npv_prime, x0=0.10, maxiter=100, tol=1e-6)
        return round(float(r_sol), 4)
    except Exception:
        try:
            r_sol = brentq(npv, -0.90, 5.0, maxiter=100)
            return round(float(r_sol), 4)
        except Exception:
            return 0.0


def initialize_day0_ledger(config: Dict[str, Any], equity_df: pd.DataFrame) -> pd.DataFrame:
    """Seed day-0 initial trade ledger as of 2026-09-28 snapshot date.

    Args:

        config: System configuration dictionary.
        equity_df: Equity OHLCV DataFrame.

    Returns:

        DataFrame containing day-0 trade log.
    """
    total_capital = config["portfolio"]["total_capital"]  # Rs 1,00,00,000
    snapshot_date = config["portfolio"]["snapshot_date"]  # 2026-09-28
    put_expiry = config["portfolio"]["put_expiry_date"]    # 2026-12-29
    lot_size = config.get("market_parameters", {}).get("nifty_lot_size", 65)

    invested_tickers = [t["symbol"] for t in config["universe"]["invested_tickers"]]
    equity_sleeve_capital = total_capital * config["portfolio"]["equity_sleeve"]

    # Filter snapshot date prices
    snap_equity = equity_df[equity_df["Date"] == snapshot_date]
    if snap_equity.empty:
        # Fallback to latest date in dataset
        latest_dt = equity_df["Date"].max()
        snap_equity = equity_df[equity_df["Date"] == latest_dt]

    prices = {}
    for _, row in snap_equity.iterrows():
        prices[row["Ticker"]] = float(row["Close"])

    trades = []
    # Capital flow 0: Cash deposit
    trades.append({
        "Date": snapshot_date,
        "Instrument": "CASH_DEPOSIT",
        "Side": "BUY",
        "Qty": 1,
        "Fill_Price": total_capital,
        "Total_Cost": total_capital,
        "Instrument_Type": "CASH"
    })

    # Equal sleeve target per stock (or equal allocation initially)
    alloc_per_stock = equity_sleeve_capital / len(invested_tickers)
    total_stock_spent = 0.0

    for ticker in invested_tickers:
        price = prices.get(ticker, 500.0)
        shares = int(alloc_per_stock // price)
        cost = round(shares * price, 2)
        total_stock_spent += cost

        trades.append({
            "Date": snapshot_date,
            "Instrument": ticker,
            "Side": "BUY",
            "Qty": shares,
            "Fill_Price": price,
            "Total_Cost": cost,
            "Instrument_Type": "EQUITY"
        })

    # Nifty 22000 PE option purchase: 8 lots @ Rs 208.20
    put_lots = 8
    put_qty = put_lots * lot_size
    put_fill_price = 208.20
    put_cost = round(put_qty * put_fill_price, 2)

    trades.append({
        "Date": snapshot_date,
        "Instrument": f"NIFTY_{put_expiry}_22000_PE",
        "Side": "BUY",
        "Qty": put_qty,
        "Fill_Price": put_fill_price,
        "Total_Cost": put_cost,
        "Instrument_Type": "OPTION"
    })

    ledger_df = pd.DataFrame(trades)
    return ledger_df


def load_or_init_ledger(config: Dict[str, Any], equity_df: pd.DataFrame) -> pd.DataFrame:
    """Load trade ledger from parquet or initialize if missing.

    Args:

        config: System configuration dictionary.
        equity_df: Equity OHLCV DataFrame.

    Returns:

        Trade ledger DataFrame.
    """
    parquet_dir = config.get("paths", {}).get("parquet_dir", "data/parquet")
    ledger_path = os.path.join(parquet_dir, "trade_ledger.parquet")

    if os.path.exists(ledger_path):
        ledger_df = pd.read_parquet(ledger_path)
    else:
        ledger_df = initialize_day0_ledger(config, equity_df)
        os.makedirs(parquet_dir, exist_ok=True)
        ledger_df.to_parquet(ledger_path, engine="pyarrow", index=False)

    return ledger_df


def compute_portfolio_valuation(ledger_df: pd.DataFrame,
                                equity_df: pd.DataFrame,
                                options_df: pd.DataFrame,
                                config: Dict[str, Any]) -> Dict[str, Any]:
    """Compute mark-to-market portfolio NAV (Stocks + Options + Cash).

    Args:

        ledger_df: Trade ledger DataFrame.
        equity_df: Daily equity OHLCV DataFrame.
        options_df: Options Bhavcopy DataFrame.
        config: System configuration dictionary.

    Returns:

        Dict with stock_value, options_value, cash_balance, total_nav, holdings table.
    """
    snapshot_date = config["portfolio"]["snapshot_date"]

    # Calculate Cash balance from ledger
    cash_inflows = ledger_df[ledger_df["Instrument"] == "CASH_DEPOSIT"]["Total_Cost"].sum()
    stock_buys = ledger_df[ledger_df["Instrument_Type"] == "EQUITY"]["Total_Cost"].sum()
    option_buys = ledger_df[ledger_df["Instrument_Type"] == "OPTION"]["Total_Cost"].sum()
    cash_balance = round(cash_inflows - stock_buys - option_buys, 2)

    # Current equity holdings
    eq_trades = ledger_df[ledger_df["Instrument_Type"] == "EQUITY"]
    holdings_records = []
    total_stock_val = 0.0

    # Get latest equity prices
    snap_eq = equity_df[equity_df["Date"] == snapshot_date]
    if snap_eq.empty:
        snap_eq = equity_df[equity_df["Date"] == equity_df["Date"].max()]

    latest_prices = dict(zip(snap_eq["Ticker"], snap_eq["Close"]))

    for ticker in eq_trades["Instrument"].unique():
        t_shares = eq_trades[eq_trades["Instrument"] == ticker]["Qty"].sum()
        price = latest_prices.get(ticker, 500.0)
        cur_val = round(t_shares * price, 2)
        total_stock_val += cur_val

        holdings_records.append({
            "Ticker": ticker,
            "Shares": t_shares,
            "Price": price,
            "Current_Value": cur_val
        })

    holdings_df = pd.DataFrame(holdings_records)

    # Mark-to-market options value
    opt_trades = ledger_df[ledger_df["Instrument_Type"] == "OPTION"]
    total_opt_val = 0.0
    if not opt_trades.empty and options_df is not None and not options_df.empty:
        snap_opt = options_df[options_df["Date"] == snapshot_date]
        if snap_opt.empty:
            snap_opt = options_df[options_df["Date"] == options_df["Date"].max()]

        for _, o_trade in opt_trades.iterrows():
            o_qty = o_trade["Qty"]
            # Match strike if possible
            match_opt = snap_opt[snap_opt["Strike"] == 22000.0]
            if not match_opt.empty:
                opt_price = float(match_opt["Close"].iloc[0])
            else:
                opt_price = float(o_trade["Fill_Price"])
            total_opt_val += round(o_qty * opt_price, 2)
    else:
        # Fallback purchase cost mark
        total_opt_val = float(option_buys)

    total_nav = round(total_stock_val + total_opt_val + cash_balance, 2)

    return {
        "Total_NAV": total_nav,
        "Stock_Value": round(total_stock_val, 2),
        "Option_Value": round(total_opt_val, 2),
        "Cash_Balance": cash_balance,
        "Holdings": holdings_df
    }
