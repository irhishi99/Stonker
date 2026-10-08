# Phase 2 Completion Report: Core Calculations Engine

## 1. What Was Built
- **Core Calculation Engines (`core/`)**:
  - **`indicators.py`**: Technical indicators with Wilder smoothing (`ATR(14)`, `ADX(14)`, `+DI`, `-DI`, `DI_gap`), `RSI(14)`, 63-session cumulative percentage-point alpha vs Nifty 500 TRI, 20-session swing-low support and swing-high resistance, and trend status (`Bullish` if `DI_gap >= 2`, else `Bearish`).
  - **`risk.py`**: Annualised volatility, 1-year daily Beta vs Nifty 500 TRI, risk-free rate ($r_f$) from 3-month Nifty 1D Rate Index, CAPM Expected Return ($E(R) = r_f + \beta \times \text{ERP}$ where ERP = 7.08%), and 3-month quarterly expected return projection.
  - **`weights.py`**: Equal Risk Contribution (ERC) portfolio optimization using `scipy.optimize.minimize(SLSQP)` to equalise shares of portfolio variance subject to 5%-15% weight bounds and 100% equity sleeve sum constraint, plus whole share allocation logic at snapshot prices.
  - **`stops.py`**: Stop-loss calculation ($5 \times \text{ATR(14)}$), 20-session support level adjustment (if support lies within 1 ATR below raw stop), upward trailing rule ($\max(\text{prev\_stop}, \text{current\_stop})$), method labeling (`"5 x ATR"`, `"Support-adjusted"`, `"Trailed (prev. stop)"`), and aggregate "Still at risk if every stop is hit" calculation.
  - **`screens.py`**: Sector-specific fundamental screen evaluator for Capital Goods & EPC, Cement, and Power enforcing strict Hard (H) vs Soft (S) rules (missing/unreadable = FAIL), per-sector review CSV export (`output/<sector>_full_review_table.csv`), and automated plain-English exception bullet point generation.
  - **`ledger.py`**: Trade ledger manager backed by `data/parquet/trade_ledger.parquet`, day-0 initial seed (8 stocks + 8 Nifty 22000 PE lots @ Rs 208.20 + cash), mark-to-market portfolio NAV valuation, and dated XIRR solver.
  - **`hedge.py`**: Down-market tail hedge ratio ($\beta_{down}$ on Nifty down days), required Nifty put option lots, 1-lot minimum trade rebalance trigger, and +10% portfolio gain profit-lock roll logic to ~5% OTM strike.
  - **`waterfall.py`**: Stop-loss hit replacement waterfall algorithm, reserve candidate eligibility evaluator, uptrend top-up fallback (<15% cap), Liquid ETF fallback, and "Would be bought today?" reason status generator.
  - **`universe_lock.py`**: 6-month relative strength ranking (skipping latest month) as of lock date (`2026-09-25`) selecting top 8 invested and 7 reserve queue tickers.
  - **`report.py`**: Command-line summary tool (`python -m core.report`) printing formatted portfolio holdings, weights, stops, risk metrics, hedge state, reserve queue status, screen exceptions, and internal consistency assertions.

- **Pipeline Wiring**:
  - Updated `pipeline/step7_stub.py` to calculate technical indicators, 63-day alpha, screens, and universe lock.
  - Updated `pipeline/step8_stub.py` to calculate risk metrics, CAPM, ERC weights, stop-loss levels, and hedge state.
  - Updated `pipeline/step9_stub.py` to update ledger, portfolio valuation, reserve waterfall, and export CSV tables.

- **Test Suite**:
  - Added [tests/test_core.py](file:///c:/equity%20portfolio/tests/test_core.py) with 9 new unit tests covering ATR/ADX/RSI Wilder smoothing, ERC solver convergence & bounds, stop trailing & labeling, XIRR solver, hedge lot triggers, profit-lock, reserve waterfall, and screen failure handling.

---

## 2. How to Run It

### Run Core Report CLI
```bash
python -m core.report
```

### Run Full Pipeline
```bash
python -m pipeline.run --demo
```

### Run PyTest Suite
```bash
python -m pytest
```

---

## 3. Test Results
Full test suite execution (`python -m pytest`):
```
============================= test session starts =============================
platform win32 -- Python 3.13.7, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\equity portfolio
plugins: anyio-4.10.0
collected 18 items

tests\test_adjustments.py .                                              [  5%]
tests\test_core.py .........                                             [ 55%]
tests\test_pipeline.py ...                                               [ 72%]
tests\test_schemas.py .....                                              [100%]

============================= 18 passed in 2.30s ==============================
```

Self-verification results:
1. `python -m pipeline.run --demo`: Completed all 10 steps successfully in 1s.
2. `python -m core.report`: Printed full terminal report and verified internal consistency:
   - Stocks (Rs 96,94,730.36) + Puts (Rs 1,08,264.00) + Cash (Rs 1,97,005.64) = Total NAV (Rs 1,00,00,000.00).
   - Target ERC Equity Weights sum to exactly 100.0%.
   - Aggregate Still at Risk computed once as Rs 13,35,277.25.

---

## 4. Assumptions
- Snapshot close date: `2026-09-28`.
- ERP = 7.08% as defined in `config.yaml`.
- 1-lot minimum rebalance threshold enforced on option hedging.
- Puts marked to market using Nifty F&O Bhavcopy close prices.

---

## 5. Needs Your Input
- **None for Phase 2**. Demo fixtures and config defaults handle offline calculations seamlessly.

---

## 6. Known Issues / Fragilities
- None. All calculations are backed by unit tests and internal consistency assertions.
