# Phase 1 Plan: Scaffold + Data Pipeline

## Overview
Phase 1 establishes the repository architecture, configuration schema, data pipeline execution runner (`pipeline/run.py`), and data ingestion/demo generators for the Indian Equity Portfolio Management Terminal.

## Steps & Deliverables

### 1. Repository Setup & Configuration
- Initialize Git repository, `.gitignore`, and project folder layout (`pipeline/`, `core/`, `data/`, `docs/`, `output/`, `research/`, `tests/`, `.github/workflows/`).
- Create `requirements.txt` with required dependencies: `streamlit`, `pandas`, `numpy`, `scipy`, `statsmodels`, `plotly`, `matplotlib`, `pyarrow`, `pyyaml`, `requests`, `pytest`, `yfinance`.
- Create `config.yaml` containing all system parameters (capital, dates, ticker universe, sector tags, indicator defaults, rate assumptions, option strike info).

### 2. Data Pipeline Architecture (`pipeline/run.py`)
- Modular pipeline executor supporting both live data fetch and synthetic `--demo` mode (defaulting to demo on live failure).
- Numbered execution pipeline (Steps 1 through 10).
- Timed execution tracking per step with JSON logging to `data/status.json`.
- Standardized summary text generation: `"Last refresh completed <date time> IST: all 10 steps OK in X min Y s."`

### 3. Pipeline Step Implementations
- **Step 1: Equity Bhavcopy Ingestion (`step1_bhavcopy.py`)**:
  - Download raw NSE Bhavcopy archives for 1+ year prior to snapshot date (`2025-09-01` to `2026-09-28`).
  - Browser-like HTTP headers, session cookie initialization, exponential retries.
  - Skip weekends and NSE official trading holidays.
  - Resumable cache layer in `data/raw/bhavcopy/`.
- **Step 2: Corporate Adjustments & Parquet Storage (`step2_adjustments.py`)**:
  - Adjust OHLCV data for splits, bonuses, and cash dividends using corporate actions database / fallback logic.
  - Compute daily turnover (`Volume * Close`).
  - Output standardized schema to `data/parquet/equity_ohlcv.parquet`.
- **Step 3: Index Histories (`step3_indices.py`)**:
  - Ingest Nifty 500 TRI, Nifty 50, Nifty Smallcap 500, Nifty500 Multicap Infra 50:30:20, Nifty500 Momentum 50, and sectoral indices (Capital Goods, Manufacturing, Energy, Infrastructure, Cement, Metal, Power).
  - Output standardized schema to `data/parquet/indices_ohlcv.parquet`.
- **Step 4: Fundamentals Data Consolidation (`step4_fundamentals.py`)**:
  - Load Screener.in CSV/XLSX export file and merge with NSE pledge disclosures.
  - Ingest key metrics: Market Cap, ROCE, OPM, Debt/Equity, Interest Cover, OCF, YoY Profit Growth, Pledged %.
  - Fall back to realistic demo fixture if screener export file is absent.
  - Output to `data/parquet/fundamentals.parquet`.
- **Step 5: Macro & Rates Ingestion (`step5_macro.py`)**:
  - Liquid fund NAV (`mfapi.in`), Nifty 1D Rate index, 10-Yr G-Sec Yield, Brent Crude oil price (`BZ=F`).
  - Output to `data/parquet/macro_rates.parquet`.
- **Step 6: Options Bhavcopy Ingestion (`step6_options.py`)**:
  - Nifty F&O Bhavcopy option chain data for held Nifty Puts (`2026-12-29` expiry, lot size 65) and nearby strikes.
  - Output to `data/parquet/options_bhavcopy.parquet`.
- **Steps 7, 8, 9**:
  - Modular stubs for future processing stages (Technical Signals, Risk Metrics, Portfolio Ledger).
- **Step 10: Pipeline Status Writer (`step10_status.py`)**:
  - Writes comprehensive run log and execution metrics to `data/status.json`.

### 4. Verification & Testing
- Unit tests (`tests/test_pipeline.py`, `tests/test_adjustments.py`, `tests/test_schemas.py`) covering holiday skipping, split adjustments, and Parquet schema validation.
- Command-line self-verification:
  - Demo run: `python -m pipeline.run --demo`
  - Live attempt run: `python -m pipeline.run` (handling blocks gracefully)
  - Unit tests: `pytest`
- Update `README.md`, `docs/ASSUMPTIONS.md`, and generate `docs/PHASE_1_REPORT.md`.
