import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from fredapi import Fred
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Page Setup
st.set_page_config(page_title="Macro Stock Predictor", layout="wide")
st.title("📈 Macro-Geopolitical Stock Analyzer")

# --- FIXED API KEY HANDLING ---
# Use .get() to avoid crashing if keys are missing from secrets
FRED_KEY = st.secrets.get("fred_api_key")
NEWS_KEY = st.secrets.get("news_api_key")

if not FRED_KEY or not NEWS_KEY:
    st.warning("⚠️ API Keys missing! Add 'fred_api_key' and 'news_api_key' to Streamlit Secrets to enable full analysis.")

# --- Logic: Sector Sensitivity ---
SECTOR_SENSITIVITY = {
    "Real Estate": 1.5, "Utilities": 1.5, "Financial Services": 1.2,
    "Technology": 1.0, "Consumer Defensive": 0.5,
}

# Sidebar Input
st.sidebar.header("User Input")
ticker_input = st.sidebar.text_input("Enter Stock Ticker", "AAPL").upper()
run_btn = st.sidebar.button("Run Analysis")

def analyze_sentiment(symbol, api_key):
    if not api_key: return 0  # Return neutral if no key
    analyzer = SentimentIntensityAnalyzer()
    url = f"https://newsapi.org{symbol}+geopolitical+OR+FED&apiKey={api_key}"
    try:
        response = requests.get(url).json()
        articles = response.get('articles', [])[:5]
        scores = [analyzer.polarity_scores(a['title'])['compound'] for a in articles]
        return sum(scores)/len(scores) if scores else 0
    except:
        return 0

if run_btn:
    col1, col2 = st.columns(2)
    
    # 1. Market Data
    t = yf.Ticker(ticker_input)
    hist = t.history(period="1y")
    sector = t.info.get('sector', 'Unknown')
    
    with col1:
        st.subheader(f"{ticker_input} Performance ({sector})")
        st.line_chart(hist['Close'])

    # 2. Interest Rates
    rate_change = 0
    if FRED_KEY:
        try:
            fred = Fred(api_key=FRED_KEY)
            rates = fred.get_series('FEDFUNDS').tail(12)
            rate_change = rates.iloc[-1] - rates.iloc[-2]
            with col2:
                st.subheader("Interest Rate Trend")
                st.line_chart(rates)
        except: st.info("Could not fetch FRED data.")

    # 3. Sentiment & Recommendation
    sentiment_score = analyze_sentiment(ticker_input, NEWS_KEY)
    multiplier = SECTOR_SENSITIVITY.get(sector, 1.0)
    macro_impact = -0.5 if rate_change > 0 else 0.5 if rate_change < 0 else 0
    final_score = sentiment_score + (macro_impact * multiplier)

    st.divider()
    st.subheader("Final AI Recommendation")
    if final_score > 0.3: st.success(f"🔥 BUY ({ticker_input})")
    elif final_score < -0.3: st.error(f"🚨 SELL ({ticker_input})")
    else: st.warning(f"⚖️ HOLD ({ticker_input})")

