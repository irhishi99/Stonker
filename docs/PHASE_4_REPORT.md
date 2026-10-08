# Phase 4 Completion Report: Risk & Hedging Tab

## 1. What Was Built
- **Core Analytics & Regression Modules (`core/`)**:
  - **`regressions.py`**:
    - Single-Index Model vs Nifty 500 TRI ($R_{i,t} = \alpha_i + \beta_i R_{bm,t} + \epsilon_{i,t}$) computing annualised Alpha (%), Alpha t-stat, Beta, Beta s.e., $R^2$, Total Volatility (%), Systematic Volatility (%), and Stock-Specific Volatility (%) for individual stocks and `PORTFOLIO`.
    - Benchmark comparison regressions across 10 sectoral/thematic index histories + Nifty 500 TRI + Equal-Weight Capex Universe (15 stocks).
    - 4-Factor Capex Cycle Model (Market + Size + Momentum + Capex Factor) with factor loadings, t-stats, and correlation matrix check ($|r| > 0.7$ warning).
    - Macro Multi-Factor Model (Market + Brent Crude daily % change + 10Y G-Sec price return $-7.0 \times \Delta y$) comparing single vs multi $R^2$, adjusted $R^2$, and t-stat verdict ($|t| > 2.0$).
    - Autocorrelation & Time Series Diagnostics: Daily AR(1) $\phi$ & t-stat, Lags 1-5 autocorrelations with $\pm 1.96/\sqrt{N}$ bounds, Ljung-Box Q-test vs $\chi^2(5)=11.07$, weekly lag-1 autocorrelation, and market efficiency verdict.
  - **`risk_reward.py`**:
    - 3-Month Risk-Reward calculator for individual stocks + `PORTFOLIO (all stocks at once)` and `PORTFOLIO (diversified)`.
    - Typical 3-month move % ($\text{annual vol} \times \sqrt{63/252}$), Target levels, 20D Resistance hurdles, Reward:Risk ratios, and Loss at stop (% of Rs 1 Cr).
    - Enforces exact match for aggregate "Still at Risk" figure across Overview and Risk & Hedging tabs.
  - **`hedge_plan.py`**:
    - Minimum-variance hedge ratio $h^*$, hedge effectiveness ($R^2$), tail hedge ratio ($\beta_{down}$).
    - Option Strike Comparison table (Strike, Option Type, Premium, Delta, Exposure Covered, Total Cost).
    - Downside Scenario Analysis P&L curve generator (-25% to 0% Nifty drop at expiry) proving option puts cap maximum portfolio loss.

- **Interactive Streamlit Tab 4 (`🛡️ Risk & Hedging` in `app.py`)**:
  - Section 1: Asset Allocation Donut Chart & Table with "% in stocks" centre annotation (96.95%) and 90% mandate note.
  - Section 2: Equal Risk Contribution (ERC) Weighting Table & variance share explanation.
  - Section 3: Capex Cycle Benchmark Regressions & 4-Factor Model Loadings Table + correlation warning.
  - Section 4: Single-Index Risk Decomposition KPIs & Breakdown Table.
  - Section 5: Macro Multi-Factor Model Regression Table (Brent & G-Sec) & verdict.
  - Section 6: CAPM Expected Return KPIs ($E(R)$ annual, 3M, rupees, $r_f$, ERP).
  - Section 7: Time Series Autocorrelation & AR(1) Diagnostics Table & Ljung-Box Q verdict.
  - Section 8: 3-Month Risk-Reward Table & exact Still-at-Risk match assertion.
  - Section 9: Hedge Plan, Decision Rationale, Downside Scenario Plotly Chart (Unhedged vs With Puts), and Strike Comparison Expander.

- **Automated Testing**:
  - Added [tests/test_regressions.py](file:///c:/equity%20portfolio/tests/test_regressions.py) with unit tests for OLS accuracy, AR(1), Ljung-Box Q test, risk-reward math, and option downside capping.
  - Updated [tests/test_app.py](file:///c:/equity%20portfolio/tests/test_app.py) with Streamlit `AppTest` verifying Tab 4 renders with zero exceptions.

---

## 2. How to Run It

### Launch Streamlit App
```bash
streamlit run app.py
```

### Run Full PyTest Suite
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
collected 25 items

tests\test_adjustments.py .                                              [  4%]
tests\test_app.py ...                                                    [ 16%]
tests\test_core.py .........                                             [ 52%]
tests\test_pipeline.py ...                                               [ 64%]
tests\test_regressions.py ....                                           [ 80%]
tests\test_schemas.py .....                                              [100%]

============================= 25 passed in 6.53s ==============================
```

Self-verification results:
1. Regressions, Ljung-Box, risk-reward math, and scenario P&L tests passed.
2. `AppTest` passed with 0 exceptions on Tab 4.
3. Still-at-Risk figure in Tab 4 (`Rs 13,35,277.25`) equals Overview tab figure EXACTLY.
4. All tables formatted cleanly without placeholder text or unnamed columns.

---

## 4. Assumptions
- 10-Yr G-Sec price sensitivity calculated using modified duration approximation ($D \approx 7.0$).
- Equity sleeve maintains $\ge 90\%$ market exposure requirement.

---

## 5. Needs Your Input
- **None for Phase 4**. All calculations run on precomputed parquet datasets.

---

## 6. Known Issues / Fragilities
- None.
