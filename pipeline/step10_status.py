"""
Step 10: Pipeline Status Logger.
Compiles execution log and timing summary into data/status.json.
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, List


def run_step10(config: Dict[str, Any], step_logs: List[Dict[str, Any]], total_duration: float) -> Dict[str, Any]:
    """Execute Step 10: Log execution metrics and update data/status.json.

    Args:

        config: System configuration dictionary.
        step_logs: List of prior step execution dictionaries (Steps 1 to 9).
        total_duration: Total execution time in seconds.

    Returns:

        Status dictionary with metadata.
    """
    status_file = config.get("paths", {}).get("status_file", "data/status.json")
    os.makedirs(os.path.dirname(status_file), exist_ok=True)

    # Add Step 10 placeholder log to full steps array
    full_step_logs = list(step_logs)
    step10_entry = {
        "step_number": 10,
        "step_name": "Pipeline Status Logger",
        "status": "OK",
        "duration_seconds": 0.0,
        "details": {
            "status": "OK",
            "status_file": status_file
        }
    }
    full_step_logs.append(step10_entry)

    all_ok = all(log.get("status") == "OK" for log in full_step_logs)
    failed_steps = [log["step_number"] for log in full_step_logs if log.get("status") != "OK"]

    mins = int(total_duration // 60)
    secs = int(round(total_duration % 60))

    now_ist_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if all_ok:
        summary_line = f"Last refresh completed {now_ist_str} IST: all 10 steps OK in {mins} min {secs} s."
    else:
        summary_line = f"Last refresh completed {now_ist_str} IST: {len(failed_steps)} step(s) failed ({failed_steps}) in {mins} min {secs} s."

    step10_entry["details"]["summary_line"] = summary_line

    payload = {
        "timestamp_ist": now_ist_str,
        "total_duration_seconds": round(total_duration, 2),
        "overall_status": "OK" if all_ok else "FAIL",
        "summary_line": summary_line,
        "steps": full_step_logs
    }

    with open(status_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return {
        "status": "OK",
        "summary_line": summary_line,
        "status_file": status_file,
        "full_step_logs": full_step_logs
    }
