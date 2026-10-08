"""
Core Fundamental Screening & Exception Generator.
Enforces sector-specific Hard (H) and Soft (S) rules on Screener data.
Writes review tables to output/ directory and produces plain-English exception bullets.
"""

import os
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple


def evaluate_stock_screens(row: pd.Series, sector: str) -> Dict[str, Any]:
    """Evaluate fundamental rules for a single stock row based on sector.

    Args:

        row: Series containing stock metrics (Market_Cap_Cr, ROCE_Pct, OPM_Pct, Debt_To_Equity,
             Interest_Coverage, OCF_Cr, YoY_Profit_Growth_Pct, Pledged_Pct, Median_Turnover_Cr).
        sector: Sector string ("Capital Goods & EPC", "Cement", "Power").

    Returns:

        Dict with hard_pass, soft_pass, total_pass, exceptions list, and metric breakdown.
    """
    exceptions = []
    hard_failures = []
    soft_failures = []

    # Helper to safely extract float
    def safe_get(key: str) -> float:
        val = row.get(key, None)
        if pd.isna(val) or val is None:
            return np.nan
        try:
            return float(val)
        except (ValueError, TypeError):
            return np.nan

    mcap = safe_get("Market_Cap_Cr")
    roce = safe_get("ROCE_Pct")
    opm = safe_get("OPM_Pct")
    de = safe_get("Debt_To_Equity")
    ic = safe_get("Interest_Coverage")
    ocf = safe_get("OCF_Cr")
    yoy_growth = safe_get("YoY_Profit_Growth_Pct")
    pledged = safe_get("Pledged_Pct")
    turnover_cr = safe_get("Median_Turnover_Cr")
    if np.isnan(turnover_cr):
        turnover_cr = safe_get("Turnover_Cr")

    # Common Hard Rule 1: Market Cap >= 5000 Cr
    if np.isnan(mcap) or mcap < 5000.0:
        hard_failures.append(f"Market Cap Rs {mcap if not np.isnan(mcap) else 'N/A'} Cr < Rs 5,000 Cr threshold (HARD)")
    
    # Common Hard Rule 2: Pledged < 15%
    if np.isnan(pledged) or pledged >= 15.0:
        hard_failures.append(f"Pledged Shares {pledged if not np.isnan(pledged) else 'N/A'}% >= 15.0% threshold (HARD)")

    # Common Hard Rule 3: Median Turnover >= 5 Cr/day
    if np.isnan(turnover_cr) or turnover_cr < 5.0:
        hard_failures.append(f"Median Daily Turnover Rs {turnover_cr if not np.isnan(turnover_cr) else 'N/A'} Cr < Rs 5.0 Cr (HARD)")

    # Common Hard Rule 4: Latest-quarter profit up YoY (> 0%)
    if np.isnan(yoy_growth) or yoy_growth <= 0.0:
        hard_failures.append(f"YoY Profit Growth {yoy_growth if not np.isnan(yoy_growth) else 'N/A'}% <= 0.0% (HARD)")

    # Sector specific rules
    if sector in ["Capital Goods & EPC", "Capital Goods"]:
        # ROCE > 8% (Soft)
        if np.isnan(roce) or roce <= 8.0:
            soft_failures.append(f"ROCE {roce if not np.isnan(roce) else 'N/A'}% <= 8.0% (SOFT)")
        # OPM > 8% (Soft)
        if np.isnan(opm) or opm <= 8.0:
            soft_failures.append(f"OPM {opm if not np.isnan(opm) else 'N/A'}% <= 8.0% (SOFT)")
        # OCF > 0 (Soft)
        if np.isnan(ocf) or ocf <= 0.0:
            soft_failures.append(f"Operating Cash Flow Rs {ocf if not np.isnan(ocf) else 'N/A'} Cr <= 0 (SOFT)")
        # Debt/Equity < 1.5 (Hard)
        if np.isnan(de) or de >= 1.5:
            hard_failures.append(f"Debt to Equity {de if not np.isnan(de) else 'N/A'} >= 1.5 (HARD)")

    elif sector == "Cement":
        # ROCE > 8% (Soft)
        if np.isnan(roce) or roce <= 8.0:
            soft_failures.append(f"ROCE {roce if not np.isnan(roce) else 'N/A'}% <= 8.0% (SOFT)")
        # OPM > 10% (Soft)
        if np.isnan(opm) or opm <= 10.0:
            soft_failures.append(f"OPM {opm if not np.isnan(opm) else 'N/A'}% <= 10.0% (SOFT)")
        # OCF > 0 (Soft)
        if np.isnan(ocf) or ocf <= 0.0:
            soft_failures.append(f"Operating Cash Flow Rs {ocf if not np.isnan(ocf) else 'N/A'} Cr <= 0 (SOFT)")
        # Debt/Equity < 1.5 (Hard)
        if np.isnan(de) or de >= 1.5:
            hard_failures.append(f"Debt to Equity {de if not np.isnan(de) else 'N/A'} >= 1.5 (HARD)")

    elif sector == "Power":
        # ROCE > 6% (Soft)
        if np.isnan(roce) or roce <= 6.0:
            soft_failures.append(f"ROCE {roce if not np.isnan(roce) else 'N/A'}% <= 6.0% (SOFT)")
        # Interest Cover > 1.5 (Hard)
        if np.isnan(ic) or ic <= 1.5:
            hard_failures.append(f"Interest Coverage {ic if not np.isnan(ic) else 'N/A'} <= 1.5 (HARD)")
        # OCF > 0 (Soft)
        if np.isnan(ocf) or ocf <= 0.0:
            soft_failures.append(f"Operating Cash Flow Rs {ocf if not np.isnan(ocf) else 'N/A'} Cr <= 0 (SOFT)")
        # Note: No Debt/Equity test for Power sector

    hard_pass = len(hard_failures) == 0
    soft_pass = len(soft_failures) == 0
    overall_pass = hard_pass and soft_pass

    all_exceptions = hard_failures + soft_failures

    return {
        "Ticker": row.get("Ticker", "UNKNOWN"),
        "Sector": sector,
        "Hard_Pass": hard_pass,
        "Soft_Pass": soft_pass,
        "Overall_Pass": overall_pass,
        "Hard_Failures": hard_failures,
        "Soft_Failures": soft_failures,
        "Exception_Bullets": all_exceptions
    }


def run_fundamental_screens(fund_df: pd.DataFrame,
                             equity_df: pd.DataFrame,
                             output_dir: str = "output") -> Tuple[pd.DataFrame, List[str]]:
    """Run screens across all tracked tickers, write review CSV tables per sector, and return exceptions.

    Args:

        fund_df: Fundamentals DataFrame from Step 4.
        equity_df: Daily equity OHLCV DataFrame from Step 2.
        output_dir: Output directory path.

    Returns:

        Tuple of (Full Screen Evaluation DataFrame, Plain-English exception bullet strings).
    """
    os.makedirs(output_dir, exist_ok=True)

    # Compute 63-session median daily turnover in Cr
    piv_turnover = equity_df.groupby("Ticker").apply(
        lambda g: (g.tail(63)["Turnover"].median() / 1e7) if len(g) >= 10 else 0.0,
        include_groups=False
    ).reset_index()
    piv_turnover.columns = ["Ticker", "Median_Turnover_Cr"]

    merged = pd.merge(fund_df, piv_turnover, on="Ticker", how="left")
    merged["Median_Turnover_Cr"] = merged["Median_Turnover_Cr"].fillna(5.0)

    eval_results = []
    bullet_list = []

    for _, row in merged.iterrows():
        ticker = row["Ticker"]
        sector = row.get("Sector", "Capital Goods & EPC")

        res = evaluate_stock_screens(row, sector)
        eval_results.append({
            "Ticker": ticker,
            "Sector": sector,
            "Market_Cap_Cr": row.get("Market_Cap_Cr", np.nan),
            "ROCE_Pct": row.get("ROCE_Pct", np.nan),
            "OPM_Pct": row.get("OPM_Pct", np.nan),
            "Debt_To_Equity": row.get("Debt_To_Equity", np.nan),
            "Interest_Coverage": row.get("Interest_Coverage", np.nan),
            "OCF_Cr": row.get("OCF_Cr", np.nan),
            "YoY_Profit_Growth_Pct": row.get("YoY_Profit_Growth_Pct", np.nan),
            "Pledged_Pct": row.get("Pledged_Pct", np.nan),
            "Median_Turnover_Cr": row.get("Median_Turnover_Cr", np.nan),
            "Hard_Pass": res["Hard_Pass"],
            "Soft_Pass": res["Soft_Pass"],
            "Overall_Pass": res["Overall_Pass"],
            "Exception_Count": len(res["Exception_Bullets"]),
            "Exceptions": "; ".join(res["Exception_Bullets"]) if res["Exception_Bullets"] else "None (Passed All)"
        })

        if res["Exception_Bullets"]:
            for exc in res["Exception_Bullets"]:
                bullet_list.append(f"- **{ticker}** ({sector}): {exc}")

    eval_df = pd.DataFrame(eval_results)

    # Write per-sector review CSV tables
    for sec in eval_df["Sector"].unique():
        sec_df = eval_df[eval_df["Sector"] == sec]
        sanitized_sec = sec.replace("&", "").replace(" ", "_").strip("_")
        out_path = os.path.join(output_dir, f"{sanitized_sec}_full_review_table.csv")
        sec_df.to_csv(out_path, index=False)

    return eval_df, bullet_list
