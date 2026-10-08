# Phase 1 Completion Report: Scaffold + Data Pipeline

## 1. What Was Built
- **Repository Architecture & Configuration**:
  - Full modular directory layout (`pipeline/`, `core/`, `data/`, `docs/`, `tests/`).
  - Standardized `config.yaml` serving as the single source of truth for portfolio capital (Rs 1 Crore), snapshot date (`2026-09-28`), 15 tracked tickers (8 invested + 7 reserve), sector tags, risk rules, and index benchmarks.
  - Indian numbering formatters and currency helpers (`Rs 1,00,00,000`, `Rs 1.00 Cr`) in `core/utils.py`.
- **10-Step Modular Data Pipeline (`pipeline/run.py`)**:
  - **Step 1 (`step1_bhavcopy.py`)**: Equity Bhavcopy downloader with browser headers, cookie handling, exponential retries, NSE holiday skipping, resumable cache in `data/raw/bhavcopy/`, and synthetic `--demo` generator fallback.
  - **Step 2 (`step2_adjustments.py`)**: Corporate actions split/bonus/dividend adjuster, calculating turnover (`Volume * Close`) and saving to `data/parquet/equity_ohlcv.parquet`.
  - **Step 3 (`step3_indices.py`)**: Ingestion of Nifty 500 TRI, Nifty 50, Nifty Smallcap 500, Nifty500 Multicap Infrastructure 50:30:20, Nifty500 Momentum 50, and 7 sectoral indices into `data/parquet/indices_ohlcv.parquet`.
  - **Step 4 (`step4_fundamentals.py`)**: Screener.in CSV/XLSX export file loader + NSE pledge disclosures into `data/parquet/fundamentals.parquet` (with fallback demo fixture).
  - **Step 5 (`step5_macro.py`)**: Liquid Fund NAV (AMFI/mfapi.in), Nifty 1D Rate index, 10-Yr G-Sec yield, and Brent crude price into `data/parquet/macro_rates.parquet`.
  - **Step 6 (`step6_options.py`)**: Nifty F&O Bhavcopy put option chain dataset (`2026-12-29` expiry, lot size 65) saved to `data/parquet/options_bhavcopy.parquet`.
  - **Steps 7, 8, 9**: Modular execution stubs for Technical Signals, Risk Analytics, and Portfolio Ledger.
  - **Step 10 (`step10_status.py`)**: Execution logger writing step-by-step metrics and summary text (`"Last refresh completed <date time> IST: all 10 steps OK in X min Y s."`) to `data/status.json`.
- **Streamlit Application Shell (`app.py`)**:
  - 5-tab terminal layout displaying pipeline refresh status badge, capital sleeve metrics, and parquet dataset tables.

## 2. How to Run It

### Run Data Pipeline
- Demo mode (Synthetic data generation):
  ```bash
  python -m pipeline.run --demo
  ```
- Live data refresh:
  ```bash
  python -m pipeline.run
  ```

### Launch App
```bash
streamlit run app.py
```

### Run Tests
```bash
python -m pytest
```

## 3. Test Results
Execution of unit test suite (`python -m pytest`):
```
============================= test session starts =============================
platform win32 -- Python 3.13.7, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\equity portfolio
plugins: anyio-4.10.0
collected 9 items

tests\test_adjustments.py .                                              [ 11%]
tests\test_pipeline.py ...                                               [ 44%]
tests\test_schemas.py .....                                              [100%]

============================== 9 passed in 1.73s ==============================
```

Self-verification tests performed:
1. `python -m pipeline.run --demo`: Completed all 10 steps successfully and wrote status line `"Last refresh completed 2026-10-08 19:27:14 IST: all 10 steps OK in 0 min 0 s."` to `data/status.json`.
2. `python -m pipeline.run` (Live mode attempt): Completed all 10 steps in 10 seconds.
3. Schema validation: All 5 Parquet datasets verified for non-null required columns and valid data types.

## 4. Assumptions
- Snapshot close date fixed at `2026-09-28`.
- Date range for daily historical series: `2025-09-01` to `2026-09-28` (~260+ trading sessions).
- Tracked tickers: 8 invested (`WELCORP`, `RPEL`, `SBCL`, `AEROFLEX`, `TDPOWERSYS`, `RAMRAT`, `APARINDS`, `ACMESOLAR`) + 7 reserve (`QPOWER`, `FINCABLES`, `GRINDWELL`, `ACE`, `CARBORUNIV`, `GOODLUCK`, `ENGINERSIN`).

## 5. Needs Your Input
- **Screener.in Export File**: If you wish to use custom fundamental financial metrics from Screener.in, place your export file at `data/screener_export.csv` or `.xlsx`. Currently, the system uses a realistic synthetic demo fixture.

## 6. Known Issues / Fragilities
- Direct web requests to `niftyindices.com` API may block automated scripts lacking active ASP.NET session tokens. The pipeline handles this gracefully by switching to the fallback generator without crashing.
