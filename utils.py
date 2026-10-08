"""
Core utilities: YAML config loading, Indian numbering formatters, and trading day helpers.
"""

import os
import yaml
from datetime import datetime, date
from typing import Any, Dict, List, Union


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Load system configuration from YAML file.

    Args:

        config_path: Path to the YAML configuration file.

    Returns:

        Dict containing configuration parameters.
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found at: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config


def format_indian_number(val: Union[int, float], decimals: int = 2) -> str:
    """Format a number according to the Indian numbering system (Lakhs, Crores).

    Args:

        val: Number to format.
        decimals: Number of decimal places.

    Returns:

        Formatted string with commas according to Indian numbering.
    """
    if val is None:
        return "N/A"

    is_negative = val < 0
    val = abs(val)

    parts = f"{val:.{decimals}f}".split(".")
    integer_part = parts[0]
    decimal_part = f".{parts[1]}" if decimals > 0 else ""

    if len(integer_part) <= 3:
        formatted_int = integer_part
    else:
        last_three = integer_part[-3:]
        remaining = integer_part[:-3]
        groups = []
        while remaining:
            groups.append(remaining[-2:])
            remaining = remaining[:-2]
        groups.reverse()
        formatted_int = ",".join(groups) + "," + last_three

    res = f"{formatted_int}{decimal_part}"
    return f"-{res}" if is_negative else res


def format_indian_currency(val: Union[int, float], abbreviate: bool = False, decimals: int = 2) -> str:
    """Format a monetary amount in Indian Rupees (Rs).

    Args:

        val: Amount in INR.
        abbreviate: If True, uses Cr/Lakh suffixes (e.g. Rs 1.00 Cr).
        decimals: Decimal precision.

    Returns:

        Formatted currency string.
    """
    if val is None:
        return "Rs N/A"

    if abbreviate:
        abs_val = abs(val)
        prefix = "-" if val < 0 else ""
        if abs_val >= 10000000:
            crores = val / 10000000.0
            return f"Rs {crores:.{decimals}f} Cr"
        elif abs_val >= 100000:
            lakhs = val / 100000.0
            return f"Rs {lakhs:.{decimals}f} Lakh"
        else:
            return f"Rs {format_indian_number(val, decimals)}"
    else:
        return f"Rs {format_indian_number(val, decimals)}"


# Official NSE holidays (approximate / standard list for 2025-2026 for pipeline skipping)
NSE_HOLIDAYS_2025_2026: List[str] = [
    # 2025
    "2025-01-26", "2025-02-26", "2025-03-14", "2025-03-31", "2025-04-10", "2025-04-14",
    "2025-04-18", "2025-05-01", "2025-08-15", "2025-08-27", "2025-10-02", "2025-10-21",
    "2025-10-22", "2025-11-05", "2025-12-25",
    # 2026
    "2026-01-26", "2026-03-03", "2026-03-26", "2026-04-03", "2026-04-14", "2026-05-01",
    "2026-08-15", "2026-09-15", "2026-10-02", "2026-10-20", "2026-11-10", "2026-12-25"
]


def is_trading_day(dt: Union[str, date, datetime]) -> bool:
    """Check if a date is a weekday and not an official NSE holiday.

    Args:

        dt: Date to check (string 'YYYY-MM-DD', date, or datetime).

    Returns:

        True if trading day, False otherwise.
    """
    if isinstance(dt, str):
        parsed_dt = datetime.strptime(dt, "%Y-%m-%d").date()
    elif isinstance(dt, datetime):
        parsed_dt = dt.date()
    else:
        parsed_dt = dt

    # Check weekend (5 = Saturday, 6 = Sunday)
    if parsed_dt.weekday() >= 5:
        return False

    date_str = parsed_dt.strftime("%Y-%m-%d")
    if date_str in NSE_HOLIDAYS_2025_2026:
        return False

    return True
