import streamlit as st
import pandas as pd
import requests
import datetime
import time
import plotly.express as px

# --- Page Config ---
st.set_page_config(page_title="2026 Macro Stock Pro", layout="wide")
st.title("📈 AI Stock Pro: 2026 Alpha Vantage Edition")

# --- Initialize Session State ---
if 'results_data' not in st.session_state:
    st.session_state.results_data = {}
if 'daily_calls' not in st.session_state:
    st.session_state.daily_calls = 0

AV_API_KEY = st.secrets.get("av_api_key")

# --- Logic Functions ---
def get_av_sentiment(ticker, api_key):
    """Fetches sentiment with safety checks for empty responses."""
    url = "https://www.alphavantage.co/query"
    params = {"function": "NEWS_SENTIMENT", "tickers": ticker, "apikey": api_key, "limit": 5}
    
    try:
        response = requests.get(url, params=params, timeout=15)
        st.session_state.daily_calls += 1
        
        # 1. CHECK FOR EMPTY RESPONSE (Fixes 'char 0' error)
        if not response.text or response.text.strip() == "":
            return None, "Empty response: Likely 5-per-minute limit triggered."

        if response.status_code != 200:
            return None, f"HTTP {response.status_code}: {response.reason}"

        # 2. CHECK FOR NON-JSON (Fixes parsing crashes)
        try:
            data = response.json()
        except:
            return None, "Server sent non-JSON data: Check daily 25-call limit."

        if "Information" in data or "Note" in data:
            return None, f"API Notice: {data.get('Information') or data.get('Note')}"

        feed = data.get("feed", [])
        if not feed: return 0.0, "No news found."

        ticker_scores = [float(s.get("ticker_sentiment_score", 0)) 
                        for art in feed for s in art.get("ticker_sentiment", []) 
                        if s.get("ticker") == ticker]
        
        return (sum(ticker_scores) / len(ticker_scores)), "Success" if ticker_scores else (0.0, "No ticker sentiment.")
        
    except Exception as e:
        return None, f"System Error: {str(e)}"

# --- Sidebar ---
with st.sidebar:
    st.header("📊 Controls")
    st.write(f"**Calls Today:** {st.session_state.daily_calls} / 25")
    watchlist = st.text_area("Enter Tickers", "AAPL, NVDA, TSLA")
    scan_btn = st.button("🔍 Run Full Analysis")
    countdown_placeholder = st.empty()

# --- Execution ---
if scan_btn:
    tickers = [t.strip().upper() for t in watchlist.split(",")]
    st.session_state.results_data = {}
    with st.status("Analyzing Market Intelligence...") as status:
        for i, t in enumerate(tickers):
            sentiment, msg = get_av_sentiment(t, AV_API_KEY)
            # 2026 Macro: Fed Rate 3.64% gives a +0.05 tailwind
            if sentiment is not None:
                final = round(sentiment + 0.05, 2)
                rec = "BUY" if final > 0.15 else ("SELL" if final < -0.15 else "HOLD")
                st.session_state.results_data[t] = {"Score": final, "Status": msg, "Rec": rec}
            else:
                st.session_state.results_data[t] = {"Status": msg, "Rec": "ERROR"}
            
            # Forced Delay to respect 5-per-minute limit
            if i < len(tickers) - 1:
                for rem in range(12, 0, -1):
                    countdown_placeholder.metric("Next Scan In...", f"{rem}s")
                    time.sleep(1)
        status.update(label="Complete!", state="complete")
    st.rerun()

# --- Display ---
if st.session_state.results_data:
    for t, info in st.session_state.results_data.items():
        with st.expander(f"{t} — {info['Rec']}"):
            if info['Status'] == "Success":
                st.metric("Final Score", info['Score'])
            else:
                st.error(info['Status'])

