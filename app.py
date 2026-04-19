import streamlit as st
import pandas as pd
import requests
import datetime
import time
import plotly.express as px

# --- Page Config ---
st.set_page_config(page_title="2026 Macro Stock Pro", layout="wide")
st.title("📈 AI Stock Pro: 2026 Macro-Adjusted Edition")

# --- Initialize Session State ---
if 'results_data' not in st.session_state:
    st.session_state.results_data = {}

AV_API_KEY = st.secrets.get("av_api_key")

# --- Logic Functions ---
def get_av_sentiment(ticker, api_key):
    url = "https://alphavantage.co"
    params = {"function": "NEWS_SENTIMENT", "tickers": ticker, "apikey": api_key, "limit": 5}
    try:
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        if "Information" in data or "Note" in data:
            return None, "API Limit/Notice reached."
        feed = data.get("feed", [])
        if not feed: return 0.0, "No news found."
        
        scores = [float(s.get("ticker_sentiment_score", 0)) 
                  for art in feed for s in art.get("ticker_sentiment", []) 
                  if s.get("ticker") == ticker]
        return (sum(scores) / len(scores)), "Success" if scores else (0.0, "No ticker sentiment.")
    except:
        return None, "Connection Error."

def analyze_ticker(ticker, user_fed_rate, geo_penalty):
    """Calculates weighted score based on user-adjusted macro factors."""
    sentiment, status = get_av_sentiment(ticker, AV_API_KEY)
    
    if sentiment is not None:
        # Rate Penalty: Subtract 0.02 for every 0.25% above a 'neutral' 3.5%
        rate_penalty = (user_fed_rate - 3.50) * 0.08
        
        # Final Score: Sentiment - Rate Impact - Geopolitical Impact
        final_score = sentiment - rate_penalty - geo_penalty
        
        if final_score > 0.15: rec, color = "BUY", "green"
        elif final_score < -0.15: rec, color = "SELL", "red"
        else: rec, color = "HOLD", "orange"
        
        st.session_state.results_data[ticker] = {
            "Score": round(final_score, 2), "Sentiment": round(sentiment, 2),
            "Recommendation": rec, "Color": color, "Status": status
        }
    else:
        st.session_state.results_data[ticker] = {"Status": status}

# --- Sidebar Controls ---
with st.sidebar:
    st.header("⚙️ Macro Controls")
    
    # 1. Fed Funds Rate Slider
    st.subheader("🏦 Federal Funds Rate")
    # Current April 2026 baseline is 3.64%
    fed_rate = st.slider("Target Rate (%)", 0.0, 10.0, 3.64, 0.25)
    
    # 2. Geopolitical Risk Select
    st.subheader("🌍 Geopolitical Indicators")
    risks = st.multiselect(
        "Active Risk Factors",
        ["Strait of Hormuz Closure", "NATO-Russia Escalation", "US-China Trade War", "Global Cybersecurity Surge"],
        default=["Strait of Hormuz Closure"]
    )
    
    # Calculate penalty: -0.10 for each major risk factor
    geo_penalty = len(risks) * 0.10
    
    st.divider()
    watchlist = st.text_area("Tickers", "AAPL, NVDA, TSLA")
    if st.button("🔍 Run Full Analysis"):
        st.session_state.results_data = {}
        tickers = [t.strip().upper() for t in watchlist.split(",")]
        for i, t in enumerate(tickers):
            analyze_ticker(t, fed_rate, geo_penalty)
            if i < len(tickers) - 1: time.sleep(12) # AV Rate Limit
        st.rerun()

# --- Display UI ---
if st.session_state.results_data:
    df = pd.DataFrame.from_dict(st.session_state.results_data, orient='index').reset_index()
    df.rename(columns={'index': 'Ticker'}, inplace=True)
    
    valid_df = df[df['Status'] == "Success"]
    if not valid_df.empty:
        st.subheader(f"📊 Global Portfolio Risk (Fed: {fed_rate}% | Risks: {len(risks)})")
        st.plotly_chart(px.bar(valid_df, x='Ticker', y='Score', color='Recommendation',
                               color_discrete_map={'BUY': '#2ecc71', 'HOLD': '#f1c40f', 'SELL': '#e74c3c'}))

    for ticker, info in st.session_state.results_data.items():
        with st.expander(f"{ticker} — {info.get('Recommendation', 'ERROR')}"):
            if info['Status'] == "Success":
                st.metric("Adjusted Score", info['Score'], delta=info['Sentiment'], delta_description="News Sentiment")
                st.caption(f"Penalties Applied: Rate ({round((fed_rate-3.5)*0.08, 2)}) | Geopolitics ({geo_penalty})")
            else:
                st.error(info['Status'])

