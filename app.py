import streamlit as st
import pandas as pd
import time
import requests
from fredapi import Fred

# --- Page Config ---
st.set_page_config(page_title="Alpha Macro Predictor", layout="wide")
st.title("📈 AI Stock Pro: Alpha Vantage Edition")

# Initialize Session State for tracking API usage
if 'api_calls_used' not in st.session_state:
    st.session_state.api_calls_used = 0

# --- Sidebar: Status Monitor & Inputs ---
with st.sidebar:
    st.header("📊 API Status Monitor")
    daily_limit = 25
    remaining = max(0, daily_limit - st.session_state.api_calls_used)
    
    # Visual Progress Bar for Credits
    st.progress(remaining / daily_limit)
    st.write(f"Credits Remaining: **{remaining}** / {daily_limit}")
    
    if remaining == 0:
        st.error("Daily limit reached! Use a new key or wait 24h.")
    
    st.divider()
    st.header("Global Watchlist")
    watchlist_input = st.text_area("Tickers (Max 5 recommended)", "AAPL, NVDA, TSLA")
    threshold = st.slider("Buy Threshold", 0.05, 0.30, 0.10)
    scan_btn = st.button("🔍 Run Alpha Vantage Scan", disabled=(remaining == 0))

# --- Main Logic ---
AV_KEY = st.secrets.get("av_api_key")
FRED_KEY = st.secrets.get("fred_api_key")

def get_av_analysis(symbol, api_key):
    # This counts as 1 request
    url = f"https://alphavantage.co{symbol}&apikey={api_key}"
    try:
        r = requests.get(url).json()
        st.session_state.api_calls_used += 1  # Increment counter
        
        # Check if API returned a rate limit note
        if "Note" in r:
            st.warning(f"Rate limit hit for {symbol}. Wait 60 seconds.")
            return None
            
        # ... (Previous sentiment calculation logic) ...
        return {"Ticker": symbol, "Score": 0.15, "Sentiment": 0.2}
    except:
        return None

if scan_btn:
    tickers = [t.strip().upper() for t in watchlist_input.split(",")]
    results = []
    
    # Progress status container
    with st.status("Analyzing Market Data...") as status:
        for s in tickers:
            if st.session_state.api_calls_used >= daily_limit:
                st.error("Limit exceeded during scan.")
                break
                
            st.write(f"Fetching data for {s}...")
            res = get_av_analysis(s, AV_KEY)
            if res: results.append(res)
            
            # To respect '5 calls per minute' (1 call every 12 seconds)
            if len(tickers) > 1:
                time.sleep(12) 
        
        status.update(label="Analysis Complete!", state="complete")

    if results:
        df = pd.DataFrame(results).sort_values(by="Score", ascending=False)
        st.subheader("🏆 Opportunities Detected")
        st.dataframe(df, use_container_width=True)

