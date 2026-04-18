import streamlit as st
import yfinance as yf
from fredapi import Fred
import pandas as pd

# Page Configuration
st.set_page_config(page_title="Stock Macro-Predictor", layout="wide")
st.title("📊 AI Stock Predictor & Macro Analyzer")

# Securely retrieve API Keys from Streamlit Secrets
# Setup these in the Streamlit Cloud Dashboard under 'Settings' > 'Secrets'
try:
    FRED_API_KEY = st.secrets["fred_api_key"]
    fred = Fred(api_key=FRED_API_KEY)
except Exception:
    st.error("Missing FRED_API_KEY in Secrets. Please add it to run macro analysis.")

# --- SIDEBAR: User Input ---
st.sidebar.header("Manual Entry")
user_input = st.sidebar.text_input("Enter Ticker Symbols (comma separated)", "AAPL, NVDA, TSLA")
tickers = [t.strip().upper() for t in user_input.split(",")]

# --- MAIN DASHBOARD ---
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Real-Time Market Performance")
    if tickers:
        # Fetching data using yfinance
        data = yf.download(tickers, period="1mo", interval="1d")['Close']
        st.line_chart(data)
    else:
        st.warning("Please enter at least one ticker symbol.")

with col2:
    st.subheader("Macro Indicators: Interest Rates")
    try:
        # 'FEDFUNDS' is the Effective Federal Funds Rate series from FRED
        rates_series = fred.get_series('FEDFUNDS')
        st.line_chart(rates_series.tail(24), use_container_width=True)
        st.caption("Federal Funds Effective Rate (Monthly)")
    except NameError:
        st.info("Interest rate data unavailable without a valid API key.")

# --- GEOPOLITICAL & NEWS ANALYSIS (Conceptual) ---
st.divider()
st.subheader("Geopolitical Event Tracking")
st.write("Current Focus: Monitoring global market fluctuations and trade news.")
# Tip: Integrate NewsAPI here to fetch real-time headlines for the entered tickers.

