import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from fredapi import Fred
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# --- Page Setup ---
st.set_page_config(page_title="Macro Stock Predictor", layout="wide")
st.title("📈 Macro-Geopolitical Stock Analyzer")

# --- API Configuration (from Streamlit Secrets) ---
# Set these up in Streamlit Cloud Dashboard under Settings > Secrets
try:
    FRED_KEY = st.secrets["fred_api_key"]
    NEWS_KEY = st.secrets["news_api_key"]
    fred = Fred(api_key=FRED_KEY)
except Exception:
    st.error("Please configure 'fred_api_key' and 'news_api_key' in Streamlit Secrets.")

# --- Logic: Sector Sensitivity ---
SECTOR_SENSITIVITY = {
    "Real Estate": 1.5,
    "Utilities": 1.5,
    "Financial Services": 1.2,
    "Technology": 1.0,
    "Consumer Defensive": 0.5,
}

# --- Sidebar: User Inputs ---
st.sidebar.header("User Input")
ticker_input = st.sidebar.text_input("Enter Stock Ticker", "AAPL").upper()
search_news = st.sidebar.button("Run Analysis")

# --- Data Fetching Functions ---
def get_stock_and_sector(symbol):
    t = yf.Ticker(symbol)
    hist = t.history(period="1y")
    sector = t.info.get('sector', 'Unknown')
    return hist, sector

def analyze_sentiment(symbol, api_key):
    analyzer = SentimentIntensityAnalyzer()
    url = f"https://newsapi.org{symbol}+geopolitical+OR+FED&apiKey={api_key}"
    response = requests.get(url).json()
    articles = response.get('articles', [])[:5]
    
    scores = []
    for art in articles:
        score = analyzer.polarity_scores(art['title'])['compound']
        scores.append(score)
    return sum(scores)/len(scores) if scores else 0

# --- Main App Execution ---
if search_news:
    col1, col2 = st.columns(2)
    
    # 1. Market Data
    hist, sector = get_stock_and_sector(ticker_input)
    with col1:
        st.subheader(f"{ticker_input} Price & Sector: {sector}")
        st.line_chart(hist['Close'])

    # 2. Interest Rates (Macro)
    try:
        rates = fred.get_series('FEDFUNDS').tail(12)
        rate_change = rates.iloc[-1] - rates.iloc[-2]
        with col2:
            st.subheader("Interest Rate Trend (Fed Funds)")
            st.line_chart(rates)
    except:
        rate_change = 0

    # 3. Sentiment & Recommendation Logic
    sentiment_score = analyze_sentiment(ticker_input, NEWS_KEY)
    
    # Calculation
    multiplier = SECTOR_SENSITIVITY.get(sector, 1.0)
    # Hikes (positive rate_change) are negative for most stocks
    macro_impact = -0.5 if rate_change > 0 else 0.5 if rate_change < 0 else 0
    final_score = sentiment_score + (macro_impact * multiplier)

    st.divider()
    st.subheader("Final AI Recommendation")
    
    if final_score > 0.3:
        st.success(f"🔥 Recommendation: BUY ({ticker_input})")
        st.write("Reason: Strong news sentiment and favorable macro conditions for this sector.")
    elif final_score < -0.3:
        st.error(f"🚨 Recommendation: SELL ({ticker_input})")
        st.write("Reason: Negative geopolitical sentiment or interest rate pressure on this sector.")
    else:
        st.warning(f"⚖️ Recommendation: HOLD ({ticker_input})")
        st.write("Reason: Neutral indicators or conflicting macro/news data.")

    st.info(f"Sentiment Score: {round(sentiment_score, 2)} | Rate Delta: {round(rate_change, 2)}")

