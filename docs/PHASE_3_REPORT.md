# Phase 3 Completion Report: Streamlit App Shell & Tabs 1-3

## 1. What Was Built
- **Streamlit Application UI Shell (`app.py`)**:
  - Full responsive Streamlit UI layout reading precomputed datasets from `data/parquet/` via `@st.cache_data`.
  - Light theme styling, custom CSS metrics cards, green/red gain/loss highlighting, and mobile-friendly containers.
  - **Standardized Header Component** rendered on every tab:
    - Main Title: *"Indian Equity Portfolio Management Terminal"*
    - Subtitle: *"Coursework: Security Analysis & Portfolio Management (SAPM) / Derivatives · IIM Bodh Gaya · Infrastructure & Capex Portfolio · Benchmark: Nifty 500 TRI"*
    - Data Timestamps: Prices, fundamentals, and benchmark TRI dates.
    - Refresh Policy Note: *"Refreshed automatically every weekday evening after the NSE close (about 7:30 pm IST)"*
    - Pipeline status summary line badge from `data/status.json`.
    - Prominent **"DEMO MODE ACTIVE"** banner whenever synthetic data is in use.
  - **Footer Disclaimer**: *"Educational project for MBA coursework (Security Analysis & Portfolio Management / Derivatives, IIM Bodh Gaya). Not investment advice."*

- **Tab 1: Portfolio Overview**:
  - **Hero Card**: Total Portfolio NAV formatted in Indian notation (`format_indian_currency`), P&L since 28-Sep-2026 snapshot close (Rs and %), breakdown into Equity Sleeve, Nifty Puts, and Reserve Cash.
  - **KPI Comparison Row**:
    - Equivalent Rs 1 Crore in Nifty 500 TRI (with "+/- Rs X ahead/behind" delta chip).
    - Equivalent Rs 1 Crore in Liquid Fund (with "+/- Rs Y ahead" delta chip).
    - Aggregate Still-at-Risk if all stops hit (with explanation tooltip).
    - Annualised XIRR %.
  - **Status Lines**: Profit-lock progress bar (+2.0% current gain, 8.0 pp to go until +10% strike roll trigger) and Downside Put Hedge ratio status (8 lots held vs 0 required).
  - **Interactive Plotly Performance Chart**: Indexed 1-year performance comparison (Portfolio vs Nifty 500 TRI vs Liquid Fund).
  - **Expanders**: Detailed holdings table, interactive editable Trade Ledger (`st.data_editor` with parquet persistence), copyable WhatsApp group update text block, and Q2 earnings calendar with estimated dates flagged.
  - **Universe & Sector Breakdown**: Locked list badge (15 tracked · 8 invested, 7 reserve frozen as of 2026-09-25 lock date), sector-coded holdings table (Price, Volatility %, CAPM 1Y & 3M Expected Return, Weight %, Shares, Value, Stop-Loss price, % below, Stop method, ADX, 63d RS Alpha, RSI, Support/Resistance), and technical caption.
  - **Reserve List & Replacement Waterfall Table**: 7 reserve stocks with 6-month RS, DI gap trend, and "Would be bought today?" reason code.
  - **Fundamental Screen Exceptions**: Plain-English bullet list of screen failures.

- **Tab 2: Fundamentals**:
  - Comprehensive 15-stock fundamental metrics table (Market Cap Rs Cr, ROCE %, Debt/Equity, Operating Cash Flow Rs Cr, OPM %, Interest Cover, Pledged %, Median Turnover Rs Cr, YoY Profit Growth %, Pass/Fail status).
  - Source attribution note (Screener.in export & NSE pledge disclosures).
  - 3-Column Fundamental Safety Screen Rules layout (Cement, Capital Goods & EPC, Power) listing tagged `(HARD)` vs `(soft)` rules and explanation box detailing Hard (mandatory) vs Soft (guideline) rules.

- **Tab 3: Technicals**:
  - 15-stock technical summary table (Symbol, Invested/Reserve Status, Sector, Price, RSI, ADX, Trend Direction).
  - **Stock Technical Deep-Dive**: Ticker selection dropdown, 1-year Plotly historical closing price chart with dashed green 20-session swing-low support line and dashed red 20-session swing-high resistance line titled `<Name> (<TICKER>) - 1-Year Historical Closing Price & Key Levels`, and metrics breakdown cards.

- **Tabs 4 & 5 Placeholders**:
  - `🛡️ Risk & Hedging` (Phase 4 placeholder).
  - `📈 Performance` (Phase 5 placeholder).

- **Automated Testing Suite**:
  - Added [tests/test_app.py](file:///c:/equity%20portfolio/tests/test_app.py) utilizing `streamlit.testing.v1.AppTest` to verify `app.py` renders cleanly across all tabs without unhandled exceptions.

---

## 2. How to Run It

### Launch Streamlit Terminal App
```bash
streamlit run app.py
```

### Run Full PyTest Suite (Including Streamlit AppTest)
```bash
python -m pytest
```

---

## 3. Test Results
Execution of complete test suite (`python -m pytest`):
```
============================= test session starts =============================
platform win32 -- Python 3.13.7, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\equity portfolio
plugins: anyio-4.10.0
collected 20 items

tests\test_adjustments.py .                                              [  5%]
tests\test_app.py ..                                                     [ 15%]
tests\test_core.py .........                                             [ 60%]
tests\test_pipeline.py ...                                               [ 75%]
tests\test_schemas.py .....                                              [100%]

============================= 20 passed in 4.66s ==============================
```

Self-verification results:
1. `streamlit.testing.v1.AppTest`: 2 test cases executed cleanly with 0 exceptions.
2. Headless launch: Streamlit server started cleanly on `http://localhost:8501`.
3. Trade ledger edits persist to `data/parquet/trade_ledger.parquet`.
4. Zero calculation logic in `app.py` — 100% precomputed data loaded via `st.cache_data`.

---

## 4. Assumptions
- Streamlit theme set to light theme with custom CSS container styling.
- All monetary values formatted using Indian numbering system (`Rs 1,00,00,000.00` / `Rs 1.00 Cr`).

---

## 5. Needs Your Input
- **None for Phase 3**. The UI shell runs seamlessly on precomputed parquet datasets.

---

## 6. Known Issues / Fragilities
- None.
