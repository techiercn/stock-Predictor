import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import time
from fredapi import Fred

# --- Page Config ---
st.set_page_config(page_title="Alpha Macro Predictor", layout="wide")
st.title("📈 AI Stock Pro: Alpha Vantage Edition")

# --- Initialize Session State ---
if 'api_calls_used' not in st.session_state:
    st.session_state.api_calls_used = 0

# --- API Keys from Secrets ---
FRED_KEY = st.secrets.get("fred_api_key")
AV_KEY = st.secrets.get("av_api_key")

# --- Functions ---
@st.cache_data(ttl=3600)
def fetch_macro_data(api_key):
    """Fetches Fed Interest Rates. Returns (current_rate, change)."""
    try:
        fred = Fred(api_key=api_key)
        rates = fred.get_series('FEDFUNDS').tail(2)
        cur_rate = rates.iloc[-1]
        rate_delta = cur_rate - rates.iloc[-2]
        return cur_rate, rate_delta
    except Exception:
        return 0.0, 0.0  # Fallback to prevent NameError

def get_av_analysis(symbol, api_key, rate_delta, cur_rate):
    """Calls Alpha Vantage and calculates score."""
    url = f"https://alphavantage.co{symbol}&apikey={api_key}"
    try:
        response = requests.get(url).json()
        st.session_state.api_calls_used += 1
        
        if "Note" in response:
            return "LIMIT_HIT"
            
        feed = response.get('feed', [])
        if not feed:
            return "NO_NEWS"

        # Average first 5 headlines
        scores = [float(item['overall_sentiment_score']) for item in feed[:5]]
        avg_sentiment = sum(scores) / len(scores)
        
        # Sector weighting logic
        t = yf.Ticker(symbol)
        sector = t.info.get('sector', 'Unknown')
        multiplier = {"Real Estate": 1.5, "Technology": 1.2, "Utilities": 1.5}.get(sector, 1.0)
        
        # Macro weighting
        macro_impact = 0.2 if rate_delta < 0 else -0.2 if rate_delta > 0 else (0.05 if cur_rate < 4 else -0.05)
        
        final_score = avg_sentiment + (macro_impact * multiplier)
        return {"Ticker": symbol, "Sector": sector, "Score": round(final_score, 2), "Sentiment": round(avg_sentiment, 2)}
    except:
        return None

# --- UI Sidebar ---
with st.sidebar:
    st.header("📊 API Status")
    daily_limit = 25
    remaining = max(0, daily_limit - st.session_state.api_calls_used)
    st.write(f"Credits Remaining: **{remaining} / {daily_limit}**")
    st.progress(remaining / daily_limit)
    
    st.divider()
    watchlist_input = st.text_area("Watchlist (Max 5 Recommended)", "AAPL, NVDA, TSLA")
    threshold = st.slider("Buy Threshold", 0.05, 0.30, 0.10)
    scan_btn = st.button("🔍 Run Full Scan", disabled=(remaining == 0))

# --- Execution ---
if not FRED_KEY or not AV_KEY:
    st.error("⚠️ API Keys Missing! Please add 'fred_api_key' and 'av_api_key' to Streamlit Secrets.")
else:
    if scan_btn:
        # Step 1: Pre-fetch macro data
        cur_rate, rate_delta = fetch_macro_data(FRED_KEY)
        
        tickers = [t.strip().upper() for t in watchlist_input.split(",")]
        results = []
        
        with st.status("Analyzing Market Data (Throttled for Free Tier)...", expanded=True) as status:
            for i, s in enumerate(tickers):
                if st.session_state.api_calls_used >= daily_limit:
                    st.error(f"🛑 Daily limit hit. Stopping at {s}.")
                    break
                
                res = get_av_analysis(s, AV_KEY, rate_delta, cur_rate)
                
                if res == "LIMIT_HIT":
                    st.warning(f"⏳ Rate limit hit on {s}. Waiting 60s...")
                    time.sleep(60) # Wait a full minute if we hit the "5 per minute" block
                elif res == "NO_NEWS":
                    st.write(f"ℹ️ {s}: No recent news found.")
                elif res:
                    results.append(res)
                    st.write(f"✅ {s} analyzed.")
                
                # Throttle to stay under 5 requests per minute
                if i < len(tickers) - 1:
                    time.sleep(12) 
            
            status.update(label="Analysis Complete!", state="complete", expanded=False)

        if results:
            df = pd.DataFrame(results).sort_values(by="Score", ascending=False)
            st.subheader("🏆 Opportunities Detected")
            st.dataframe(df, use_container_width=True)
            
            top_buys = df[df['Score'] >= threshold]
            if not top_buys.empty:
                st.balloons()
                st.success(f"Recommended Picks: {', '.join(top_buys['Ticker'].tolist())}")
        else:
            st.info("No stocks could be scored. Check API limits or ticker symbols.")

