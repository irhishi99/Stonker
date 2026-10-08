# Phase 5 Completion Report: Performance Attribution & Efficient Frontier Tab

## 1. What Was Built
- **Core Calculation Engines (`core/`)**:
  - **`performance.py`**:
    - Compounded vs simple return annualization engine & compounding effect.
    - Risk-adjusted ratios: Sharpe Ratio, Treynor Ratio, Jensen's Alpha (annualised & period), Sortino Ratio (downside vol; `-` display when no losing days exist).
    - Drawdown & Capture Ratios: Max drawdown, Up-capture %, Down-capture %, Tracking error %, Information Ratio.
    - Standardized 4-window Performance Attribution Table (`Live since snapshot`, `Last quarter (63s)`, `6-Month Backtest`, `1-Year Backtest`).
    - Guarantees exact match for Live column portfolio return and XIRR vs Overview tab.
    - Fallback logic when live window sessions $n < 20$: uses 1-year daily beta (current weights) and populates `Beta estimated from` row.
  - **`frontier.py`**:
    - Modern Portfolio Theory (MPT) Efficient Frontier solver (`scipy.optimize.minimize` SLSQP).
    - Global Minimum Variance Portfolio (GMVP) long-only ($\sum w_i = 1.0, w_i \ge 0$).
    - GMVP 5–15% limits ($\sum w_i = 1.0, 0.05 \le w_i \le 0.15$).
    - Tangency Portfolio (Maximum Sharpe Ratio $\max \frac{w' \mu - r_f}{\sqrt{w' S w}}$).
    - Capital Market Line (CML) through Nifty 500 TRI ($r_f \to \text{Nifty 500}$).
    - Capital Allocation Line (CAL) through Tangency portfolio ($r_f \to \text{Tangency}$).
    - Effective Number of Stocks ($N_{eff} = 1 / \sum w_i^2$).

- **Interactive Streamlit Tab 5 (`📈 Performance` in `app.py`)**:
  - Section 1: Intro text explaining Live column (real portfolio from trade ledger: stocks + puts + cash) vs Backtest columns (simulated today's weights over past prices).
  - Section 2: Conditional Yellow Warning Box rendered when live sessions $< 20$ explaining annualization extrapolation, period return focus, 1-year beta fallback, and Sortino dash `-` display.
  - Section 3: 4-Window Performance Attribution Table (26 standardized metrics rows).
  - Section 4: Plain-English Formula Footnote Reference paragraph defining every metric.
  - Section 5: Growth of Rs 1 Crore Line Chart (1-Year Backtest: Portfolio vs Nifty 500 TRI starting at Rs 1,00,00,000).
  - Section 6: Capital Market Line (CML) & Efficient Frontier Plotly Chart with markers for:
    - Our Portfolio (Red Star)
    - Nifty 500 TRI (Blue Square)
    - Tangency Portfolio (Green Diamond)
    - GMVP Long-Only (Purple Triangle)
    - GMVP 5-15% (Purple Open Triangle)
    - Risk-Free Rate $r_f$ (Black Dot)
    - Individual 8 stock markers labelled with ticker names.
    - Ex-post CML caption explaining stock picking tailwinds.
  - Section 7: GMVP vs Our Weights Summary Table & Weights Comparison Matrix Expander.

- **Automated Testing Suite**:
  - Added [tests/test_performance.py](file:///c:/equity%20portfolio/tests/test_performance.py) with unit tests for Sharpe/Sortino/Treynor/Jensen math, capture ratios, GMVP bounds, and tangency Sharpe maximizer.
  - Updated [tests/test_app.py](file:///c:/equity%20portfolio/tests/test_app.py) verifying Tab 5 rendering with zero exceptions.

---

## 2. How to Run It

### Launch Streamlit Terminal App
```bash
streamlit run app.py
```

### Run Full PyTest Suite
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
collected 30 items

tests\test_adjustments.py .                                              [  3%]
tests\test_app.py ...                                                    [ 13%]
tests\test_core.py .........                                             [ 43%]
tests\test_performance.py .....                                          [ 60%]
tests\test_pipeline.py ...                                               [ 70%]
tests\test_regressions.py ....                                           [ 83%]
tests\test_schemas.py .....                                              [100%]

============================= 30 passed in 6.62s ==============================
```

Self-verification results:
1. Sharpe/Sortino/Treynor/Jensen, capture ratios, XIRR, GMVP bounds, and tangency Sharpe tests passed.
2. `AppTest` passed on Tab 5 with 0 exceptions.
3. Live column portfolio return and XIRR equal Overview tab figures EXACTLY.
4. Warning box renders conditionally when live sessions $< 20$ and hides when $\ge 20$.

---

## 4. Assumptions
- CML & CAL lines constructed ex-post over past 1-year historical daily returns.
- Risk-free rate $r_f = 4.48\%$ per annum from Nifty 1D Rate Index.

---

## 5. Needs Your Input
- **None for Phase 5**. All calculations run on precomputed parquet datasets.

---

## 6. Known Issues / Fragilities
- None.
