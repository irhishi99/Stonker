"""
Step 9: Trade Ledger Management, Portfolio Valuation, Reserve Waterfall Report, and Performance Summary.
Outputs data/parquet/portfolio_summary.parquet and output/reserve_status_report.csv.
"""

import os
import pandas as pd
import numpy as np
from typing import Dict, Any

from core.ledger import load_or_init_ledger, compute_portfolio_valuation, solve_xirr
from core.waterfall import generate_reserve_status_report


def run_step9(config: Dict[str, Any], demo: bool = False) -> Dict[str, Any]:
    """Execute Step 9: Ledger seeding, portfolio valuation, and reserve waterfall status.

    Args:

        config: System configuration dict.
        demo: Flag for synthetic mode.

    Returns:

        Status dictionary.
    """
    parquet_dir = config.get("paths", {}).get("parquet_dir", "data/parquet")
    output_dir = config.get("paths", {}).get("output_dir", "output")

    equity_df = pd.read_parquet(os.path.join(parquet_dir, "equity_ohlcv.parquet"))
    fund_df = pd.read_parquet(os.path.join(parquet_dir, "fundamentals.parquet"))
    options_df = pd.read_parquet(os.path.join(parquet_dir, "options_bhavcopy.parquet"))

    # 1. Trade Ledger & Portfolio NAV
    ledger_df = load_or_init_ledger(config, equity_df)
    valuation = compute_portfolio_valuation(ledger_df, equity_df, options_df, config)

    # 2. XIRR Baseline
    snapshot_date = config["portfolio"]["snapshot_date"]
    total_capital = config["portfolio"]["total_capital"]
    cash_flows = [
        ("2026-09-01", -total_capital),
        (snapshot_date, valuation["Total_NAV"])
    ]
    xirr_val = solve_xirr(cash_flows)

    # 3. Reserve Waterfall Evaluation
    res_queue = config["universe"]["reserve_queue"]
    reserve_report_df = generate_reserve_status_report(res_queue, fund_df, equity_df, config)
    reserve_report_df.to_csv(os.path.join(output_dir, "reserve_status_report.csv"), index=False)

    # Save summary parquet
    summary_df = pd.DataFrame([{
        "Snapshot_Date": snapshot_date,
        "Total_NAV": valuation["Total_NAV"],
        "Stock_Value": valuation["Stock_Value"],
        "Option_Value": valuation["Option_Value"],
        "Cash_Balance": valuation["Cash_Balance"],
        "XIRR_Ann_%": round(xirr_val * 100.0, 2)
    }])

    out_parquet = os.path.join(parquet_dir, "portfolio_summary.parquet")
    summary_df.to_parquet(out_parquet, engine="pyarrow", index=False)

    return {
        "status": "OK",
        "total_nav": valuation["Total_NAV"],
        "xirr_ann_pct": round(xirr_val * 100.0, 2),
        "reserve_candidates_evaluated": len(reserve_report_df),
        "parquet_file": out_parquet,
        "is_demo": demo
    }
