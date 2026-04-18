import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from fredapi import Fred
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# --- Page Setup ---
st.set_page_config(page_title="Macro Predictor Pro", layout="wide")
st.title("📈 AI Macro-Geopolitical Stock Analyzer")

# --- API Keys ---
FRED_KEY = st.secrets.get("fred_api_key")
NEWS_KEY = st.secrets.get("news_api_key")

if not FRED_KEY or not NEWS_KEY:
    st.warning("⚠️ Add 'fred_api_key' and 'news_api_key' to Streamlit Secrets to enable full analysis.")

# --- Sector Sensitivity Settings ---
SECTOR_SENSITIVITY = {
    "Real Estate": 1.5, "Utilities": 1.5, "Financial Services": 1.2,
    "Technology": 1.0, "Consumer Defensive": 0.5,
}

# --- Sidebar ---
st.sidebar.header("Stock Analysis Settings")
ticker_input = st.sidebar.text_input("Enter Ticker", "AAPL").upper()
# Sensitivty slider lets you manually adjust how "aggressive" the AI is
user_threshold = st.sidebar.slider("AI Signal Sensitivity", 0.05, 0.30, 0.10)
run_btn = st.sidebar.button("Generate Recommendation")

def analyze_sentiment(symbol, api_key):
    if not api_key: return 0
    analyzer = SentimentIntensityAnalyzer()
    # Broaden search to ensure we find articles
    url = f"https://newsapi.org{symbol}+(stock+OR+market+OR+fed)&apiKey={api_key}"
    try:
        r = requests.get(url).json()
        articles = r.get('articles', [])[:10] # Use more articles for better average
        if not articles: return 0
        scores = [analyzer.polarity_scores(a['title'])['compound'] for a in articles]
        return sum(scores)/len(scores)
    except: return 0

if run_btn:
    col1, col2 = st.columns(2)
    
    # 1. Market & Sector Data
    t = yf.Ticker(ticker_input)
    hist = t.history(period="1y")
    sector = t.info.get('sector', 'Unknown')
    
    with col1:
        st.subheader(f"{ticker_input} Performance ({sector})")
        st.line_chart(hist['Close'])

    # 2. Macro Indicators (FRED)
    rate_change = 0
    current_rate = 0
    if FRED_KEY:
        try:
            fred = Fred(api_key=FRED_KEY)
            rates = fred.get_series('FEDFUNDS').tail(12)
            current_rate = rates.iloc[-1]
            rate_change = current_rate - rates.iloc[-2]
            with col2:
                st.subheader("Interest Rate Trend")
                st.line_chart(rates)
        except: st.info("Could not fetch macro data.")

    # 3. Enhanced Recommendation Logic
    sentiment_score = analyze_sentiment(ticker_input, NEWS_KEY)
    multiplier = SECTOR_SENSITIVITY.get(sector, 1.0)
    
    # Macro Logic: If rates are steady (delta=0), we look at absolute levels
    # Rates < 4% are generally accommodative; > 4% are restrictive
    if rate_change != 0:
        macro_impact = 0.2 if rate_change < 0 else -0.2
    else:
        macro_impact = 0.05 if current_rate < 4.0 else -0.05
    
    final_score = sentiment_score + (macro_impact * multiplier)

    # Display Recommendation
    st.divider()
    st.subheader("AI Trading Signal")
    
    if final_score >= user_threshold:
        st.success(f"🔥 RECOMMENDATION: BUY ({ticker_input})")
        st.write(f"**Rationale**: High sentiment ({round(sentiment_score, 2)}) and favorable macro environment.")
    elif final_score <= -user_threshold:
        st.error(f"🚨 RECOMMENDATION: SELL ({ticker_input})")
        st.write(f"**Rationale**: Negative sentiment or macro-pressure detected for {sector}.")
    else:
        st.warning(f"⚖️ RECOMMENDATION: HOLD ({ticker_input})")
        st.write("Reason: Indicators are currently neutral or contradictory.")

    # Technical Details
    with st.expander("View Data Details"):
        st.write(f"Raw Sentiment Score: {round(sentiment_score, 4)}")
        st.write(f"Current Interest Rate: {current_rate}%")
        st.write(f"Sector Multiplier: {multiplier}x")

