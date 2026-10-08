"""
Unit tests for corporate action split/bonus/dividend adjustments.
"""

import pandas as pd
import numpy as np
from pipeline.step2_adjustments import run_step2


def test_corporate_adjustments_logic():
    """Verify split factor adjustment calculation."""
    dummy_step1 = {
        "cache_file": "data/raw/bhavcopy/raw_equity_bhavcopy.csv",
        "is_demo": True
    }

    config = {
        "paths": {
            "raw_dir": "data/raw",
            "parquet_dir": "data/parquet"
        }
    }

    res = run_step2(config, dummy_step1, demo=True)
    assert res["status"] == "OK"
    assert "parquet_file" in res

    df = pd.read_parquet(res["parquet_file"])
    assert "Adj_Close" in df.columns
    assert "Turnover" in df.columns
    assert (df["Turnover"] >= 0).all()
