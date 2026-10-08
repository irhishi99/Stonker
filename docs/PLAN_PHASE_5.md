# Phase 5 Plan: Performance Attribution & Efficient Frontier

## Overview
Phase 5 implements comprehensive portfolio performance analytics, factor capture ratios, drawdown tracking, risk-adjusted metrics (Sharpe, Sortino, Treynor, Jensen's Alpha, Information Ratio), long-only efficient frontier optimization, Capital Market Line (CML) / Capital Allocation Line (CAL) visualization, and the interactive Streamlit Tab 5 (`📈 Performance`).

## Core Modules to Build in `core/`

1. **`core/performance.py`**:
   - Return compounding & annualization engine (compounded, simple, compounding effect).
   - Risk-adjusted ratios: Sharpe, Sortino (downside vol; `-` if no losing days), Treynor, Jensen's Alpha (annualised & period).
   - Drawdown & Capture Ratios: Max drawdown, Up-capture, Down-capture, Tracking error, Information ratio.
   - Multi-window Performance Table builder (`Live since snapshot`, `Last quarter (63 sessions)`, `6-month backtest`, `1-year backtest`).
   - Guarantees exact match for Live column portfolio return and XIRR vs Overview tab.

2. **`core/frontier.py`**:
   - Long-only Efficient Frontier solver (`scipy.optimize.minimize` SLSQP).
   - Global Minimum Variance Portfolio (GMVP) long-only ($\sum w_i = 1, w_i \ge 0$).
   - GMVP 5-15% limits ($\sum w_i = 1, 0.05 \le w_i \le 0.15$).
   - Tangency Portfolio (Maximum Sharpe ratio).
   - CML & CAL line generator ($r_f \to \text{Market}$ and $r_f \to \text{Tangency}$).
   - Effective Number of Stocks ($N_{eff} = 1/\sum w_i^2$).

## Streamlit Tab 5 UI (`app.py`)
- Section 1: Intro Text (Live vs Backtest explanation).
- Section 2: Conditional Yellow Warning Box (< 20 sessions indicator).
- Section 3: 4-Window Performance Attribution Table.
- Section 4: Formula Footnote & Definitions.
- Section 5: Growth of Rs 1 Crore Line Chart (1-Year Backtest).
- Section 6: Capital Market Line (CML) & Efficient Frontier Plotly Chart with markers for Portfolio (red star), Nifty 500 (blue square), Tangency (green diamond), GMVPs (purple triangles), Risk-Free (black dot), individual stock labels, and zoom detail.
- Section 7: GMVP vs Our Weights Summary Table & Weights Comparison Expander.

## Verification & Test Plan
- Unit tests in `tests/test_performance.py` covering Sharpe/Sortino/Treynor/Jensen math, capture ratios, GMVP bounds, and tangency Sharpe maximizer.
- AppTest in `tests/test_app.py` verifying Tab 5 rendering.
- Exact match assertion for Live column return and XIRR vs Overview tab.
- Warning box visibility test (< 20 vs >= 20 sessions).
