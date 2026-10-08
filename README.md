# Indian Equity Portfolio Management Terminal

An end-to-end portfolio management, risk analytics, option hedging, and performance attribution terminal built for MBA coursework (*Security Analysis & Portfolio Management / Derivatives*, IIM Bodh Gaya).

The terminal manages a **Rs 1 Crore Infrastructure & Capex Portfolio** of Indian stocks, hedged with Nifty put options and benchmarked against the **Nifty 500 TRI**.

---

## 🏗 Architecture & Stack
- **Python Version**: Python 3.11+
- **Frontend / UI**: Streamlit (5 interactive tabs: Portfolio Overview, Fundamentals, Technicals, Risk & Hedging, Performance)
- **Data Engineering & Storage**: Apache Parquet (`pyarrow`), Pandas, NumPy, SciPy, Statsmodels, Plotly, PyYAML
- **Automation**: GitHub Actions (`.github/workflows/refresh.yml`)
- **Testing**: PyTest (`streamlit.testing.v1.AppTest` UI testing + cross-tab consistency suite)

```
equity portfolio/
├── app.py                     # Streamlit UI Entrypoint (reads precomputed parquet data)
├── config.yaml                # Global Configuration (Single Source of Truth)
├── requirements.txt           # Pinned Python Dependencies
├── .gitignore                 # Git ignore specification
├── .streamlit/                # Streamlit configuration (theme, layout)
│   └── config.toml
├── .github/workflows/         # Automated Pipeline Refresh Workflow
│   └── refresh.yml
├── pipeline/                  # Modular 10-step Data Pipeline
│   ├── run.py                 # Pipeline Master Execution Runner
│   ├── step1_bhavcopy.py      # NSE Equity Bhavcopy Ingestion / Demo Generator
│   ├── step2_adjustments.py   # Corporate Action Adjustments (Splits/Bonuses/Dividends)
│   ├── step3_indices.py       # Benchmark & Sectoral Index Histories
│   ├── step4_fundamentals.py  # Screener.in + NSE Pledge Disclosures Loader
│   ├── step5_macro.py        # Liquid Fund NAV, Nifty 1D Rate, 10Y G-Sec Yield, Brent Crude
│   ├── step6_options.py      # Nifty F&O Put Options Chain Bhavcopy Data
│   ├── step7_stub.py         # Technical Signals, 63d Alpha & Screens
│   ├── step8_stub.py         # Risk Analytics, ERC Weights, Stops & Option Hedge
│   ├── step9_stub.py         # Trade Ledger, Valuation, Waterfall & Report Generator
│   └── step10_status.py       # Pipeline Logger & Status File Writer
├── core/                      # Quantitative Finance Models & Calculation Engines
│   ├── indicators.py          # ATR(14), ADX(14), RSI(14) Wilder Smoothing & Alpha
│   ├── risk.py                # Annualised Volatility, Beta vs Nifty 500, CAPM E(R)
│   ├── weights.py             # Equal Risk Contribution (ERC) SLSQP Portfolio Optimization
│   ├── stops.py               # 5x ATR Stop-Loss, 20D Support Adjustment & Trailing
│   ├── screens.py             # Fundamental Hard (H) vs Soft (S) Sector Screening
│   ├── ledger.py              # Trade Ledger Management, Mark-to-Market NAV, XIRR
│   ├── hedge.py               # Down-Market Beta, Option Lot Trigger & Profit-Lock Roll
│   ├── waterfall.py           # Stop-Loss Replacement Waterfall & Reserve Queue Status
│   ├── universe_lock.py       # Lock Date 6M Relative Strength Ranking
│   ├── regressions.py         # Single-Index, 4-Factor Capex, Macro & AR(1) Diagnostics
│   ├── risk_reward.py         # 3-Month Risk-Reward Analytics
│   ├── hedge_plan.py          # Min-Variance Hedge Ratio, Put Strikes & Downside Scenarios
│   ├── performance.py        # 4-Window Performance Attribution & Capture Ratios
│   ├── frontier.py           # Modern Portfolio Theory (MPT) Frontier, GMVP & CML/CAL Lines
│   ├── utils.py               # Indian Number Formatters & Trading Day Calendar
│   └── report.py              # Command-Line Summary Report Script (`python -m core.report`)
├── data/
│   ├── raw/                   # Raw cached data & CSV downloads
│   ├── parquet/               # Production Parquet datasets
│   └── status.json            # Pipeline execution status & duration metrics
├── output/                    # Sector review CSV tables & status reports
├── docs/                      # Documentation, Plans, & Deployment Guides
│   ├── PLAN_PHASE_1.md - PLAN_PHASE_6.md
│   ├── PHASE_1_REPORT.md - PHASE_6_REPORT.md
│   ├── ASSUMPTIONS.md
│   └── DEPLOY.md
└── tests/                     # Automated Test Suite (35 Unit Tests)
    ├── test_pipeline.py
    ├── test_adjustments.py
    ├── test_schemas.py
    ├── test_core.py
    ├── test_regressions.py
    ├── test_performance.py
    ├── test_consistency.py
    └── test_app.py
```

---

## 📡 Data Sources, Direct URL Patterns & Fragilities

| Data Domain | Data Provider / Source | Target Endpoint / URL Pattern | Known Fragility & Resilience Fallback |
| :--- | :--- | :--- | :--- |
| **Equity Bhavcopy** | National Stock Exchange (NSE India) | `https://archives.nseindia.com/content/historical/EQUITIES/{YYYY}/{MMM}/cm{DD}{MMM}{YYYY}bhav.csv.zip` or `yfinance` API (`.NS`) | NSE blocks requests missing browser user-agent / session cookies (HTTP 403/429). **Fallback**: Auto-resumes via `yfinance` or synthetic `--demo` generator. |
| **Indices Histories** | Nifty Indices (`niftyindices.com`) | `https://www.niftyindices.com/api/indices/historicaldata` or `yfinance` (`^NSEI`) | NiftyIndices requires dynamic ASP.NET session tokens. **Fallback**: `yfinance` download or synthetic index generator calibrated to historical volatility. |
| **Fundamentals** | Screener.in Export & NSE Disclosures | Custom CSV/XLSX export file at `data/screener_export.csv` | Missing export file or schema change. **Fallback**: Realistic synthetic Screener dataset for all 15 tracked tickers. |
| **Macro & Rates** | AMFI India / `mfapi.in` & Yahoo Finance | AMFI Scheme API: `https://api.mfapi.in/mf/{scheme_code}` \| Brent Crude: `yfinance` (`BZ=F`) | Network rate limits on public APIs. **Fallback**: Default G-Sec yield (6.8%) and synthetic macro rate path. |
| **Options Bhavcopy** | NSE F&O Bhavcopy Archive | `https://archives.nseindia.com/content/historical/DERIVATIVES/{YYYY}/{MMM}/fo{DD}{MMM}{YYYY}bhav.csv.zip` | Archive unavailability for historical F&O contracts. **Fallback**: Black-Scholes synthetic put option chain simulation. |

---

## 🚀 Quick Start Guide

### 1. Install Dependencies
```bash
python -m pip install -r requirements.txt
```

### 2. Run Data Pipeline
To execute the pipeline in offline **Demo Mode** (synthetic data generation):
```bash
python -m pipeline.run --demo
```

To attempt a **Live Data Refresh**:
```bash
python -m pipeline.run
```

### 3. Print CLI Portfolio Summary Report
```bash
python -m core.report
```

### 4. Launch Streamlit Application
```bash
streamlit run app.py
```

### 5. Run Full Automated Test Suite
```bash
python -m pytest
```

---

## ✏️ How to Modify Trades or Customise Tickers

### Adding / Editing a Trade in the Ledger
1. Open the app via `streamlit run app.py` and navigate to Tab 1 (`📊 Portfolio Overview`).
2. Expand **"📜 Trade Ledger (Interactive)"**.
3. Use the `st.data_editor` table to add, modify, or delete trade rows (Date, Instrument, Side, Qty, Fill_Price).
4. Click **"Save Trade Ledger Changes"**. The app will overwrite `data/parquet/trade_ledger.parquet` and instantly recompute NAV, P&L, and XIRR across all tabs.

### Replacing the Stock Universe
1. Open `config.yaml`.
2. Edit `universe.invested_tickers` or `universe.reserve_queue` with your target symbols and sector tags.
3. Re-run the data refresh pipeline (`python -m pipeline.run --demo`). All downstream screens, weights, stops, regressions, and frontier models will automatically update.

---

## 📋 Consolidated System Assumptions

1. **Portfolio Capital & Sleeve Partitioning**:
   - Total Portfolio Capital: Rs 1,00,00,000 (1 Crore).
   - Equity Sleeve: 97% (Rs 97,00,000 target).
   - Reserve Cash: 3% (Rs 3,00,00,000 target minus initial option put premiums).
2. **Snapshot & Lock Dates**:
   - Snapshot Date: `2026-09-28` (close).
   - Universe Lock Date: `2026-09-25`.
3. **Numbering & Currency Notation**:
   - All financial figures formatted in Indian numbering system (Lakhs, Crores, `Rs` symbol).
4. **Hedge Plan Policy**:
   - Tail-risk protection via OTM Nifty Put Options (`2026-12-29` expiry, lot size 65).
   - Minimum 1-lot trade threshold enforced. Profit-lock roll triggered at +10% portfolio gain.

---

## 🔒 Educational-Use Disclaimer
*This repository was created strictly for educational purposes as part of MBA coursework in Security Analysis & Portfolio Management (SAPM) and Derivatives at IIM Bodh Gaya. It is intended for academic research only and does not constitute financial or investment advice.*
