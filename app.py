import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from fredapi import Fred
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# --- Page Config ---
st.set_page_config(page_title="Macro Pro: NewsAPI Version", layout="wide")
st.title("📈 AI Stock Pro: NewsAPI Edition")

# --- API Keys from Secrets ---
FRED_KEY = st.secrets.get("fred_api_key")
NEWS_KEY = st.secrets.get("news_api_key")

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

@st.cache_data(ttl=1800)
def get_stock_analysis(symbol, api_key, rate_delta, cur_rate):
    try:
        t = yf.Ticker(symbol)
        sector = t.info.get('sector', 'Unknown')
        
        # Sentiment Analysis via NewsAPI.org
        analyzer = SentimentIntensityAnalyzer()
        url = f"https://newsapi.org{symbol}&apiKey={api_key}&language=en&pageSize=5"
        
        r = requests.get(url).json()
        if r.get("status") == "error":
            st.sidebar.error(f"NewsAPI Error: {r.get('message')}")
            return None
            
        articles = r.get('articles', [])
        sentiment = sum([analyzer.polarity_scores(a['title'])['compound'] for a in articles])/len(articles) if articles else 0
        
        # Scoring Logic
        multiplier = {"Real Estate": 1.5, "Utilities": 1.5, "Technology": 1.2}.get(sector, 1.0)
        macro_impact = 0.2 if rate_delta < 0 else -0.2 if rate_delta > 0 else (0.05 if cur_rate < 4 else -0.05)
        
        final_score = sentiment + (macro_impact * multiplier)
        return {"Ticker": symbol, "Sector": sector, "Score": round(final_score, 2), "Sentiment": round(sentiment, 2)}
    except: return None

# --- UI Sidebar ---
st.sidebar.header("Global Watchlist")
watchlist_input = st.sidebar.text_area("Tickers to Scan", "AAPL, NVDA, TSLA, MSFT")
threshold = st.sidebar.slider("Buy Threshold", 0.05, 0.30, 0.10)
scan_btn = st.sidebar.button("🔍 Run NewsAPI Scan")

if scan_btn:
    if not FRED_KEY or not NEWS_KEY:
        st.error("Missing API Keys! Check your Streamlit Secrets.")
    else:
        cur_rate, rate_delta = fetch_macro_data(FRED_KEY)
        tickers = [t.strip().upper() for t in watchlist_input.split(",")]
        results = []
        progress = st.progress(0)

        for i, s in enumerate(tickers):
            res = get_stock_analysis(s, NEWS_KEY, rate_delta, cur_rate)
            if res: results.append(res)
            progress.progress((i + 1) / len(tickers))

        if results:
            df = pd.DataFrame(results).sort_values(by="Score", ascending=False)
            st.subheader("🏆 Opportunities Detected")
            st.dataframe(df, use_container_width=True)
        else:
            st.error("Scan failed. NewsAPI might be blocking the cloud request (Error 426).")

