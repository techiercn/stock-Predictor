import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from fredapi import Fred

# --- Page Config ---
st.set_page_config(page_title="Macro Pro: Alpha Vantage", layout="wide")
st.title("📈 AI Stock Pro: Alpha Vantage & Macro Edition")

# --- API Keys ---
FRED_KEY = st.secrets.get("fred_api_key")
AV_KEY = st.secrets.get("av_api_key")

# --- Cached Macro Data (FRED) ---
@st.cache_data(ttl=3600)
def fetch_macro_data(api_key):
    if not api_key: return 0.0, 0.0
    try:
        fred = Fred(api_key=api_key)
        rates = fred.get_series('FEDFUNDS').tail(2)
        cur_rate = rates.iloc[-1]
        rate_delta = cur_rate - rates.iloc[-2]
        return cur_rate, rate_delta
    except: return 0.0, 0.0

# --- Cached Stock Analysis (Alpha Vantage) ---
@st.cache_data(ttl=3600)
def get_av_analysis(symbol, api_key, rate_delta, cur_rate):
    try:
        # Sector Info via yfinance
        t = yf.Ticker(symbol)
        sector = t.info.get('sector', 'Unknown')
        
        # Alpha Vantage News Sentiment API
        # Documentation: https://www.alphavantage.co/documentation/#news-sentiment
        url = f"https://alphavantage.co{symbol}&apikey={api_key}"
        r = requests.get(url).json()
        
        # AV returns a list of feed items with overall sentiment
        feed = r.get('feed', [])
        if not feed:
            return {"Ticker": symbol, "Sector": sector, "Score": 0.0, "Sentiment": 0.0, "Details": "No news found"}

        # Calculate average sentiment score from feed
        sentiment_scores = [float(item['overall_sentiment_score']) for item in feed[:5]]
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
        
        # Macro weighting
        multiplier = {"Real Estate": 1.5, "Utilities": 1.5, "Technology": 1.2}.get(sector, 1.0)
        macro_impact = 0.2 if rate_delta < 0 else -0.2 if rate_delta > 0 else (0.05 if cur_rate < 4 else -0.05)
        
        final_score = avg_sentiment + (macro_impact * multiplier)
        return {"Ticker": symbol, "Sector": sector, "Score": round(final_score, 2), "Sentiment": round(avg_sentiment, 2)}
    except Exception as e:
        return None

# --- UI Sidebar ---
st.sidebar.header("Global Watchlist")
watchlist_input = st.sidebar.text_area("Tickers (Max 5 recommended for Free Tier)", "AAPL, NVDA, TSLA, MSFT")
threshold = st.sidebar.slider("Buy Threshold", 0.05, 0.30, 0.10)
scan_btn = st.sidebar.button("🔍 Run Alpha Vantage Scan")

# --- Main App Execution ---
if not FRED_KEY or not AV_KEY:
    st.error("Missing API Keys! Add 'fred_api_key' and 'av_api_key' to your Streamlit Secrets.")
else:
    cur_rate, rate_delta = fetch_macro_data(FRED_KEY)

    if scan_btn:
        tickers = [t.strip().upper() for t in watchlist_input.split(",")]
        results = []
        progress = st.progress(0)

        for i, s in enumerate(tickers):
            res = get_av_analysis(s, AV_KEY, rate_delta, cur_rate)
            if res: results.append(res)
            progress.progress((i + 1) / len(tickers))

        if results:
            df = pd.DataFrame(results).sort_values(by="Score", ascending=False)
            st.subheader("🏆 Opportunities Detected")
            st.dataframe(df, use_container_width=True)
            
            top_buys = df[df['Score'] >= threshold]
            if not top_buys.empty:
                st.success(f"Found {len(top_buys)} stock(s) above your threshold!")
        else:
            st.error("Scan failed. You may have exceeded your 25 daily requests or 5 per minute limit.")

