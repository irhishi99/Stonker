# Phase 3 Plan: Streamlit Application Shell & Tabs 1-3

## Overview
Phase 3 builds the complete user interface for the Indian Equity Portfolio Management Terminal in `app.py` and modular tab components under `ui/` (or structured functions in `app.py`). It reads precomputed datasets from `data/parquet/` via `st.cache_data`, renders responsive Streamlit UI elements formatted in Indian numbering notation, and includes automated testing via `streamlit.testing.v1.AppTest`.

## UI Structure & Layout Plan

### 1. Global Shell & Header (`app.py`)
- Light theme aesthetics, custom CSS for KPI cards, green/red indicator badges, and mobile responsiveness.
- Common header rendered on every tab:
  - Terminal title: "Indian Equity Portfolio Management Terminal"
  - Coursework subtitle: "Coursework: Security Analysis & Portfolio Management (SAPM) / Derivatives · IIM Bodh Gaya · Infrastructure & Capex Portfolio · Benchmark: Nifty 500"
  - Data timestamps: Prices through snapshot date, Fundamentals fetch stamp, Benchmark TRI stamp.
  - Refresh policy note: "Refreshed automatically every weekday evening after the NSE close (about 7:30 pm IST)"
  - Status summary badge from `data/status.json`.
  - "Demo Data Active" warning banner whenever demo data is in use.
- Footer disclaimer: "Educational project for MBA coursework (SAPM / Derivatives, IIM Bodh Gaya). Not investment advice."

### 2. Tab 1: Portfolio Overview (`render_tab1`)
- **Hero Card**: Total NAV, P&L since 2026-09-28 snapshot close (Rs and %), breakdown into Stocks, Put Options, Cash.
- **KPI Comparison Row**:
  - Nifty 500 TRI benchmark equivalent (with "+/- Rs X ahead/behind" chip).
  - Liquid Fund equivalent (with "+/- Rs Y ahead/behind" chip).
  - Aggregate Still-at-Risk if all stops hit (with tooltip explanation).
  - Annualised XIRR %.
- **Status Indicators**: Profit-lock progress bar / pp to trigger, Hedge ratio (lots held vs lots needed).
- **Comparative Line Chart**: Plotly chart of Portfolio vs Nifty 500 TRI vs Liquid Fund indexed to Rs Lakh / 100.
- **Expanders**:
  - Holdings Table (detailed P&L per stock).
  - Interactive Trade Ledger (`st.data_editor` to view/edit trades and save back to parquet).
  - Copyable WhatsApp group update summary.
  - Q2 Results Calendar (with estimated dates flagged).
- **Portfolio Constituents Table**: Sector badges, Ticker/Name, Price, Volatility, Expected Return (CAPM 1Y & 3M), Weight (%, shares, Rs), Stop-loss (price, % below, method), ADX, 63d RS Alpha, RSI, Support/Resistance.
- **Reserve List Table**: 7 reserve stocks with 6-month RS, DI gap trend, "Would be bought today?" status & reason.
- **Screen Exceptions**: Plain-English bullet list of fundamental exceptions + config theme-fit notes.

### 3. Tab 2: Fundamentals (`render_tab2`)
- Title: "Fundamental Analysis & Quality Screening".
- 15-stock comprehensive fundamental metrics table with pass/fail badges per rule.
- Screener.in & NSE pledge disclosure source attribution note.
- "Fundamental Safety Screen (current-year, per sector)" 3-column layout (Cement, Capital Goods & EPC, Power) listing tagged (HARD) vs (soft) rules and an explanation of Hard vs Soft rule philosophy.

### 4. Tab 3: Technicals (`render_tab3`)
- Title: "Quantitative Technical Indicators & Price Structure".
- 15-stock technical summary table (Symbol, Invested/Reserve Status, Sector, Price, RSI(14), ADX(14), Trend Direction with green/red background).
- Interactive Stock Technical Deep-Dive:
  - Ticker selection dropdown.
  - 1-Year Plotly historical closing price chart with dashed green support and dashed red resistance lines.
  - Title: `<Name> (<TICKER>) - 1-Year Historical Closing Price & Key Levels`.

### 5. Tabs 4 & 5: Placeholders
- Tab 4 (`🛡️ Risk & Hedging`): Placeholder panel describing upcoming Phase 4 risk & option simulation tools.
- Tab 5 (`📈 Performance`): Placeholder panel describing upcoming Phase 5 performance attribution & factor regression tools.

## Testing & Verification Plan
- Create `tests/test_app.py` using `streamlit.testing.v1.AppTest` to run `app.py` headlessly, cycle through all 5 tabs, and verify zero unhandled exceptions.
- Test interactive trade ledger editing.
- Verify `docs/ASSUMPTIONS.md` and `docs/PHASE_3_REPORT.md`.
