import streamlit as st
import pandas as pd
import requests
import time
from fredapi import Fred

# --- Initialize Session State to Store Results ---
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None

st.title("📈 AI Stock Pro: Resilient 2026 Analyzer")

# --- Fetch API Keys ---
AV_KEY = st.secrets.get("av_api_key")
FRED_KEY = st.secrets.get("fred_api_key")

# --- Execution Logic ---
with st.sidebar:
    watchlist = st.text_area("Tickers", "AAPL, NVDA, TSLA")
    run_scan = st.button("🔍 Run Full Analysis")

if run_scan:
    # (Existing Logic to fetch FRED cur_rate/rate_delta)
    # We use a fallback if FRED fails (current April 2026 rate is ~3.64%)
    cur_rate, rate_delta = 3.64, 0.0 
    
    tickers = [t.strip().upper() for t in watchlist.split(",")]
    temp_results = []
    
    with st.status("Analyzing Data...") as status:
        for symbol in tickers:
            url = f"https://alphavantage.co{symbol}&apikey={AV_KEY}"
            data = requests.get(url).json()
            
            if "feed" in data and data["feed"]:
                # Process score and recommendation...
                temp_results.append({"Ticker": symbol, "Score": 0.25, "Recommendation": "BUY"})
            time.sleep(12) # Stay under 5 calls per minute limit
        status.update(label="Complete!", state="complete")
    
    # SAVE to session state so it survives the download rerun
    st.session_state.analysis_results = temp_results

# --- ALWAYS RENDER IF DATA EXISTS ---
if st.session_state.analysis_results:
    df = pd.DataFrame(st.session_state.analysis_results)
    st.subheader("📊 Final Analysis Report")
    st.dataframe(df, use_container_width=True)
    
    # Export Button is now outside the "if run_scan" block
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download CSV Report",
        data=csv,
        file_name="market_report.csv",
        mime='text/csv'
    )

