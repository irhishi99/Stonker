# Phase 2 Plan: Core Calculations Engine

## Overview
Phase 2 implements all quantitative finance, technical indicator, risk, weighting, hedging, screening, stop-loss, and portfolio ledger engines in `core/`, adds comprehensive unit tests in `tests/`, wires them into pipeline steps 7-9, and provides a CLI report module `python -m core.report`.

## Core Modules to Build in `core/`

1. **`core/indicators.py`**:
   - Technical Indicators with Wilder smoothing: `ATR(14)`, `ADX(14)`, `+DI`, `-DI`, `DI_gap = +DI - -DI`, `RSI(14)`.
   - 63-session relative strength / cumulative percentage-point alpha vs Nifty 500 TRI.
   - 20-session swing-low support and 20-session swing-high resistance levels.
   - Trend determination (`Bullish` if `DI_gap >= 2`, else `Bearish`).

2. **`core/risk.py`**:
   - 1-year annualised volatility (daily log returns).
   - Portfolio & stock Beta vs Nifty 500 TRI over 1 year.
   - Risk-free rate `rf` from 3-month annualised Nifty 1D Rate Index.
   - CAPM Expected Return `E(R) = rf + beta * ERP` (ERP = 7.08%).
   - 3-month expected return: `(1 + annual)^(1/4) - 1`.

3. **`core/weights.py`**:
   - Equal Risk Contribution (ERC) portfolio optimization using `scipy.optimize.minimize(SLSQP)`.
   - Target equal risk contribution: $RC_i = w_i (S w)_i / (w' S w) = 1/N$.
   - Weight bounds: 5% to 15% per stock, summing to 100% of equity sleeve.
   - Whole share allocation calculation at snapshot close prices.

4. **`core/stops.py`**:
   - Raw stop-loss = `price - 5 * ATR(14)`.
   - Support adjustment: if 20-session support is within 1 ATR below raw stop (`raw_stop - 1*ATR <= support <= raw_stop`), adjust stop to just below support (`support - 0.01`).
   - Upward trailing rule: `stop_t = max(stop_{t-1}, current_calculated_stop)`.
   - Method labeling: `"5 x ATR"`, `"Support-adjusted"`, or `"Trailed (prev. stop)"`.
   - Aggregate "Still at risk if every stop is hit" calculation: $\sum \text{shares}_i \times (\text{price}_i - \text{stop}_i)$.

5. **`core/screens.py`**:
   - Sector-specific fundamental screen evaluator (Capital Goods & EPC, Cement, Power).
   - Strict Hard (H) vs Soft (S) rule enforcement (Missing/unreadable = FAIL).
   - Review tables written to `output/<sector>_full_review_table.csv`.
   - Automated plain-English screen exception generator.

6. **`core/ledger.py`**:
   - Trade ledger manager backed by `data/parquet/trade_ledger.parquet`.
   - Day-0 initial seed (2026-09-28 snapshot): 8 stocks + 8 Nifty 22000 PE lots + cash.
   - Portfolio mark-to-market valuation function (Stocks + Options + Cash).
   - XIRR Newton/Brentq solver for dated cash flows.

7. **`core/hedge.py`**:
   - Down-market tail hedge ratio ($\beta_{down}$).
   - Required Nifty put option lots: $\text{round}(\beta_{down} \times V_{equity} / (P_{nifty} \times 65))$.
   - Full-lot minimum trade condition ($\Delta \text{lots} \ge 1$).
   - Profit-lock roll trigger (+10% gain trigger -> roll to ~5% OTM strike).

8. **`core/waterfall.py`**:
   - Stop-loss hit replacement algorithm.
   - Ranked reserve queue review with explicit "Would be bought today?" reason code.
   - Replacement hierarchy: Qualified Reserve -> Uptrend Top-up (<15% cap) -> Liquid Fund.

9. **`core/universe_lock.py`**:
   - Universe lock date ranking (`2026-09-25`).
   - 6-month relative strength calculation skipping the latest month.
   - Top 8 invested / 7 reserve queue assignment.

10. **`core/report.py`**:
    - Command-line summary tool (`python -m core.report`).
    - Validates internal consistency (stocks + puts + cash = total, weights = 100%).

## Pipeline Integration
- Update `pipeline/step7_stub.py` -> calculate technical indicators, 63-day alpha, screens, universe lock.
- Update `pipeline/step8_stub.py` -> calculate risk metrics, CAPM, ERC weights, stop-loss levels, hedge state.
- Update `pipeline/step9_stub.py` -> update ledger, portfolio valuation, reserve waterfall, export CSV tables.

## Verification Plan
- Unit tests covering known-answer indicators, ERC solver, stop trailing, XIRR, hedge lots, screens, and waterfall logic.
- Execute `python -m pipeline.run --demo` and verify pipeline log.
- Execute `python -m core.report` and verify printed portfolio metrics and internal consistency checks.
