"""
Core 3-Month Risk-Reward Analytics Module.
Calculates typical 3-month expected volatility moves, target resistance hurdles,
reward:risk ratios, and guarantees exact match for aggregate 'Still at Risk' figures.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple


def compute_risk_reward_table(equity_df: pd.DataFrame,
                               risk_stops_df: pd.DataFrame,
                               total_capital: float = 10000000.0) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Compute 3-Month Risk-Reward Table for individual stocks and PORTFOLIO rows.

    Args:

        equity_df: Equity OHLCV DataFrame.
        risk_stops_df: Portfolio risk and stop-loss DataFrame from Step 8.
        total_capital: Total capital base (e.g. Rs 1,00,00,000).

    Returns:

        Tuple of (Risk-Reward DataFrame, Summary KPIs dict).
    """
    records = []

    total_downside_rs = 0.0
    total_upside_rs_undiversified = 0.0

    for _, row in risk_stops_df.iterrows():
        ticker = row["Ticker"]
        price = float(row["Price"])
        shares = int(row["Shares"])
        stop_loss = float(row["Stop_Loss"])
        ann_vol = float(row["Ann_Vol"])
        support = float(row.get("Support_20D", stop_loss))

        # Swing resistance
        t_df = equity_df[equity_df["Ticker"] == ticker].tail(20)
        resistance = float(t_df["High"].max()) if not t_df.empty else price * 1.10

        downside_pct = ((price - stop_loss) / price) * 100.0
        typical_3m_move_pct = (ann_vol * np.sqrt(63.0 / 252.0)) * 100.0
        target_level = price * (1.0 + typical_3m_move_pct / 100.0)

        hurdle_pct = ((resistance - price) / price) * 100.0
        upside_pct = typical_3m_move_pct

        rr_ratio = upside_pct / downside_pct if downside_pct > 0 else 0.0

        loss_rs = shares * (price - stop_loss)
        total_downside_rs += loss_rs

        upside_rs = shares * (price * (typical_3m_move_pct / 100.0))
        total_upside_rs_undiversified += upside_rs

        loss_pct_capital = (loss_rs / total_capital) * 100.0

        records.append({
            "Stock": ticker,
            "Price (Rs)": round(price, 2),
            "Stop-Loss (Rs)": round(stop_loss, 2),
            "Downside to Stop (%)": round(downside_pct, 2),
            "Typical 3M Move (%)": round(typical_3m_move_pct, 2),
            "Target Level (Rs)": round(target_level, 2),
            "First Hurdle (Rs)": round(resistance, 2),
            "Hurdle Above Price (%)": round(hurdle_pct, 2),
            "Upside (%)": round(upside_pct, 2),
            "Reward:Risk": round(rr_ratio, 2),
            "Loss at Stop (% of Capital)": round(loss_pct_capital, 2),
            "Loss_Rs": loss_rs,
            "Upside_Rs": upside_rs
        })

    df_stocks = pd.DataFrame(records)

    # 1. PORTFOLIO (all stocks at once / undiversified sum)
    total_stock_value = float((risk_stops_df["Shares"] * risk_stops_df["Price"]).sum())
    portfolio_downside_pct = (total_downside_rs / total_stock_value) * 100.0
    portfolio_upside_undiv_pct = (total_upside_rs_undiversified / total_stock_value) * 100.0
    portfolio_rr_undiv = portfolio_upside_undiv_pct / portfolio_downside_pct if portfolio_downside_pct > 0 else 0.0

    row_portfolio_undiv = {
        "Stock": "PORTFOLIO (all stocks at once)",
        "Price (Rs)": round(total_stock_value, 2),
        "Stop-Loss (Rs)": round(total_stock_value - total_downside_rs, 2),
        "Downside to Stop (%)": round(portfolio_downside_pct, 2),
        "Typical 3M Move (%)": round(portfolio_upside_undiv_pct, 2),
        "Target Level (Rs)": round(total_stock_value + total_upside_rs_undiversified, 2),
        "First Hurdle (Rs)": np.nan,
        "Hurdle Above Price (%)": np.nan,
        "Upside (%)": round(portfolio_upside_undiv_pct, 2),
        "Reward:Risk": round(portfolio_rr_undiv, 2),
        "Loss at Stop (% of Capital)": round((total_downside_rs / total_capital) * 100.0, 2),
        "Loss_Rs": total_downside_rs,
        "Upside_Rs": total_upside_rs_undiversified
    }

    # 2. PORTFOLIO (diversified)
    # Estimate portfolio volatility considering correlation diversification
    piv = equity_df.pivot(index="Date", columns="Ticker", values="Close")[risk_stops_df["Ticker"]].dropna()
    log_rets = np.log(piv / piv.shift(1)).dropna()
    weights = risk_stops_df["Target_Weight"].values
    weights = weights / weights.sum()

    port_ret = (log_rets * weights).sum(axis=1)
    port_ann_vol = float(port_ret.std() * np.sqrt(252))

    typical_3m_div_pct = (port_ann_vol * np.sqrt(63.0 / 252.0)) * 100.0
    total_upside_rs_div = total_stock_value * (typical_3m_div_pct / 100.0)
    portfolio_rr_div = typical_3m_div_pct / portfolio_downside_pct if portfolio_downside_pct > 0 else 0.0

    row_portfolio_div = {
        "Stock": "PORTFOLIO (diversified)",
        "Price (Rs)": round(total_stock_value, 2),
        "Stop-Loss (Rs)": round(total_stock_value - total_downside_rs, 2),
        "Downside to Stop (%)": round(portfolio_downside_pct, 2),
        "Typical 3M Move (%)": round(typical_3m_div_pct, 2),
        "Target Level (Rs)": round(total_stock_value + total_upside_rs_div, 2),
        "First Hurdle (Rs)": np.nan,
        "Hurdle Above Price (%)": np.nan,
        "Upside (%)": round(typical_3m_div_pct, 2),
        "Reward:Risk": round(portfolio_rr_div, 2),
        "Loss at Stop (% of Capital)": round((total_downside_rs / total_capital) * 100.0, 2),
        "Loss_Rs": total_downside_rs,
        "Upside_Rs": total_upside_rs_div
    }

    full_df = pd.concat([df_stocks, pd.DataFrame([row_portfolio_undiv, row_portfolio_div])], ignore_index=True)

    summary_kpis = {
        "Upside_Typical_Move_Rs": round(total_upside_rs_div, 2),
        "Downside_Still_At_Risk_Rs": round(total_downside_rs, 2),
        "Reward_Risk_Ratio": round(portfolio_rr_div, 2),
        "Typical_Move_Diversified_Rs": round(total_upside_rs_div, 2)
    }

    return full_df, summary_kpis
