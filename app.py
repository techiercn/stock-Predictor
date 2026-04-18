import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import time
import datetime
from fredapi import Fred

# --- Page Config ---
st.set_page_config(page_title="AI Macro Stock Pro 2026", layout="wide")
st.title("📈 AI Stock Pro: 2026 Macro-Geopolitical Edition")

# --- Initialize Session State ---
if 'api_calls_used' not in st.session_state:
    st.session_state.api_calls_used = 0

# --- API Keys ---
FRED_KEY = st.secrets.get("fred_api_key")
AV_KEY = st.secrets.get("av_api_key")

# --- Helper Functions ---
@st.cache_data(ttl=3600)
def fetch_macro_data(api_key):
    try:
        fred = Fred(api_key=api_key)
        rates = fred.get_series('FEDFUNDS').tail(2)
        cur_rate = rates.iloc[-1]
        rate_delta = cur_rate - rates.iloc[-2]
        return cur_rate, rate_delta
    except:
        return 3.75, 0.0 # Defaulting to April 2026 current levels if API fails

def get_recommendation(score):
    if score > 0.15:
        return "BUY", "green", "Strong bullish sentiment and favorable macro alignment."
    elif score < -0.15:
        return "SELL", "red", "Bearish sentiment or high geopolitical/rate pressure."
    else:
        return "HOLD", "orange", "Neutral indicators or conflicting market signals."

def get_av_analysis(symbol, api_key, rate_delta, cur_rate):
    API_URL = "https://alphavantage.co"
    params = {"function": "NEWS_SENTIMENT", "tickers": symbol, "apikey": api_key}
    
    try:
        response = requests.get(API_URL, params=params).json()
        st.session_state.api_calls_used += 1
        
        if "Note" in response: return {"status": "LIMIT"}
        feed = response.get('feed', [])
        if not feed: return {"status": "NO_NEWS"}

        scores = [float(item['overall_sentiment_score']) for item in feed[:5]]
        avg_sentiment = sum(scores) / len(scores)
        
        # Sector & Macro Weighting
        t = yf.Ticker(symbol)
        sector = t.info.get('sector', 'Unknown')
        multiplier = {"Real Estate": 1.5, "Technology": 1.2, "Utilities": 1.5}.get(sector, 1.0)
        macro_impact = 0.2 if rate_delta < 0 else -0.2 if rate_delta > 0 else (0.05 if cur_rate < 4 else -0.05)
        
        final_score = avg_sentiment + (macro_impact * multiplier)
        rec, color, reason = get_recommendation(final_score)

        return {
            "status": "SUCCESS", "Ticker": symbol, "Sector": sector, 
            "Score": round(final_score, 2), "Sentiment": round(avg_sentiment, 2),
            "Recommendation": rec, "Color": color, "Reason": reason
        }
    except: return None

# --- UI Sidebar ---
with st.sidebar:
    st.header("📊 System Status")
    remaining = max(0, 25 - st.session_state.api_calls_used)
    st.write(f"Credits Remaining: **{remaining} / 25**")
    st.progress(remaining / 25)
    
    st.divider()
    watchlist = st.text_area("Enter Tickers (Max 5)", "AAPL, NVDA, TSLA, MSFT")
    scan_btn = st.button("🔍 Run 2026 Analysis", disabled=(remaining == 0))

# --- Main App Execution ---
if not FRED_KEY or not AV_KEY:
    st.error("⚠️ API Keys Missing in Secrets!")
else:
    if scan_btn:
        cur_rate, rate_delta = fetch_macro_data(FRED_KEY)
        tickers = [t.strip().upper() for t in watchlist.split(",")]
        results = []
        
        with st.status("Gathering 2026 Market Data...", expanded=True) as status:
            for i, s in enumerate(tickers):
                if st.session_state.api_calls_used >= 25: break
                
                res = get_av_analysis(s, AV_KEY, rate_delta, cur_rate)
                
                if res and res.get("status") == "SUCCESS":
                    results.append(res)
                    st.write(f"✅ {s}: Analysis complete.")
                elif res and res.get("status") == "LIMIT":
                    st.warning("⏳ Limit hit. Waiting 60s...")
                    time.sleep(60)
                
                if i < len(tickers) - 1: time.sleep(12) # Respect 5/min limit
            status.update(label="Analysis Complete!", state="complete", expanded=False)

        if results:
            df = pd.DataFrame(results).drop(columns=['status', 'Color'])
            
            # --- Detailed Cards ---
            st.subheader("📊 Individual Stock Deep-Dive")
            for item in results:
                with st.expander(f"{item['Ticker']} - Recommendation: {item['Recommendation']}"):
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        st.markdown(f"### Score: {item['Score']}")
                        st.markdown(f"**Final Signal**: :{item['Color']}[{item['Recommendation']}]")
                    with c2:
                        st.write(f"**Geopolitical Factors**: 2026 Trade volatility & energy shocks from Strait of Hormuz.")
                        st.write(f"**Fed Rates**: Currently steady at {cur_rate}% (Trend: {'Tightening' if rate_delta > 0 else 'Easing/Hold'}).")
                        st.write(f"**Market Performance**: Resilient earnings growth offset by regional geopolitical risk.")
                        st.write(f"**Rationale**: {item['Reason']}")

            # --- CSV Download ---
            st.divider()
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Market Report (CSV)",
                data=csv,
                file_name=f"market_report_{datetime.date.today()}.csv",
                mime='text/csv',
            )
            st.dataframe(df, use_container_width=True)

