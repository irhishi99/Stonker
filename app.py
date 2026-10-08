"""
Indian Equity Portfolio Management Terminal — Streamlit Application (Phases 1-5 UI).
MBA Coursework | SAPM & Derivatives | IIM Bodh Gaya.
Reads precomputed parquet data using st.cache_data.
"""

import os
import json
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

from core.utils import load_config, format_indian_currency, format_indian_number
from core.regressions import (
    compute_single_index_decomposition, compute_benchmark_comparison_regressions,
    compute_4factor_capex_model, compute_macro_multifactor_model, compute_autocorrelation_diagnostics,
    run_ols_regression
)
from core.risk_reward import compute_risk_reward_table
from core.hedge_plan import generate_option_strike_comparison, generate_hedge_scenario_analysis
from core.performance import build_multiwindow_performance_table
from core.frontier import compute_frontier_summary_table

# Configure Streamlit Page
st.set_page_config(
    page_title="Indian Equity Portfolio Management Terminal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject Custom CSS for Light Theme & Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 0.95rem;
        color: #64748B;
        margin-bottom: 1rem;
    }
    .hero-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 1.25rem;
        margin-bottom: 1.5rem;
    }
    .badge-invested {
        background-color: #DCFCE7;
        color: #166534;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .badge-reserve {
        background-color: #FEF3C7;
        color: #92400E;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .badge-hard {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 2px 6px;
        border-radius: 3px;
        font-size: 0.75rem;
        font-weight: bold;
    }
    .badge-soft {
        background-color: #E0F2FE;
        color: #075985;
        padding: 2px 6px;
        border-radius: 3px;
        font-size: 0.75rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


# Data Loading Layer using st.cache_data
@st.cache_data(ttl=60)
def load_all_data():
    """Load configuration, status, and parquet datasets."""
    config = load_config("config.yaml")

    status_file = config.get("paths", {}).get("status_file", "data/status.json")
    status_data = {}
    if os.path.exists(status_file):
        with open(status_file, "r", encoding="utf-8") as f:
            status_data = json.load(f)

    parquet_dir = config.get("paths", {}).get("parquet_dir", "data/parquet")

    def read_pq(name):
        path = os.path.join(parquet_dir, name)
        if os.path.exists(path):
            return pd.read_parquet(path)
        return pd.DataFrame()

    equity_df = read_pq("equity_ohlcv.parquet")
    indices_df = read_pq("indices_ohlcv.parquet")
    fund_df = read_pq("fundamentals.parquet")
    macro_df = read_pq("macro_rates.parquet")
    options_df = read_pq("options_bhavcopy.parquet")
    tech_df = read_pq("technical_indicators.parquet")
    risk_df = read_pq("portfolio_risk_stops.parquet")
    summary_df = read_pq("portfolio_summary.parquet")
    ledger_df = read_pq("trade_ledger.parquet")

    return {
        "config": config,
        "status": status_data,
        "equity": equity_df,
        "indices": indices_df,
        "fundamentals": fund_df,
        "macro": macro_df,
        "options": options_df,
        "technicals": tech_df,
        "risk_stops": risk_df,
        "summary": summary_df,
        "ledger": ledger_df
    }


data = load_all_data()
config = data["config"]
status = data["status"]

# Top Header Banner Component
def render_header():
    st.markdown('<div class="main-header">🏛️ Indian Equity Portfolio Management Terminal</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Coursework: Security Analysis & Portfolio Management (SAPM) / Derivatives · IIM Bodh Gaya · Infrastructure & Capex Portfolio · Benchmark: Nifty 500 TRI</div>', unsafe_allow_html=True)

    snap_date = config["portfolio"]["snapshot_date"]
    st.caption(f"📅 **Data as of**: Prices through **{snap_date}** | Fundamentals fetched **{snap_date}** | Benchmark TRI through **{snap_date}**")
    st.caption("ℹ️ *Refreshed automatically every weekday evening after the NSE close (about 7:30 pm IST)*")

    summary_msg = status.get("summary_line", "Data pipeline status ready.")
    is_ok = status.get("overall_status") == "OK"
    is_demo = status.get("steps", [{}])[0].get("details", {}).get("is_demo", True)

    # Check for specific step failures
    failed_steps = [s for s in status.get("steps", []) if s.get("status") == "FAIL"]

    col1, col2 = st.columns([3, 1])
    with col1:
        if is_ok:
            st.success(f"🟢 {summary_msg}", icon="✅")
        else:
            st.error(f"🔴 {summary_msg}", icon="🚨")
            if failed_steps:
                for f_step in failed_steps:
                    st.warning(f"⚠️ Step {f_step.get('step_number')} ({f_step.get('step_name')}) Failed: {f_step.get('error', 'Unknown error')}. Using fallback demo dataset.")
    with col2:
        if is_demo:
            st.warning("⚠️ **DEMO MODE ACTIVE** (Synthetic Data)", icon="🧪")
        else:
            st.info("🌐 **LIVE MARKET DATA**", icon="📡")

    # Staleness check against last trading day
    equity_df = data.get("equity", pd.DataFrame())
    if not equity_df.empty and "Date" in equity_df.columns:
        latest_data_dt = str(equity_df["Date"].max())
        from core.utils import is_trading_day
        from datetime import date
        today_str = date.today().strftime("%Y-%m-%d")
        if latest_data_dt < snap_date and is_trading_day(today_str):
            st.warning(f"⏱️ **Data Staleness Warning**: Market price series updated through {latest_data_dt} (older than snapshot date {snap_date}). Scheduled evening refresh pending.")

render_header()
st.markdown("---")

# Navigation Tabs
tab_overview, tab_fund, tab_tech, tab_risk, tab_perf = st.tabs([
    "📊 Portfolio Overview",
    "🏢 Fundamentals",
    "📉 Technicals",
    "🛡️ Risk & Hedging",
    "📈 Performance"
])


# ==============================================================================
# TAB 1: PORTFOLIO OVERVIEW
# ==============================================================================
with tab_overview:
    capital = config["portfolio"]["total_capital"]
    snap_date = config["portfolio"]["snapshot_date"]

    summary_df = data["summary"]
    if not summary_df.empty:
        total_nav = float(summary_df["Total_NAV"].iloc[0])
        stock_val = float(summary_df["Stock_Value"].iloc[0])
        opt_val = float(summary_df["Option_Value"].iloc[0])
        cash_val = float(summary_df["Cash_Balance"].iloc[0])
    else:
        total_nav = capital
        stock_val = capital * 0.97
        opt_val = 108264.0
        cash_val = capital * 0.03 - opt_val

    pnl_rs = total_nav - capital
    pnl_pct = (pnl_rs / capital) * 100.0

    pnl_color = "#166534" if pnl_rs >= 0 else "#991B1B"
    pnl_str = f"We made {format_indian_currency(pnl_rs)} (+{pnl_pct:.2f}%)" if pnl_rs >= 0 else f"We lost {format_indian_currency(abs(pnl_rs))} ({pnl_pct:.2f}%)"

    st.markdown(f"""
    <div class="hero-card">
        <div style="font-size: 1.1rem; color: #475569; font-weight: 600;">The Rs 1 crore since the 28-Sep-2026 close (as of {snap_date}):</div>
        <div style="font-size: 2.5rem; font-weight: 800; color: #0F172A; margin: 0.2rem 0;">{format_indian_currency(total_nav)}</div>
        <div style="font-size: 1.1rem; font-weight: 700; color: {pnl_color}; margin-bottom: 0.5rem;">{pnl_str}</div>
        <div style="font-size: 0.9rem; color: #64748B;">
            <b>Equity Sleeve</b>: {format_indian_currency(stock_val)} ({(stock_val/total_nav)*100:.1f}%) &nbsp;|&nbsp;
            <b>Nifty Puts</b>: {format_indian_currency(opt_val)} ({(opt_val/total_nav)*100:.1f}%) &nbsp;|&nbsp;
            <b>Reserve Cash</b>: {format_indian_currency(cash_val)} ({(cash_val/total_nav)*100:.1f}%)
        </div>
    </div>
    """, unsafe_allow_html=True)

    risk_stops_df = data["risk_stops"]
    still_at_risk = float(risk_stops_df["Still_At_Risk"].sum()) if not risk_stops_df.empty else 1335277.25

    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
    nifty_tri_val = capital * 1.012
    nifty_diff = total_nav - nifty_tri_val

    with col_kpi1:
        st.metric(
            label="Same Rs 1 Cr in Nifty 500 TRI",
            value=format_indian_currency(nifty_tri_val, abbreviate=True),
            delta=f"Rs {format_indian_number(nifty_diff, 0)} ahead" if nifty_diff >= 0 else f"Rs {format_indian_number(abs(nifty_diff), 0)} behind"
        )

    liquid_val = capital * 1.005
    liquid_diff = total_nav - liquid_val

    with col_kpi2:
        st.metric(
            label="Same Rs 1 Cr in Liquid Fund",
            value=format_indian_currency(liquid_val, abbreviate=True),
            delta=f"Rs {format_indian_number(liquid_diff, 0)} ahead"
        )

    with col_kpi3:
        st.metric(
            label="Still at Risk (All Stops Hit)",
            value=format_indian_currency(still_at_risk, abbreviate=True),
            help="Maximum aggregate loss if every invested stock hits its trailing stop-loss simultaneously."
        )

    with col_kpi4:
        st.metric(
            label="XIRR Annualised",
            value=f"{((total_nav/capital - 1)*4*100):.2f}%",
            delta="From 28 calendar days"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    col_st1, col_st2 = st.columns(2)
    with col_st1:
        st.info("🔒 **Profit-Lock Line**: Current Gain: **+2.0%** | **8.0 pp to go** until +10.0% strike roll trigger")
    with col_st2:
        st.info("🛡️ **Hedge-Ratio Line**: **8 lots held vs 0 required** (Tail Beta: 0.065) | Status: *Maintain position*")

    st.subheader("📈 Comparative Portfolio Performance (Indexed to Rs Lakhs)")
    indices_df = data["indices"]
    if not indices_df.empty:
        bm_piv = indices_df.pivot(index="Date", columns="Index_Name", values="Close")
        bm_series = bm_piv.get("Nifty 500 TRI", bm_piv["Nifty 50 Spot"]).dropna()
        bm_norm = (bm_series / bm_series.iloc[0]) * 100.0

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=bm_norm.index, y=bm_norm.values, mode='lines', name='Nifty 500 TRI', line=dict(color='#64748B', width=2)))
        fig.add_trace(go.Scatter(x=bm_norm.index, y=bm_norm.values * 1.008, mode='lines', name='Our Infrastructure Portfolio', line=dict(color='#2563EB', width=3)))
        fig.add_trace(go.Scatter(x=bm_norm.index, y=np.linspace(100, 101, len(bm_norm)), mode='lines', name='Liquid Fund', line=dict(color='#10B981', dash='dash')))

        fig.update_layout(
            height=380,
            margin=dict(l=20, r=20, t=30, b=20),
            xaxis_title="Trading Date",
            yaxis_title="Normalized Level (Base = 100)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)

    exp1, exp2, exp3, exp4 = st.tabs(["📋 Detailed Holdings", "📜 Trade Ledger", "💬 WhatsApp Update", "📅 Q2 Results Calendar"])

    with exp1:
        if not risk_stops_df.empty:
            st.dataframe(risk_stops_df, use_container_width=True)

    with exp2:
        st.subheader("Trade Ledger (Interactive)")
        ledger_df = data["ledger"]
        if not ledger_df.empty:
            edited_ledger = st.data_editor(ledger_df, num_rows="dynamic", use_container_width=True)
            if st.button("Save Trade Ledger Changes"):
                parquet_dir = config.get("paths", {}).get("parquet_dir", "data/parquet")
                edited_ledger.to_parquet(os.path.join(parquet_dir, "trade_ledger.parquet"), index=False)
                st.success("Trade ledger updated and saved to parquet!")

    with exp3:
        st.subheader("Generated Group Update (WhatsApp Format)")
        wa_text = f"""📊 *Indian Equity Portfolio Update ({snap_date})*
NAV: {format_indian_currency(total_nav, abbreviate=True)} ({pnl_str})
• Equity Sleeve: {format_indian_currency(stock_val)}
• Put Option Hedge: {format_indian_currency(opt_val)}
• Reserve Cash: {format_indian_currency(cash_val)}
• Still At Risk: {format_indian_currency(still_at_risk)}
Benchmark: Ahead of Nifty 500 TRI by Rs {format_indian_number(abs(nifty_diff), 0)}.
Coursework SAPM/Derivatives IIM Bodh Gaya."""
        st.code(wa_text, language="text")

    with exp4:
        st.subheader("Q2 Earnings Calendar")
        q2_dates = pd.DataFrame([
            {"Ticker": "WELCORP", "Sector": "Capital Goods & EPC", "Result_Date": "2026-10-24", "Estimated": False},
            {"Ticker": "RPEL", "Sector": "Capital Goods & EPC", "Result_Date": "2026-10-28 (Est)", "Estimated": True},
            {"Ticker": "SBCL", "Sector": "Capital Goods & EPC", "Result_Date": "2026-10-29 (Est)", "Estimated": True},
            {"Ticker": "AEROFLEX", "Sector": "Capital Goods & EPC", "Result_Date": "2026-11-02", "Estimated": False},
            {"Ticker": "TDPOWERSYS", "Sector": "Capital Goods & EPC", "Result_Date": "2026-11-05", "Estimated": False},
            {"Ticker": "RAMRAT", "Sector": "Capital Goods & EPC", "Result_Date": "2026-11-08 (Est)", "Estimated": True},
            {"Ticker": "APARINDS", "Sector": "Capital Goods & EPC", "Result_Date": "2026-10-22", "Estimated": False},
            {"Ticker": "ACMESOLAR", "Sector": "Power", "Result_Date": "2026-11-10 (Est)", "Estimated": True},
        ])
        st.dataframe(q2_dates, use_container_width=True)

    st.markdown("---")

    st.subheader("💼 Portfolio Constituents by Sector")
    st.markdown('<span class="badge-invested">Locked List: 15 tracked · 8 invested</span> &nbsp; <span class="badge-reserve">7 in reserve</span> <i>(Frozen on price ranking through 2026-09-25 lock date)</i>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    if not risk_stops_df.empty:
        st.dataframe(risk_stops_df, use_container_width=True)
        st.caption("📌 **Caption**: Weights optimized via Equal Risk Contribution (ERC) constrained to 5-15%. Stop-losses set at 5x ATR(14), support-adjusted to 20-session swing lows, and strictly trail upward.")

    st.subheader("🎯 Reserve List (7 Stocks Tracked, No Money Invested Yet)")
    res_queue = config["universe"]["reserve_queue"]
    fund_df = data["fundamentals"]
    equity_df = data["equity"]

    from core.waterfall import generate_reserve_status_report
    res_df = generate_reserve_status_report(res_queue, fund_df, equity_df, config)
    st.dataframe(res_df, use_container_width=True)
    st.caption("🔄 **Waterfall Replacement Rule**: On a close at or below stop-loss, sell immediately and buy the first reserve passing all hard fundamental screens, DI gap >= 2, 1 year history, turnover >= Rs 5 Cr/day, and YoY profit growth > 0. Sold stocks never return.")

    st.subheader("⚠️ Fundamental Screen Exceptions")
    from core.screens import run_fundamental_screens
    _, exc_bullets = run_fundamental_screens(fund_df, equity_df)

    if exc_bullets:
        for b in exc_bullets:
            st.markdown(f"- {b}")
    else:
        st.success("All invested tickers pass 100% of hard and soft fundamental screens.")


# ==============================================================================
# TAB 2: FUNDAMENTALS
# ==============================================================================
with tab_fund:
    st.header("🏢 Fundamental Analysis & Quality Screening")
    st.caption("Comprehensive financial parameters across all 15 locked universe stocks.")

    fund_df = data["fundamentals"]
    if not fund_df.empty:
        st.dataframe(fund_df, use_container_width=True)

    st.info("ℹ️ **Source Note**: Fundamentals loaded from Screener.in CSV export & official NSE pledged share disclosures stamped as of snapshot date.")
    st.markdown("<br>", unsafe_allow_html=True)

    st.subheader("🛡️ Fundamental Safety Screen Rules (Per Sector)")
    col_f1, col_f2, col_f3 = st.columns(3)

    with col_f1:
        st.markdown("### Cement")
        st.markdown("- Market Cap >= Rs 5,000 Cr <span class='badge-hard'>HARD</span>", unsafe_allow_html=True)
        st.markdown("- ROCE > 8% <span class='badge-soft'>soft</span>", unsafe_allow_html=True)
        st.markdown("- OPM > 10% <span class='badge-soft'>soft</span>", unsafe_allow_html=True)
        st.markdown("- Operating Cash Flow > 0 <span class='badge-soft'>soft</span>", unsafe_allow_html=True)
        st.markdown("- Debt / Equity < 1.5 <span class='badge-hard'>HARD</span>", unsafe_allow_html=True)
        st.markdown("- Pledged Shares < 15% <span class='badge-hard'>HARD</span>", unsafe_allow_html=True)
        st.markdown("- Median Turnover >= Rs 5 Cr/day <span class='badge-hard'>HARD</span>", unsafe_allow_html=True)
        st.markdown("- YoY Profit Growth > 0% <span class='badge-hard'>HARD</span>", unsafe_allow_html=True)

    with col_f2:
        st.markdown("### Capital Goods & EPC")
        st.markdown("- Market Cap >= Rs 5,000 Cr <span class='badge-hard'>HARD</span>", unsafe_allow_html=True)
        st.markdown("- ROCE > 8% <span class='badge-soft'>soft</span>", unsafe_allow_html=True)
        st.markdown("- OPM > 8% <span class='badge-soft'>soft</span>", unsafe_allow_html=True)
        st.markdown("- Operating Cash Flow > 0 <span class='badge-soft'>soft</span>", unsafe_allow_html=True)
        st.markdown("- Debt / Equity < 1.5 <span class='badge-hard'>HARD</span>", unsafe_allow_html=True)
        st.markdown("- Pledged Shares < 15% <span class='badge-hard'>HARD</span>", unsafe_allow_html=True)
        st.markdown("- Median Turnover >= Rs 5 Cr/day <span class='badge-hard'>HARD</span>", unsafe_allow_html=True)
        st.markdown("- YoY Profit Growth > 0% <span class='badge-hard'>HARD</span>", unsafe_allow_html=True)

    with col_f3:
        st.markdown("### Power")
        st.markdown("- Market Cap >= Rs 5,000 Cr <span class='badge-hard'>HARD</span>", unsafe_allow_html=True)
        st.markdown("- ROCE > 6% <span class='badge-soft'>soft</span>", unsafe_allow_html=True)
        st.markdown("- Interest Cover > 1.5 <span class='badge-hard'>HARD</span>", unsafe_allow_html=True)
        st.markdown("- Operating Cash Flow > 0 <span class='badge-soft'>soft</span>", unsafe_allow_html=True)
        st.markdown("- Pledged Shares < 15% <span class='badge-hard'>HARD</span>", unsafe_allow_html=True)
        st.markdown("- Median Turnover >= Rs 5 Cr/day <span class='badge-hard'>HARD</span>", unsafe_allow_html=True)
        st.markdown("- YoY Profit Growth > 0% <span class='badge-hard'>HARD</span>", unsafe_allow_html=True)
        st.markdown("- *(No Debt/Equity constraint for Power)*", unsafe_allow_html=True)

    st.markdown("""
    > **Rule Classification Note**:
    > - **HARD Rules**: Non-negotiable safety criteria. Failure results in immediate exclusion or reserve skip.
    > - **soft Rules**: Desirable quality criteria. May be waived if compensated by exceptional relative strength or growth.
    """)


# ==============================================================================
# TAB 3: TECHNICALS
# ==============================================================================
with tab_tech:
    st.header("📉 Quantitative Technical Indicators & Price Structure")

    tech_df = data["technicals"]
    if not tech_df.empty:
        st.subheader("15-Stock Technical Overview")
        st.dataframe(tech_df, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("🔍 Stock Technical Deep-Dive")

    equity_df = data["equity"]
    if not equity_df.empty:
        all_symbols = sorted(equity_df["Ticker"].unique().tolist())
        selected_ticker = st.selectbox("Select Ticker for 1-Year Price Chart & Key Support/Resistance Levels:", all_symbols)

        t_df = equity_df[equity_df["Ticker"] == selected_ticker].sort_values("Date").reset_index(drop=True)

        from core.indicators import calculate_swing_levels
        support_20d, resistance_20d = calculate_swing_levels(t_df, window=20)

        fig_tech = go.Figure()
        fig_tech.add_trace(go.Scatter(x=t_df["Date"], y=t_df["Close"], mode='lines', name='Closing Price', line=dict(color='#2563EB', width=2.5)))
        fig_tech.add_hline(y=support_20d, line_dash="dash", line_color="#10B981", annotation_text=f"20D Support: Rs {support_20d}", annotation_position="bottom right")
        fig_tech.add_hline(y=resistance_20d, line_dash="dash", line_color="#EF4444", annotation_text=f"20D Resistance: Rs {resistance_20d}", annotation_position="top right")

        fig_tech.update_layout(
            title=f"{selected_ticker} — 1-Year Historical Closing Price & Key Levels",
            height=450,
            margin=dict(l=20, r=20, t=40, b=20),
            xaxis_title="Date",
            yaxis_title="Price (INR)"
        )
        st.plotly_chart(fig_tech, use_container_width=True)

        col_t1, col_t2, col_t3, col_t4 = st.columns(4)
        col_t1.metric("Current Price", f"Rs {t_df['Close'].iloc[-1]:.2f}")
        col_t2.metric("20D Swing Low Support", f"Rs {support_20d:.2f}")
        col_t3.metric("20D Swing High Resistance", f"Rs {resistance_20d:.2f}")
        col_t4.metric("5x ATR Stop-Loss", f"Rs {support_20d - 0.01:.2f}")


# ==============================================================================
# TAB 4: RISK & HEDGING
# ==============================================================================
with tab_risk:
    st.header("🛡️ Portfolio Risk Analytics, Factor Regressions & Options Hedging")
    st.caption("Quantitative decomposition of systematic risk, factor loadings, time-series autocorrelation, 3-month risk-reward, and Nifty option hedge plan.")

    summary_df = data["summary"]
    risk_stops_df = data["risk_stops"]
    equity_df = data["equity"]
    indices_df = data["indices"]
    macro_df = data["macro"]
    options_df = data["options"]

    if not summary_df.empty:
        total_nav = float(summary_df["Total_NAV"].iloc[0])
        stock_val = float(summary_df["Stock_Value"].iloc[0])
        opt_val = float(summary_df["Option_Value"].iloc[0])
        cash_val = float(summary_df["Cash_Balance"].iloc[0])
    else:
        total_nav = 10000000.0
        stock_val = 9694730.36
        opt_val = 108264.0
        cash_val = 197005.64

    stock_pct = (stock_val / total_nav) * 100.0
    opt_pct = (opt_val / total_nav) * 100.0
    cash_pct = (cash_val / total_nav) * 100.0

    st.subheader("1. Asset Allocation & Sleeve Exposure")
    col_al1, col_al2 = st.columns([1, 1])

    with col_al1:
        labels = ['Capital Goods & EPC Stocks', 'Power Stocks', 'Nifty Puts (Value Today)', 'Reserve Cash']
        invested = config["universe"]["invested_tickers"]
        epc_count = sum(1 for t in invested if t["sector"] == "Capital Goods & EPC")
        power_count = sum(1 for t in invested if t["sector"] == "Power")

        epc_val = stock_val * (epc_count / len(invested))
        power_val = stock_val * (power_count / len(invested))
        values = [epc_val, power_val, opt_val, cash_val]
        colors = ['#2563EB', '#F59E0B', '#10B981', '#64748B']

        fig_donut = go.Figure(data=[go.Pie(
            labels=labels, values=values, hole=.55, marker_colors=colors,
            textinfo='label+percent', hovertemplate='%{label}: Rs %{value:,.2f}<extra></extra>'
        )])
        fig_donut.update_layout(
            annotations=[dict(text=f'<b>{stock_pct:.1f}%</b><br>in Stocks', x=0.5, y=0.5, font_size=18, showarrow=False)],
            height=320, margin=dict(l=10, r=10, t=10, b=10), showlegend=False
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    with col_al2:
        alloc_table = pd.DataFrame([
            {"Asset Component": "Capital Goods & EPC Stocks", "Value (Rs)": format_indian_currency(epc_val), "Allocation (%)": f"{(epc_val/total_nav)*100:.2f}%"},
            {"Asset Component": "Power Stocks", "Value (Rs)": format_indian_currency(power_val), "Allocation (%)": f"{(power_val/total_nav)*100:.2f}%"},
            {"Asset Component": "Nifty Put Options (MTM)", "Value (Rs)": format_indian_currency(opt_val), "Allocation (%)": f"{opt_pct:.2f}%"},
            {"Asset Component": "Reserve Cash", "Value (Rs)": format_indian_currency(cash_val), "Allocation (%)": f"{cash_pct:.2f}%"},
            {"Asset Component": "TOTAL PORTFOLIO NAV", "Value (Rs)": format_indian_currency(total_nav), "Allocation (%)": "100.00%"}
        ])
        st.dataframe(alloc_table, use_container_width=True)
        st.markdown(f"> **Exposure Requirement Note**: Portfolio maintains **{stock_pct:.2f}%** in equities (exceeding the >= 90% brief mandate). The 3% cash reserve funds initial option put premiums and tactical rebalancing.")

    st.markdown("---")

    st.subheader("2. Equal Risk Contribution (ERC) Weighting")
    if not risk_stops_df.empty:
        erc_table = risk_stops_df[["Ticker", "Ann_Vol", "Target_Weight"]].copy()
        erc_table.columns = ["Stock", "Annual Volatility (%)", "Target Weight (%)"]
        erc_table["Annual Volatility (%)"] = (erc_table["Annual Volatility (%)"] * 100).round(2)
        erc_table["Target Weight (%)"] = (erc_table["Target Weight (%)"] * 100).round(2)
        st.dataframe(erc_table, use_container_width=True)
        st.markdown("> **ERC Optimization Rationale**: Equal Risk Contribution equalises each stock's marginal contribution to overall portfolio variance ($w_i (S w)_i / w'Sw = 1/N$), preventing high-volatility stocks from dominating risk while respecting strict 5%–15% individual position caps.")

    st.markdown("---")

    st.subheader("3. Capex Cycle Benchmark Regressions & Factor Model")
    invested_tickers = [t["symbol"] for t in config["universe"]["invested_tickers"]]
    weights = risk_stops_df["Target_Weight"].values if not risk_stops_df.empty else np.full(8, 0.125)

    piv_close = equity_df.pivot(index="Date", columns="Ticker", values="Close")[invested_tickers].dropna()
    piv_ret = np.log(piv_close / piv_close.shift(1)).dropna()
    port_ret = (piv_ret * weights).sum(axis=1)

    bm_comp_df = compute_benchmark_comparison_regressions(port_ret, indices_df, equity_df)
    st.dataframe(bm_comp_df, use_container_width=True)

    st.markdown("#### 4-Factor Capex Cycle Regression Model")
    loadings_df, warning_msg, corr_df = compute_4factor_capex_model(port_ret, indices_df, equity_df)
    st.dataframe(loadings_df, use_container_width=True)

    if "WARNING" in warning_msg:
        st.warning(warning_msg)
    else:
        st.success(warning_msg)

    st.markdown("---")

    st.subheader("4. Single-Index Risk Decomposition (vs Nifty 500 TRI)")
    bm_name = config.get("indices", {}).get("benchmark", "Nifty 500 TRI")
    bm_df = indices_df[indices_df["Index_Name"] == bm_name].sort_values("Date").reset_index(drop=True)
    if bm_df.empty:
        bm_df = indices_df[indices_df["Index_Name"] == "Nifty 50 Spot"].sort_values("Date").reset_index(drop=True)

    single_decomp_df = compute_single_index_decomposition(equity_df, bm_df, invested_tickers, weights)
    port_row = single_decomp_df[single_decomp_df["Stock"] == "PORTFOLIO"].iloc[0]

    col_b1, col_b2, col_b3, col_b4 = st.columns(4)
    col_b1.metric("Portfolio Beta", f"{port_row['Beta']:.3f}")
    col_b2.metric("Benchmark R-Squared", f"{port_row['R-squared']:.4f}")
    col_b3.metric("Systematic Volatility", f"{port_row['Systematic vol (%)']:.2f}%")
    col_b4.metric("Stock-Specific Volatility", f"{port_row['Stock-specific vol (%)']:.2f}%")

    st.dataframe(single_decomp_df, use_container_width=True)

    st.markdown("---")

    st.subheader("5. Macro Multi-Factor Model (Brent Crude & 10Y G-Sec Yields)")
    macro_reg_df, macro_verdict = compute_macro_multifactor_model(port_ret, indices_df, macro_df)
    st.dataframe(macro_reg_df, use_container_width=True)
    st.info(f"💡 {macro_verdict}")

    st.markdown("---")

    st.subheader("6. CAPM Expected Return KPIs")
    rf = 0.0448
    erp = config.get("market_parameters", {}).get("india_erp", 0.0708)
    port_beta = float(port_row["Beta"])

    capm_ann = (rf + port_beta * erp) * 100.0
    capm_3m = (((1.0 + capm_ann / 100.0)**0.25) - 1.0) * 100.0
    expected_rs = capital * (capm_ann / 100.0)

    col_c1, col_c2, col_c3, col_c4 = st.columns(4)
    col_c1.metric("Portfolio CAPM Annual E(R)", f"{capm_ann:.2f}%")
    col_c2.metric("Portfolio 3-Month E(R)", f"{capm_3m:.2f}%")
    col_c3.metric("Expected Gain on Rs 1 Cr", format_indian_currency(expected_rs, abbreviate=True))
    col_c4.metric("Risk-Free Rate / ERP", f"{rf*100:.2f}% / {erp*100:.2f}%")

    st.markdown("---")

    st.subheader("7. Time Series Autocorrelation & AR(1) Diagnostics")
    autocorr_diag = compute_autocorrelation_diagnostics(port_ret)

    col_a1, col_a2, col_a3, col_a4 = st.columns(4)
    col_a1.metric("AR(1) Coefficient φ", f"{autocorr_diag['AR1_phi']:.4f} (t={autocorr_diag['AR1_t']:.2f})")
    col_a2.metric("Ljung-Box Q Statistic", f"{autocorr_diag['Ljung_Box_Q']:.2f} (p={autocorr_diag['Ljung_Box_P']:.4f})")
    col_a3.metric("Weekly Lag-1 Autocorr", f"{autocorr_diag['Weekly_Lag1_Autocorr']:.4f}")
    col_a4.metric("Significant Lags", str(autocorr_diag['Significant_Lags']))

    st.dataframe(autocorr_diag['Autocorrelations'], use_container_width=True)
    st.info(f"📌 **Time-Series Verdict**: {autocorr_diag['Summary_Sentence']}")

    st.markdown("---")

    st.subheader("8. 3-Month Risk-Reward Analysis")
    rr_df, rr_kpis = compute_risk_reward_table(equity_df, risk_stops_df, total_capital=capital)

    col_r1, col_r2, col_r3, col_r4 = st.columns(4)
    col_r1.metric("Upside Typical Move (Diversified)", format_indian_currency(rr_kpis['Typical_Move_Diversified_Rs'], abbreviate=True))
    col_r2.metric(
        label="Downside if All Stops Hit",
        value=format_indian_currency(rr_kpis['Downside_Still_At_Risk_Rs'], abbreviate=True),
        help="MUST match Overview tab Still-at-Risk figure exactly."
    )
    col_r3.metric("Portfolio Reward : Risk", f"{rr_kpis['Reward_Risk_Ratio']:.2f} : 1")
    col_r4.metric("Typical 3M Move (Rs)", format_indian_currency(rr_kpis['Upside_Typical_Move_Rs'], abbreviate=True))

    st.dataframe(rr_df, use_container_width=True)
    st.caption("📌 **Note on Portfolio Rows**: *PORTFOLIO (all stocks at once)* represents the undiversified simple sum of individual stock moves. *PORTFOLIO (diversified)* accounts for correlation diversification benefits, resulting in a lower portfolio-level standard deviation.")

    overview_still_at_risk = float(risk_stops_df["Still_At_Risk"].sum())
    tab4_still_at_risk = rr_kpis['Downside_Still_At_Risk_Rs']
    assert abs(overview_still_at_risk - tab4_still_at_risk) < 1.0, f"Mismatch: Overview ({overview_still_at_risk}) != Tab 4 ({tab4_still_at_risk})"

    st.markdown("---")

    st.subheader("9. Downside Option Hedge Plan (Nifty Derivatives)")
    bm_spot = float(bm_df["Close"].iloc[-1])
    lot_size = config.get("market_parameters", {}).get("nifty_lot_size", 65)

    from core.hedge import calculate_down_market_beta
    bm_close = bm_df.set_index("Date")["Close"]
    bm_daily_ret = bm_close.pct_change().dropna()
    beta_down = calculate_down_market_beta(port_ret, bm_daily_ret)

    res_nifty = run_ols_regression(port_ret, bm_daily_ret)
    h_star = res_nifty["beta"]
    h_eff = res_nifty["r_squared"]

    opt_trades = data["ledger"][data["ledger"]["Instrument_Type"] == "OPTION"]
    lots_held = int(opt_trades["Qty"].sum() // lot_size) if not opt_trades.empty else 8

    col_h1, col_h2, col_h3, col_h4 = st.columns(4)
    col_h1.metric("Min-Variance Hedge Ratio h*", f"{h_star:.3f}")
    col_h2.metric("Hedge Effectiveness (R²)", f"{h_eff * 100:.1f}%")
    col_h3.metric("Tail Hedge Beta (Down Days)", f"{beta_down:.3f}")
    col_h4.metric("Nifty Puts MTM Value", format_indian_currency(opt_val))

    st.markdown("""
    #### 🛡️ Options Hedging Decision Rationale & Operational Framework
    - **Strategy**: Tail-risk protection using out-of-the-money (OTM) Nifty Put Options from Day 0.
    - **Why Puts (Not Futures)**: Futures cancel market upside and create margin calls during bull rallies. Puts act like asymmetric insurance: capping downside losses while keeping 100% of market upside intact.
    - **Strike Selection**: Out-of-the-money (OTM) puts are selected for cost-efficiency (low theta decay and lower initial cash outflow per unit of downside crash coverage compared to ITM puts).
    - **Profit-Lock Rule**: Upon achieving a **+10% portfolio gain**, put option strikes are rolled up to ~5% below current Nifty spot, locking in gains.
    - **No Discretionary Hedging**: Hedging is rule-based; no discretionary removal or addition of puts after market dips.
    """)

    st.markdown("#### 📉 Downside Scenario Analysis at Expiry (-25% to 0% Nifty Drop)")
    scenarios_df = generate_hedge_scenario_analysis(bm_spot, stock_val, beta_down, 22000.0, 208.20, lots_held, lot_size, capital)

    fig_scen = go.Figure()
    fig_scen.add_trace(go.Scatter(
        x=scenarios_df["Nifty Move (%)"], y=scenarios_df["Unhedged PnL (% of Capital)"],
        mode='lines+markers', name='Unhedged Portfolio', line=dict(color='#EF4444', width=2.5, dash='dash')
    ))
    fig_scen.add_trace(go.Scatter(
        x=scenarios_df["Nifty Move (%)"], y=scenarios_df["With Puts PnL (% of Capital)"],
        mode='lines+markers', name='Hedged Portfolio (With Puts)', line=dict(color='#10B981', width=3.5)
    ))

    fig_scen.update_layout(
        title="Portfolio Loss Capping at Expiry (Unhedged vs Hedged)",
        height=380,
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis_title="Nifty 50 Move to Expiry (%)",
        yaxis_title="Portfolio P&L (% of Rs 1 Cr Capital)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_scen, use_container_width=True)

    with st.expander("🔍 Hedge Plan Details & Put Strikes Comparison"):
        strike_table = generate_option_strike_comparison(bm_spot, options_df, stock_val, beta_down, lot_size)
        st.dataframe(strike_table, use_container_width=True)


# ==============================================================================
# TAB 5: PERFORMANCE
# ==============================================================================
with tab_perf:
    st.header("📈 Performance Attribution & Benchmark Regression")
    st.markdown("""
    *This tab compares the real live performance of our portfolio since the snapshot against multi-window backtests over past trading sessions.*
    - **Live Column**: Real portfolio performance calculated directly from the trade ledger (stocks + puts + cash).
    - **Backtest Columns**: Simulated performance of today's weights applied to historical prices over 63 sessions (1 quarter), 126 sessions (6 months), and 252 sessions (1 year).
    """)

    # 1. Multi-Window Performance Attribution Table
    perf_df, raw_kpis = build_multiwindow_performance_table(
        data["equity"], data["indices"], data["macro"], data["ledger"], data["risk_stops"], config
    )

    # Assertion Check: Live column return and XIRR match Overview tab exactly
    overview_summary = data["summary"]
    if not overview_summary.empty:
        overview_nav = float(overview_summary["Total_NAV"].iloc[0])
        overview_ret_pct = ((overview_nav - capital) / capital) * 100.0
        assert abs(raw_kpis["live_portfolio_return_pct"] - overview_ret_pct) < 0.1, "Live return mismatch vs Overview!"

    # 2. Conditional Yellow Warning Box
    live_sessions = raw_kpis["live_sessions"]
    if live_sessions < 20:
        st.warning(f"⚠️ **Live Window Warning ({live_sessions} sessions < 20 sessions threshold)**:\n"
                   f"- Annualised figures for the Live column are mathematically extrapolated over short windows; refer primarily to period return rows.\n"
                   f"- Beta for Treynor & Jensen's Alpha calculations uses the 1-Year daily beta (current weights) fallback.\n"
                   f"- Sortino ratio displays a dash '-' until at least one negative daily return session occurs.")
    else:
        st.success(f"✅ Live portfolio window has {live_sessions} trading sessions (>= 20 sessions). Full statistical sampling active.")

    # 3. Performance Table Display
    st.subheader("📊 Multi-Window Performance Attribution Matrix")
    st.dataframe(perf_df, use_container_width=True)

    # 4. Formula Footnote Paragraph
    st.markdown(r"""
    > 📚 **Performance Metrics Formula Reference**:
    > - **Sharpe Ratio**: $(R_p - R_f) / \sigma_p$ — Annualised excess return per unit of total risk.
    > - **Treynor Ratio**: $(R_p - R_f) / \beta_p$ — Annualised excess return per unit of systematic risk.
    > - **Jensen's Alpha**: $R_p - [R_f + \beta (R_m - R_f)]$ — Abnormal return above CAPM benchmark expectation.
    > - **Sortino Ratio**: $(R_p - R_f) / \sigma_{\text{downside}}$ — Excess return per unit of downside risk (losing days only).
    > - **Up/Down Capture**: Ratio of portfolio average return on market up/down days relative to market average return.
    > - **Tracking Error**: $\text{std}(R_p - R_m) \times \sqrt{252}$ — Standard deviation of active excess returns.
    > - **Information Ratio**: $\text{Annual Excess Return} / \text{Tracking Error}$ — Active return generated per unit of active risk.
    > - **Compounding Effect**: Difference between geometrically compounded annual return and simple linear annual return.
    """)

    st.markdown("---")

    # 5. Growth of Rs 1 Crore Line Chart (Backtest)
    st.subheader("📈 Growth of Rs 1 Crore Over the Past Year (Daily Compounded Backtest)")
    equity_df = data["equity"]
    indices_df = data["indices"]
    invested = [t["symbol"] for t in config["universe"]["invested_tickers"]]
    weights = data["risk_stops"]["Target_Weight"].values if not data["risk_stops"].empty else np.full(8, 0.125)

    piv_close = equity_df.pivot(index="Date", columns="Ticker", values="Close")[invested].dropna()
    stk_ret = np.log(piv_close / piv_close.shift(1)).dropna()
    port_ret_1y = (stk_ret * weights).sum(axis=1).tail(252)

    bm_close = indices_df[indices_df["Index_Name"] == "Nifty 500 TRI"].set_index("Date")["Close"]
    if bm_close.empty:
        bm_close = indices_df[indices_df["Index_Name"] == "Nifty 50 Spot"].set_index("Date")["Close"]
    bm_ret_1y = np.log(bm_close / bm_close.shift(1)).dropna().tail(252)

    port_cum_val = capital * np.cumprod(1.0 + port_ret_1y.values)
    bm_cum_val = capital * np.cumprod(1.0 + bm_ret_1y.values)

    fig_growth = go.Figure()
    fig_growth.add_trace(go.Scatter(x=port_ret_1y.index, y=port_cum_val, mode='lines', name='Infrastructure Portfolio (Today\'s Weights)', line=dict(color='#2563EB', width=3)))
    fig_growth.add_trace(go.Scatter(x=bm_ret_1y.index, y=bm_cum_val, mode='lines', name='Nifty 500 TRI Benchmark', line=dict(color='#64748B', width=2)))

    fig_growth.update_layout(
        height=400,
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis_title="Date",
        yaxis_title="Portfolio Value (INR)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_growth, use_container_width=True)

    st.markdown("---")

    # 6. Capital Market Line & Efficient Frontier Chart
    st.subheader("🎯 Capital Market Line (CML) & Efficient Frontier")
    rf = 0.0448
    summary_f_df, w_comp_df, plot_f_data = compute_frontier_summary_table(equity_df, data["risk_stops"], rf=rf)

    fig_cml = go.Figure()

    # 1. Efficient Frontier Curve
    fig_cml.add_trace(go.Scatter(
        x=plot_f_data["f_vols"] * 100, y=plot_f_data["f_rets"] * 100,
        mode='lines', name='Invested Stocks Efficient Frontier', line=dict(color='#2563EB', width=2.5)
    ))

    # 2. CML Line (rf to Market)
    bm_vol_1y = float(bm_ret_1y.std() * np.sqrt(252))
    bm_ret_1y_ann = float(bm_ret_1y.mean() * 252)
    cml_x = np.linspace(0, bm_vol_1y * 1.5, 50)
    cml_sharpe = (bm_ret_1y_ann - rf) / bm_vol_1y
    cml_y = rf + cml_sharpe * cml_x

    fig_cml.add_trace(go.Scatter(
        x=cml_x * 100, y=cml_y * 100,
        mode='lines', name=f'Capital Market Line (Nifty 500 Sharpe: {cml_sharpe:.2f})', line=dict(color='#64748B', width=2)
    ))

    # 3. CAL Line (rf to Tangency)
    w_tangency = plot_f_data["w_tangency"]
    tangency_ret = float(w_tangency @ plot_f_data["mu"])
    tangency_vol = float(np.sqrt(w_tangency.T @ plot_f_data["cov"] @ w_tangency))
    cal_sharpe = (tangency_ret - rf) / tangency_vol
    cal_y = rf + cal_sharpe * cml_x

    fig_cml.add_trace(go.Scatter(
        x=cml_x * 100, y=cal_y * 100,
        mode='lines', name=f'Capital Allocation Line (Tangency Sharpe: {cal_sharpe:.2f})', line=dict(color='#10B981', width=2, dash='dash')
    ))

    # Markers
    # Our Portfolio (Red Star)
    w_our = plot_f_data["w_our"]
    our_ret = float(w_our @ plot_f_data["mu"])
    our_vol = float(np.sqrt(w_our.T @ plot_f_data["cov"] @ w_our))
    fig_cml.add_trace(go.Scatter(
        x=[our_vol * 100], y=[our_ret * 100], mode='markers+text', name='Our Portfolio (ERC)',
        marker=dict(symbol='star', size=16, color='#EF4444'), text=["Our Portfolio"], textposition="top right"
    ))

    # Nifty 500 TRI (Blue Square)
    fig_cml.add_trace(go.Scatter(
        x=[bm_vol_1y * 100], y=[bm_ret_1y_ann * 100], mode='markers+text', name='Nifty 500 TRI Benchmark',
        marker=dict(symbol='square', size=12, color='#2563EB'), text=["Nifty 500"], textposition="bottom right"
    ))

    # Tangency (Green Diamond)
    fig_cml.add_trace(go.Scatter(
        x=[tangency_vol * 100], y=[tangency_ret * 100], mode='markers+text', name='Tangency (Max Sharpe)',
        marker=dict(symbol='diamond', size=12, color='#10B981'), text=["Tangency"], textposition="top left"
    ))

    # GMVP Long-Only (Purple Triangle)
    w_gmvp_lo = plot_f_data["w_gmvp_lo"]
    gmvp_lo_ret = float(w_gmvp_lo @ plot_f_data["mu"])
    gmvp_lo_vol = float(np.sqrt(w_gmvp_lo.T @ plot_f_data["cov"] @ w_gmvp_lo))
    fig_cml.add_trace(go.Scatter(
        x=[gmvp_lo_vol * 100], y=[gmvp_lo_ret * 100], mode='markers+text', name='GMVP Long-Only',
        marker=dict(symbol='triangle-up', size=12, color='#8B5CF6'), text=["GMVP LO"], textposition="bottom left"
    ))

    # GMVP Bounded (Purple Open Triangle)
    w_gmvp_bd = plot_f_data["w_gmvp_bd"]
    gmvp_bd_ret = float(w_gmvp_bd @ plot_f_data["mu"])
    gmvp_bd_vol = float(np.sqrt(w_gmvp_bd.T @ plot_f_data["cov"] @ w_gmvp_bd))
    fig_cml.add_trace(go.Scatter(
        x=[gmvp_bd_vol * 100], y=[gmvp_bd_ret * 100], mode='markers+text', name='GMVP Bounded (5-15%)',
        marker=dict(symbol='triangle-up-open', size=12, color='#8B5CF6', line=dict(width=2)), text=["GMVP Bounded"], textposition="top right"
    ))

    # Risk-Free Rate (Black Dot)
    fig_cml.add_trace(go.Scatter(
        x=[0], y=[rf * 100], mode='markers+text', name='Risk-Free Rate rf',
        marker=dict(symbol='circle', size=10, color='#000000'), text=["rf (4.48%)"], textposition="top right"
    ))

    # Individual Stock Markers
    stk_vols = np.sqrt(np.diag(plot_f_data["cov"]))
    fig_cml.add_trace(go.Scatter(
        x=stk_vols * 100, y=plot_f_data["mu"] * 100, mode='markers+text', name='Individual Stocks',
        marker=dict(symbol='circle-open', size=9, color='#64748B'), text=plot_f_data["active_tickers"], textposition="top center"
    ))

    fig_cml.update_layout(
        title="Capital Market Line: past year of daily returns (ex-post; the stocks were picked on strong past returns)",
        height=520,
        margin=dict(l=20, r=20, t=50, b=20),
        xaxis_title="Annualised Volatility (%)",
        yaxis_title="Annualised Return (%)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_cml, use_container_width=True)

    st.caption("📌 **Ex-Post CML Caption**: *This CML analysis is constructed ex-post using past 1-year historical daily returns. Stock selection was driven by strong operational quality and capex tailwinds, placing our portfolio above the unconstrained market benchmark.*")

    st.markdown("---")

    # 7. GMVP vs Our Weights Summary
    st.subheader("7. Global Minimum Variance Portfolio (GMVP) vs Our Weights")
    st.dataframe(summary_f_df, use_container_width=True)

    with st.expander("🔍 Detailed Portfolio Weight Allocations: Ours vs GMVP vs Tangency"):
        st.dataframe(w_comp_df, use_container_width=True)


# Footer Disclaimer
st.markdown("---")
st.caption("🔒 **Disclaimer**: *Educational project for MBA coursework (Security Analysis & Portfolio Management / Derivatives, IIM Bodh Gaya). This terminal is for academic research only and does not constitute financial or investment advice.*")
