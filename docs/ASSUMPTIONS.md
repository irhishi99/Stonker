# Consolidated System Assumptions & Technical Specifications

This document lists all quantitative assumptions, default parameters, and design choices enforced across the **Indian Equity Portfolio Management Terminal**.

---

## 1. Portfolio Capital & Sleeve Allocation
- **Total Initial Capital**: Rs 1,00,00,000 (Rs 1 Crore).
- **Equity Sleeve**: 97% (Rs 97,00,000 baseline target value).
- **Reserve Cash Sleeve**: 3% (Rs 3,00,000 baseline target minus initial option put premiums).
- **Minimum Market Exposure**: The portfolio maintains at least 90% equity market exposure at all times under normal operating conditions.

---

## 2. Benchmark & Index Specifications
- **Primary Benchmark**: Nifty 500 TRI (Total Returns Index).
- **Equity Risk Premium (ERP)**: 7.08% per annum (configured in `config.yaml`).
- **Risk-Free Rate ($r_f$)**: 4.48% per annum derived from the 3-month annualised Nifty 1D Rate Index / 10-Yr G-Sec yield baseline.
- **Nifty Derivative Contract**: Nifty 50 Index Put Options, Lot Size = 65 shares, Expiry Date = `2026-12-29`.

---

## 3. Indicator & Risk Parameters
- **ATR Period**: 14 trading sessions.
- **ATR Multiple for Stop-Loss**: $5.0 \times \text{ATR(14)}$.
- **Support Buffer**: 1.0 ATR. If a 20-session swing-low support level lies within 1 ATR below the raw stop, the effective stop is adjusted to just below that support price (`support - 0.01`).
- **Trailing Stop Rule**: Stops only trail upward ($\max(\text{prev\_stop}, \text{calc\_stop})$).
- **Relative Strength Window**: 63 trading sessions (~3 months).
- **Directional Indicator (DI) Gap**: $\text{DI\_Gap} = +\text{DI}_{14} - -\text{DI}_{14}$. Trend is defined as `Bullish` if $\text{DI\_Gap} \ge +2.0$, else `Bearish`.

---

## 4. Fundamental Screening Rules
- **Capital Goods & EPC**:
  - Market Cap $\ge$ Rs 5,000 Cr (HARD)
  - ROCE $>$ 8% (SOFT)
  - OPM $>$ 8% (SOFT)
  - Operating Cash Flow $>$ 0 (SOFT)
  - Debt / Equity $<$ 1.5 (HARD)
  - Pledged Shares $<$ 15% (HARD)
  - 63-day Median Turnover $\ge$ Rs 5 Cr/day (HARD)
  - Latest Quarter Profit YoY Growth $>$ 0% (HARD)
- **Cement**:
  - Same as Capital Goods & EPC except OPM $>$ 10% (SOFT).
- **Power**:
  - Market Cap $\ge$ Rs 5,000 Cr (HARD)
  - ROCE $>$ 6% (SOFT)
  - Interest Coverage $>$ 1.5 (HARD)
  - Operating Cash Flow $>$ 0 (SOFT)
  - Pledged Shares $<$ 15% (HARD)
  - 63-day Median Turnover $\ge$ Rs 5 Cr/day (HARD)
  - Latest Quarter Profit YoY Growth $>$ 0% (HARD)
  - *(No Debt/Equity constraint for Power sector)*

---

## 5. Weighting & Hedging Policies
- **Equal Risk Contribution (ERC)**: Portfolio weights optimized via scipy SLSQP to equalize marginal variance contribution subject to 5%–15% position bounds and 100% equity sleeve constraint.
- **Tail Risk Option Hedging**:
  - Down-market Beta ($\beta_{down}$) calculated on Nifty down days ($R_m < 0$).
  - Target put lots required = $\text{round}(\beta_{down} \times V_{\text{stock}} / (P_{\text{nifty}} \times 65))$.
  - Minimum 1-lot rebalance threshold enforced.
  - Profit-Lock Roll: Triggered at +10% portfolio gain; rolls puts up to ~5% OTM strike.

---

## 6. Reserve Replacement Waterfall
- On a stop-loss breach, stock is sold immediately.
- Replacement order:
  1. Qualified Reserve queue candidate passing ALL hard fundamental screens, DI gap $\ge 2$, 1-year history, turnover $\ge$ Rs 5 Cr/day, and YoY profit growth $>$ 0.
  2. Fallback 1: Top up existing held stocks still in uptrend ($\text{DI\_Gap} \ge 2$) under 15% weight cap.
  3. Fallback 2: Hold cash / Liquid ETF.
- Policy: A sold stock never returns to the portfolio.
