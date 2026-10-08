"""
Main Data Pipeline Runner (`pipeline/run.py`).
Executes 10-step data refresh pipeline in sequence with timing logs and error handling.
"""

import sys
import time
import argparse
from typing import Dict, Any, List

from core.utils import load_config
from pipeline.step1_bhavcopy import run_step1
from pipeline.step2_adjustments import run_step2
from pipeline.step3_indices import run_step3
from pipeline.step4_fundamentals import run_step4
from pipeline.step5_macro import run_step5
from pipeline.step6_options import run_step6
from pipeline.step7_stub import run_step7
from pipeline.step8_stub import run_step8
from pipeline.step9_stub import run_step9
from pipeline.step10_status import run_step10


def run_pipeline(demo: bool = False, config_path: str = "config.yaml") -> Dict[str, Any]:
    """Run all 10 pipeline steps sequentially.

    Args:

        demo: If True, forces demo synthetic data generation.
        config_path: Path to configuration file.

    Returns:

        Final pipeline run summary payload.
    """
    config = load_config(config_path)
    step_logs: List[Dict[str, Any]] = []

    pipeline_start_time = time.time()
    step1_res = {}

    # Step 1: Equity Bhavcopy
    t0 = time.time()
    try:
        step1_res = run_step1(config, demo=demo)
        dur = time.time() - t0
        step_logs.append({
            "step_number": 1,
            "step_name": "Ingest Equity Bhavcopy",
            "status": "OK",
            "duration_seconds": round(dur, 3),
            "details": step1_res
        })
    except Exception as e:
        dur = time.time() - t0
        step_logs.append({
            "step_number": 1,
            "step_name": "Ingest Equity Bhavcopy",
            "status": "FAIL",
            "duration_seconds": round(dur, 3),
            "error": str(e)
        })

    # Step 2: Price Adjustments & Parquet Export
    t0 = time.time()
    try:
        step2_res = run_step2(config, step1_res, demo=demo)
        dur = time.time() - t0
        step_logs.append({
            "step_number": 2,
            "step_name": "Corporate Adjustments & Parquet",
            "status": "OK",
            "duration_seconds": round(dur, 3),
            "details": step2_res
        })
    except Exception as e:
        dur = time.time() - t0
        step_logs.append({
            "step_number": 2,
            "step_name": "Corporate Adjustments & Parquet",
            "status": "FAIL",
            "duration_seconds": round(dur, 3),
            "error": str(e)
        })

    # Step 3: Index Histories
    t0 = time.time()
    try:
        step3_res = run_step3(config, demo=demo)
        dur = time.time() - t0
        step_logs.append({
            "step_number": 3,
            "step_name": "Index Histories",
            "status": "OK",
            "duration_seconds": round(dur, 3),
            "details": step3_res
        })
    except Exception as e:
        dur = time.time() - t0
        step_logs.append({
            "step_number": 3,
            "step_name": "Index Histories",
            "status": "FAIL",
            "duration_seconds": round(dur, 3),
            "error": str(e)
        })

    # Step 4: Fundamentals Consolidation
    t0 = time.time()
    try:
        step4_res = run_step4(config, demo=demo)
        dur = time.time() - t0
        step_logs.append({
            "step_number": 4,
            "step_name": "Fundamentals Database",
            "status": "OK",
            "duration_seconds": round(dur, 3),
            "details": step4_res
        })
    except Exception as e:
        dur = time.time() - t0
        step_logs.append({
            "step_number": 4,
            "step_name": "Fundamentals Database",
            "status": "FAIL",
            "duration_seconds": round(dur, 3),
            "error": str(e)
        })

    # Step 5: Macro & Rates
    t0 = time.time()
    try:
        step5_res = run_step5(config, demo=demo)
        dur = time.time() - t0
        step_logs.append({
            "step_number": 5,
            "step_name": "Macro & Rates Ingestion",
            "status": "OK",
            "duration_seconds": round(dur, 3),
            "details": step5_res
        })
    except Exception as e:
        dur = time.time() - t0
        step_logs.append({
            "step_number": 5,
            "step_name": "Macro & Rates Ingestion",
            "status": "FAIL",
            "duration_seconds": round(dur, 3),
            "error": str(e)
        })

    # Step 6: Options Bhavcopy
    t0 = time.time()
    try:
        step6_res = run_step6(config, demo=demo)
        dur = time.time() - t0
        step_logs.append({
            "step_number": 6,
            "step_name": "Options Bhavcopy Ingestion",
            "status": "OK",
            "duration_seconds": round(dur, 3),
            "details": step6_res
        })
    except Exception as e:
        dur = time.time() - t0
        step_logs.append({
            "step_number": 6,
            "step_name": "Options Bhavcopy Ingestion",
            "status": "FAIL",
            "duration_seconds": round(dur, 3),
            "error": str(e)
        })

    # Step 7: Technical Signals (Stub)
    t0 = time.time()
    try:
        step7_res = run_step7(config, demo=demo)
        dur = time.time() - t0
        step_logs.append({
            "step_number": 7,
            "step_name": "Technical Signals (Stub)",
            "status": "OK",
            "duration_seconds": round(dur, 3),
            "details": step7_res
        })
    except Exception as e:
        dur = time.time() - t0
        step_logs.append({
            "step_number": 7,
            "step_name": "Technical Signals (Stub)",
            "status": "FAIL",
            "duration_seconds": round(dur, 3),
            "error": str(e)
        })

    # Step 8: Risk Analytics (Stub)
    t0 = time.time()
    try:
        step8_res = run_step8(config, demo=demo)
        dur = time.time() - t0
        step_logs.append({
            "step_number": 8,
            "step_name": "Risk & Hedging Analytics (Stub)",
            "status": "OK",
            "duration_seconds": round(dur, 3),
            "details": step8_res
        })
    except Exception as e:
        dur = time.time() - t0
        step_logs.append({
            "step_number": 8,
            "step_name": "Risk & Hedging Analytics (Stub)",
            "status": "FAIL",
            "duration_seconds": round(dur, 3),
            "error": str(e)
        })

    # Step 9: Portfolio Ledger (Stub)
    t0 = time.time()
    try:
        step9_res = run_step9(config, demo=demo)
        dur = time.time() - t0
        step_logs.append({
            "step_number": 9,
            "step_name": "Portfolio Ledger & Attribution (Stub)",
            "status": "OK",
            "duration_seconds": round(dur, 3),
            "details": step9_res
        })
    except Exception as e:
        dur = time.time() - t0
        step_logs.append({
            "step_number": 9,
            "step_name": "Portfolio Ledger & Attribution (Stub)",
            "status": "FAIL",
            "duration_seconds": round(dur, 3),
            "error": str(e)
        })

    # Step 10: Status Writer
    total_duration = time.time() - pipeline_start_time
    try:
        step10_res = run_step10(config, step_logs, total_duration)
        summary = step10_res.get("summary_line", "Pipeline refresh complete.")
        all_logs = step10_res.get("full_step_logs", step_logs)
    except Exception as e:
        summary = f"Pipeline failed during step 10: {str(e)}"
        all_logs = step_logs

    print(summary)

    return {
        "summary": summary,
        "step_logs": all_logs
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Indian Equity Portfolio Management Terminal - Data Pipeline")
    parser.add_argument("--demo", action="store_true", help="Run pipeline in synthetic demo mode")
    parser.add_argument("--config", type=str, default="config.yaml", help="Path to config file")

    args = parser.parse_args()
    run_pipeline(demo=args.demo, config_path=args.config)
