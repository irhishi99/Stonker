"""
Unit tests for data pipeline runner, holiday skipping, and status logging.
"""

import os
import json
import pytest
from datetime import datetime
from core.utils import load_config, is_trading_day, format_indian_currency, format_indian_number
from pipeline.run import run_pipeline


def test_trading_day_calendar():
    """Verify holiday skipping and weekend filtering."""
    # Weekend test (2026-09-26 is Saturday, 2026-09-27 is Sunday)
    assert not is_trading_day("2026-09-26"), "Saturday should not be a trading day"
    assert not is_trading_day("2026-09-27"), "Sunday should not be a trading day"

    # Known weekday (2026-09-28 is Monday)
    assert is_trading_day("2026-09-28"), "Monday 2026-09-28 should be a trading day"

    # Known NSE Holiday (2026-01-26 Republic Day)
    assert not is_trading_day("2026-01-26"), "Republic Day should not be a trading day"


def test_indian_formatting():
    """Verify Indian currency and number formatting."""
    assert format_indian_number(10000000) == "1,00,00,000.00"
    assert format_indian_currency(10000000) == "Rs 1,00,00,000.00"
    assert format_indian_currency(10000000, abbreviate=True) == "Rs 1.00 Cr"
    assert format_indian_currency(500000, abbreviate=True) == "Rs 5.00 Lakh"


def test_demo_pipeline_run(tmp_path):
    """Verify full --demo pipeline execution end-to-end."""
    res = run_pipeline(demo=True, config_path="config.yaml")

    assert "summary" in res
    assert "Last refresh completed" in res["summary"]

    status_file = "data/status.json"
    assert os.path.exists(status_file)

    with open(status_file, "r") as f:
        data = json.load(f)

    assert data["overall_status"] == "OK"
    assert len(data["steps"]) == 10
    for s in data["steps"]:
        assert s["status"] == "OK"
