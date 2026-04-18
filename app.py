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
    # 1. Fetch macro data FIRST so variables exist
    cur_rate, rate_delta = fetch_macro_data(FRED_KEY)
    
    # 2. Proceed with scanning loop
    tickers = [t.strip().upper() for t in watchlist_input.split(",")]
    results = []
    
    for s in tickers:
        # Now rate_delta and cur_rate are defined!
        res = get_av_analysis(s, AV_KEY, rate_delta, cur_rate)
        if res:
            results.append(res)

            else:
                st.error(f"❌ {s}: API limit hit or connection failed.")
            
            # Critical: Wait 12s between stocks to avoid the 5-per-minute limit
            if len(tickers) > 1:
                time.sleep(12) 
        
        status.update(label="Analysis Complete!", state="complete", expanded=False)

    # Display the final results table
    if results:
        st.subheader("🏆 Opportunities Detected")
        df = pd.DataFrame(results).sort_values(by="Score", ascending=False)
        st.dataframe(df, use_container_width=True)
    else:
        # This tells you why the table is missing
        st.info("ℹ️ No stocks could be analyzed. Check the warnings in the sidebar/status box.")

