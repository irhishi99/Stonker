"""
Step 4: Consolidate Screener.in export file + NSE pledge disclosures into fundamentals database.
Outputs data/parquet/fundamentals.parquet.
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List


def generate_demo_fundamentals(config: Dict[str, Any]) -> pd.DataFrame:
    """Generate realistic Screener.in + NSE pledge fundamentals fixture.

    Args:

        config: System configuration dict.

    Returns:

        DataFrame with fundamental metrics for 15 tracked tickers.
    """
    invested = config["universe"]["invested_tickers"]
    reserve = config["universe"]["reserve_queue"]

    ticker_meta = {}
    for item in invested:
        ticker_meta[item["symbol"]] = item["sector"]
    for item in reserve:
        ticker_meta[item["symbol"]] = item["sector"]

    np.random.seed(2026)

    # Realistic financial fundamentals per stock tailored to Capex/Infra theme
    sample_data = {
        "WELCORP": {"mcap": 16250.0, "roce": 18.5, "opm": 14.2, "de": 0.45, "ic": 5.8, "ocf": 1450.0, "yoy_profit_growth": 24.5, "pledged": 0.0},
        "RPEL": {"mcap": 3100.0, "roce": 22.1, "opm": 18.6, "de": 0.12, "ic": 12.4, "ocf": 280.0, "yoy_profit_growth": 38.2, "pledged": 0.0},
        "SBCL": {"mcap": 3450.0, "roce": 24.8, "opm": 21.0, "de": 0.08, "ic": 18.2, "ocf": 310.0, "yoy_profit_growth": 19.8, "pledged": 0.0},
        "AEROFLEX": {"mcap": 2480.0, "roce": 28.4, "opm": 20.4, "de": 0.05, "ic": 22.0, "ocf": 210.0, "yoy_profit_growth": 29.1, "pledged": 0.0},
        "TDPOWERSYS": {"mcap": 5300.0, "roce": 21.6, "opm": 16.8, "de": 0.02, "ic": 25.5, "ocf": 480.0, "yoy_profit_growth": 31.4, "pledged": 0.0},
        "RAMRAT": {"mcap": 3120.0, "roce": 19.2, "opm": 9.8, "de": 0.38, "ic": 7.2, "ocf": 260.0, "yoy_profit_growth": 16.7, "pledged": 0.0},
        "APARINDS": {"mcap": 32600.0, "roce": 31.5, "opm": 11.2, "de": 0.22, "ic": 14.8, "ocf": 2900.0, "yoy_profit_growth": 28.9, "pledged": 0.0},
        "ACMESOLAR": {"mcap": 18400.0, "roce": 14.8, "opm": 82.5, "de": 1.45, "ic": 2.8, "ocf": 1850.0, "yoy_profit_growth": 42.0, "pledged": 4.5},
        # Reserve Queue
        "QPOWER": {"mcap": 12800.0, "roce": 16.2, "opm": 34.0, "de": 0.85, "ic": 4.1, "ocf": 1120.0, "yoy_profit_growth": 21.0, "pledged": 0.0},
        "FINCABLES": {"mcap": 17600.0, "roce": 20.4, "opm": 13.5, "de": 0.01, "ic": 35.0, "ocf": 1340.0, "yoy_profit_growth": 15.2, "pledged": 0.0},
        "GRINDWELL": {"mcap": 24900.0, "roce": 26.8, "opm": 19.8, "de": 0.03, "ic": 42.0, "ocf": 1820.0, "yoy_profit_growth": 18.4, "pledged": 0.0},
        "ACE": {"mcap": 16400.0, "roce": 29.1, "opm": 15.4, "de": 0.04, "ic": 28.0, "ocf": 1250.0, "yoy_profit_growth": 35.6, "pledged": 0.0},
        "CARBORUNIV": {"mcap": 26800.0, "roce": 22.3, "opm": 16.2, "de": 0.11, "ic": 19.5, "ocf": 1950.0, "yoy_profit_growth": 14.8, "pledged": 0.0},
        "GOODLUCK": {"mcap": 3200.0, "roce": 17.8, "opm": 8.9, "de": 0.62, "ic": 4.9, "ocf": 240.0, "yoy_profit_growth": 26.2, "pledged": 0.0},
        "ENGINERSIN": {"mcap": 11800.0, "roce": 25.4, "opm": 12.8, "de": 0.00, "ic": 50.0, "ocf": 980.0, "yoy_profit_growth": 22.1, "pledged": 0.0},
    }

    records = []
    fetch_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for ticker, sector in ticker_meta.items():
        metrics = sample_data.get(ticker, {
            "mcap": 5000.0, "roce": 15.0, "opm": 12.0, "de": 0.5, "ic": 5.0, "ocf": 300.0, "yoy_profit_growth": 15.0, "pledged": 0.0
        })

        records.append({
            "Ticker": ticker,
            "Sector": sector,
            "Market_Cap_Cr": metrics["mcap"],
            "ROCE_Pct": metrics["roce"],
            "OPM_Pct": metrics["opm"],
            "Debt_To_Equity": metrics["de"],
            "Interest_Coverage": metrics["ic"],
            "OCF_Cr": metrics["ocf"],
            "YoY_Profit_Growth_Pct": metrics["yoy_profit_growth"],
            "Pledged_Pct": metrics["pledged"],
            "Fetch_Date": fetch_stamp,
            "Data_Source": "Screener_Demo_Fixture"
        })

    return pd.DataFrame(records)


def run_step4(config: Dict[str, Any], demo: bool = False) -> Dict[str, Any]:
    """Execute Step 4: Fundamentals consolidation.

    Args:

        config: System configuration dict.
        demo: Flag for synthetic fallback.

    Returns:

        Status dictionary.
    """
    screener_path = config.get("paths", {}).get("screener_export", "data/screener_export.csv")

    is_demo_used = False
    source = "screener_export_file"

    if demo or not os.path.exists(screener_path):
        is_demo_used = True
        source = "demo_fixture" if demo else f"demo_fallback (Missing export file at {screener_path})"
        df = generate_demo_fundamentals(config)
    else:
        try:
            # Parse existing screener export file
            ext = os.path.splitext(screener_path)[1].lower()
            if ext in [".xlsx", ".xls"]:
                raw_df = pd.read_excel(screener_path)
            else:
                raw_df = pd.read_csv(screener_path)

            fetch_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            raw_df["Fetch_Date"] = fetch_stamp
            raw_df["Data_Source"] = "Screener.in Export File"
            df = raw_df
        except Exception as e:
            is_demo_used = True
            source = f"demo_fallback (Parse error: {str(e)})"
            df = generate_demo_fundamentals(config)

    parquet_dir = config.get("paths", {}).get("parquet_dir", "data/parquet")
    os.makedirs(parquet_dir, exist_ok=True)
    parquet_path = os.path.join(parquet_dir, "fundamentals.parquet")

    df.to_parquet(parquet_path, engine="pyarrow", index=False)

    return {
        "status": "OK",
        "rows": len(df),
        "source": source,
        "is_demo": is_demo_used,
        "parquet_file": parquet_path
    }
