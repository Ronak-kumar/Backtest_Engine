import streamlit as st
import pandas as pd
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor
import plotly.express as px

# --- Configuration & Data ---
INDEX_URLS = {
    "Nifty 50": "https://archives.nseindia.com/content/indices/ind_nifty50list.csv",
    "Nifty Midcap 150": "https://archives.nseindia.com/content/indices/ind_niftymidcap150list.csv",
    "Nifty 500": "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
}


@st.cache_data
def get_index_constituents(index_name):
    df = pd.read_csv(INDEX_URLS[index_name])
    for col in ['Industry', 'Sectors', 'Sector']:
        if col in df.columns:
            df = df.rename(columns={col: 'Sector'})
            break
    return df


def fetch_stock_data(symbol):
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        info = ticker.info
        return {
            "Symbol": symbol,
            "Industry_YF": info.get('industry', 'Other'),
            "Price": info.get('currentPrice'),
            "PE": info.get('trailingPE'),
            "ROE": info.get('returnOnEquity'),
            "D/E": info.get('debtToEquity'),
            "CurrentRatio": info.get('currentRatio'),
            "Cash": info.get('totalCash', 0) / 1e7,
            "MarketCap": info.get('marketCap', 0) / 1e7
        }
    except Exception:
        return None


# --- UI Setup ---
st.set_page_config(layout="wide", page_title="Quant Audit Terminal", page_icon="⚖️")

# Styling for a "Trading Terminal" feel
st.markdown("""
    <style>
    .stMetric { background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 15px; }
    div[data-testid="stExpander"] { border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

st.title("⚖️ Institutional Fundamental Audit Terminal")

with st.sidebar:
    st.header("Screener Controls")
    universe = st.selectbox("Market Universe", list(INDEX_URLS.keys()))
    constituents = get_index_constituents(universe)

    available_sectors = ["All"] + sorted(constituents['Sector'].unique().tolist())
    selected_sector = st.selectbox("Sector Filter", available_sectors)

    run_btn = st.button("⚡ ANALYZE SELECTED", use_container_width=True)

if "master_df" not in st.session_state:
    st.session_state.master_df = None

# --- Execution Gate ---
if run_btn:
    # THE LOGIC GATE: Filter symbols BEFORE API calls
    if selected_sector != "All":
        targets = constituents[constituents['Sector'] == selected_sector]['Symbol'].tolist()
    else:
        targets = constituents['Symbol'].tolist()

    with st.spinner(f"Auditing {len(targets)} Balance Sheets..."):
        with ThreadPoolExecutor(max_workers=20) as executor:
            results = list(executor.map(fetch_stock_data, targets))

        df = pd.DataFrame([r for r in results if r is not None])

        # Clean numeric data to prevent Rank Errors
        for col in ['PE', 'ROE', 'D/E', 'CurrentRatio']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        df = df.dropna(subset=['PE', 'ROE'])

        # Scoring Logic (Multi-Factor)
        df['Score'] = (df['ROE'].rank(pct=True) * 50) + (df['PE'].rank(pct=True, ascending=False) * 50)
        st.session_state.master_df = df.sort_values('Score', ascending=False)

# --- Analysis Display ---
if st.session_state.master_df is not None:
    mdf = st.session_state.master_df

    # SAFETY CHECK: Only proceed if we actually have data
    if not mdf.empty:
        # Metric Dashboard
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Top Pick", mdf.iloc[0]['Symbol'])
        m2.metric("Universe Median P/E", f"{mdf['PE'].median():.1f}")
        m3.metric("Avg ROE", f"{(mdf['ROE'].mean() * 100):.1f}%")
        m4.metric("Stocks Scanned", len(mdf))

        st.divider()

        # THE DEEP AUDIT CARD
        st.subheader("🎯 Stock Audit Deep-Dive")
        selected_stock = st.selectbox("Select Symbol for Audit", mdf['Symbol'].unique())

        if selected_stock:
            # Fetch Full Balance Sheet for the specific stock
            with st.spinner(f"Downloading Full Balance Sheet for {selected_stock}..."):
                ticker_obj = yf.Ticker(f"{selected_stock}.NS")
                full_bs = ticker_obj.quarterly_balance_sheet
                sdata = mdf[mdf['Symbol'] == selected_stock].iloc[0]

            # 1. --- Visual Metrics Row ---
            st.markdown(f"### 📊 Financial Audit: {selected_stock}")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Market Cap", f"₹{sdata['MarketCap']:.1f} Cr")
            c2.metric("P/E Ratio", f"{sdata['PE']:.2f}")
            c3.metric("ROE", f"{(sdata['ROE'] * 100):.2f}%")
            c4.metric("D/E Ratio", f"{(sdata['D/E'] / 100):.2f}")

            # 2. --- Color-Coded Balance Sheet ---
            st.subheader("📑 Raw Balance Sheet (Quarterly)")


            def color_bs_values(val):
                """Logic: Large positive cash/assets = Green, Large liabilities/debt = Red"""
                try:
                    if val > 1e8: return 'color: #00ff00;'  # Significant Positive (Green)
                    if val < 0: return 'color: #ff4b4b;'  # Negative/Debt (Red)
                except:
                    pass
                return ''  # Neutral (Blank/White)


            if not full_bs.empty:
                # Displaying the last 4 quarters
                st.dataframe(full_bs.style.applymap(color_bs_values), use_container_width=True)
            else:
                st.error("Could not retrieve detailed Balance Sheet rows for this symbol.")

            # 3. --- Automated Pros & Cons Summary ---
            st.divider()
            st.subheader("📝 Fundamental Audit Summary")

            # Benchmarks
            roe_pct = (sdata['ROE'] or 0) * 100
            de_ratio = (sdata['D/E'] or 0) / 100
            cr_ratio = sdata['CurrentRatio'] or 0

            col_pro, col_con = st.columns(2)

            with col_pro:
                st.markdown("#### ✅ PROS (Strengths)")
                pros = []
                if de_ratio < 0.5: pros.append(
                    f"**Debt Mastery:** Very low leverage ({de_ratio:.2f}). Safe for long-term holding.")
                if roe_pct > 20: pros.append(f"**High Efficiency:** ROE of {roe_pct:.1f}% shows strong management.")
                if cr_ratio > 1.5: pros.append(
                    f"**Liquidity King:** Current ratio of {cr_ratio:.2f} ensures short-term safety.")
                if sdata['Cash'] > (sdata['MarketCap'] * 0.05): pros.append(
                    f"**Cash Rich:** Cash reserves are >5% of Market Cap.")

                if pros:
                    for p in pros: st.success(p)
                else:
                    st.write("No significant fundamental strengths detected.")

            with col_con:
                st.markdown("#### ❌ CONS (Risks)")
                cons = []
                if de_ratio > 1.5: cons.append(
                    f"**High Leverage:** Debt is {de_ratio:.2f}x Equity. High interest risk.")
                if sdata['PE'] > 60: cons.append(f"**Valuation Trap:** P/E of {sdata['PE']:.1f} is very expensive.")
                if roe_pct < 10: cons.append(f"**Efficiency Drain:** ROE below 10% is sub-par for the sector.")
                if cr_ratio < 1.0: cons.append(f"**Liquidity Crunch:** Current Ratio < 1.0. High risk of default.")

                if cons:
                    for c in cons: st.error(c)
                else:
                    st.write("No major fundamental red flags detected.")

            # Leaderboard Table at the bottom
        with st.expander("📂 View Full Scanned Leaderboard"):
            st.dataframe(
                mdf[['Symbol', 'Industry_YF', 'Price', 'PE', 'ROE', 'Score']].style.background_gradient(cmap='RdYlGn',
                                                                                                        subset=[
                                                                                                            'Score']))

        # Leaderboard Table
        # with st.expander("📂 View Full Scanned Data"):
        #     st.dataframe(
        #         mdf[['Symbol', 'Industry_YF', 'Price', 'PE', 'ROE', 'Score']].style.background_gradient(cmap='RdYlGn',
        #                                                                                                 subset=[
        #                                                                                                     'Score']))

    else:
        # If no data was found for the selection
        st.warning(
            "No valid data found for the selected Sector/Index. This can happen if the API is restricted or the sector name is mismatched.")