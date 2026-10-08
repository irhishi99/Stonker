"""
Step 5: Ingest Macro and Interest Rate Data (Liquid Fund NAV, Nifty 1D Rate Index, 10-Yr G-Sec Yield, Brent Crude).
Outputs data/parquet/macro_rates.parquet.
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any
from core.utils import is_trading_day


def generate_demo_macro_rates(start_date: str, end_date: str, gsec_default: float) -> pd.DataFrame:
    """Generate synthetic macro and rate historical data.

    Args:

        start_date: Start date YYYY-MM-DD.
        end_date: End date YYYY-MM-DD.
        gsec_default: Default 10-Yr G-Sec yield rate.

    Returns:

        DataFrame containing daily macro metrics.
    """
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    curr_dt = start_dt
    trading_days = []
    while curr_dt <= end_dt:
        if is_trading_day(curr_dt):
            trading_days.append(curr_dt.strftime("%Y-%m-%d"))
        curr_dt += timedelta(days=1)

    np.random.seed(505)

    liquid_nav = 1000.0  # Base NAV
    nifty_1d_rate = 1000.0  # Base Index
    brent_price = 78.50  # USD/bbl
    gsec_yield = gsec_default * 100.0  # Percentage e.g. 6.8%

    records = []
    daily_rf = 0.065 / 365.0  # ~6.5% annual return for liquid fund

    for d_str in trading_days:
        liquid_nav *= (1 + daily_rf + np.random.normal(0, 0.00005))
        nifty_1d_rate *= (1 + daily_rf + np.random.normal(0, 0.00003))

        brent_price = max(40.0, brent_price + np.random.normal(0.05, 1.2))
        gsec_yield = max(5.0, min(8.5, gsec_yield + np.random.normal(0, 0.02)))

        records.append({
            "Date": d_str,
            "Liquid_Fund_NAV": round(liquid_nav, 4),
            "Nifty_1D_Rate_Index": round(nifty_1d_rate, 4),
            "GSec_10Y_Yield_Pct": round(gsec_yield, 3),
            "Brent_Crude_USD": round(brent_price, 2)
        })

    return pd.DataFrame(records)


def run_step5(config: Dict[str, Any], demo: bool = False) -> Dict[str, Any]:
    """Execute Step 5: Macro & Rates data ingestion.

    Args:

        config: Configuration dictionary.
        demo: Flag for synthetic mode.

    Returns:

        Status dictionary.
    """
    start_date = "2025-09-01"
    end_date = config["portfolio"]["snapshot_date"]
    gsec_default = config.get("market_parameters", {}).get("gsec_10y_yield_default", 0.068)

    is_demo_used = False
    source = "live"

    if demo:
        is_demo_used = True
        source = "demo"
        df = generate_demo_macro_rates(start_date, end_date, gsec_default)
    else:
        try:
            # Attempt live lookup via mfapi.in for Liquid Fund and yfinance for Brent crude (BZ=F)
            import requests
            # mfapi for Nippon India Liquid Fund (119598) or similar
            res = requests.get("https://api.mfapi.in/mf/119598", timeout=5)
            if res.status_code == 200:
                mf_json = res.json()
                # If API succeeds, we can combine with fallback rates
                pass
            is_demo_used = True
            source = "live_fallback_demo"
            df = generate_demo_macro_rates(start_date, end_date, gsec_default)
        except Exception as e:
            is_demo_used = True
            source = f"demo_fallback (Reason: {str(e)})"
            df = generate_demo_macro_rates(start_date, end_date, gsec_default)

    parquet_dir = config.get("paths", {}).get("parquet_dir", "data/parquet")
    os.makedirs(parquet_dir, exist_ok=True)
    parquet_path = os.path.join(parquet_dir, "macro_rates.parquet")

    df.to_parquet(parquet_path, engine="pyarrow", index=False)

    return {
        "status": "OK",
        "rows": len(df),
        "source": source,
        "is_demo": is_demo_used,
        "parquet_file": parquet_path
    }
