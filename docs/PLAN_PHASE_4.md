# Phase 4 Plan: Risk & Hedging Engine & Interactive Tab

## Overview
Phase 4 implements advanced risk analytics, factor regressions (single-index, capex cycle factor model, macro multi-factor model), AR(1) time-series autocorrelations, 3-month risk-reward analytics, option hedge plan simulations, and the interactive Streamlit Tab 4 (`🛡️ Risk & Hedging`).

## Core Modules to Build in `core/`

1. **`core/regressions.py`**:
   - Single-index regression (portfolio and stocks vs Nifty 500 TRI): Alpha, Alpha t-stat, Beta, Beta s.e., R-squared, Total Vol, Systematic Vol, Stock-Specific Vol.
   - Benchmark comparison regressions across 10 indices + Nifty 500 + Equal-weight capex universe.
   - 4-Factor Capex Cycle Model: Market + Size (Smallcap 500 - Nifty 500) + Momentum (Momentum 50 - Nifty 500) + Capex Factor (Capex Universe - Nifty 500). Factor loadings, t-stats, and correlation warning ($|r| > 0.7$).
   - Macro Multi-factor Model: Market + Brent Crude daily change % + 10-Yr G-Sec price return ($-7.0 \times \Delta y$). Single vs Multi $R^2$, Adjusted $R^2$, and t-stat verdict.
   - Time Series Autocorrelation: AR(1) $\phi$ & t-stat, lags 1-5 autocorrelations with $\pm 1.96/\sqrt{N}$ bounds, Ljung-Box Q test vs $\chi^2(5)=11.07$, weekly lag-1 autocorrelation.

2. **`core/risk_reward.py`**:
   - 3-Month Risk-Reward calculator for individual stocks and portfolio levels (`PORTFOLIO all stocks` vs `PORTFOLIO diversified`).
   - Typical 3-month move % ($\text{annual vol} \times \sqrt{63/252}$), Target levels, 20D Resistance hurdles, Reward:Risk ratios.
   - Loss at stop (% of Rs 1 Cr).
   - Guarantees exact match for aggregate "Still at Risk" figure across tabs.

3. **`core/hedge_plan.py`**:
   - Minimum-variance hedge ratio $h^*$, hedge effectiveness ($R^2$), tail hedge ratio $\beta_{down}$.
   - Put option strike analysis table (Strike, Premium, Delta, Exposure covered).
   - Scenario analysis generator: Nifty move (-25% to 0%) vs Portfolio P&L % for Unhedged vs Hedged with Puts.

## Streamlit Tab 4 UI (`app.py`)
- Section 1: Portfolio Allocation Donut Chart & Table.
- Section 2: Equal Risk Contribution (ERC) Weighting Table.
- Section 3: Capex Cycle Benchmark Regressions & 4-Factor Model.
- Section 4: Beta & Single-Index Risk Decomposition Table.
- Section 5: Macro Multi-factor Regression (Brent & G-Sec).
- Section 6: CAPM Expected Return KPIs.
- Section 7: Autocorrelation & AR(1) Time-Series Diagnostics.
- Section 8: 3-Month Risk-Reward Analysis Table.
- Section 9: Hedge Plan, Decision Rationale, Scenario Plotly Chart, Strike Comparison Expander.

## Verification & Test Plan
- Unit tests in `tests/test_regressions.py` covering OLS stats, AR(1), Ljung-Box, risk-reward math, and scenario payoff.
- AppTest in `tests/test_app.py` verifying Tab 4 rendering.
- Exact match assertion for "Still at Risk" figure across Overview and Risk & Hedging tabs.
