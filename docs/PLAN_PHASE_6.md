# Phase 6 Plan: Automation, Deployment & Comprehensive QA

## Overview
Phase 6 delivers automated data pipeline refresh via GitHub Actions (`.github/workflows/refresh.yml`), Streamlit Community Cloud deployment configuration (`.streamlit/config.toml`, `docs/DEPLOY.md`), staleness and error recovery banners in `app.py`, automated cross-tab consistency verification (`tests/test_consistency.py`), and finalized production documentation (`README.md`, `docs/ASSUMPTIONS.md`, `docs/PHASE_6_REPORT.md`).

## Key Deliverables & Implementation Plan

### 1. GitHub Actions Refresh Workflow (`.github/workflows/refresh.yml`)
- Schedule: Weekdays at 14:00 UTC / 19:30 IST (`cron: '0 14 * * 1-5'`).
- Manual trigger: `workflow_dispatch`.
- Steps:
  1. Checkout repository with Git LFS / standard options.
  2. Setup Python 3.11.
  3. Install dependencies from `requirements.txt`.
  4. Run `python -m pipeline.run` with retry logic for network requests.
  5. Commit updated `data/` and `output/` files back to `main`/`master` branch.
  6. Fail loudly on non-zero exit code or step error in `data/status.json`.
- Local YAML validation via Python `yaml.safe_load`.

### 2. Staleness Handling & Error Recovery in UI (`app.py`)
- Check latest date in `equity_ohlcv.parquet` against current date / last trading day using `is_trading_day()`.
- Display a warning banner if data is stale (e.g., > 1 trading day old).
- Display a prominent error banner if `data/status.json` contains step failures, listing failed step numbers and error messages.

### 3. Streamlit Cloud Readiness & Deployment Guide
- `.streamlit/config.toml`: Light theme, wide layout, primary color `#2563EB`.
- `docs/DEPLOY.md`: Step-by-step instructions for deploying to Streamlit Community Cloud, secrets management, repository settings, and UptimeRobot keep-alive ping setup.

### 4. Cross-Tab Consistency Test Suite (`tests/test_consistency.py`)
- Automated PyTest module asserting exact metrics consistency across tabs:
  - Total Portfolio NAV (Overview == Risk & Hedging == Performance Live column).
  - Aggregate Still-at-Risk amount (Overview == Risk & Hedging Tab 4 Section 8).
  - Annualised XIRR (Overview == Performance Live column).
  - Portfolio Beta (Risk & Hedging == Performance 1-Year Beta).
  - Target Equity Weights sum to 100.0%.
  - All monetary values formatted in Indian numbering notation.

### 5. Production Documentation (`README.md`, `docs/ASSUMPTIONS.md`, `docs/PHASE_6_REPORT.md`)
- Update `README.md` with complete instructions for local setup, pipeline runs, trade ledger editing, stock universe customization, data source fragilities, assumptions, limitations, and SAPM / Derivatives disclaimer.
- Update `docs/ASSUMPTIONS.md` with full consolidated system assumptions.
- Generate `docs/PHASE_6_REPORT.md` summarizing QA test results, deployment readiness, and manual user steps.
