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
if 'quota_info' not in st.session_state:
    st.session_state.quota_info = {"limit_daily": 25} # AV Free Tier Limit

# --- API Keys ---
AV_API_KEY = st.secrets.get("av_api_key")

# --- Logic Functions ---
def get_av_sentiment(ticker, api_key):
    """Fetches specialized financial sentiment from Alpha Vantage."""
    url = "https://alphavantage.co"
    params = {
        "function": "NEWS_SENTIMENT",
        "tickers": ticker,
        "apikey": api_key,
        "limit": 5 # Limit articles to save processing
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        data = response.json()

        # Handle API Error messages (Rate limits/Invalid keys)
        if "Information" in data or "Note" in data:
            return None, data.get("Information") or data.get("Note")

        feed = data.get("feed", [])
        if not feed:
            return 0.0, "No recent financial news found."

        # Extract ticker-specific sentiment score
        ticker_scores = []
        for article in feed:
            for sentiment_data in article.get("ticker_sentiment", []):
                if sentiment_data.get("ticker") == ticker:
                    ticker_scores.append(float(sentiment_data.get("ticker_sentiment_score", 0)))
        
        avg_score = sum(ticker_scores) / len(ticker_scores) if ticker_scores else 0.0
        return avg_score, "Success"
        
    except Exception as e:
        return None, f"Connection Error: {str(e)}"

def analyze_ticker(ticker):
    """Processes ticker with 2026 Macro context."""
    cur_rate = 3.64 # Fed Rate for April 2026
    sentiment, status = get_av_sentiment(ticker, AV_API_KEY)
    
    if sentiment is not None:
        final_score = sentiment + (0.05 if cur_rate < 4.0 else -0.05)
        if final_score > 0.15: rec, color = "BUY", "green"
        elif final_score < -0.15: rec, color = "SELL", "red"
        else: rec, color = "HOLD", "orange"
        
        st.session_state.results_data[ticker] = {
            "Score": round(final_score, 2), "Sentiment": round(sentiment, 2),
            "Recommendation": rec, "Color": color, "Status": status
        }
    else:
        st.session_state.results_data[ticker] = {"Status": status}

# --- Sidebar ---
with st.sidebar:
    st.header("📊 Control Center")
    st.info("Note: Alpha Vantage Free Tier allows 25 requests/day.")
    watchlist_input = st.text_area("Enter Tickers", "AAPL, NVDA, TSLA, SCHD")
    
    if st.button("🔍 Run Full Analysis"):
        st.session_state.results_data = {}
        tickers = [t.strip().upper() for t in watchlist_input.split(",")]
        for t in tickers:
            analyze_ticker(t)
            time.sleep(12) # 5 requests per minute limit

# --- Main App Execution ---
if not AV_API_KEY:
    st.warning("⚠️ Alpha Vantage API Key missing! Add 'av_api_key' to Secrets.")
    st.stop()

if st.session_state.results_data:
    df = pd.DataFrame.from_dict(st.session_state.results_data, orient='index').reset_index()
    df.rename(columns={'index': 'Ticker'}, inplace=True)
    
    valid_df = df[df['Status'] == "Success"]
    if not valid_df.empty:
        st.subheader("📊 Sentiment vs 2026 Macro Baseline")
        fig = px.bar(valid_df, x='Ticker', y='Score', color='Recommendation',
                     color_discrete_map={'BUY': '#2ecc71', 'HOLD': '#f1c40f', 'SELL': '#e74c3c'})
        st.plotly_chart(fig, use_container_width=True)

    for ticker, info in st.session_state.results_data.items():
        with st.expander(f"{ticker} — {info.get('Recommendation', 'FAILED')}"):
            if info['Status'] == "Success":
                st.metric("Weighted Score", info['Score'], delta=info['Sentiment'])
                st.write(f"**Signal**: :{info['Color']}[{info['Recommendation']}]")
            else:
                st.error(f"Error: {info['Status']}")
                if st.button(f"🔄 Retry {ticker}", key=f"retry_{ticker}"):
                    analyze_ticker(ticker)
                    st.rerun()
else:
    st.info("👈 Enter tickers in the sidebar and run analysis.")

